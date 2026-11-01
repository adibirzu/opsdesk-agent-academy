# Builder trace checklist — what works and what still needs a backend

The same app contract can be implemented in several builders. Their backend
capabilities are different. **Three Langfuse configuration values do not create
OpenTelemetry instrumentation or prove that a trace arrived.**

## Current evidence

| Route | Verified now | Still required before claiming end-to-end traces |
| --- | --- | --- |
| Lovable | The selected Sol-model run was independently found in Langfuse: six observations, including two generations. Reviewed app and provider checkpoints are available. | Every new run must still be matched by its own exact trace and session. This does not prove OCI APM or Log Analytics delivery. |
| v0 | Builder-generated frontend/source comparison; direct browser frontend acceptance remains unverified. | Supported authenticated backend, atomic per-user quota enforcement, compatible instrumentation, one authorized native-model canary and independent exact trace readback. Do not expose inference before these controls work. |
| Base44 | The synthetic frontend has been rehearsed. | The current plan does not provide the required server-functions/secrets capability for this integration. Native-model and trace acceptance are not complete. Use the existing Lovable route or the local Codex example if those capabilities are unavailable; no purchase or upgrade is required by this checklist. |
| Codex / CLI | Thirty-five isolated tests verify the reviewed local implementation. | A learner-owned real app-model binding and telemetry configuration, one authorized live canary and independent exact trace readback. Tests are not live provider acceptance. |

## Common finish line

1. Keep the same learner-owned OpsDesk app. Use only synthetic incidents.
2. Create or select your **own separate Langfuse project for this builder/runtime**.
   Do not share a presenter’s keys or reuse another learner’s project.
3. Inspect the backend before adding secrets. It needs an authenticated server
   action, atomic per-user quota reservation, bounded model/tool calls and an
   early change-request stop. Browser code must not invoke an unprotected model.
4. Implement compatible server-side OTel/Langfuse instrumentation. Create a root
   agent span and the actual authorization, model and tool spans. Preserve causal
   parent/child relationships, random session correlation and exact trace IDs.
   Keep missing token/cost fields unknown. Never manufacture model/tool events.
5. Add these values **only in that runtime’s supported server Secrets/configuration**:

   ```text
   LANGFUSE_BASE_URL=<YOUR_LANGFUSE_ORIGIN>
   LANGFUSE_PUBLIC_KEY=<YOUR_PROJECT_PUBLIC_KEY>
   LANGFUSE_SECRET_KEY=<YOUR_PROJECT_SECRET_KEY>
   ```

   Use narrowly scoped ingestion access where supported. Keep values out of
   builder chat, source code, browser variables, screenshots and logs. Do not
   export directly from the browser or embed a project read credential.
6. Verify configuration presence without printing values. Run isolated tests for
   anonymous denial, quota enforcement, tool schemas, bounded calls, policy stops,
   missing configuration and exporter failure. Do not turn off authentication or
   broaden CORS to get a green result.
7. With applicable authority and available credits, run **one** synthetic normal
   investigation. Do not retry paid inference automatically. Record the actual
   returned model, tool events, reported usage and safe export status privately.
8. Copy the exact trace ID and random session label privately. In the signed-in
   Langfuse owner UI, select the correct project and independently match both.
   Inspect the real tree, status, model generations, tools and reported usage.
   An exporter acknowledgment or HTTP 200 alone is not this check.
9. Test the explicit change-request stop. It must report `approval_required` and
   zero model calls. If the blocked path is instrumented, expect an agent/policy
   trace without fabricated generations. Keep this separate from a normal run.
10. Review privacy: exported metadata must not contain ticket text, prompts,
    answers, identities, credentials or private infrastructure details. Keep raw
    receipts private. Report each destination separately: Langfuse acceptance
    cannot substitute for OCI APM or Log Analytics readback.

## Apply it to your builder

### Lovable — use the working server pattern

Follow [Connect Langfuse](langfuse.html), then [Read a trace](langfuse-basics.html).
Inspect the actual [reference app server instrumentation](https://github.com/adibirzu/opsdesk-agent-academy/blob/main/reference-app/src/lib/langfuse.server.ts)
and [bounded agent](https://github.com/adibirzu/opsdesk-agent-academy/blob/main/reference-app/src/lib/opsdesk-agent.server.ts).
These are implementation references, not portable credentials or a guarantee
that every builder supports the same APIs. Complete the
[Lovable route](lovable.html) in your own project.

### v0 — finish the protected backend first

Preserve the existing frontend. Ask the coding agent to implement the common
finish line using the runtime actually available to your v0 project. Review its
session validation, atomic quota storage, server-only secrets and model/tool
adapter before making a model call. Port the reference instrumentation to that
server API; do not paste Lovable-specific wrappers unchanged. When prerequisites
are missing, stop the live acceptance claim and use the verified Lovable example
for the demonstration.

### Base44 — respect the current plan’s capability boundary

Check whether your existing plan exposes supported server functions and Secrets.
The current rehearsal account cannot complete this server integration on its
present plan. Do not paste keys into a chat or client bundle as a workaround.
Keep the frontend checkpoint and continue using the existing Lovable route or
local Codex implementation. Buying or upgrading a plan is not an automatic step.

### Codex / CLI — local tests, then a separately authorized live run

Use the [Codex and CLI guide](CODEX-CLI-DEMO.md) and inspect
[the local example](https://github.com/adibirzu/opsdesk-agent-academy/tree/main/examples/codex-opsdesk).
Run its documented tests and launch commands. Supply your own runtime model and
Langfuse project only through supported private server configuration. The coding
model is not automatically the app model. A passing local test suite does not
create an authenticated remote backend or a provider trace.

## Keep the handoff honest

For each route, record: app baseline; tests passed; model/backend availability;
export acknowledgment; exact independent Langfuse readback; known blockers.
Mark missing gates **pending**, not “connected.” Downloaded video chapters show
edited narrated checkpoints and clearly labelled gaps; they do not make an
unconfigured learner runtime work.
