Prepare OpsDesk's agent for OCI Generative AI Applications + Deployments. Use the
repository's existing enterprise hosting sources as references. Do not assume the
local Studio native-SSE API and the hosted LangGraph JSON API are interchangeable.
Document the app-server adapter, authenticated invocation and normalized response.

Read the applicable OCI skills and project rules. Resolve the approved account,
region, compartment, application, deployment, image repository and identity before
any cloud operation. Do read-only inspection only where it is already authorized.
Do not scan unrelated profiles, credentials, shared resources or other owners.

Produce a concrete reviewed deployment packet: configuration/secret references,
container platform and source hash, proposed image digest, scan/admission checks,
application networking/authentication, narrow IAM requirements, rollout/rollback
steps, cost/retention and the exact invocation/readback acceptance commands.
Use resource/workload identity and Vault where supported. No browser credentials.
On an ARM Mac, do not build amd64 using emulation; identify an approved native builder.

Preserve the agent's bounded tools and session/trace lineage. Configure its OTel
metadata export to the operator's own Langfuse; optional APM/Log Analytics are
separately configured and verified. Preserve failures; an ACTIVE deployment,
HTTP200 or exporter flush does not establish model or telemetry acceptance.

Do not build/push, create IAM/resources, activate a deployment or invoke a paid model
under this preparation task. Present the exact proposed resource changes and a
reviewable artifact; deployment requires the operator's current scoped authority.
