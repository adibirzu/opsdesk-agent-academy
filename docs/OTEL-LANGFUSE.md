# Add the trace behind the button

Participants click Analyze safely first. Then explain the invisible path:
app action → agent → authorization → real model/tool calls → answer. The local
reference already uses the shared OpenTelemetry Observer; no additional local
collector daemon is required for this exporter path.

## What to show in code

Open `src/agent_workshop/studio.py` and `observability.py`. Use this source map:

```sh
rg -n 'agent.run|security.authorize|llm.complete|tool\.|gen_ai.usage' \
  src/agent_workshop/studio.py
rg -n 'OTLPSpanExporter|langfuse.session.id|x-langfuse-ingestion-version|def flush' \
  src/agent_workshop/observability.py
```

Explain the small shape of the change (an excerpt, not a standalone runnable app):

```python
with observer.span("agent.run", {"session.id": session_id,
        "langfuse.session.id": session_id}):
    with observer.span("llm.complete", {
            "langfuse.observation.type": "generation"}) as span:
        reply = model.complete(messages, tools, emit)
        span.set_attribute("gen_ai.response.model", reply.model)
        if reply.input_tokens is not None:
            span.set_attribute("gen_ai.usage.input_tokens", reply.input_tokens)
```

The actual loop also records output usage, individual tool spans, authorization,
failures and limits. A generation must wrap each real model call, not the entire
agent loop. Session context propagates to children. The app browser sees run
metadata; the private project credentials remain in the runtime.

## Configure your own project

Keep the Studio TOML private with mode 0600. Set the telemetry table to your own
endpoint and key environment references; never publish real keys or a presenter's
private destination. A participant template is `telemetry.example.toml`.
Use `--secrets /private/path/keys.env` only with the operator's own 0600 file.

The existing exporter posts HTTP/protobuf to
`<LANGFUSE_BASE_URL>/api/public/otel/v1/traces`, with server-side Basic authentication
for the project pair and `x-langfuse-ingestion-version: 4`. Generic OTel base
configuration ends at `/api/public/otel`; signal-specific trace configuration
includes `/v1/traces`. Do not append that suffix twice.

## The three receipts

1. **Local:** exact run/session/trace in the private record, including errors.
2. **Delivery:** the exporter attempted delivery and reports its result.
3. **Backend:** an independent query finds this exact trace/session and the
   expected generation/tool or zero-generation authorization observation.

Click Check exact trace in the reference after an actual run. If delivery or
readback fails, keep the failed record; do not show a prerecorded trace as new.
Readback alone does not prove that an answer is grounded or safe.

## Security and cost lesson

This workshop exports metadata only, excluding ticket text, prompts, answers,
tool payloads, credentials and hidden reasoning. That reduces content-level
debugging and evaluation visibility intentionally. Do not enable automatic SDK
content capture merely to get a richer screenshot. Token counts are provider
reports or unknown; prices require explicit matching rates and are estimates.
OTel records the boundary; it does not enforce a tool permission by itself.

Official references, checked 2026-10-31:
[Langfuse native OpenTelemetry](https://langfuse.com/integrations/native/opentelemetry),
[trace structure and observations](https://langfuse.com/docs/observability/best-practices).
