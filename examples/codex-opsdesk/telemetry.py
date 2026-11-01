"""Isolated OpenTelemetry spans, allowlisted metadata, one explicit OTLP export."""
import base64
from contextlib import contextmanager
import secrets
from urllib.parse import urlsplit
from urllib.request import Request, build_opener
from security import NoRedirect

ATTRS = frozenset(('langfuse.observation.type', 'langfuse.session.id', 'status', 'model_calls',
                   'tool.name', 'gen_ai.request.model', 'gen_ai.response.model',
                   'gen_ai.usage.input_tokens', 'gen_ai.usage.output_tokens'))


class Telemetry:
    def __init__(self, config, sender=None):
        self.session = secrets.token_hex(16)
        self.provider = self.exporter = self.tracer = None
        self.sender = sender or self._send
        self.config, self.error = None, None
        values = [config.get(n, '') for n in ('LANGFUSE_BASE_URL', 'LANGFUSE_PUBLIC_KEY', 'LANGFUSE_SECRET_KEY')]
        if not any(values):
            return
        try:
            parsed = urlsplit(values[0])
            parsed_port = parsed.port  # Force malformed/invalid port validation before transport.
            valid = (all(type(v) is str and v for v in values) and parsed.scheme == 'https'
                     and bool(parsed.hostname) and not parsed.username and not parsed.password
                     and parsed.path in ('', '/') and not parsed.query and not parsed.fragment
                     and (parsed_port is None or parsed_port > 0))
        except (ValueError, TypeError):
            valid = False
        if not valid:
            self.error = 'invalid_configuration'; return
        try:
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace.export import SimpleSpanProcessor
            from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
            self.exporter = InMemorySpanExporter()
            self.provider = TracerProvider(resource=Resource({'service.name': 'opsdesk-codex-cli'}))
            self.provider.add_span_processor(SimpleSpanProcessor(self.exporter))
            self.tracer = self.provider.get_tracer('opsdesk.portable', '1.0')
            self.config = (values[0].rstrip('/') + '/api/public/otel/v1/traces', values[1], values[2])
        except ImportError:
            self.error = 'sdk_unavailable'

    @contextmanager
    def span(self, name, attributes):
        if self.tracer is None:
            yield None; return
        safe = {k: v for k, v in attributes.items() if k in ATTRS}
        safe['langfuse.session.id'] = self.session
        # SDK's automatic exception recording is disabled: error text may contain private data.
        from opentelemetry.context import Context
        kwargs = {'context': Context()} if name == 'opsdesk.run' else {}
        with self.tracer.start_as_current_span(name, attributes=safe, record_exception=False,
                                               set_status_on_exception=False, **kwargs) as span:
            yield span

    @staticmethod
    def set(span, attributes):
        if span:
            for key, value in attributes.items():
                if key in ATTRS:
                    span.set_attribute(key, value)

    @staticmethod
    def trace_id(span):
        return format(span.get_span_context().trace_id, '032x') if span else None

    @staticmethod
    def _send(url, body, headers):
        request = Request(url, data=body, headers=headers, method='POST')
        with build_opener(NoRedirect).open(request, timeout=5) as response:
            # Never decode or expose response body, headers, or raw exceptions.
            return response.status

    def finish(self):
        if self.error:
            return {'status': self.error, 'readback': 'not_verified'}
        if not self.config:
            return {'status': 'not_configured', 'readback': 'not_verified'}
        try:
            from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans
            spans = self.exporter.get_finished_spans()
            payload = encode_spans(spans).SerializeToString()
            url, public, secret = self.config
            # Credentials only enter the approved server transport; no printed derived value.
            basic = base64.b64encode((public + ':' + secret).encode()).decode()
            status = self.sender(url, payload, {'Content-Type': 'application/x-protobuf',
                'Authorization': 'Basic ' + basic, 'x-langfuse-ingestion-version': '4'})
            return {'status': 'acknowledged' if 200 <= status < 300 else 'failed',
                    'http_status': status, 'span_count': len(spans), 'readback': 'not_verified',
                    'session_label': self.session}
        except Exception:
            return {'status': 'failed', 'readback': 'not_verified'}
        finally:
            self.provider.shutdown()
