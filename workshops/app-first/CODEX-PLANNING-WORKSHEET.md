# OpsDesk planning worksheet

Keep this beside the same app. Use invented training examples. Keep account names,
private URLs, project IDs, credentials and raw receipts out of this public template.
Save completed private bindings in your own ignored storage.

## Product in one sentence

For **[learner/user]**, OpsDesk helps **[useful read-only outcome]** by **[visible
journey]**, while **[actions that always require another approval]** stay blocked.

## Decisions to settle before building

| Decision | Your answer | A useful OpsDesk starting point |
| --- | --- | --- |
| First-hour result | [answer] | A clickable inbox and one genuine, safely bounded investigation |
| Visible inputs | [answer] | Three synthetic incidents; title, description, service, priority |
| Visible actions | [answer] | Create → search/filter → select → investigate → inspect actual result |
| In-memory state | [answer] | Explicit training-only state; document what reload/restart resets |
| Allowed tools | [answer] | `service_health` and `release_diff`, synthetic and read-only |
| Blocked action | [answer] | Change/restart/remediate stops server-side before provider construction |
| App model | [selected exact model] | Separate from the coding assistant; reference uses a server-owned Sol selection |
| Runtime identity | [answer] | Authenticated app session; loopback alone is not production authentication |
| Quota | [answer] | Atomic hosted reservation; no per-worker memory fallback on serverless |
| Run budget | [answer] | At most three calls total, including the optional reviewer; no automatic retry |
| Reviewer | [answer] | Separate context, no tools, checks draft against the same synthetic evidence |
| Telemetry | [answer] | Allowlisted metadata, usage and status; omit prompt/answer text and identity |
| Langfuse project | [private reference only] | A separate project and server-only keys for this independent runtime |
| Cost display | [answer] | Per-role provider-reported tokens and source-dated estimate; missing stays unknown |
| Local launch | [command] | Foreground loopback process; stop only the process you own |
| Deployment package | [manifest/source reference] | Required runtime-only allowlist copy; no private settings or working-folder upload |
| Vercel target | [private reference only] | Learner-owned preview project; review upload/secrets/cost before deployment |
| Rollback/cleanup | [answer] | Baseline copy, named owned resources, expiry/retention and explicit authority |

## Acceptance table

Record evidence privately; do not paste secrets or raw URLs into this worksheet.
A checked row is a learning aid, not independent execution proof.

| Check | Expected | Observed / evidence class |
| --- | --- | --- |
| Create/search/filter/select | Real controls update the same app | [not checked] |
| Missing backend | Honest disconnected status, no canned answer | [not checked] |
| Anonymous request | Rejected before inference | [not checked] |
| Explicit change | `approval_required`, zero model calls | [not checked] |
| Invalid service/tool arguments | Rejected before side effect | [not checked] |
| Origin/body limits | Foreign/missing Origin and oversized body rejected | [not checked] |
| Hosted quota | Atomic reservation; unavailable quota fails closed | [not checked] |
| Real investigation | Actual model identity, tool results and reported usage | [not checked] |
| Reviewer | Separate context; no tools; bounded shared call budget | [not checked] |
| Cost | Per-role usage; estimated cost clearly separated from billing | [not checked] |
| Langfuse | Exact trace/session independently found in the app's intended project | [not checked] |
| Upload boundary | Fresh prepare_deploy.py output, reviewed manifest and default-deny .vercelignore; no private files | [not checked] |
| Vercel | Actual preview, auth, policy and bounded inference checked | [not checked] |
| Privacy | Reviewed frames contain no tenant/account names, avatars, private IDs or keys | [not checked] |

## Planning session prompt

Open the [planning prompt](prompts/08-codex-plan.md) in Codex and answer one question
at a time. If `grill-me` is already installed in your own Codex environment, you
may ask it to facilitate that conversation. It is optional. The plain questions
above work without installing a skill or a third-party repository.

## Carry the app forward

- Starting baseline/source copy: [private reference]
- Capability added in this part: [answer]
- Launch/test commands: [answer]
- Actual checks and unresolved gaps: [answer]
- Next change to the same app: [answer]

Do not begin a separate disconnected prototype to make a later lesson look green.
Do not infer OCI APM, Log Analytics or deployment success from local tests or one
Langfuse acknowledgment.
