# Guardrails belong in the execution path

Use the local synthetic app and isolated tests only. This is an implementation map, not a claim of general attack resistance or production readiness.

| Boundary | Existing local control | Evidence to inspect | Remaining limitation |
|---|---|---|---|
| HTTP request | Exact Host/Origin, bounded JSON and strict schemas | studio.make_server | Loopback app; not public production authentication |
| Session/ticket | Opaque server session and session-owned JSON ticket lookup | Session; desk_backend; test_desk_backend.py | No durable enterprise user/tenant directory |
| Before inference | Explicit change intent returns approval_required before model construction | Studio.run; zero-step policy test | Terminal stop; no approval/resume workflow |
| Tool proposal | Exact registry, argument schema and duplicate-field rejection | SCHEMAS; _unique_fields; _validate | Does not classify every malicious natural-language instruction |
| Tool powers | Narrow synthetic read handlers; no shell or infrastructure writes | Registered tool handler code | Real connectors need their own identity and least-privilege design |
| Consumption | Step/context/output bounds, timeouts and reported-token checks | Studio/StreamingModel | Unknown usage and provider billing prevent an absolute spend guarantee |
| Retrieved text | Prompt identifies it as untrusted; code still limits tools | SYSTEM and tool dispatch | Prompt guidance is not a guaranteed injection filter |
| Display | textContent rather than HTML interpretation | web/desk.js and studio.js | No semantic safety, grounding or PII/DLP filter; streaming output is already visible |
| Telemetry | Studio rejects content capture; explicit destinations and key references | Settings.load and Observer | Metadata can still be sensitive; verify the intended project independently |

## Explain the layers

Input checks establish shape and scope. Authorization controls the action. Tool validation controls execution. Output handling controls how a result reaches the user. Telemetry records those decisions; it does not grant permission or replace enforcement.

Do not call the model's refusal a guardrail unless the relevant executable action was actually blocked. A prompt can ask for a change while using query intent; read-only registered capabilities must still prevent writes. The zero-generation demonstration applies specifically to the explicit change-intent branch.

## Local verification

From the repository root after installing the studio extra:

```sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_desk_backend.py' -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_studio.py' -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_studio_recovery.py' -v
```

These tests use isolated HTTP servers and explicit model doubles. They prove specific contracts, not a live provider's policy behavior. For a real model exercise, use only the configured synthetic scenario, preserve the actual answer and distinguish unsafe generated wording from unauthorized handler execution.

## Extend the same app in Part 5

1. Inspect current app authentication and session ownership; do not confuse an opaque cookie with enterprise login.
2. Add focused negative tests before changing tool permissions. Preserve the working create/select/analyze journey.
3. For future privileged tools, design user-bound approval, expiry, replay protection and reauthorization before adding a resume API. None is supplied by the terminal workshop stop.
4. If content moderation, sensitive-data detection or grounding checks are required, choose an explicit policy and verify it with positive/negative cases. Decide how streamed tokens are buffered or gated before display. Do not claim a regex or one model-based judge guarantees prevention.
5. Preserve denial, timeout, model/tool failure and export-failure outcomes. Never turn them into a canned success.
6. Verify least-privilege service credentials, egress/network policy, dependency/image provenance and production identity separately for cloud hosting.

Read [OWASP prompt-injection guidance](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) and [Part 5](part-5-secure-by-construction.html). Awareness guidance is not proof of implementation.
