# What works, what needs a backend

Start with this review before adding more features.

| Capability | First visible checkpoint | Extra requirement |
|---|---|---|
|Select/search/filter tickets|Works in preview|None; labelled synthetic data|
|Create a ticket|Visible immediately in this tab|Persistence/auth are deliberately separate|
|AI analysis|Initially disconnected/not run|Actual agent endpoint and tool-capable model|
|Read health/release evidence|Actual tool observations|Registered constrained tools; fixtures remain synthetic|
|Propose a next check|Actual model answer|Human grounding review; no causal certainty from one clue|
|Apply infrastructure changes|Unavailable|No deployment, rollback or shell tool in this workshop|
|Test change permission|approval_required before inference|Application policy; not OCI IAM|
|Trace the action|Local record, then export status|Operator's Langfuse project and exact backend readback|
|Cloud hosting|Application/deployment walkthrough|Prepared approved OCI resources and a fresh signed invocation|

The local reference uses `/desk`, `/desk.css` and `/desk.js` in the existing Studio
server. `/api/config` initializes an opaque HttpOnly SameSite cookie and exposes
only model aliases/public metadata. `/api/chat` uses the same server session,
strict origin checks, bounded agent/tool loop and metadata-only Observer. Ticket
text is rendered with textContent; ticket state stays in memory, with no browser
storage or database claim. Selecting a ticket clears the displayed run evidence.

This reference provides no production multi-user login, persistence, tenant
isolation or public API service. A generated app must implement its own user
identity and server integration before deployment. Do not treat preview polish,
a source scan, an application being ACTIVE or exporter flush as end-to-end proof.
