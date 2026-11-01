# OpsDesk — continue the Codex-created app

This is a portable extension of the course's actual from-zero Codex app. Keep the
same incident inbox and synthetic tickets, then add a protected investigator,
an optional independent reviewer, reported usage/cost estimates, and metadata-only
OpenTelemetry tracing. It is a single-presenter teaching application, not an
enterprise identity system or production incident service.

**Locally verified:** 35 tests pass, including one actual owned-loopback WSGI login/policy journey and real OTel protobuf serialization through a transport double. No runtime model/provider or remote export was called. Live model entitlement,
Vercel deployment, shared Redis quota service, and exact Langfuse readback require
separate configured and authorized checks. A green test is not provider proof.

## Run locally

Read the source and dependencies before installation. Use Python 3.12+ in this
folder; these commands install only into a new project virtual environment:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
mkdir -p local/private
.venv/bin/python configure_local.py --output local/private/settings.json
.venv/bin/python app.py --settings local/private/settings.json --port 8000
```

Open `http://127.0.0.1:8000`. The configuration helper hides provider/Langfuse key
entry, generates separate random app-login/signing secrets, and refuses to
overwrite a settings file. It prints no credentials. Open the private settings
file privately to copy `WORKSHOP_LOGIN_SECRET` into the password field; omit this
step from screenshots and recordings. Never share that file or put secrets in
builder chat, shell arguments, browser source, or Git.

Without a model key, investigations honestly return `model_not_configured`.
Change requests still return `approval_required` with zero model calls. The
local helper explicitly chooses a **single-process** quota store. This is useful
for a laptop rehearsal and is never a fallback in deployed serverless mode.
Ctrl-C stops the owned foreground server. Ticket changes are process memory only;
restarts and separate serverless instances can show different ticket lists.
Persistent incident storage is not implemented.

## Actual browser acceptance journey

1. Sign into this app using your privately supplied workshop secret. Builder/CLI
   authentication does not sign you into the app automatically.
2. Create `Workshop checkout check`, select `checkout`, choose Medium, and use
   an explicitly synthetic description. Search and filter; inspect the selected
   ticket. Text renders as text, never HTML.
3. Select the payments fixture and click **Analyze safely** once, only after the
   model account/credits and bounded run are authorized. Require a real returned
   answer and both `service_health` and `release_diff` events. Unknown usage stays
   unknown. There is no scripted successful model path.
4. Select **Add an independent reviewer** for a separately authorized comparison
   run. The reviewer has a separate prompt/context and no tools. It receives only
   the synthetic fixture evidence and investigator draft, treated as untrusted
   input. All roles share a maximum of three model calls. If the investigator
   consumes the whole budget, the reviewer is explicitly `not_run_budget`.
5. Click **Test a change request**. It must return `approval_required` before quota
   reservation/model construction, with zero model calls and no executor.
6. If tracing is configured, close the private identifier disclosure before
   recording. Match the exact trace ID and random session privately in the owner
   Langfuse UI. Export acknowledgment is not independent readback.

## Server configuration

Use your own approved settings. `.env.example` contains placeholders only; the
app does not automatically load environment files. Hosted settings go in the
platform's protected server environment.

| Setting | Purpose |
| --- | --- |
| `WORKSHOP_LOGIN_SECRET` | At least 32 random characters; app sign-in secret. |
| `SESSION_SIGNING_SECRET` | Different random secret; HMAC-signs 1-hour HttpOnly sessions. |
| `PUBLIC_ORIGIN` | Exact origin; HTTPS in deployed mode. No wildcard CORS. If absent on Vercel, the platform-provided `VERCEL_URL` is used exactly. |
| `AI_GATEWAY_API_KEY` | Approved server-side Vercel AI Gateway credential. Builder credits are not proof of runtime entitlement. |
| `LANGFUSE_BASE_URL` | Your project's HTTPS origin, e.g. the official EU Cloud origin. |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` | Your project-specific ingestion pair, server only. |
| `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN` | Your owned shared quota database. No automatic service creation. |
| `QUOTA_NAMESPACE` | Unique deployment label so independent apps do not share quota keys. |
| `LOCAL_SINGLE_PROCESS_QUOTA=1` | Explicit local rehearsal mode; ignored as a fallback when `VERCEL=1`. |

Only the fixed server-owned `openai/gpt-6-sol` model and fixed Gateway URL are
used. Neither endpoint nor model comes from a browser request. Per-presenter
quota is reserved atomically in one Redis Lua operation: 2 investigations per
minute and 10 per UTC day. No IP address, account email, ticket content, session
label or user-provided quota identity is sent to Redis. One run can make up to
three model calls, not three quota reservations. Backend/credential failures do
not trigger retries or return raw error text.

Signing out clears the local cookie. It does not revoke a stolen, otherwise
valid cookie before its one-hour expiry. Use this teaching login only within a
reviewed workshop scope; enterprise SSO, separate user roles, session revocation,
and robust abuse/rate controls for sign-in require additional implementation.

## Costs and telemetry

Every successful provider response may supply input/output usage. Missing,
malformed or mismatched usage stays unknown; partial successful steps never
masquerade as a complete run total. Per-role steps and total call count are shown.

The displayed cost is an **uncached catalog estimate, not a bill**. The verified
[Vercel model catalog](https://ai-gateway.vercel.sh/v1/models) on 1 November 2026
listed GPT-6 Sol standard input at USD 2/million tokens and output at USD
10/million tokens. The example estimates only the matching returned model and
short-context input range. It does not assume cache discounts, priority/flex
pricing, platform billing, free credits or actual charges. Refresh sourced rates
when using this in a later workshop.

`telemetry.py` creates a fresh isolated OpenTelemetry provider per run. It never
registers a global provider or instruments HTTP/provider clients automatically.
Root, authorization, investigator, reviewer, model and tool spans export only
allowlisted metadata. No prompts, answers, ticket descriptions, user identities,
raw tool arguments/results, credentials or private URLs are exported. Automatic
exception-event recording is disabled. A single bounded OTLP/protobuf request
uses the Langfuse v4 ingestion header; redirects are not followed, and export
errors are not retried. The UI always reports independent readback as unverified;
a separately authenticated operator verifies arrival.

## Vercel handoff — review before mutations

[Vercel's current Python runtime documentation](https://vercel.com/docs/functions/runtimes/python)
supports WSGI entrypoints. This example defines `app:app` in `pyproject.toml` and
keeps the same local callable. `vercel.json` caps function duration at 60 seconds
and excludes private local settings, virtual environments, caches, tests, credential folders and logs. The default-deny `.vercelignore` allows only the four runtime Python modules, dependency/entrypoint configuration, and three exact static files to be uploaded. Unlike `.gitignore`, this is explicitly consumed by the Vercel CLI. No deployment was performed by
creating these files.

Before any hosted run, review the exact owned Vercel account/project, plan and
spend settings; the new preview's visibility/protection; AI Gateway entitlement;
owned Redis region/retention/cost; server secrets; Langfuse project; rollback and
resource cleanup. Require scoped current authority for deployment, persistent
credential creation and new services. Avoid paid upgrades or automatic top-ups.

First prepare a new, explicit runtime-only source folder. This helper never walks private directories and never copies local settings, keys, virtual environments or caches. Inspect its small manifest; do not place credentials into the prepared source. The deployment boundary does not depend on `.gitignore`.

```sh
python3.12 prepare_deploy.py --output local/private/vercel-source-01
cd local/private/vercel-source-01
```

After the reviewed scope is approved, use the current installed CLI's help to
confirm commands. A typical new-project flow from the **prepared source folder** is:

```sh
vercel whoami
vercel link
vercel env add WORKSHOP_LOGIN_SECRET preview --sensitive
vercel env add SESSION_SIGNING_SECRET preview --sensitive
vercel env add AI_GATEWAY_API_KEY preview --sensitive
vercel env add LANGFUSE_BASE_URL preview
vercel env add LANGFUSE_PUBLIC_KEY preview --sensitive
vercel env add LANGFUSE_SECRET_KEY preview --sensitive
vercel env add UPSTASH_REDIS_REST_URL preview --sensitive
vercel env add UPSTASH_REDIS_REST_TOKEN preview --sensitive
vercel env add QUOTA_NAMESPACE preview
vercel deploy --dry
# Only with the exact preview deployment approval:
vercel deploy
```

`vercel link`, environment writes, and deployment mutate external state; these
are review instructions, not permission or evidence of execution. Enter secrets
at protected prompts, never as `--value` arguments or recorded terminal text.
Never use `--prod` to bypass preview review. Set `PUBLIC_ORIGIN` to the exact
chosen origin if using a stable alias/custom domain. Default platform hostname
matching intentionally rejects unconfigured aliases.

Separate acceptance gates: local source tests → reviewed preview deployment →
authorized real low-cost model run → actual role/usage output → one-attempt OTLP
acknowledgment → exact Langfuse readback. Keep any missing gate unverified.
