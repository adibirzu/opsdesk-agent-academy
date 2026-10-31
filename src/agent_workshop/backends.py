"""Explicit, bounded backend adapters; no implicit acceptance claims."""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import io
import json
import re
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import HTTPBasicAuthHandler, HTTPPasswordMgrWithDefaultRealm, Request, build_opener, HTTPRedirectHandler

from .config import Config, endpoint, secret

_TRACE = re.compile(r"^[0-9a-fA-F]{32}$")
_SESSION = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _oci_auth(config: Config):
    import oci
    auth = config.oci.get("auth_type", "API_KEY")
    if auth == "API_KEY":
        return oci.config.from_file(profile_name=config.oci.get("profile", "DEFAULT"))
    if auth == "INSTANCE_PRINCIPAL":
        return oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    if auth == "RESOURCE_PRINCIPAL":
        return oci.auth.signers.get_resource_principals_signer()
    if auth == "OKE_WORKLOAD_IDENTITY":
        from .auth import oke_signer
        return oke_signer()
    raise ValueError("unsupported OCI auth type")


def _clients(config: Config) -> dict[str, Any]:
    import oci
    auth_type = config.oci.get("auth_type", "API_KEY")
    auth = _oci_auth(config)
    base = dict(auth) if auth_type == "API_KEY" else {}
    base["region"] = config.oci["region"]
    kwargs = {"timeout": (5, 10), "retry_strategy": oci.retry.NoneRetryStrategy()}
    la = oci.log_analytics.LogAnalyticsClient(base, **kwargs) if auth_type == "API_KEY" else oci.log_analytics.LogAnalyticsClient(base, signer=auth, **kwargs)
    monitoring = oci.monitoring.MonitoringClient(base, **kwargs) if auth_type == "API_KEY" else oci.monitoring.MonitoringClient(base, signer=auth, **kwargs)
    monitoring_ingestion_endpoint = oci.regions.endpoint_for("monitoring", config.oci["region"]).replace("://telemetry.", "://telemetry-ingestion.", 1)
    ingestion_kwargs = {**kwargs, "service_endpoint": monitoring_ingestion_endpoint}
    monitoring_ingestion = (oci.monitoring.MonitoringClient(base, **ingestion_kwargs) if auth_type == "API_KEY"
                             else oci.monitoring.MonitoringClient(base, signer=auth, **ingestion_kwargs))
    apm_cfg = dict(base); apm_cfg["region"] = config.oci.get("apm_region", config.oci["region"])
    apm = oci.apm_traces.QueryClient(apm_cfg, **kwargs) if auth_type == "API_KEY" else oci.apm_traces.QueryClient(apm_cfg, signer=auth, **kwargs)
    return {"log_analytics": la, "monitoring": monitoring, "monitoring_ingestion": monitoring_ingestion, "apm": apm}


def _safe_error(exc: Exception) -> str:
    return type(exc).__name__.lower().replace("error", "") + " failure"


def _rows(data: Any) -> list[dict[str, Any]]:
    try:
        import oci
        value = oci.util.to_dict(data)
    except Exception:
        value = data
    if isinstance(value, dict):
        value = value.get("query_result_rows", value.get("rows", value.get("items", value.get("data", []))))
    if not isinstance(value, list): return []
    rows = []
    for row in value:
        if not isinstance(row, dict):
            row = getattr(row, "__dict__", {})
        # APM QueryResultRow stores the useful columns in this nested map.
        if isinstance(row, dict) and isinstance(row.get("query_result_row_data"), dict):
            row = row["query_result_row_data"]
        rows.append(row if isinstance(row, dict) else {})
    return rows


def _require_config(config: Config) -> None:
    needed = ("region", "compartment_id", "log_namespace", "log_group_id")
    if any(not config.oci.get(k) for k in needed):
        raise ValueError("OCI backend configuration incomplete")


def publish_events(config: Config, event_path: str | Path, *, clients: dict[str, Any] | None = None, max_bytes: int = 1_000_000) -> dict[str, Any]:
    _require_config(config)
    path = Path(event_path)
    if path.is_symlink() or not path.is_file(): raise ValueError("event file must be a regular file")
    if path.stat().st_size > max_bytes: raise ValueError("event file exceeds bounded size")
    body = path.read_bytes()
    try:
        records = []
        for raw_line in body.splitlines():
            if not raw_line.strip():
                continue
            event = json.loads(raw_line)
            if not isinstance(event, dict):
                raise ValueError("event lines must be JSON objects")
            stamp = event.get("time")
            try:
                when = datetime.fromisoformat(str(stamp).replace("Z", "+00:00")) if stamp else datetime.now(timezone.utc)
            except ValueError:
                when = datetime.now(timezone.utc)
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            log_record = {
                "timeUnixNano": str(int(when.timestamp() * 1_000_000_000)),
                "body": {"stringValue": raw_line.decode("utf-8")},
                "attributes": [
                    {"key": "session.id", "value": {"stringValue": str(event.get("session.id", event.get("session_id", ""))) }},
                    {"key": "run_id", "value": {"stringValue": str(event.get("run_id", ""))}},
                    {"key": "service.name", "value": {"stringValue": str(event.get("service.name", config.telemetry.get("service_name", "agent-workshop")))}}
                ],
            }
            trace_id = str(event.get("trace_id", ""))
            span_id = str(event.get("span_id", ""))
            if re.fullmatch(r"[0-9a-fA-F]{32}", trace_id): log_record["traceId"] = trace_id
            if re.fullmatch(r"[0-9a-fA-F]{16}", span_id): log_record["spanId"] = span_id
            records.append(log_record)
        payload = json.dumps({"resourceLogs": [{"resource": {"attributes": [{"key": "service.name", "value": {"stringValue": config.telemetry.get("service_name", "agent-workshop")}}]}, "scopeLogs": [{"scope": {"name": "agent_workshop"}, "logRecords": records}]}]}).encode()
        client = (clients or _clients(config))["log_analytics"]
        # The SDK accepts raw JSON bytes. A BytesIO stream with application/json
        # is sent through its model serializer and raises TypeError before I/O.
        result = client.upload_otlp_logs(config.oci["log_namespace"], config.oci["log_group_id"], payload, content_type="application/json")
        return {"status": "accepted", "backend_verified": False, "provider": "log_analytics", "response_available": bool(result)}
    except Exception as exc:
        return {"status": "failed", "backend_verified": False, "error": _safe_error(exc)}


def publish_metrics(config: Config, counts: dict[str, int], *, clients: dict[str, Any] | None = None) -> dict[str, Any]:
    _require_config(config)
    if not isinstance(counts, dict) or any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in counts.values()):
        raise ValueError("metric counts must be non-negative integers")
    try:
        details = []
        for service, value in counts.items():
            if not isinstance(service, str) or not service or len(service) > 64: raise ValueError("invalid service dimension")
            import oci
            metric_cls = getattr(oci.monitoring.models, "MetricDataDetails", oci.monitoring.models.MetricData)
            details.append(metric_cls(compartment_id=config.oci["compartment_id"], namespace="agent_workshop", name="workshop_" + service, dimensions={"service.name": config.telemetry.get("service_name", "agent-workshop")}, datapoints=[oci.monitoring.models.Datapoint(timestamp=datetime.now(timezone.utc), value=value)]))
        configured_clients = clients or _clients(config)
        client = configured_clients.get("monitoring_ingestion", configured_clients["monitoring"])
        import oci
        response = client.post_metric_data(oci.monitoring.models.PostMetricDataDetails(metric_data=details, batch_atomicity="NON_ATOMIC"))
        response_data = getattr(response, "data", response)
        failed = (response_data.get("failed_metrics_count", 0) if isinstance(response_data, dict)
                  else getattr(response_data, "failed_metrics_count", 0)) or 0
        if failed:
            return {"status": "failed", "backend_verified": False, "provider": "monitoring", "failed_metrics": int(failed)}
        return {"status": "accepted", "backend_verified": False, "provider": "monitoring", "metric_count": len(details)}
    except ValueError: raise
    except Exception as exc:
        return {"status": "failed", "backend_verified": False, "error": _safe_error(exc)}


def _langfuse(config: Config, trace_id: str, session_id: str, *, http_get=None, deadline_seconds=60) -> dict[str, Any]:
    endpoint_url = config.telemetry.get("langfuse_endpoint")
    pub_name, sec_name = config.telemetry.get("langfuse_public_key_env"), config.telemetry.get("langfuse_secret_key_env")
    if not endpoint_url or not pub_name or not sec_name: return {"status": "unconfigured", "records": []}
    end = datetime.now(timezone.utc)
    url = endpoint(endpoint_url, local=True, allowed_hosts=config.telemetry.get("allowed_hosts", [])) + "/api/public/v2/observations?" + urlencode({
        "traceId": trace_id, "sessionId": session_id, "limit": 100, "fields": "core,basic,model,usage",
        "fromStartTime": (end - timedelta(minutes=30)).isoformat(), "toStartTime": end.isoformat()})
    auth = base64.b64encode((secret(pub_name) + ":" + secret(sec_name)).encode()).decode()
    getter = http_get or (lambda req: build_opener(_NoRedirect()).open(req, timeout=10).read(256000))
    raw = getter(Request(url, headers={"Authorization": "Basic " + auth, "Accept": "application/json"}))
    data = json.loads(raw)
    records = data.get("data", data.get("observations", []))
    records = [r for r in records if r.get("traceId") == trace_id and r.get("sessionId") == session_id and (str(r.get("type", "")).lower() == "generation") and (r.get("model") or r.get("modelName"))]
    return {"status": "verified" if records else "not_found", "records": records}


def _apm(config: Config, trace_id: str, session_id: str, *, clients=None, deadline_seconds=60) -> dict[str, Any]:
    if not config.oci.get("apm_domain_id"): return {"status": "unconfigured", "records": []}
    try:
        import oci
        client = (clients or _clients(config))["apm"]
        end = datetime.now(timezone.utc); start = end - timedelta(minutes=30)
        query = "show (spans) traceId, spanId, operationName where traceId = '" + trace_id + "'"
        details = oci.apm_traces.models.QueryDetails(query_text=query)
        response = client.query(config.oci["apm_domain_id"], start, end, query_details=details)
        rows = _rows(getattr(response, "data", response))
        return {"status": "verified" if rows else "not_found", "records": rows}
    except Exception as exc:
        return {"status": "failed", "error": _safe_error(exc), "records": []}


def _logan(config: Config, trace_id: str, session_id: str, *, clients=None, deadline_seconds=60) -> dict[str, Any]:
    if not all(config.oci.get(k) for k in ("log_namespace", "compartment_id")): return {"status": "unconfigured", "matched_records": 0}
    try:
        import oci
        client = (clients or _clients(config))["log_analytics"]
        end = datetime.now(timezone.utc); start = end - timedelta(minutes=30)
        details = oci.log_analytics.models.QueryDetails(compartment_id=config.oci["compartment_id"], query_string="'" + trace_id + "' and '" + session_id + "' | stats count as matched_records", sub_system="LOG", time_filter=oci.log_analytics.models.TimeRange(time_start=start, time_end=end), should_run_async=False)
        response = client.query(config.oci["log_namespace"], details)
        rows = _rows(getattr(response, "data", response))
        count = 0
        if rows and isinstance(rows[0], dict): count = int(rows[0].get("matched_records", 0) or 0)
        return {"status": "verified" if count > 0 else "not_found", "matched_records": count}
    except Exception as exc:
        return {"status": "failed", "error": _safe_error(exc), "matched_records": 0}


def verify_metrics(config: Config, *, clients=None, deadline_seconds=60) -> dict[str, Any]:
    """Read back one workshop metric without conflating it with trace proof."""
    if not all(config.oci.get(k) for k in ("region", "compartment_id")):
        return {"status": "unconfigured", "metric_count": 0}
    try:
        import oci
        service = config.telemetry.get("service_name", "agent-workshop")
        end = datetime.now(timezone.utc)
        start = end - timedelta(minutes=30)
        query = 'workshop_runs[1m]{service.name = "' + service.replace('"', '') + '"}.sum()'
        details = oci.monitoring.models.SummarizeMetricsDataDetails(namespace="agent_workshop", query=query,
                                                                       start_time=start, end_time=end)
        configured_clients = clients or _clients(config)
        client = configured_clients.get("monitoring", configured_clients.get("monitoring_ingestion"))
        response = client.summarize_metrics_data(config.oci["compartment_id"], details)
        data = getattr(response, "data", response)
        rows = data if isinstance(data, list) else getattr(data, "items", [])
        count = len(rows) if isinstance(rows, list) else 0
        return {"status": "verified" if count else "not_found", "metric_count": count,
                "namespace": "agent_workshop", "metric": "workshop_runs", "service": service}
    except Exception as exc:
        return {"status": "failed", "error": _safe_error(exc), "metric_count": 0}


def verify(config: Config, trace_id: str, session_id: str, deadline_seconds: int = 60, *, providers: dict[str, Any] | None = None) -> dict[str, Any]:
    if not _TRACE.fullmatch(trace_id) or int(trace_id, 16) == 0: raise ValueError("trace_id must be nonzero hex32")
    if not _SESSION.fullmatch(session_id): raise ValueError("invalid session_id")
    if isinstance(deadline_seconds, bool) or not 1 <= deadline_seconds <= 120: raise ValueError("deadline must be 1..120 seconds")
    providers = providers or {}
    results = {}
    deadline = time.monotonic() + deadline_seconds
    names = ("langfuse", "apm", "logan")
    functions = {}
    for name in names:
        functions[name] = providers.get(name) or {"langfuse": _langfuse, "apm": _apm, "logan": _logan}[name]
    for name in names:
        try:
            fn = functions[name]
            if fn is None:
                results[name] = {"status": "unconfigured", "records": []}
            else:
                result = fn(config=config, trace_id=trace_id, session_id=session_id, deadline_seconds=deadline_seconds)
                results[name] = result
        except Exception as exc:
            results[name] = {"status": "failed", "error": _safe_error(exc), "records": []}
    # Ingestion is eventually consistent. Poll all providers round-robin so a
    # slow/missing backend cannot starve the others; backoff is bounded by 3s
    # and the caller's absolute deadline.
    delay = 0.25
    while any(results.get(name, {}).get("status") in {"pending", "not_found"} for name in names) and time.monotonic() < deadline:
        time.sleep(min(delay, max(0.0, deadline - time.monotonic())))
        for name in names:
            if results.get(name, {}).get("status") not in {"pending", "not_found"} or time.monotonic() >= deadline:
                continue
            try:
                results[name] = functions[name](config=config, trace_id=trace_id, session_id=session_id,
                                                deadline_seconds=max(1, int(deadline - time.monotonic())))
            except Exception as exc:
                results[name] = {"status": "failed", "error": _safe_error(exc), "records": []}
        delay = min(delay * 2, 3.0)
    lf = results["langfuse"].get("records", [])
    apm = results["apm"].get("records", [])
    logan = results["logan"].get("matched_records", 0)
    exact_lf = any(r.get("traceId") == trace_id and r.get("sessionId") == session_id and str(r.get("type", "")).lower() == "generation" and (r.get("model") or r.get("modelName")) for r in lf)
    exact_apm = any(r.get("traceId") == trace_id for r in apm)
    summary = {}
    for name, result in results.items():
        item = {"status": result.get("status", "unknown")}
        if "records" in result:
            item["record_count"] = len(result["records"]) if isinstance(result["records"], list) else 0
        if "matched_records" in result:
            item["matched_records"] = result["matched_records"]
        if "error" in result:
            item["error"] = result["error"]
        summary[name] = item
    return {"backend_verified": bool(exact_lf and exact_apm and isinstance(logan, int) and logan > 0), "providers": summary, "trace_id": trace_id, "session_id": session_id}
