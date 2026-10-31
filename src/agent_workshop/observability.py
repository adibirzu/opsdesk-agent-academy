"""One OTel provider, correlated JSON events, optional explicit backend exporters."""
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import base64
import json
import os
import re
import time
import uuid
from .config import endpoint, secret

_ids = ContextVar("workshop_ids", default={})
_trace = ContextVar("workshop_trace", default="")
_span = ContextVar("workshop_span", default="")


def mask(value):
    if isinstance(value, dict):
        return {k: "[REDACTED]" if re.sub(r"[^a-z]", "", str(k).lower()) in
                {"secret", "password", "authorization", "apikey", "credential", "tokenvalue", "token"} else mask(v)
                for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [mask(v) for v in value]
    if isinstance(value, str):
        if value.lstrip().startswith(("{", "[")):
            try: return json.dumps(mask(json.loads(value)))
            except (ValueError, TypeError): pass
        value = re.sub(r"ocid1\.[A-Za-z0-9._-]+", "[REDACTED_ID]", value)
        value = re.sub(r"(?i)(?:bearer\s+|sk-)[A-Za-z0-9._-]{8,}", "[REDACTED]", value)
        value = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[REDACTED_EMAIL]", value)
        value = re.sub(r"(?i)\b(password|token|secret|api_key)\s*[=:]\s*[^\s,;]+", r"\1=[REDACTED]", value)
        return value[:8000]
    return value


class _LocalSpan:
    def __init__(self):
        self.attributes = {}

    def set_attribute(self, name, value):
        self.attributes[name] = value

    def set_status(self, status):
        self.attributes["otel.status_code"] = getattr(status, "status_code", status)


class Observer:
    def __init__(self, settings=None, event_path=None, stream=None, *, provider=None):
        self.settings = settings or {}
        self.capture_content = bool(self.settings.get("capture_content", False))
        self.path = Path(event_path).expanduser() if event_path else None
        self.stream = stream
        self.provider = None
        self._exporter_names = []
        self.export_errors = []
        self.counts = {"runs": 0, "errors": 0, "events": 0, "policy_blocks": 0}
        if self.path:
            if self.path.is_symlink():
                raise ValueError("Event path must not be a symlink")
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            fd = os.open(self.path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
            os.close(fd)
            os.chmod(self.path, 0o600)
        if provider is not None:
            self.provider = provider
            self.tracer = provider.get_tracer("agent-workshop")
        elif self.settings.get("enabled"):
            self._init_otel()

    def content_attribute(self, value, limit=4000):
        """Return bounded, masked content suitable for an OTel string attribute."""
        return json.dumps(mask(value), default=str, separators=(",", ":"))[:limit]

    def _init_otel(self):
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider, SpanProcessor
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter, SpanExportResult
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        observer = self

        class Enrich(SpanProcessor):
            def on_start(self, span, parent_context=None):
                for k, v in _ids.get().items():
                    span.set_attribute(k, v)
            def on_end(self, span): pass
            def shutdown(self): pass
            def force_flush(self, timeout_millis=30000): return True

        class Checked(SpanExporter):
            def __init__(self, inner, name): self.inner, self.name = inner, name
            def export(self, spans):
                result = self.inner.export(spans)
                if result != SpanExportResult.SUCCESS: observer.export_errors.append(self.name)
                return result
            def shutdown(self): return self.inner.shutdown()
            def force_flush(self, timeout_millis=30000): return self.inner.force_flush(timeout_millis)

        self.provider = TracerProvider(resource=Resource.create({
            "service.name": self.settings.get("service_name", "agent-workshop"),
            "service.version": "0.1.0", "deployment.environment.name": "workshop"}))
        self.provider.add_span_processor(Enrich())
        destinations = []
        allowed_hosts = self.settings.get("allowed_hosts")
        if (self.settings.get("apm_endpoint") or self.settings.get("langfuse_endpoint")) and not allowed_hosts:
            raise ValueError("Telemetry endpoints require exact allowed_hosts")
        if self.settings.get("apm_endpoint"):
            base = endpoint(self.settings["apm_endpoint"], allowed_hosts=allowed_hosts).split("/20200101")[0]
            destinations.append(("apm", base + "/20200101/opentelemetry/private/v1/traces",
                {"Authorization": "dataKey " + secret(self.settings["apm_key_env"])}))
        if self.settings.get("langfuse_endpoint"):
            auth = secret(self.settings["langfuse_public_key_env"]) + ":" + secret(self.settings["langfuse_secret_key_env"])
            destinations.append(("langfuse", endpoint(self.settings["langfuse_endpoint"], local=True, allowed_hosts=allowed_hosts) + "/api/public/otel/v1/traces",
                {"Authorization": "Basic " + base64.b64encode(auth.encode()).decode(), "x-langfuse-ingestion-version": "4"}))
        if not destinations:
            raise ValueError("Enabled telemetry requires at least one explicit exporter")
        for name, url, headers in destinations:
            self.provider.add_span_processor(BatchSpanProcessor(Checked(OTLPSpanExporter(endpoint=url, headers=headers, timeout=10), name)))
            self._exporter_names.append(name)
        self.tracer = self.provider.get_tracer("agent-workshop")

    @contextmanager
    def span(self, name, attributes=None, *, kind=None):
        attributes = mask(attributes or {})
        root = name == "agent.run"
        previous = _ids.get()
        token = _ids.set({**previous, **{k: v for k, v in attributes.items() if k in
                         {"session.id", "workshop.run_id", "langfuse.session.id", "agent.role", "gen_ai.agent.name"}}})
        if root:
            self.counts["runs"] += 1
        try:
            if self.provider:
                # Preserve ERROR status without exporting raw exception messages
                # in status descriptions or automatic exception events.
                span_options = {"kind": kind} if kind is not None else {}
                with self.tracer.start_as_current_span(name, attributes=attributes, record_exception=False, set_status_on_exception=False, **span_options) as span:
                    ctx = span.get_span_context()
                    trace_tok = _trace.set(format(ctx.trace_id, "032x"))
                    span_tok = _span.set(format(ctx.span_id, "016x"))
                    try:
                        yield span
                    except Exception:
                        from opentelemetry.trace import Status, StatusCode
                        span.set_status(Status(StatusCode.ERROR))
                        raise
                    finally: _trace.reset(trace_tok); _span.reset(span_tok)
            else:
                trace_tok = _trace.set(_trace.get() or uuid.uuid4().hex)
                span_tok = _span.set(uuid.uuid4().hex[:16])
                try: yield _LocalSpan()
                finally: _trace.reset(trace_tok); _span.reset(span_tok)
        finally:
            _ids.reset(token)

    def trace_id(self): return _trace.get()

    def event(self, name, **fields):
        self.counts["events"] += 1
        if name == "security.decision" and fields.get("decision") == "approval_required":
            self.counts["policy_blocks"] += 1
        if "error" in name or "fail" in name: self.counts["errors"] += 1
        record = mask({"time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                       "event": name, "service.name": self.settings.get("service_name", "agent-workshop"),
                       **_ids.get(), **fields, "trace_id": _trace.get(), "span_id": _span.get()})
        line = json.dumps(record, default=str)
        if self.path:
            with self.path.open("a") as out: out.write(line + "\n")
        if self.stream:
            self.stream.write(line + "\n"); self.stream.flush()

    def flush(self):
        ok = self.provider.force_flush(timeout_millis=10000) if self.provider else True
        return {"flush_ok": bool(ok) and not self.export_errors,
                "exporters": self._exporter_names, "export_errors": sorted(set(self.export_errors)),
                "backend_readback": "not_verified", "backend_verified": False,
                "counts": self.counts.copy()}

    def close(self):
        result = self.flush()
        if self.provider: self.provider.shutdown()
        return result
