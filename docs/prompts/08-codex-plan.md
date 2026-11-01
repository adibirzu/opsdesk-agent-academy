Plan the SAME OpsDesk app with me before writing code. Do not implement, install,
call a model from the app, read secrets, publish, deploy or change cloud resources
during this planning conversation. Use synthetic training information only.

Ask one focused question at a time, explain unfamiliar terms, and record my
answers in a local APP-PLAN.md. If I already answered a question in our app
status/source, inspect that approved source and avoid asking again.

Cover these decisions:
1. Who uses the app, and what useful result should they get in the first hour?
2. What is the visible journey: create, search/filter, select, investigate?
3. What may the agent read, and which changes must always stop before a model call?
4. Which data is synthetic, private, or excluded from prompts and telemetry?
5. Which backend/model is explicitly available? The coding model and app model
   are separate. Use the selected Sol profile for this reference; do not silently
   select Astra or another model. Missing access stays unconfigured.
6. Which controls enforce authenticated access, strict inputs, selected-service
   tools, atomic quotas and a bounded total investigator/reviewer call budget?
7. What will OpenTelemetry export to this app's separate Langfuse project, and
   how will we independently verify one exact trace and session?
8. Where will the app run locally and, only after approval, on Vercel? What are
   the project owner, retention/cost limits, rollback and cleanup boundaries?
9. How will the reviewer get a separate context with no tools, and how will
   actual per-role tokens and estimated cost be shown without claiming a bill?
10. What is the fallback if model, hosting or telemetry access is unavailable?

Finish with a concise app definition, capability list, architecture/trust boundary
sketch, staged implementation plan, acceptance table and unresolved decisions.
Separate locally verified results from configured connections and live provider
acceptance. Do not declare a backend or deployment working from a source snippet.

Then show me the plan for review. A reviewed plan does not authorize secret reads,
new credentials, a provider call, deployment, publishing, purchases or IAM changes.
Stop planning without touching implementation until I ask to build.
