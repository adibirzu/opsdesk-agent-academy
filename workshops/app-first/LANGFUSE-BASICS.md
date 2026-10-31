# Lab: Follow one agent run

## Agent instructions — complete this lab with the learner

Use the same OpsDesk app and the learner's own approved Langfuse project. Read the
app's instructions and preserve its working model, auth, quotas and tool scope.
This is a 20-minute read-only walkthrough of an existing trace; do not generate
more inference simply to obtain screenshots. Never copy presenter credentials.

1. Open lovable.html#connect-traces and langfuse-basics.html. Explain where the
   app, harness, OpenTelemetry exporter and Langfuse each participate.
2. Inspect one existing completed app run. If necessary build the visible Agent
   trace panel from real execution events. Label local recording, export result
   and independent provider readback separately. Never invent observations.
3. If instrumentation is absent, use prompts/06-langfuse-simple.md. The learner
   enters only LANGFUSE_BASE_URL, LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in
   server Secrets, never chat, browser variables or Git. Keep ingestion-only role.
4. Run the authenticated presence-only setup check. It must make zero model and
   telemetry calls. Do not confuse presence with valid credentials or delivery.
5. Copy the real trace ID privately. Use the authenticated Langfuse owner/viewer
   UI to match it in the intended project and time range. In Tracing, layouts may
   list observations; open one to inspect its parent trace. Check the session too.
6. Expand Tree. Explain the root, access check, actual generations and tools.
   Two generations are not two agents. For the recorded example, expect 6
   observations: root, authorization, generation 1, service_health, release_diff,
   generation 2. Do not force the learner's trace into that shape.
7. Select Timeline. Identify the slower model call. Do not add overlapping
   durations. A 0 ms display may be rounding, not absent execution.
8. Select a generation and inspect its token breakdown, returned model and
   metadata. Recorded generation 1: 311 input, 48 output, total 359. Generation 2:
   450 input, 139 output, total 589. Total run: 948. These are historical receipts,
   not expected fixed outputs. Cost inferred from model rates is not an invoice.
9. Check all observed input/output and attributes. This workshop exports metadata
   only. Exclude identity, credentials, private endpoints, prompts/answers, ticket
   text and raw tool payloads. Do not expose hidden chain-of-thought.
10. Explain missing-config, invalid-config, failed/partial export and acknowledged
    without readback. Diagnose before rerunning. No widening access or weakening
    destination validation. An ingestion key cannot power a read dashboard.
11. Capture only explicitly selected app/trace regions. Review pixels before
    sharing: exclude name, email, profile photo, project/trace/session IDs, keys,
    browser address bars and unrelated records. Keep originals private.
12. Save a private acceptance record: exact run correlation, observed shape,
    reported usage, export status, provider readback, privacy check, limitations.
    Mark learner checkboxes self-reported, never provider acceptance.

## If a new live run is needed

Describe the exact model, synthetic input, destination and bounded call count.
Obtain any applicable usage approval. Run once and read that exact trace back;
do not retry inference automatically. Do not create accounts, keys, permissions,
resources, paid upgrades or public access without the learner's authority.

## Deliver

A learner who can find a trace, explain its steps/time/usage, separate calculated
cost from billing, and state what is intentionally excluded. Do not claim OCI APM,
Log Analytics, cloud hosting or universal security acceptance from this lab.

Official references:
- https://langfuse.com/docs/observability/best-practices
- https://langfuse.com/docs/observability/features/token-and-cost-tracking
- https://langfuse.com/docs/observability/features/trace-ids-and-distributed-tracing

## Verified zero-model policy trace

The latest rehearsal also matched the exact policy trace/session independently in
Langfuse. It contains two observations (agent root and authorization), no generation
nodes, root status approval_required and model_calls 0. See
[the real app and provider screenshots](lovable.html#verified-policy-trace).
Authorization to invoke the app and permission to execute a requested change are
different decisions. Repeat this check in the learner's own project.

The reference transport uses manual no-follow redirects: inspect a 3xx as a failure,
never forward credentials automatically. Select Preview on the newest completed
change card before Open preview so you test the intended runtime revision.
