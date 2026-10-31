# OpsDesk · Business leaders & first-time builders · Part 1

## Instructions for the agent

Extend the same working OpsDesk app. Read applicable project instructions, inspect the baseline and preserve unrelated work. Use synthetic data and the learner’s explicitly selected model. Never invent an answer, token count, trace or acceptance result. Keep credentials in private server-side configuration. Do not publish, buy credits, activate cloud services, change IAM or expand access without exact authority.

## Learner and method

No IT knowledge / C-level

Browser-first. Describe the outcome, use a builder and validate the result in plain language.

## Prerequisites

An owned builder account, available build credits and an explicitly selected app AI/backend option. No terminal is required for this route.

## Starting state

A fresh learner workspace and a working, student-owned tool-capable model endpoint.

## New capability

A functional incident inbox and one real AI investigation.

## Follow this workflow

## Words used in this route

- **Backend:** The private part of the app that calls AI and runs approved lookups; your builder can generate it.
- **Tool evidence:** Information returned by an actual permitted lookup, not a model’s guess.
- **Guardrail:** A rule enforced by the app before an action can run.

1. Describe the operator and payments incident in one sentence; choose one builder and confirm available credits.
2. Paste the app definition. Click create, search, filter and select; ask the builder to fix one actual usability issue.
3. Use an explicitly selected managed AI option or a supported private server integration. Add keys only through its server-side secret UI, never the project chat.
4. Click Analyze safely on the selected ticket. Require a real answer with actual evidence, then verify loading and failure messages.

## Request for the implementation agent

Extend our existing OpsDesk app for Part 1: A functional incident inbox and one real AI investigation. Follow this No IT knowledge / C-level learner route. Explain the next action in plain language and use the builder UI; do not require me to run terminal commands. Implement backend checks in code, not just in a prompt. Use synthetic data and my explicitly selected backend. Never invent a successful answer, usage or trace. Keep keys in server secrets. Do not publish, buy credits, activate cloud services or change permissions without specific authority. Complete the route actions, verify actual results and report blockers honestly.

## Completion gates

- [ ] Create, search, filter and select an invented ticket in the actual app.
- [ ] Analyze the selected ticket using a real configured model and at least one permitted tool; display the actual answer.
- [ ] Show loading, busy and failure states without fake AI success, browser keys or automatic retries.
- [ ] Restart the app using documented commands and reproduce the core journey. Persistence beyond the documented memory lifetime is not required.

## If blocked

If access, credentials or native model support are missing, preserve the working app and mark that acceptance checkpoint blocked. A local model-double test or static preview is not a real app/model/provider result.

## Handoff

Record files or builder changes, exact synthetic input, actual app outcome, start/stop or reopen steps, evidence references and unresolved gaps. Preserve the working app for the next part. Mark results as local/model-double/browser-reference/provider-verified; do not merge these evidence classes. Never claim that a successful login or preview completes the real AI journey.

## Deeper explanations

- [Lovable quick start](https://docs.lovable.dev/introduction/getting-started): Understand the prompt → preview loop and build-credit prerequisites.
- [Course implementation reference](../replicate.html): Use the detailed setup, contracts and troubleshooting when you need the technical layer.

## First-time builder help

Start with the visible app definition in prompts/01-build-app.md. Then connect the actual AI action using prompts/02-connect-agent.md and API-CONTRACT.md. Ask your builder to implement server code through its supported backend features; a chat subscription alone is not a runtime integration. Use langfuse.html for observability and GUARDRAILS.md for enforced controls. If you require a local-code alternative, switch explicitly to the IT starter route rather than pretending the browser-only route has been executed.

## prompts/01-build-app.md

Build OpsDesk, a small incident board for an operations team. Start with the visible
app only. I should be able to click and use it before adding AI.

Create three synthetic tickets: payments is slow (high), checkout needs a health
check (medium), catalog availability check (low). Each has id, title, description,
service and priority. Show an inbox, priority filter, search, selected-ticket detail
and a New ticket form. Ticket edits stay in memory for this first exercise.

Add an Ask AI panel with Analyze safely, a result area and an initial state reading
"AI is not connected yet". Do not generate a fake AI response, pretend to authenticate
a user, or imply that a database exists. Mark all tickets as synthetic training data.

Use Oracle Redwood for a clear desktop/mobile layout: Oracle red accents, warm stone
surfaces, Georgia headings and local Figtree/system UI text. Use only approved brand
assets. Keep compact incident rows and one clear action. Make loading, empty,
validation and failure states usable. Render ticket text as text, never raw HTML.
No paid integrations, real customer data, production connectors, automatic publishing,
real model calls or secrets in this first build. Show which visible features work
and which capabilities still need a backend. Then stop for a review of the preview.

## prompts/02-connect-agent.md

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
