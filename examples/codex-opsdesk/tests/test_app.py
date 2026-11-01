"""Isolated HTTP/agent/telemetry contracts. No real model, key, or remote service."""
import io
import json
from pathlib import Path
import sys
import threading
import unittest
from contextlib import contextmanager
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import Application
from engine import Agent, Gateway, MODEL, cost_estimate, reported_usage, synthetic_tool
from security import Invalid, LocalQuota, RedisQuota, Sessions
from telemetry import Telemetry

LOGIN = 'fixture-login-' + 'x' * 32
SIGN = 'fixture-sign-' + 'y' * 32
ORIGIN = 'http://127.0.0.1:8000'
ENV = {'PUBLIC_ORIGIN': ORIGIN, 'WORKSHOP_LOGIN_SECRET': LOGIN, 'SESSION_SIGNING_SECRET': SIGN,
       'LOCAL_SINGLE_PROCESS_QUOTA': '1'}


class FakeTelemetry:
    def __init__(self): self.names, self.attrs = [], []
    @contextmanager
    def span(self, name, attrs):
        self.names.append(name); self.attrs.append(attrs); yield self
    def trace_id(self, _): return '0' * 32
    def set(self, _, attrs): self.attrs.append(attrs)
    def finish(self): return {'status': 'fixture_not_exported', 'readback': 'not_verified'}


def reply(content=None, tools=None, usage=True, model='gpt-6-sol'):
    message = {'role': 'assistant', 'content': content}
    if tools is not None: message['tool_calls'] = tools
    result = {'model': model, 'choices': [{'message': message, 'finish_reason': 'tool_calls' if tools else 'stop'}]}
    if usage: result['usage'] = {'prompt_tokens': 100, 'completion_tokens': 20, 'total_tokens': 120}
    return result


def calls(service='payments'):
    return [{'id': 'call-' + name, 'type': 'function', 'function': {'name': name, 'arguments': json.dumps({'service': service})}}
            for name in ('service_health', 'release_diff')]


class FakeModel:
    def __init__(self, responses): self.responses, self.requests = list(responses), []
    def complete(self, messages, *, tools, timeout):
        self.requests.append({'messages': messages.copy(), 'tools': tools, 'timeout': timeout})
        result = self.responses.pop(0)
        if isinstance(result, Exception): raise result
        return result


def request(app, path, data=None, cookie='', origin=ORIGIN, method=None, raw=None, **overrides):
    body = raw if raw is not None else json.dumps(data).encode() if data is not None else b''
    environ = {'REQUEST_METHOD': method or ('POST' if data is not None or raw is not None else 'GET'),
               'PATH_INFO': path, 'HTTP_HOST': '127.0.0.1:8000', 'HTTP_ORIGIN': origin,
               'HTTP_COOKIE': cookie, 'CONTENT_TYPE': 'application/json',
               'CONTENT_LENGTH': str(len(body)), 'wsgi.input': io.BytesIO(body), **overrides}
    captured = {}
    def start(status, headers): captured.update(status=int(status[:3]), headers=dict(headers))
    raw_response = b''.join(app(environ, start))
    captured['body'] = json.loads(raw_response) if captured['headers']['Content-Type'].startswith('application/json') else raw_response
    return captured


def cookie_for(app): return app.sessions.issue(LOGIN).split(';', 1)[0]


class BoundaryTests(unittest.TestCase):
    def test_auth_login_cookie_and_tamper(self):
        app = Application(ENV)
        failed = request(app, '/api/login', {'password': 'wrong'})
        self.assertEqual(failed['status'], 401)
        good = request(app, '/api/login', {'password': LOGIN})
        cookie = good['headers']['Set-Cookie']
        self.assertIn('HttpOnly; SameSite=Strict', cookie)
        self.assertNotIn(LOGIN, cookie)
        self.assertTrue(app.sessions.authenticate(cookie.split(';', 1)[0]))
        self.assertFalse(app.sessions.authenticate(cookie.split(';', 1)[0] + 'tampered'))

    def test_secure_and_expired_session(self):
        now = [1000]
        sessions = Sessions(LOGIN, SIGN, secure=True, clock=lambda: now[0])
        cookie = sessions.issue(LOGIN)
        self.assertIn('; Secure', cookie)
        now[0] += 3601
        self.assertFalse(sessions.authenticate(cookie))

    def test_unauthorized_rejected_before_factory(self):
        constructed = []
        app = Application(ENV, model_factory=lambda: constructed.append(True))
        r = request(app, '/api/investigate', {'service': 'payments', 'action': 'investigate', 'review': False})
        self.assertEqual(r['status'], 401); self.assertEqual(constructed, [])

    def test_change_before_quota_and_model(self):
        class ExplodingQuota:
            mode = 'fixture'
            def reserve(self): raise AssertionError('Quota must not run on policy path')
        app = Application(ENV, model_factory=lambda: (_ for _ in ()).throw(AssertionError()),
                          quota=ExplodingQuota(), telemetry_factory=FakeTelemetry)
        r = request(app, '/api/investigate', {'service': 'payments', 'action': 'change', 'review': True}, cookie_for(app))
        self.assertEqual(r['body']['outcome'], 'approval_required')
        self.assertEqual(r['body']['model_calls'], 0)

    def test_host_origin_and_missing_origin(self):
        app = Application(ENV)
        for updates in ({'HTTP_HOST': 'other.example'}, {'HTTP_ORIGIN': 'https://other.example'}, {'HTTP_ORIGIN': None}):
            r = request(app, '/api/login', {'password': LOGIN}, **updates)
            self.assertEqual(r['status'], 403)

    def test_body_schema_duplicates_and_constants(self):
        app = Application(ENV); cookie = cookie_for(app)
        for raw in (b'{', b'{"service":"payments","action":"investigate","review":NaN}',
                    b'{"service":"payments","service":"catalog","action":"investigate","review":false}'):
            self.assertEqual(request(app, '/api/investigate', cookie=cookie, raw=raw)['status'], 400)
        self.assertEqual(request(app, '/api/login', raw=b' ' * 4097)['status'], 413)
        self.assertEqual(request(app, '/api/login', {'password': LOGIN}, CONTENT_LENGTH='99999999999999999999')['status'], 413)
        self.assertEqual(request(app, '/api/login', {'password': LOGIN}, HTTP_TRANSFER_ENCODING='chunked')['status'], 415)

    def test_ticket_text_and_service_validation(self):
        app = Application(ENV); cookie = cookie_for(app)
        ticket = {'title': '<script>example</script>', 'description': 'Synthetic only', 'service': 'payments', 'priority': 'high'}
        r = request(app, '/api/tickets', ticket, cookie)
        self.assertEqual(r['status'], 201); self.assertEqual(r['body']['title'], ticket['title'])
        ticket['service'] = 'arbitrary'
        self.assertEqual(request(app, '/api/tickets', ticket, cookie)['status'], 400)
        self.assertIn('textContent', (Path(__file__).parents[1] / 'static/app.js').read_text())

    def test_serverless_never_falls_back_to_process_quota(self):
        app = Application({**ENV, 'VERCEL': '1', 'PUBLIC_ORIGIN': 'https://workshop.example'}, model_factory=lambda: None)
        self.assertIsNone(app.quota)

    def test_default_vercel_origin_is_exact_server_value(self):
        env = {**ENV, 'VERCEL': '1', 'VERCEL_URL': 'preview.example'}; env.pop('PUBLIC_ORIGIN')
        app = Application(env)
        self.assertEqual(app.origin, 'https://preview.example')
        r = request(app, '/api/status', HTTP_HOST='preview.example', HTTP_ORIGIN=None)
        self.assertEqual(r['status'], 200)


class RealLocalHTTPTests(unittest.TestCase):
    def test_wsgi_entrypoint_over_owned_loopback_socket(self):
        from http.client import HTTPConnection
        from wsgiref.simple_server import make_server
        from app import QuietHandler
        application = Application(ENV, telemetry_factory=FakeTelemetry)
        with make_server('127.0.0.1', 0, application, handler_class=QuietHandler) as server:
            port = server.server_port
            application.origin = f'http://127.0.0.1:{port}'
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                client = HTTPConnection('127.0.0.1', port, timeout=3)
                client.request('GET', '/')
                page = client.getresponse(); body = page.read()
                self.assertEqual(page.status, 200); self.assertIn(b'Agent investigation', body)
                payload = json.dumps({'password': LOGIN})
                client.request('POST', '/api/login', payload, {'Content-Type': 'application/json', 'Origin': application.origin})
                login = client.getresponse(); login.read()
                self.assertEqual(login.status, 200)
                cookie = login.getheader('Set-Cookie').split(';', 1)[0]
                payload = json.dumps({'service': 'payments', 'action': 'change', 'review': True})
                client.request('POST', '/api/investigate', payload, {'Content-Type': 'application/json', 'Origin': application.origin, 'Cookie': cookie})
                result = client.getresponse(); data = json.loads(result.read())
                self.assertEqual(result.status, 200); self.assertEqual(data['outcome'], 'approval_required')
                self.assertEqual(data['model_calls'], 0)
                client.close()
            finally:
                server.shutdown(); thread.join(timeout=3)
                self.assertFalse(thread.is_alive())


class QuotaTests(unittest.TestCase):
    def test_atomic_concurrent_two_per_minute(self):
        quota = LocalQuota(clock=lambda: 100)
        accepted = []
        threads = [threading.Thread(target=lambda: accepted.append(quota.reserve())) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(sum(accepted), 2)

    def test_ten_per_utc_day(self):
        clock = [60]
        quota = LocalQuota(clock=lambda: clock[0])
        for _ in range(5):
            self.assertTrue(quota.reserve()); self.assertTrue(quota.reserve()); clock[0] += 60
        self.assertFalse(quota.reserve())
        clock[0] = 86401; self.assertTrue(quota.reserve())

    def test_one_redis_atomic_reservation_and_namespace(self):
        calls_ = []
        def transport(url, data, headers, **kw): calls_.append(data); return {'result': 1}
        quota = RedisQuota('https://owned.example.upstash.io', 'fixture-only', 'demo', clock=lambda: 100, transport=transport)
        self.assertTrue(quota.reserve()); self.assertEqual(len(calls_), 1)
        self.assertEqual(calls_[0][:1], ['EVAL']); self.assertIn(':presenter:', calls_[0][-1])
        with self.assertRaises(Invalid): RedisQuota('https://attacker.example', 'x', 'demo')

    def test_missing_quota_prevents_construction(self):
        model = []
        run = Agent(lambda: model.append(1), None, FakeTelemetry()).run({'service': 'payments', 'action': 'investigate', 'review': False})
        self.assertEqual(run['outcome'], 'quota_not_configured'); self.assertEqual(model, [])

    def test_store_failure_is_closed_and_redacted(self):
        class Broken:
            def reserve(self): raise RuntimeError('private-token-do-not-echo')
        run = Agent(lambda: None, Broken(), FakeTelemetry()).run({'service': 'payments', 'action': 'investigate', 'review': False})
        self.assertEqual(run['model_calls'], 0); self.assertEqual(run['outcome'], 'failed')
        self.assertNotIn('private-token', json.dumps(run))


class AgentTests(unittest.TestCase):
    def run_model(self, replies, review=False):
        model, telemetry = FakeModel(replies), FakeTelemetry()
        run = Agent(lambda: model, LocalQuota(), telemetry).run({'service': 'payments', 'action': 'investigate', 'review': review})
        return run, model, telemetry

    def test_real_role_handoff_with_global_three_call_budget(self):
        run, model, telemetry = self.run_model([reply(tools=calls()), reply('Cause unconfirmed; inspect the diff.'), reply('No cause established. Keep read-only checks.')], True)
        self.assertEqual(run['outcome'], 'completed'); self.assertEqual(run['model_calls'], 3)
        self.assertEqual(run['review_status'], 'completed'); self.assertEqual(run['usage']['total'], 360)
        self.assertFalse(model.requests[-1]['tools'])
        self.assertNotIn('tool', [m['role'] for m in model.requests[-1]['messages']])
        self.assertIn('agent.reviewer', telemetry.names); self.assertIn('tool.release_diff', telemetry.names)
        self.assertEqual([a['role'] for a in run['agents']], ['investigator', 'investigator', 'reviewer'])
        self.assertEqual([a['model_calls'] for a in run['agent_summaries']], [2, 1])
        self.assertEqual([a['usage']['total'] for a in run['agent_summaries']], [240, 120])

    def test_reviewer_not_run_when_investigator_uses_budget(self):
        one = calls()
        run, model, _ = self.run_model([reply(tools=one[:1]), reply(tools=one[1:]), reply('Cause remains unconfirmed.')], True)
        self.assertEqual(len(model.requests), 3); self.assertEqual(run['review_status'], 'not_run_budget')
        self.assertIsNone(run['review'])

    def test_no_fake_answer_without_tool_evidence(self):
        run, _, _ = self.run_model([reply('Invented answer')])
        self.assertEqual(run['outcome'], 'failed'); self.assertIsNone(run['answer'])

    def test_service_scope_and_unknown_tools_are_rejected(self):
        for tool_calls in (calls('catalog'), [{'id': 'x', 'type': 'function', 'function': {'name': 'shell', 'arguments': '{}'}}]):
            run, _, _ = self.run_model([reply(tools=tool_calls)])
            self.assertEqual(run['outcome'], 'failed'); self.assertEqual(run['model_calls'], 1)

    def test_duplicate_tool_fields_rejected(self):
        t = calls(); t[0]['function']['arguments'] = '{"service":"payments","service":"catalog"}'
        run, _, _ = self.run_model([reply(tools=t)])
        self.assertEqual(run['outcome'], 'failed')

    def test_provider_error_is_not_retried_or_exposed(self):
        run, model, _ = self.run_model([RuntimeError('secret-provider-header')])
        self.assertEqual(len(model.requests), 1); self.assertEqual(run['model_calls'], 1)
        self.assertIsNone(run['usage']); self.assertNotIn('secret-provider-header', json.dumps(run))

    def test_partial_usage_does_not_masquerade_as_run_total(self):
        run, _, _ = self.run_model([reply(tools=calls()), RuntimeError('failed')])
        self.assertIsNone(run['usage']); self.assertIsNone(run['cost'])

    def test_unknown_usage_or_model_keeps_cost_unknown(self):
        run, _, _ = self.run_model([reply(tools=calls(), usage=False), reply('Cause unconfirmed.')])
        self.assertIsNone(run['cost']); self.assertIsNone(run['usage'])
        self.assertIsNone(cost_estimate('unknown', {'input': 1, 'output': 1, 'total': 2}))
        self.assertIsNone(cost_estimate(MODEL, {'input': 272001, 'output': 1, 'total': 272002}))
        self.assertIsNone(reported_usage({'prompt_tokens': True, 'completion_tokens': 1}))

    def test_reviewer_cannot_invoke_tools(self):
        run, _, _ = self.run_model([reply(tools=calls()), reply('Cause unconfirmed.'), reply(tools=calls())], True)
        self.assertEqual(run['outcome'], 'failed'); self.assertIsNone(run['review'])

    def test_late_provider_result_is_not_accepted(self):
        clock = [0]
        class Late:
            def complete(self, *args, **kwargs):
                clock[0] = 40
                return reply(tools=calls())
        run = Agent(lambda: Late(), LocalQuota(), FakeTelemetry(), clock=lambda: clock[0]).run({'service': 'payments', 'action': 'investigate', 'review': False})
        self.assertEqual(run['outcome'], 'failed'); self.assertEqual(run['model_calls'], 1)
        self.assertIsNone(run['answer'])

    def test_gateway_owns_model_endpoint_and_cap(self):
        seen = []
        def transport(url, data, headers, **kw): seen.append((url, data)); return reply('test')
        Gateway('fixture-key', transport).complete([], tools=False, timeout=3)
        self.assertEqual(seen[0][0], 'https://ai-gateway.vercel.sh/v1/chat/completions')
        self.assertEqual(seen[0][1]['model'], MODEL); self.assertEqual(seen[0][1]['max_tokens'], 900)
        self.assertNotIn('tools', seen[0][1]); self.assertNotIn('service_tier', seen[0][1])


class TelemetryTests(unittest.TestCase):
    def test_not_configured_is_not_acknowledged(self):
        t = Telemetry({})
        self.assertEqual(t.finish()['status'], 'not_configured')
        self.assertEqual(t.finish()['readback'], 'not_verified')

    def test_invalid_origin_does_not_create_transport(self):
        for origin in ('http://example.test', 'https://user:pass@example.test', 'https://example.test/path', 'https://[', 'https://example.test:bad', 'https://example.test:99999'):
            t = Telemetry({'LANGFUSE_BASE_URL': origin, 'LANGFUSE_PUBLIC_KEY': 'fixture', 'LANGFUSE_SECRET_KEY': 'fixture'})
            self.assertEqual(t.finish()['status'], 'invalid_configuration')

    def test_actual_sdk_spans_export_only_allowlisted_metadata_once(self):
        try:
            from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
        except ImportError:
            self.skipTest('Install the pinned OTel requirements for SDK serialization verification.')
        sends = []
        def sender(url, body, headers): sends.append((url, body, headers)); return 200
        t = Telemetry({'LANGFUSE_BASE_URL': 'https://cloud.langfuse.com', 'LANGFUSE_PUBLIC_KEY': 'fixture-public', 'LANGFUSE_SECRET_KEY': 'fixture-secret'}, sender)
        if t.tracer is None: self.fail('SDK unavailable despite protobuf dependency')
        with t.span('opsdesk.run', {'langfuse.observation.type': 'agent', 'prompt': 'must-not-export'}) as root:
            with t.span('agent.investigator', {'status': 'completed', 'user.email': 'never-export'}): pass
            t.set(root, {'status': 'completed', 'authorization': 'never-export'})
        result = t.finish()
        self.assertEqual(result['status'], 'acknowledged'); self.assertEqual(result['span_count'], 2)
        self.assertEqual(result['readback'], 'not_verified'); self.assertEqual(len(sends), 1)
        decoded = ExportTraceServiceRequest(); decoded.ParseFromString(sends[0][1])
        dump = str(decoded)
        for forbidden in ('must-not-export', 'never-export', 'fixture-secret', 'fixture-public', 'user.email', 'prompt'):
            self.assertNotIn(forbidden, dump)
        self.assertIn('agent.investigator', dump)
        self.assertIn('x-langfuse-ingestion-version', sends[0][2])

    def test_export_failure_not_retried_or_exposed(self):
        try:
            import opentelemetry.sdk.trace
        except ImportError: self.skipTest('Pinned SDK required')
        attempts = []
        def sender(*args): attempts.append(1); raise RuntimeError('credential-bearing-error')
        t = Telemetry({'LANGFUSE_BASE_URL': 'https://cloud.langfuse.com', 'LANGFUSE_PUBLIC_KEY': 'fixture', 'LANGFUSE_SECRET_KEY': 'fixture'}, sender)
        with t.span('opsdesk.run', {}): pass
        result = t.finish()
        self.assertEqual(attempts, [1]); self.assertEqual(result['status'], 'failed')
        self.assertNotIn('credential', json.dumps(result))


if __name__ == '__main__': unittest.main()
