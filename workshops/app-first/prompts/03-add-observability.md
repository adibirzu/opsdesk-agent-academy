Instrument the agent runtime with OpenTelemetry and export metadata to the operator's
own Langfuse project. Work on server code only; never add secret keys to browser code.
Use existing framework/OTel instrumentation where available and inspect current
Langfuse docs before choosing attributes. Do not instrument the builder's internal
coding model or claim visibility into its hidden infrastructure.

One AI action gets one trace; conversation turns share a server-owned session.
Use an agent parent, a generation per real model call, authorization and tool spans.
Record actual returned model, reported input/output token usage, status and time.
Mark generation/tool observation types correctly; propagate session/run attributes
to child spans. Record failed tools even if a final answer follows.

Export metadata only: no ticket descriptions, prompts, answers, tool payloads, keys,
customer identifiers or hidden reasoning. Unknown tokens/cost stay unknown. Estimate
price only from explicit matching model rates; never call it an invoice.

Use the explicitly configured Langfuse OTLP HTTP trace endpoint and server-side
project-key authentication. Keep file recording, exporter delivery and independent
exact trace/session readback separate. Handle export errors without a fake success.
Test privacy, correlation, policy with zero model calls and export failure. Do not send real
traces until the operator configures and authorizes their destination.
