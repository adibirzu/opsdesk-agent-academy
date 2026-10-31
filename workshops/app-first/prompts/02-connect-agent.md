Connect OpsDesk's AI panel to a server-owned agent, keeping the visible app unchanged.
Use the workshop API contract and the exact operator-approved endpoint supplied
outside this prompt. Do not invent a URL, model, key or successful response.

The agent must inspect the selected synthetic incident, use read-only service_health
and release_diff if registered, separate observations from hypotheses and recommend
one safe next check. It cannot run shell, read credentials, deploy or roll back.
Use the explicitly selected model; no automatic provider or scripted fallback.

Keep credentials in your platform's server-side secret store. Browser code calls
our same-origin server function, not the provider or OCI IAM endpoint directly.
Derive session/user scope on the server; never trust a browser-supplied tenant or
permission claim. Validate ticket IDs/fields and cap body size, steps and output.

Add a Test a change request control. Enforce its change intent in code before model
construction; return approval_required without any model invocation or real change.
Implement busy, failure and unavailable-backend states. No automatic retry of AI.
Keep real failures visible and verify that creating/filtering tickets still works.
Do not expose a local server through a public tunnel or enable wildcard CORS.
