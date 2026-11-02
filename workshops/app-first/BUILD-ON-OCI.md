# Build OpsDesk on OCI — agent instructions

## Outcome
Continue the learner's existing OpsDesk app using OCI Enterprise AI capabilities.
Preserve the visible inbox, ticket form, search, filter and selection. Implement a
server-side provider adapter and a bounded agent harness. This brief is a build
contract, not permission to use credentials, incur charges or deploy.

## Read first
- Existing app instructions, source, tests and private learner-approved app plan.
- [Official Enterprise AI skills](https://github.com/oracle/skills/tree/main/oci/enterprise-ai).
- [Agent approaches](https://docs.oracle.com/en-us/iaas/Content/generative-ai/agents.htm).
- [Responses API quick start](https://docs.oracle.com/en-us/iaas/Content/generative-ai/get-started-agents.htm).
- [Managed hosting](https://docs.oracle.com/en-us/iaas/Content/generative-ai/deploying-agents.htm).

## Scope and inputs
Have the learner select their OCI compartment, region, Generative AI project,
available model, authentication method, retention and spending boundary. Keep
actual identifiers and credentials private. Discover current model availability;
do not copy a presenter model ID or endpoint. Use IAM-supported runtime identity
where appropriate instead of embedding long-lived credentials.

## Implement incrementally
1. Inspect the existing app. Save a private baseline and the checks already passed.
2. Add a server-only OCI Responses API adapter using the current official SDK and
   authentication instructions. Keep the existing provider adapter separate so
   failures do not silently switch provider or billing account.
3. Use synthetic tasks and only the fixed service_health/release_diff tools.
   Validate service and argument schemas; expose no arbitrary URL, shell or write
   tool. Cap calls and output. Stop explicit change requests before inference.
4. Enforce app authentication, Origin/schema/body limits and an atomic hosted
   quota. Preserve honest missing-configuration and error states.
5. Add Conversations, File Search, vector stores or project memory only when the
   product needs them. Filter retrieval by caller access and review retention.
6. Add allowlisted OpenTelemetry spans and structured events without raw ticket,
   prompt, answer, identity or credential contents. Configure each chosen exporter
   separately; do not assume an OCI deployment automatically configures Langfuse,
   APM or Log Analytics.
7. Show actual returned model, reported tokens and measured duration. Cost needs
   dated, matching rates and explicit assumptions; unknown cost stays unknown.
8. Run isolated tests. Do not call real providers or read private keys in tests.

## Hosting packet — prepare before applying
Use the documented OCI Generative AI hosted application/deployment route when a
custom managed runtime is needed. Prepare the container image contract and OCI
Container Registry reference; application authentication, endpoint, networking,
scaling and storage decisions; runtime identity and narrow IAM requirements;
spend estimate; image rollback; and resource cleanup/retention plan. Obtain the
owner's exact approval before creating, changing or activating cloud resources.
Do not substitute an unreviewed public endpoint or remove authentication.

## Live acceptance — separate from source tests
After authorization, make one bounded synthetic model call, record its actual
answer/tools/usage, and stop on failure without an automatic paid retry. Match
its exact trace and random session independently in the learner's Langfuse
project. Verify the same operation separately in OCI APM and Log Analytics when
configured. Confirm the hosted identity boundary and repeat the visible app
journey plus a zero-model policy-stop case. Missing evidence stays unverified.

## App continuity checkpoint
Keep the same app and repeat earlier checks. Record source revision, commands,
observed results, missing evidence and the next safe action in a private handoff.
No cloud resources or inference are created by reading this guide.

## Observability references
- [OCI APM](https://docs.oracle.com/en-us/iaas/application-performance-monitoring/home.htm)
- [Log Analytics](https://docs.oracle.com/en-us/iaas/log-analytics/home.htm)
- [Connect Langfuse](langfuse.html)
- [Read a trace](langfuse-basics.html)
- [Model guardrails](https://docs.oracle.com/en-us/iaas/Content/generative-ai/guardrails.htm)
