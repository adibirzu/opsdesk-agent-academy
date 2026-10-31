# Choose one builder

Use the same app definition in all three. The product lesson is the same; account,
credit, backend, export and network entitlements must be checked in your account.
No workshop-specific paid plan is assumed.

| Builder | First action | Server integration to request |
|---|---|---|
|Base44|Paste01-build-app; inspect the preview|A supported backend function/custom API integration with server-side secrets|
|v0|Paste01-build-app; inspect its Next.js preview|A server route/action with private environment variables|
|Lovable|Paste01-build-app; inspect the app|A server function or supported custom connector with secrets added through its secret UI|

For the facilitator's primary lane, **v0 is a practical choice when visible
server-side code is part of the lesson**: its documented full-stack path uses
Next.js routes/actions. This is a workflow choice, not a quality ranking. Use
Base44 or Lovable if the audience already has those accounts and the required
backend capability. Do not spend the hour comparing generated screenshots.

## Small platform additions to the shared prompt

**Base44:** “Use the platform's supported app components. Begin with in-memory
synthetic records. Leave integrations disconnected. Later, put external credentials
in backend secrets and authenticate the caller before privileged function work.”

**v0:** “Use the supported Next.js app structure. Begin with a visible UI and local
state. Later, put provider/OCI/Langfuse calls behind a server route/action. Never
prefix a secret with NEXT_PUBLIC_; that prefix exposes a value to browser code.”

**Lovable:** “Use the project's supported stack. Begin with synthetic records and
local state. Later, connect the API through a server function or approved connector.
Use Add secret rather than pasting keys into the project chat.” Newer Lovable apps
and older React/Vite projects can use different backend function mechanisms; inspect
the generated project instead of assuming an Edge Function is always the answer.

## Network reality

A SaaS backend cannot reach a laptop's `127.0.0.1`, and Lovable documents that the
API must be internet-reachable. For the workshop, either run exported code locally
with the local agent or provide a separately approved reachable authenticated
backend. Private OCI endpoints need an approved server/network path. Neither a
wildcard CORS rule nor a public tunnel is part of this lab.

A builder's personal/chat MCP connector is not automatically a runtime capability
of the published app. Register the integration in the actual application backend.

## Official references, checked 2026-10-31

- [Base44 developer platform](https://base44.com/developers): managed backend components and deployment.
- [Base44 integrations](https://base44.com/integrations): supported connector/custom integration approach; check current account entitlements.
- [v0 full-stack workflow](https://v0.app/docs/full-stack-apps): start with UI, then add server/data logic.
- [v0 external API variables](https://v0.app/docs/external-apis): environment scopes for preview and deployment.
- [Lovable any API](https://docs.lovable.dev/integrations/any-api): server secrets, function variants and reachability.
- [Lovable connector types](https://docs.lovable.dev/integrations/introduction): app connections versus personal chat context.
