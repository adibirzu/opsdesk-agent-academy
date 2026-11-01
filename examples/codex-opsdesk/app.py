"""Same OpsDesk app, with an explicit authenticated server harness and WSGI adapter."""
import argparse
import json
import os
from pathlib import Path
import secrets
import threading
from urllib.parse import urlsplit
from wsgiref.simple_server import make_server, WSGIRequestHandler

from engine import Agent, Gateway, MODEL
from security import (ACTIONS, MAX_BODY, SERVICES, Invalid, LocalQuota, RedisQuota,
                      Sessions, choice, exact, text, unique_object, valid_origin)
from telemetry import Telemetry

STATIC = Path(__file__).parent / 'static'
CONFIG_NAMES = ('VERCEL', 'VERCEL_URL', 'PUBLIC_ORIGIN', 'WORKSHOP_LOGIN_SECRET',
    'SESSION_SIGNING_SECRET', 'AI_GATEWAY_API_KEY', 'LANGFUSE_BASE_URL',
    'LANGFUSE_PUBLIC_KEY', 'LANGFUSE_SECRET_KEY', 'UPSTASH_REDIS_REST_URL',
    'UPSTASH_REDIS_REST_TOKEN', 'QUOTA_NAMESPACE', 'LOCAL_SINGLE_PROCESS_QUOTA')
SEEDS = [
    dict(id='TRAIN-101', title='Payments is slow', service='payments', priority='high',
         description='Synthetic report: payment latency increased after a release; cause unconfirmed.'),
    dict(id='TRAIN-102', title='Checkout health check', service='checkout', priority='medium',
         description='Synthetic training availability check.'),
    dict(id='TRAIN-103', title='Catalog availability', service='catalog', priority='low',
         description='Synthetic training catalog check.'),
]


def response(status, value, mime='application/json; charset=utf-8', extra=()):
    body = json.dumps(value).encode() if mime.startswith('application/json') else value
    headers = [('Content-Type', mime), ('Content-Length', str(len(body))), ('Cache-Control', 'no-store'),
               ('X-Content-Type-Options', 'nosniff'), ('Referrer-Policy', 'no-referrer'),
               ('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")]
    return status, headers + list(extra), body


class Application:
    def __init__(self, env=None, *, model_factory=None, quota=None, telemetry_factory=None):
        source = os.environ if env is None else env
        self.env = {key: source[key] for key in CONFIG_NAMES if key in source}
        self.deployed = self.env.get('VERCEL') == '1'
        self.origin = self.env.get('PUBLIC_ORIGIN', '')
        if not self.origin and self.deployed and self.env.get('VERCEL_URL'):
            self.origin = 'https://' + self.env['VERCEL_URL']
        self.sessions = Sessions(self.env.get('WORKSHOP_LOGIN_SECRET', ''),
                                 self.env.get('SESSION_SIGNING_SECRET', ''), secure=self.deployed)
        self.model_factory = model_factory
        if model_factory is None and self.env.get('AI_GATEWAY_API_KEY'):
            self.model_factory = lambda: Gateway(self.env['AI_GATEWAY_API_KEY'])
        self.telemetry_factory = telemetry_factory or (lambda: Telemetry(self.env))
        self.quota, self.quota_error = quota, False
        if quota is None:
            if self.env.get('UPSTASH_REDIS_REST_URL') and self.env.get('UPSTASH_REDIS_REST_TOKEN'):
                try:
                    self.quota = RedisQuota(self.env['UPSTASH_REDIS_REST_URL'],
                        self.env['UPSTASH_REDIS_REST_TOKEN'], self.env.get('QUOTA_NAMESPACE', ''))
                except Invalid:
                    self.quota_error = True
            elif not self.deployed and self.env.get('LOCAL_SINGLE_PROCESS_QUOTA') == '1':
                self.quota = LocalQuota()
        self.lock, self.tickets = threading.Lock(), [t.copy() for t in SEEDS]

    def __call__(self, environ, start_response):
        try:
            status, headers, body = self.dispatch(environ)
        except Exception:
            status, headers, body = response(500, {'error': 'Server request failed safely. No automatic retry.'})
        names = {200: 'OK', 201: 'Created', 400: 'Bad Request', 401: 'Unauthorized',
                 403: 'Forbidden', 404: 'Not Found', 413: 'Content Too Large',
                 415: 'Unsupported Media Type', 429: 'Too Many Requests',
                 500: 'Internal Server Error', 503: 'Service Unavailable'}
        start_response(f'{status} {names[status]}', headers)
        return [body]

    def dispatch(self, e):
        if not valid_origin(self.origin, self.deployed) or e.get('HTTP_HOST') != urlsplit(self.origin).netloc:
            return response(403, {'error': 'Exact configured Host required.'})
        method, path = e.get('REQUEST_METHOD'), e.get('PATH_INFO')
        origin = e.get('HTTP_ORIGIN')
        if (method == 'POST' or origin is not None) and origin != self.origin:
            return response(403, {'error': 'Exact configured Origin required.'})
        signed_in = self.sessions.authenticate(e.get('HTTP_COOKIE'))
        if method == 'GET':
            if path == '/api/status':
                return response(200, {'signed_in': signed_in,
                    'auth_configured': self.sessions.configured, 'model_configured': self.model_factory is not None,
                    'quota_mode': self.quota.mode if self.quota else 'not_configured',
                    'runtime_mode': 'vercel_serverless' if self.deployed else 'local',
                    'model': MODEL, 'telemetry_readback': 'not_verified'})
            if path == '/api/tickets':
                with self.lock:
                    tickets = [t.copy() for t in self.tickets]
                return response(200, {'tickets': tickets, 'synthetic': True, 'persistence': 'process_memory_only'})
            assets = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}
            if path in assets:
                name, mime = assets[path]
                return response(200, (STATIC / name).read_bytes(), mime + '; charset=utf-8')
            return response(404, {'error': 'Route not found.'})
        if method != 'POST' or path not in ('/api/login', '/api/logout', '/api/tickets', '/api/investigate'):
            return response(404, {'error': 'Route not found.'})
        if e.get('HTTP_TRANSFER_ENCODING') or e.get('CONTENT_TYPE') != 'application/json':
            return response(415, {'error': 'Use a bounded JSON request.'})
        length = e.get('CONTENT_LENGTH', '')
        if not length.isascii() or not length.isdecimal():
            return response(400, {'error': 'One valid Content-Length required.'})
        if len(length) > 5 or int(length) > MAX_BODY:
            return response(413, {'error': 'Request exceeds body limit.'})
        if path not in ('/api/login',) and not signed_in:
            return response(401, {'error': 'Sign in to the workshop app first.'})
        try:
            raw = e['wsgi.input'].read(int(length))
            if len(raw) != int(length):
                raise Invalid('Incomplete body.')
            data = json.loads(raw.decode(), object_pairs_hook=unique_object,
                              parse_constant=lambda _: (_ for _ in ()).throw(Invalid('Invalid JSON.')))
            if path == '/api/login':
                exact(data, ('password',))
                cookie = self.sessions.issue(data['password'])
                if cookie is None:
                    return response(401, {'error': 'Sign-in failed or server authentication is not configured.'})
                return response(200, {'signed_in': True}, extra=[('Set-Cookie', cookie)])
            if path == '/api/logout':
                exact(data, ())
                return response(200, {'signed_in': False}, extra=[('Set-Cookie', self.sessions.cookie('', 0))])
            if path == '/api/tickets':
                exact(data, ('title', 'description', 'service', 'priority'))
                ticket = {'title': text(data['title'], 120), 'description': text(data['description'], 2000),
                          'service': choice(data['service'], SERVICES), 'priority': choice(data['priority'], ('high', 'medium', 'low'))}
                with self.lock:
                    if len(self.tickets) >= 50:
                        raise Invalid('Training ticket limit reached.')
                    ticket['id'] = f'TRAIN-{101 + len(self.tickets)}'
                    self.tickets.append(ticket)
                return response(201, ticket)
            result = Agent(self.model_factory, self.quota, self.telemetry_factory()).run(data)
            return response(429 if result['outcome'] == 'rate_limited' else 200, result)
        except (Invalid, UnicodeDecodeError, json.JSONDecodeError, RecursionError):
            return response(400, {'error': 'Request failed strict input validation.'})


app = Application()


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *_args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--settings', help='Private 0600 JSON file created by configure_local.py')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('Use an unprivileged port.')
    config = {key: os.environ[key] for key in CONFIG_NAMES if key in os.environ}
    if args.settings:
        settings_path = Path(args.settings).expanduser()
        if settings_path.is_symlink() or not settings_path.is_file() or settings_path.stat().st_mode & 0o077:
            parser.error('Settings must be a private 0600 regular file, not a symlink.')
        allowed = {'WORKSHOP_LOGIN_SECRET', 'SESSION_SIGNING_SECRET', 'AI_GATEWAY_API_KEY',
                   'LANGFUSE_BASE_URL', 'LANGFUSE_PUBLIC_KEY', 'LANGFUSE_SECRET_KEY',
                   'UPSTASH_REDIS_REST_URL', 'UPSTASH_REDIS_REST_TOKEN', 'QUOTA_NAMESPACE',
                   'LOCAL_SINGLE_PROCESS_QUOTA'}
        values = json.loads(settings_path.read_text())
        if type(values) is not dict or set(values) - allowed or any(type(v) is not str for v in values.values()):
            parser.error('Settings have an unsupported field or value.')
        config.update(values)
    config['PUBLIC_ORIGIN'] = f'http://127.0.0.1:{args.port}'
    application = Application(config)
    if not application.sessions.configured:
        print('Authentication is not configured. Set the two private server auth secrets before a real investigation.')
    with make_server('127.0.0.1', args.port, application, handler_class=QuietHandler) as server:
        print(f'OpsDesk loopback UI: http://127.0.0.1:{args.port}; live acceptance is separate.', flush=True)
        server.serve_forever()


if __name__ == '__main__':
    main()
