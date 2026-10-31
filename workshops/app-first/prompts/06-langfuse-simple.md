Add Langfuse visibility to this existing working AI app without rebuilding it.
I will supply only LANGFUSE_BASE_URL, LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY
through the platform's server-side secret/environment settings. Never ask me to
paste keys in this chat, expose them in browser code, use a public-prefixed env
variable, or create a new model/provider connection. Keep the app's current LLM.

Inspect the actual server execution path and any existing OpenTelemetry setup.
Reuse it; do not add duplicate spans/exporters. Use current official Langfuse
SDK/OTLP documentation and a version compatible with the selected server/runtime.
Current JS/TS SDK v6 and Python SDK v5 require Langfuse v4.59.0+; for older self-hosted
servers use a compatible supported SDK or OTLP path. Record exact dependency
versions. Do not copy a legacy ingestion API example into a new Cloud integration.

Instrument actual work: one agent root/trace per app action; a random server-owned
session label for conversation grouping; authorization; one generation for each
actual model call; validated tool calls with their actual success/failure. Record
model ID and provider-reported usage, or unknown if not available. Keep the
explicit change-intent stop before model construction and show zero generations
on that path. Do not expose hidden chain-of-thought.

Export metadata only: no names, emails, account/tenant IDs, ticket text,
prompts/answers, tool payloads, keys or private endpoints. Filter attributes before
export, including attributes added automatically by framework integrations.
Use a deliberate allowed-host destination and server-only project credentials.
Wait/flush appropriately in the actual server runtime, but do not claim that
flush success proves backend readback. Report telemetry failure separately from
AI outcome; never replace a real answer with a fake success or retry AI just to
repair a trace.

Make configuration simple: missing values display 'Langfuse not configured';
saving secrets does not run inference. After one real synthetic app action, show
the actual trace ID, export outcome and a link to the correct Langfuse project
trace when available. Independently find that exact trace/session and expected
observations in the intended project before marking 'verified'. Do not invent
IDs, screenshots, costs or delivered traces.

Test the app's existing happy path, a zero-generation change stop, a dependency
failure and missing/rejected telemetry config. Keep raw receipts private. Give me
one short setup checklist and explain exactly where the three values belong in
this platform. Do not publish, purchase, alter account-wide permissions or send
telemetry to an unapproved destination.

Add a visible Agent trace panel below the real answer, derived only from actual
run events and export results. Show local execution, calls, usage, elapsed time
and exporter status. Add Copy trace ID / Copy session label inside a collapsed
presentation-safe disclosure with copy feedback. Explain how to locate that exact
trace in the learner-owned Langfuse project. Never embed a reader key, iframe or
claim automatic independent readback. Keep raw payloads and identifiers hidden
from the default presentation view. Add isolated mapping/privacy tests.
