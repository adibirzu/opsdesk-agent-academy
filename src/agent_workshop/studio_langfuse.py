"""One explicit, metadata-only trace readback; no ingestion or automatic retry."""

import base64
import json
from urllib.error import HTTPError
from urllib.request import Request, build_opener
from .config import endpoint, secret
from .models import _NoRedirect


def verify_trace(telemetry, trace_id, session_id, policy_stop):
    if not telemetry.get("enabled"):
        return {"backend_verified": False, "status": "unconfigured"}
    base = endpoint(
        telemetry["langfuse_endpoint"],
        local=True,
        allowed_hosts=telemetry["allowed_hosts"],
    )
    auth = (
        secret(telemetry["langfuse_public_key_env"])
        + ":"
        + secret(telemetry["langfuse_secret_key_env"])
    )
    request = Request(
        base + "/api/public/traces/" + trace_id,
        headers={
            "Authorization": "Basic " + base64.b64encode(auth.encode()).decode(),
            "Accept": "application/json",
            "User-Agent": "agent-workshop-studio/1.0",
        },
    )
    try:
        with build_opener(_NoRedirect()).open(request, timeout=10) as response:
            data = json.loads(response.read(256000))
        rows = data.get("observations", [])
        exact = (
            data.get("id") == trace_id
            and data.get("sessionId") == session_id
            and isinstance(rows, list)
            and bool(rows)
            and all(
                isinstance(row, dict) and row.get("traceId") == trace_id for row in rows
            )
        )
        generations = (
            [
                row
                for row in rows
                if isinstance(row, dict)
                and str(row.get("type", "")).lower() == "generation"
            ]
            if isinstance(rows, list)
            else []
        )
        decision = (
            any(
                row.get("name") == "security.authorize"
                and (row.get("metadata") or {})
                .get("attributes", {})
                .get("security.decision")
                == "approval_required"
                for row in rows
                if isinstance(row, dict)
            )
            if isinstance(rows, list)
            else False
        )
        verified = bool(
            exact and ((not generations and decision) if policy_stop else generations)
        )
        return {
            "backend_verified": verified,
            "status": "verified" if verified else "not_matched",
            "observation_count": len(rows) if isinstance(rows, list) else 0,
            "generation_count": len(generations),
        }
    except HTTPError as exc:
        return {
            "backend_verified": False,
            "status": "pending" if exc.code == 404 else "failed",
            "http_status": exc.code,
        }
    except Exception:
        return {"backend_verified": False, "status": "failed"}
