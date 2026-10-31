# Practical choices and troubleshooting

These are engineering recommendations for the workshop, not measured claims that
one provider/model is best. Choose from the participant's permitted, working
models. Prove streaming and native tools before adding more architecture.

## Choose a model route

| Route | Useful when | Verify before presenting |
|---|---|---|
| Existing Ollama model | You want laptop-owned inference | Model is installed and fits memory; chosen model supports tools; OpenAI-compatible streaming works |
| Existing LM Studio server | You prefer a local model/server interface | Exact model ID, server binding/auth and native tool behavior |
| Owned LiteLLM gateway | You already operate models behind a common endpoint | Correct URL/key/model allowlist; actual deployment available; no unintended paid fallback |
| Approved HTTPS provider | You prefer external inference | Explicit data destination, key, model compatibility, rates and spending controls |

Do not assume API compatibility guarantees every model or every option. The
workshop uses the OpenAI-compatible chat-completions stream and native tool calls,
not each provider's separate native API. Inspect actual returned usage and IDs.
Use loopback or an approved trusted path; the private-HTTP opt-in is not TLS.

Primary sources checked for these capabilities:
[Ollama tool calling](https://docs.ollama.com/capabilities/tool-calling),
[Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility),
[LM Studio compatibility](https://lmstudio.ai/docs/developer/openai-compat),
[Codex CLI](https://learn.chatgpt.com/docs/codex/cli),
[Langfuse OTLP](https://langfuse.com/integrations/native/opentelemetry).
These pages do not prove any participant's account or live model availability.

## Keep the design small

Start with one agent and one tool. Add retrieval when the task needs context,
a graph when branching/persistence requirements justify it, and multiple agents
only with a clear division of responsibilities and measurable benefit. A second
model or a named role is not a new identity boundary.

Keep configuration server-side. Maintain a tool allowlist and exact schemas,
bound requests/responses and calls, reject extra/duplicate arguments, and check
policy before inference. Treat retrieved text as data. Prefer a deterministic
capability boundary over a long system prompt that promises safety.

Record metadata with content capture off. Add sensitive content only after a
specific data/destination decision, not just to make a trace more interesting.
Keep prices explicitly configured and estimates separate from invoices. Never
infer a USD0 bill from missing usage, an included subscription or a local GPU.

## Diagnose the layer that actually failed

| Symptom | What it proves | Next check |
|---|---|---|
| Page loads | Local HTTP/UI works | Submit one real turn; check server and provider |
| /models returns401 | Endpoint responded, auth is missing/denied | Exact key environment binding and model access |
| Model listed but no deployment | Catalog is not inference readiness | Bound model deployment/server status, with owner authority |
| Tool text in answer but no tool span | Fluent text is not tool evidence | Actual native call and observation |
| Truncated stream | Run did not complete | Preserve partial SSE; inspect provider finish/limits; no silent retry |
| Missing usage | Provider data is incomplete | Keep null, use known lower bound and other bounds |
| Project auth succeeds, OTLP403 | Read API auth is not write-path availability | Ingestion route/edge policy with its owner; do not bypass it |
| Exporter flush succeeds, trace missing | Delivery is not backend acceptance | Exact trace/session, schema and ingestion window |
| Wrong session trace | Join/ownership failed | Reject it; do not show another session's data |
| SSH rejected | Host access is unavailable | Correct owned user/identity; do not guess accounts or reuse unrelated secrets |
| CI job never starts | No runner/test result exists | Account/execution restriction; retain local test evidence separately |

Pause only the dependent live action. Continue source, contracts, documentation
and local control demonstrations. Do not weaken a negative test, switch identities,
change edge/IAM rules, disable TLS or create a paid fallback to obtain a green demo.
Use an exact reviewed repair plan when a shared-resource change is necessary.

## Classroom pacing

A prepared reference and small fixed contracts make the session recoverable.
Timebox code generation, preserve its actual output, and announce a switch to the
reference if needed. Let the audience predict an expected failure before clicking.
Make the invisible boundary visible: no model call on policy stop, no handler on
bad arguments, no provider-verified badge on a local file.

Finish with a participant changing one safe tool, writing its negative test,
explaining the trace and naming the remaining evidence gap. This is a stronger
takeaway than watching an agent produce an impressive but ungrounded answer.
