# OpsDesk cloud handoff — complete with your coding agent

Work in the existing OpsDesk app. Read project instructions, source and private
status first. Preserve the working baseline. Fill the sections below from actual
evidence, using placeholders in shareable copies. Never insert presenter bindings.
This template is a review packet; it neither authorizes deployment nor proves it.

## 1. What works today?
- Source revision / dependency lock:
- Current frontend and server runtime:
- Actual model / native tool support:
- Create/search/select/analysis evidence:
- Security-stop evidence:
- Telemetry export and independent readback evidence, separately:
- Known failure / unresolved acceptance:

## 2. What would move to OCI?
- Frontend stays here:
- App server / bridge stays or moves here:
- Agent container entrypoint and API contract:
- Adapter from the current app request/response to the hosted endpoint:
- Runtime configuration versus active image deployment:
- Native build architecture and approved artifact identity:

Use OCI-HOSTING.md and API-CONTRACT.md. Inspect the actual implementation; do not
assume the Lovable native TypeScript backend is the hosted Python coordinator.

## 3. How does access work?
- Browser authentication:
- Server authentication to the hosted endpoint:
- Runtime identity, least-privilege tool scope and network path:
- Private secret references, never values:
- Exact resource scope and approval required before changes:

Do not build, push, create IAM/resources, activate a deployment, change networking
or buy services from this exercise alone. Resolve the learner's own target and
obtain its applicable authority before live actions. Do not disable authentication.

## 4. How will you verify it?
Record separate statuses for source, local tests, configured runtime and provider
acceptance. A health check or an ACTIVE resource is not full acceptance.

| Check | Required evidence | Actual status |
|---|---|---|
| App | authenticated synthetic invocation and correct response | pending |
| Security | explicit policy stop, zero model calls | pending |
| Langfuse | exact trace/session and expected observations | pending |
| OCI APM, if configured | exact correlated trace/spans | pending |
| Log Analytics, if configured | exact structured event readback | pending |
| Rollback | documented trigger and verified prior artifact path | pending |

Without cloud access, submit this packet as design-only. Preserve the local app.
No model call should be repeated merely to repair telemetry. No public screenshot
may contain accounts, secrets, private URLs, identifiers or unrelated records.

## 5. Who runs and stops it?
- Resource / security / cost owners:
- Approved usage bounds and retention:
- Rollback trigger and prior artifact:
- Exact stop/cleanup inventory, held privately:
- Next operator's start, verification and stop instructions:

## Acceptance discussion

Explain the browser → server → hosted agent path in plain language. Point to the
actual runtime and authentication contract. Identify which evidence proves each
telemetry destination, and which is still unavailable. Keep the handoff reviewable
without creating resources or claiming a deployment you did not perform.
