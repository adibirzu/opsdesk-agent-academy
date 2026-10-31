"""Loopback-only deployed API; access through SSH, no public listener."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import hmac
import json
import re
from importlib import resources
from .config import secret
from .cli import execute
from .page_telemetry import PageTelemetry


class WorkshopHTTPServer(ThreadingHTTPServer):
    """Keep probes responsive, with a fixed ceiling on connection threads."""
    daemon_threads = False

    def __init__(self, *args, **kwargs):
        self._slots = threading.BoundedSemaphore(16)
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()


_SESSION = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_MAX_BODY_BYTES = 16000
_AGENT_ROLES = {"coordinator", "log_analyst", "trace_analyst", "security_analyst"}


def _token(config):
    """Return the configured token, without exposing configuration errors."""
    configured = config.telemetry.get("service_token_env")
    if not isinstance(configured, str) or not configured:
        return None
    try:
        return secret(configured)
    except (TypeError, ValueError):
        return None


def _authorized(config, header):
    token = _token(config)
    return token is not None and hmac.compare_digest((header or "").encode(), ("Bearer " + token).encode())


_PAGES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/assets/workshop.css": ("workshop.css", "text/css; charset=utf-8"),
    "/assets/workshop.js": ("workshop.js", "text/javascript; charset=utf-8"),
    "/favicon.svg": ("favicon.svg", "image/svg+xml"),
}
_PAGE_CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; "
             "connect-src 'self'; img-src 'self' data:; base-uri 'none'; "
             "frame-ancestors 'none'; form-action 'self'; object-src 'none'")


def handler(config, *, page_provider=None):
    run_lock = threading.Lock()
    metrics = {"runs": 0, "failures": 0, "policy_blocks": 0}
    _page_telemetry = PageTelemetry(config.telemetry, provider=page_provider)
    class Handler(BaseHTTPRequestHandler):
        page_telemetry = _page_telemetry

        def log_message(self, *_): pass

        def setup(self):
            super().setup()
            self.connection.settimeout(15)

        def respond(self, code, data):
            raw=json.dumps(data).encode()
            self.send_response(code)
            self.send_header("Content-Type","application/json")
            self.send_header("Cache-Control","no-store")
            self.send_header("Content-Length",str(len(raw)))
            self.end_headers(); self.wfile.write(raw)

        def do_GET(self):
            if self.path in _PAGES:
                return self._page(self.path)
            if self.path == "/metrics":
                if not self.authorized():
                    return self.respond(401,{"error":"unauthorized"})
                raw=(f'agent_workshop_runs_total {metrics["runs"]}\nagent_workshop_failures_total {metrics["failures"]}\nagent_workshop_policy_blocks_total {metrics["policy_blocks"]}\n').encode()
                self.send_response(200); self.send_header("Content-Type","text/plain; version=0.0.4")
                self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw); return
            if self.path not in {"/health", "/ready"}: return self.respond(404,{"error":"not_found"})
            self.respond(200,{"status":"ready","provider_verified":False})

        def _page(self, path):
            resource_name, content_type = _PAGES.get(path, (None, None))
            if resource_name is None:
                return self.respond(404, {"error": "not_found"})
            try:
                resource = resources.files("agent_workshop").joinpath("web", resource_name)
                body = resource.read_bytes()
            except (FileNotFoundError, OSError):
                return self.respond(404, {"error": "not_found"})
            with self.page_telemetry.span("GET", path) as span:
                if span is not None:
                    span.set_attribute("http.status_code", 200)
                    span.set_attribute("http.response.status_code", 200)
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Security-Policy", _PAGE_CSP)
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                trace_id = self.page_telemetry.trace_id()
                if trace_id:
                    self.send_header("X-Workshop-Trace-Id", trace_id)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        def close_telemetry(cls):
            return cls.page_telemetry.close()

        close_telemetry = classmethod(close_telemetry)

        def authorized(self):
            # OCI hosted endpoint authentication uses Authorization for its
            # request signature. Keep application authentication independent.
            custom = self.headers.get("X-Workshop-Token")
            if custom is not None:
                token = _token(config)
                return token is not None and hmac.compare_digest(custom.encode(), token.encode())
            return _authorized(config, self.headers.get("Authorization"))

        def do_POST(self):
            if self.path!="/run": return self.respond(404,{"error":"not_found"})
            if _token(config) is None: return self.respond(503,{"error":"service_auth_not_configured"})
            if not self.authorized():
                return self.respond(401,{"error":"unauthorized"})
            try:
                length=int(self.headers.get("Content-Length","0"))
                if not 1<=length<=_MAX_BODY_BYTES: return self.respond(413,{"error":"invalid_size"})
                data=json.loads(self.rfile.read(length))
                if not isinstance(data,dict) or set(data)-{"prompt","session_id","fail_tool","operation","agent_role"}: raise ValueError()
                if not isinstance(data.get("prompt"),str) or not isinstance(data.get("session_id"),str): raise ValueError()
                if not _SESSION.fullmatch(data["session_id"]): raise ValueError()
                if not isinstance(data.get("fail_tool",False),bool): raise ValueError()
                if data.get("operation", "investigate") not in {"investigate", "remediate"}: raise ValueError()
                if data.get("agent_role", "coordinator") not in _AGENT_ROLES: raise ValueError()
            except (ValueError,TypeError): return self.respond(400,{"error":"invalid_request"})
            if not run_lock.acquire(blocking=False):
                return self.respond(429, {"error": "run_in_progress"})
            try:
                execute_kwargs = {"fail_tool": data.get("fail_tool", False),
                                  "operation": data.get("operation", "investigate")}
                # Preserve the established default call shape while forwarding
                # an explicitly selected specialist role.
                if "agent_role" in data:
                    execute_kwargs["agent_role"] = data["agent_role"]
                result=execute(config,data["prompt"],data["session_id"],"local/service-events.jsonl",
                               **execute_kwargs)
                metrics["runs"] += 1
                if result["outcome"]=="approval_required": metrics["policy_blocks"] += 1
                elif result["outcome"]!="success": metrics["failures"] += 1
                code = {"success": 200, "approval_required": 409}.get(result["outcome"], 502)
                self.respond(code,result)
            except Exception: self.respond(502,{"outcome":"failure","error":"run_failed"})
            finally: run_lock.release()
    return Handler


def serve(config, bind="localhost", port=8765):
    if bind!="localhost": raise ValueError("Service binds to localhost only; use an SSH tunnel")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("Service port must be between 1 and 65535")
    handler_class = handler(config)
    server=WorkshopHTTPServer((bind,port),handler_class)
    server.timeout=5
    try: server.serve_forever(poll_interval=.5)
    finally:
        server.server_close()
        handler_class.close_telemetry()
