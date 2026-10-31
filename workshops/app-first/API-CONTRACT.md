# One app action, one server call

For the generated app, create a same-origin server function/route:

```http
POST /api/analyze-ticket
Content-Type: application/json

{"ticket_id":"TRAIN-101","intent":"query"}
```

Use the authenticated user and server-owned ticket lookup. Validate the exact body,
allowed ticket and permitted action before calling the agent. Browser ticket IDs
are not authorization. Derive the session on the server, scope history to that
user and never accept a model endpoint, key, tenant, role or permission from the
browser. Change intent stops before inference; do not implement a resume/write API.

A normalized result contains:

```json
{
  "outcome": "success",
  "answer": "The actual model answer belongs here; this is a contract example.",
  "trace_id": "<ACTUAL_TRACE_ID>",
  "session_id": "<SERVER_OWNED_SESSION>",
  "input_tokens": null,
  "output_tokens": null,
  "estimated_cost_usd": null,
  "backend_verified": false
}
```

This JSON is a schema illustration, never a fixture to return as a successful
analysis. A UI should distinguish running, success, approval_required, model/tool
failure, export failure and unverified readback. Do not automatically retry AI.

## Local authored reference

The local Studio now implements GET `/api/tickets`, POST `/api/tickets` and
POST `/api/analyze-ticket`. Tickets are owned by the opaque browser session and
kept in server memory, with three synthetic seed tickets and a 50-ticket limit.
Reload keeps that session's tickets; resetting the conversation or restarting the
process removes them. The server selects the first configured model alias.
The JSON adapter invokes the same bounded, instrumented agent as chat. It returns
the actual answer in memory and saves a content-free private receipt.

The existing `/desk` screen still uses POST `/api/chat` (SSE) and tab-local tickets;
the JSON endpoints are available for the app you build. Neither loopback cookie
ownership nor the static preview is production user authentication. A hosted app
must add authenticated identity and durable user-scoped persistence separately.
Host/Origin checks, concurrency exclusion and trace ownership apply to both APIs.
No CORS shortcut or browser-provided model endpoint is accepted.

## Prepared OCI hosted backend

The existing hosted example in this repository exposes signed application
invocation to `/run`. Its application token, when configured, is also supplied by
the server-side caller. The request is:

```json
{
  "prompt": "<BOUNDED_SYNTHETIC_TICKET_TASK>",
  "session_id": "<SERVER_DERIVED_ASCII_SESSION>",
  "operation": "investigate",
  "agent_role": "coordinator"
}
```

The server integration signs OCI IAM requests or uses the explicitly selected
identity-domain auth mode. Never place OCI private keys or long-lived bearer
secrets in browser code. OCI IAM signing is not replaced by an application token.

The local Studio uses native tool-call streaming; the existing hosted example
uses the repository's LangGraph/JSON coordinator. They are different runtime
adapters. Normalize the hosted response in the app's server function and test
it; changing a URL does not automatically port Studio sessions or its SSE API.
Do not advertise `/desk` as already deployed to OCI by this new workshop.
