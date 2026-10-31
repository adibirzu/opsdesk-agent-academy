"""Loopback-only workshop for a reviewed local learner app. No cloud configuration."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import threading
import uuid
from http.server import BaseHTTPRequestHandler

from .coordinator import run_coordinator
from .observability import Observer
from .runtime import ModelReply
from .service import WorkshopHTTPServer
from .trace_walkthrough import summarize_events


def private_json(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as file:
        json.dump(value, file, indent=2)


def load_app(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.suffix != '.py':
        raise ValueError('Select a reviewed regular Python app file')
    spec = importlib.util.spec_from_file_location('local_workshop_learner', path)
    app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app)
    if not all(hasattr(app, name) for name in ('FIXTURE', 'analyze_inventory', 'build_agent', 'ScriptedModel')):
        raise ValueError('App does not implement the learner contract')
    if app.FIXTURE.get('source') != 'synthetic' and app.FIXTURE.get('evidence') != 'synthetic fixture':
        raise ValueError('This local lane accepts only the synthetic learner fixture')
    return app


class LocalSession:
    def __init__(self, app, output):
        self.app, self.output = app, Path(output)
        if self.output.is_symlink():
            raise ValueError('Evidence directory must not be symlinked')
        self.output.mkdir(mode=0o700, parents=True, exist_ok=False)
        self.lock = threading.Lock()
        self.session_id = 'local-' + uuid.uuid4().hex[:16]

    def run(self, operation):
        if operation not in ('investigate', 'remediate', 'unsafe'):
            raise ValueError('Unknown local operation')
        if not self.lock.acquire(blocking=False):
            raise BlockingIOError('Another local run is active')
        observer = None
        try:
            out = self.output / uuid.uuid4().hex
            out.mkdir(mode=0o700)
            observer = Observer({}, out/'events.jsonl')
            initialized = 0
            class UnsafeModel:
                def complete(self, messages):
                    return ModelReply('{"tool":"delete_volume","arguments":{}}', 'scripted-denied-action')
            def factory():
                nonlocal initialized
                initialized += 1
                model = UnsafeModel() if operation == 'unsafe' else self.app.ScriptedModel()
                return self.app.build_agent(model, observer)
            data = run_coordinator(factory, observer, 'Report synthetic volume candidates; do not delete anything.',
                                   self.session_id, 'remediate' if operation == 'remediate' else 'investigate')
            observer.flush()
            data.update(inference_mode='scripted_rehearsal', tool_data='synthetic',
                        estimated_llm_cost_usd=None, cost_status='unavailable_scripted_model',
                        coding_cost_status='Codex subscription usage is separate; invoice cost not measured',
                        provider_verified=False, exporters=[], model_initializations=initialized,
                        report=self.app.analyze_inventory(self.app.FIXTURE) if data['outcome'] == 'success' else None)
            data['walkthrough'] = summarize_events(out/'events.jsonl', data['trace_id'], self.session_id)
            private_json(out/'result.json', data)
            return data
        finally:
            if observer is not None:
                observer.close()
            self.lock.release()


def make_server(session, port=8768):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        @property
        def origin(self):
            return 'http://127.0.0.1:' + str(self.server.server_address[1])
        def reply(self, status, body, kind='application/json'):
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(body)
        def do_GET(self):
            if self.headers.get('Host') != self.origin.removeprefix('http://'):
                return self.reply(403, b'{}')
            if self.path != '/': return self.reply(404, b'{}')
            self.reply(200, PAGE.encode(), 'text/html; charset=utf-8')
        def do_POST(self):
            if (self.path != '/run' or self.headers.get('Host') != self.origin.removeprefix('http://')
                    or self.headers.get('Origin') != self.origin
                    or self.headers.get('Content-Type') != 'application/json'
                    or self.headers.get('Transfer-Encoding')):
                return self.reply(403, b'{"error":"Use this local page and its buttons."}')
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 2 <= length <= 128: raise ValueError('Invalid body size')
                request = json.loads(self.rfile.read(length))
                if not isinstance(request, dict) or set(request) != {'operation'} or not isinstance(request['operation'], str):
                    raise ValueError('Invalid operation')
                result = session.run(request['operation'])
                self.reply(200, json.dumps(result).encode())
            except BlockingIOError:
                self.reply(429, b'{"error":"A run is active. Wait for its result."}')
            except ValueError:
                self.reply(400, b'{"error":"Choose one of the three local operations."}')
            except Exception:
                self.reply(500, b'{"error":"Local run failed. Inspect private evidence; no automatic retry."}')
    return WorkshopHTTPServer(('127.0.0.1', port), Handler)


PAGE = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Inside AI Agents — Local Lab</title><style>
:root{color-scheme:light;font-family:system-ui,sans-serif;color:#27241f;background:#faf7f2}*{box-sizing:border-box}
body{max-width:1120px;margin:0 auto;padding:36px 24px}header{border-top:5px solid #c74634;padding-top:20px}
h1{font-size:clamp(30px,5vw,54px);letter-spacing:-.04em;margin:12px 0}h2{font-size:22px}p{line-height:1.6;max-width:80ch}
.label{font-size:13px;text-transform:uppercase;letter-spacing:.12em;color:#725e48}.flow{display:flex;flex-wrap:wrap;gap:12px;margin:24px 0;padding:16px 0;border-block:1px solid #d5ccbf}
button{font:inherit;border:1px solid #8b7966;border-radius:4px;background:#fffdf9;color:inherit;padding:12px 16px;cursor:pointer;margin:0 8px 12px 0}
button:first-child{background:#a53226;border-color:#a53226;color:white}button:hover{filter:brightness(.94)}button:focus-visible{outline:3px solid #447e7a;outline-offset:3px}button:disabled{opacity:.55;cursor:wait}
.grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:28px}.grid>*{min-width:0}pre{background:#efe9df;padding:18px;white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.65 ui-monospace,monospace;border-left:3px solid #8c7760;min-height:120px}
#status{font-weight:650;min-height:28px}footer{margin-top:32px;border-top:1px solid #d5ccbf;padding-top:14px;font-size:14px;color:#665f56}@media(max-width:720px){.grid{grid-template-columns:minmax(0,1fr)}body{padding:24px 16px}}
</style><header><div class="label">Coding workshop / local edition</div><h1>Inside AI Agents</h1><p>Create the app with Codex. Watch the harness control its actions.</p></header>
<div class="flow"><strong>Codex creates app.py</strong><span>→ contracts pass</span><span>→ Scripted agent</span><span>→ allowlisted tool</span><span>→ local trace</span></div>
<p>This page runs the reviewed learner app on your laptop. Inventory is synthetic, the agent model is scripted, and observability stays in private local files. No tenancy, access token or API key is needed.</p>
<div id="actions"><button data-operation="investigate">Run volume report</button><button data-operation="remediate">Stop a requested change</button><button data-operation="unsafe">Reject an unknown tool</button></div>
<p id="status" role="status" aria-live="polite">Ready. Choose a case to start; nothing runs automatically.</p>
<div class="grid"><section><h2>Input → result</h2><p>Report synthetic volumes older than 30 days, with complete attachment evidence. Never delete them.</p><pre id="result">No result yet.</pre></section><section><h2>Follow the harness</h2><p>Session → authorization → model → validated tool → answer. A policy stop has no model invocation.</p><pre id="trace">Your correlated local events will appear here.</pre></section></div>
<details><summary>Inspect the complete local receipt</summary><pre id="receipt">No receipt yet.</pre></details>
<footer>Illustrative storage savings are not an LLM bill. Scripted token usage/cost stays unknown. Codex coding uses your Codex account separately. OCI APM, Log Analytics and Langfuse ingestion are not verified in this local lane.</footer>
<script>
const buttons=[...document.querySelectorAll('button')],status=document.getElementById('status');
buttons.forEach(button=>button.onclick=async()=>{buttons.forEach(b=>b.disabled=true);status.textContent='Running the local harness…';try{
const response=await fetch('/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operation:button.dataset.operation}),redirect:'error'});
const data=await response.json();if(!response.ok)throw Error('Local request rejected.');
document.getElementById('result').textContent=JSON.stringify({outcome:data.outcome,decision:data.decision,steps:data.steps,model_initializations:data.model_initializations,report:data.report,estimated_llm_cost_usd:data.estimated_llm_cost_usd,cost_status:data.cost_status},null,2);
document.getElementById('trace').textContent=JSON.stringify(data.walkthrough,null,2);document.getElementById('receipt').textContent=JSON.stringify(data,null,2);status.textContent='Finished: '+data.outcome+'. Evidence saved locally.';
}catch(error){status.textContent='Request failed. Inspect the local terminal; no automatic retry.'}finally{buttons.forEach(b=>b.disabled=false)}});
</script></html>'''


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', required=True, help='Reviewed learner app.py; importing it executes local Python code')
    parser.add_argument('--output', required=True, help='New private evidence directory; existing data is preserved')
    parser.add_argument('--port', type=int, default=8768)
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535: parser.error('Use an unprivileged loopback port')
    session = LocalSession(load_app(args.app), args.output)
    server = make_server(session, args.port)
    print('Open http://127.0.0.1:'+str(args.port)+' — SCRIPTED AGENT / SYNTHETIC TOOLS / LOCAL EVIDENCE', flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
