# OpsDesk · Business leaders & first-time builders · Part 4

## Instructions for the agent

Extend the same working OpsDesk app. Read applicable project instructions, inspect the baseline and preserve unrelated work. Use synthetic data and the learner’s explicitly selected model. Never invent an answer, token count, trace or acceptance result. Keep credentials in private server-side configuration. Do not publish, buy credits, activate cloud services, change IAM or expand access without exact authority.

## Learner and method

No IT knowledge / C-level

Browser-first. Describe the outcome, use a builder and validate the result in plain language.

## Prerequisites

An owned builder account, available build credits and an explicitly selected app AI/backend option. No terminal is required for this route.

## Starting state

The same app with a verified model binding and usage display from Part 3.

## New capability

Correlated OTel spans, Langfuse readback and an OCI app/log integration path.

## Follow this workflow

## Words used in this route

- **Backend:** The private part of the app that calls AI and runs approved lookups; your builder can generate it.
- **Tool evidence:** Information returned by an actual permitted lookup, not a model’s guess.
- **Guardrail:** A rule enforced by the app before an action can run.

1. Create your own hosted Langfuse project or use your own existing installation. Keep its project keys private.
2. Give the builder the instrumentation prompt. Store project keys in server secrets and disable content capture.
3. Run one synthetic ticket action and find its actual trace ID in your own Langfuse project.
4. Explain local recording, delivery and readback in plain language. APM/log integration is an optional separate setup.

## Request for the implementation agent

Extend our existing OpsDesk app for Part 4: Correlated OTel spans, Langfuse readback and an OCI app/log integration path. Follow this No IT knowledge / C-level learner route. Explain the next action in plain language and use the builder UI; do not require me to run terminal commands. Implement backend checks in code, not just in a prompt. Use synthetic data and my explicitly selected backend. Never invent a successful answer, usage or trace. Keep keys in server secrets. Do not publish, buy credits, activate cloud services or change permissions without specific authority. Complete the route actions, verify actual results and report blockers honestly.

## Completion gates

- [ ] Show actual generation/tool spans and an exact Langfuse trace readback in the configured project.
- [ ] Keep existing app features working; treat APM/log delivery as separate acceptance.

## If blocked

If access, credentials or native model support are missing, preserve the working app and mark that acceptance checkpoint blocked. A local model-double test or static preview is not a real app/model/provider result.

## Handoff

Record files or builder changes, exact synthetic input, actual app outcome, start/stop or reopen steps, evidence references and unresolved gaps. Preserve the working app for the next part. Mark results as local/model-double/browser-reference/provider-verified; do not merge these evidence classes. Never claim that a successful login or preview completes the real AI journey.

## Deeper explanations

- [Langfuse OTel integration](https://langfuse.com/integrations/native/opentelemetry): Check endpoint/auth conventions and ingestion-version behavior.
- [Course implementation reference](../langfuse.html): Use the detailed setup, contracts and troubleshooting when you need the technical layer.

## First-time builder help

Start with the visible app definition in prompts/01-build-app.md. Then connect the actual AI action using prompts/02-connect-agent.md and API-CONTRACT.md. Ask your builder to implement server code through its supported backend features; a chat subscription alone is not a runtime integration. Use langfuse.html for observability and GUARDRAILS.md for enforced controls. If you require a local-code alternative, switch explicitly to the IT starter route rather than pretending the browser-only route has been executed.
