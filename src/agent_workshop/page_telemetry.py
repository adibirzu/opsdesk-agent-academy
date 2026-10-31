"""APM-only, privacy-bounded tracing for workshop web pages."""
from contextlib import contextmanager

from .observability import Observer


_APM_KEYS = frozenset({"enabled", "apm_endpoint", "apm_key_env", "allowed_hosts", "service_name"})


class PageTelemetry:
    """Own one process-scoped page observer for a service handler class."""

    def __init__(self, settings=None, *, provider=None):
        settings = settings or {}
        self.observer = None
        # Page spans are deliberately APM-only. Langfuse settings never cross
        # this boundary, and an incomplete APM configuration creates no spans.
        if (settings.get("enabled") and settings.get("apm_endpoint") and
                settings.get("apm_key_env")):
            apm_settings = {key: value for key, value in settings.items() if key in _APM_KEYS}
            base_name = settings.get("service_name", "agent-workshop")
            apm_settings["service_name"] = base_name if base_name.endswith("-http") else base_name + "-http"
            self.observer = Observer(apm_settings, provider=provider)

    @property
    def enabled(self):
        return self.observer is not None

    def trace_id(self):
        return self.observer.trace_id() if self.observer else None

    @contextmanager
    def span(self, method, route):
        if not self.observer:
            yield None
            return
        from opentelemetry.trace import SpanKind
        with self.observer.span("http.server.request", {
                "http.method": method, "http.request.method": method, "http.route": route}, kind=SpanKind.SERVER) as span:
            yield span

    def close(self):
        return self.observer.close() if self.observer else None
