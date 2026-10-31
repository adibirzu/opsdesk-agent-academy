"""Tiny local app over two fixed OCI reads. No LLM-generated shell commands."""
import argparse
from http.server import BaseHTTPRequestHandler
import json
from pathlib import Path
import uuid
import threading

from agent_workshop.cloud_demo import OPERATIONS, run_check
from agent_workshop.config import Config, load
from agent_workshop.models import live_model
from agent_workshop.page_telemetry import PageTelemetry
from agent_workshop.service import WorkshopHTTPServer


class LocalServer(WorkshopHTTPServer):
    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(5)
        return connection, address


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--scripted", action="store_true", help="Offline fixture; no cloud or model")
    mode.add_argument("--config", help="Private TOML with explicit OCI scope")
    parser.add_argument("--operation", choices=OPERATIONS, default="compute")
    parser.add_argument("--output", required=True, help="New private evidence directory per console run")
    parser.add_argument("--session", default="cloud-app-demo")
    parser.add_argument("--export", action="store_true", help="Send normalized metadata to configured backends")
    parser.add_argument("--agent", action="store_true", help="Let the configured LLM select the fixed read tool")
    parser.add_argument("--verify", action="store_true", help="Read back agent trace/session in APM, Langfuse and Logan, plus the metric window")
    parser.add_argument("--readback-only", metavar="RESULT_JSON", help="Verify a saved live agent receipt; no inference, tools or uploads")
    parser.add_argument("--serve", action="store_true", help="Loopback page; each button performs one check")
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args(argv)
    if args.readback_only is not None and not args.readback_only.strip():
        parser.error("--readback-only requires a nonempty receipt path")
    if args.readback_only is not None and (args.scripted or args.agent or args.export or args.verify or args.serve):
        parser.error("--readback-only requires --config and cannot run or export anything")
    if args.scripted and (args.export or args.agent): parser.error("Scripted mode does not enable exports or live inference")
    if args.agent and args.serve: parser.error("Use --agent in the console; the tiny HTTP app performs direct SDK reads")
    if args.verify and (not args.agent or not args.export): parser.error("--verify requires --agent --export")
    if not 1024 <= args.port <= 65535: parser.error("Port must be 1024..65535")
    config = Config() if args.scripted else load(args.config)
    if config.telemetry.get("capture_content", False): parser.error("Use a metadata-only participant config")
    if args.readback_only is not None:
        from .cloud_demo import verify_saved_run
        result = verify_saved_run(config, args.readback_only, args.output)
        print(json.dumps(result, indent=2))
        return 0 if result["backend_verified"] else 1

    def check(operation):
        output = Path(args.output) / uuid.uuid4().hex if args.serve else Path(args.output)
        return run_check(config, output, args.session, operation, scripted=args.scripted, export=args.export,
                         model=live_model(config) if args.agent else None)

    if not args.serve:
        result = check(args.operation)
        if args.verify:
            from agent_workshop.backends import verify, verify_metrics
            from agent_workshop.cloud_demo import langfuse_generations
            result["readback"] = verify(config, result["trace_id"], args.session,
                                        providers={"langfuse": langfuse_generations})
            result["metric_readback"] = verify_metrics(config)
            result["metric_readback"]["scope"] = "service time window; not an exact per-run join"
            result["backend_verified"] = result["readback"]["backend_verified"] and result["metric_readback"]["status"] == "verified"
            (Path(args.output) / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
        return 0 if result["outcome"] == "success" and (not args.verify or result["backend_verified"]) else 1

    active = threading.Lock()
    pages = PageTelemetry(config.telemetry if args.export else {})
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_GET(self):
            with pages.span("GET", "/" if self.path == "/" else "unmatched") as span:
                if span: span.set_attribute("http.response.status_code", 200 if self.path == "/" else 404)
                self.reply(200, PAGE.encode(), "text/html; charset=utf-8") if self.path == "/" else self.reply(404, b"{}")
        def do_POST(self):
            # Browser same-origin POST only; DNS rebinding and cross-site forms
            # cannot trigger signed reads or telemetry/model costs.
            origin = "http://127.0.0.1:" + str(args.port)
            if (self.headers.get("Host") != "127.0.0.1:" + str(args.port) or
                    self.headers.get("Origin") != origin or self.headers.get("Content-Type") != "application/json"):
                return self.reply(403, b"{}")
            if self.path not in ("/check/compute", "/check/metrics"): return self.reply(404, b"{}")
            if not active.acquire(blocking=False): return self.reply(429, b'{"error":"A check is already running"}')
            try:
                result = check(self.path.rsplit("/", 1)[1])
                self.reply(200 if result["outcome"] == "success" else 502, json.dumps(result).encode())
            except Exception:
                self.reply(502, b'{"outcome":"failure","error":"Check private configuration; no fallback"}')
            finally:
                active.release()
        def reply(self, status, body, kind="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            if pages.trace_id(): self.send_header("X-Workshop-Trace-Id", pages.trace_id())
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)

    server = LocalServer(("127.0.0.1", args.port), Handler)
    print("Open http://127.0.0.1:" + str(args.port) + " — " + ("OFFLINE FIXTURE" if args.scripted else "LIVE OCI SDK") +
          ("; exports enabled" if args.export else "; local evidence only"), flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        server.server_close()
        pages.close()
    return 0


PAGE = '''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>My first observable OCI app</title>
<style>body{font:18px system-ui;background:#faf7f2;color:#25231f;max-width:850px;margin:6vh auto;padding:24px}
button{font:inherit;padding:12px;margin:8px 8px 8px 0;cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eee8de;padding:20px}h1{font-size:36px}</style>
<h1>My first observable OCI app</h1><p>One click → one bounded read → one trace and correlated events.</p>
<p>Reads use the presenter's fixed compartment. Results show counts and known states; names, IDs and addresses stay out of the response. Read the <code>source</code> field: <code>synthetic</code> is an offline fixture; <code>oci_sdk</code> is a real API read. <code>partial</code> means more pages exist.</p>
<button data-operation="compute">Check Compute</button><button data-operation="metrics">Discover workshop metrics</button>
<pre id="result" aria-live="polite">Choose a check. No check runs automatically.</pre>
<p>Exporter acceptance is not provider readback. Use the returned trace and session IDs to find the evidence.</p>
<script>document.querySelectorAll('button').forEach(b=>b.onclick=async()=>{const buttons=document.querySelectorAll('button');buttons.forEach(x=>x.disabled=true);const out=document.getElementById('result');out.textContent='Reading OCI; no automatic retry…';try{const r=await fetch('/check/'+b.dataset.operation,{method:'POST',headers:{'Content-Type':'application/json'},redirect:'error'});out.textContent=JSON.stringify(await r.json(),null,2)}catch(e){out.textContent='Request failed. Inspect private console evidence; no retry was made.'}finally{buttons.forEach(x=>x.disabled=false)}})</script>'''


def entrypoint(argv=None):
    try:
        return main(argv)
    except Exception as exc:
        print(json.dumps({"outcome": "failure", "error_type": type(exc).__name__,
                          "message": "Check the private configuration or receipt; no fallback was attempted"}))
        return 1


if __name__ == "__main__": raise SystemExit(entrypoint())
