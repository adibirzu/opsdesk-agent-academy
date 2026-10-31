# The last ten minutes: where does the agent run?

Show **OCI Generative AI → hosted Applications + Deployments**. This is the
managed container hosting path for a custom agent runtime. The OCI Responses API
is another agent-building approach; using it is not required merely to host an
existing container. These are separate capabilities.

## Prepare before the session

Use an owned approved application/deployment, known region/compartment, selected
auth mode and approved container digest. Check current availability and permissions
in that environment. The workshop does not create IAM or resources automatically.
Never attempt an unplanned build, networking repair or paid deployment on stage.

This repository already contains `deploy/enterprise`, `src/agent_workshop/hosted.py`
and the LangGraph coordinator hosting sample. Rehearse its current image, API and
telemetry separately; historical deployment receipts are not fresh acceptance.
The new local OpsDesk reference is not automatically part of that image.

## Walkthrough, not a platform sales tour

| Time | Show | Practical question |
|---|---|---|
|0–2min|Application configuration|Which networking, identity and scaling settings does this agent use?|
|2–4min|Deployment and active image|Which reviewed source/image version is serving?|
|4–6min|Invocation endpoint and server bridge|How does the app call it without browser credentials?|
|6–8min|One bounded prepared invocation, if authorized and available|Can we join the actual response to its trace?|
|8–10min|Logs, telemetry destinations and handoff|Which receipt proves each part, and what is still missing?|

An application supplies runtime configuration. Its deployments select versions of
a container image; activating a deployment selects the running version. Preserve
the previous approved artifact for rollback and follow the deployment gate. An
ACTIVE resource or successful health check alone does not prove model/tool behavior.

The documented packaging flow is container → OCIR → application → deployment →
activation → endpoint. On this ARM Mac, use an approved native builder for amd64;
do not build it with emulation. Actual build/push/apply/activation needs scoped
resource and cost authority; this workshop guide grants none.

## Authentication the audience can understand

Browser → application server → authenticated OCI application endpoint → agent.
For OCI IAM mode, the server signs requests. For identity-domain modes, use the
selected supported OAuth/browser-session flow. Do not switch to no authentication
or embed a long-lived credential in the frontend to make a demonstration work.
Copy the endpoint from the actual application; IAM and bearer-token endpoint forms
can differ. Append the runtime's supported custom path, such as `/run`.

A public-inbound endpoint is not necessarily unauthenticated. A private endpoint
is not reachable from a SaaS builder by default. Resolve that network/server path
before the hour. See [API-CONTRACT.md](API-CONTRACT.md) for the adapter boundary.

## Observability destinations

Langfuse receives the agent's explicitly configured OTel metadata. The shared
hosted sample also has OCI APM export and Log Analytics/Monitoring integration
paths. Each needs its own configuration, permissions, export and exact readback.
The local Studio edition enables Langfuse export only; adding it does not imply
that OCI APM or Log Analytics automatically receives those local turns.

If OCI access is unavailable, use this architecture/source walkthrough and label
it as such. Do not relabel a local run or an old screenshot as a fresh deployment.

Official references, checked 2026-10-31:
- [Deploying a custom agent runtime](https://docs.oracle.com/en-us/iaas/Content/generative-ai/deploying-agents.htm)
- [Applications and deployments](https://docs.oracle.com/en-us/iaas/Content/generative-ai/applications-deployments.htm)
- [Hosted deployment activation](https://docs.oracle.com/en-us/iaas/Content/generative-ai/deployments.htm)
- [Invocation and authentication modes](https://docs.oracle.com/en-us/iaas/Content/generative-ai/use-applications.htm)
- [Responses versus hosted approaches](https://docs.oracle.com/en-us/iaas/Content/generative-ai/agents.htm)
