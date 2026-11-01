# Build OpsDesk with Codex and rehearse from the CLI

This route creates a local app from a written contract, tests its visible controls
and checks a small server-side policy boundary. Keep one app throughout the course.
The coding assistant and the model called by your app are different runtimes.
A successful Codex build does **not** prove that your app has called an LLM.

The initial local contract intentionally returns `model_not_configured` for a
normal investigation. It never substitutes a canned answer. Real AI, Langfuse,
OCI APM and Log Analytics each need their own configured connection and independent
acceptance check. Do not describe the local policy rehearsal as hosted AI acceptance.

## Recorded local checkpoint — 1 November 2026

A real Codex invocation created the isolated teaching app. After a complete source
review, an independent run passed all **12 generated-app unit tests** and **nine
HTTP rehearsal gates**: the page, honest disconnected result, change stop, schema,
malformed JSON, unexpected field, both Origin cases and the body limit. The owned
server process was stopped and the reviewed source remained unchanged. These are
local checks; no app-model inference or telemetry was requested. Real AI and the
CLI app’s separate Langfuse project remain unverified.

## 1. Open your own checkout

Use an existing Python 3.12+ and Codex CLI installation. No paid API or global
package installation is required by these commands. Sign into Codex with your own
supported account if the CLI requests it; keep that screen out of recordings.

```sh
git clone https://github.com/adibirzu/opsdesk-agent-academy.git
cd opsdesk-agent-academy
python3.12 --version
codex --version
codex exec --help
```

If this folder already exists, open it and inspect `git status --short` rather
than overwriting it. The flags below were checked against the presenter’s CLI;
use your installed CLI help if your version differs. Do not use bypass flags. If a nested desktop environment blocks the CLI app-server startup, stop and review the host permission boundary. Retain the inner workspace sandbox; do not switch to an unrestricted execution flag to hide the failure.

## 2. Create the folder and plan with Codex

From the repository root, create a **new** learner workspace. `mkdir` deliberately
stops if that app folder already exists; reopen your existing app instead of
replacing it.

```sh
mkdir -p local/private
mkdir local/private/codex-opsdesk
codex -C local/private/codex-opsdesk
```

In the Codex conversation, paste the [planning prompt](prompts/08-codex-plan.md).
Use the [planning worksheet](CODEX-PLANNING-WORKSHEET.md) to settle the user journey,
tool scope, model, authentication, quotas, traces, hosting and finish line. Keep
account/project bindings in private notes. Ask Codex to save `APP-PLAN.md` in this
same app folder and stop before implementation.

Optional: if `grill-me` is already installed in **your** environment, type
`$grill-me` inside the Codex conversation and ask it to facilitate the planning
questions. This is a Codex skill request, **not** a shell command. The plain
planning prompt is the dependency-free fallback; no new skill install is needed.

**Expected:** a reviewed app definition, capability list, architecture sketch,
step-by-step implementation plan and acceptance table. A plan is not a running app
and authorizes no secret read, model canary or cloud deployment. The recorded
checkpoint above proves the later local build/test stage, not a filmed planning
session that has not yet been captured.

## 3. Give Codex a bounded, reproducible build task

Choose a new private folder if the example exists. This preserves earlier work.
The portable template below follows the executed task contract, with operator-specific paths removed. It creates no cloud resources, makes no app-model calls, installs
nothing and publishes nothing. The local Codex invocation itself uses your chosen
coding-model account and its available allowance.

```sh
mkdir -p local/private/codex-opsdesk
cat > local/private/codex-opsdesk/TASK.md <<'PROMPT'
Build a runnable OpsDesk app from zero in this directory using only Python
standard library, HTML, CSS, JavaScript and unittest. Do not install packages.
Edit only this folder. Do not inspect credentials, cloud configuration, browser
profiles or other private folders. Use only synthetic training data. No model
provider calls, telemetry exports, background servers, commits, publishing or
cloud actions while building.

Create app.py with a foreground server bound to 127.0.0.1 and --port argument.
Use a responsive Redwood-inspired layout: warm stone, red accents, Georgia
headings and system UI text. Do not download assets. Show three synthetic tickets,
search, a priority filter, selection, a validated New ticket form and an honest
not-connected AI panel. Keep ticket state in memory. Render ticket text with
textContent, never as HTML. Show validation, empty and error states.

Implement POST /api/investigate accepting only service and action. Permit services
payments, checkout and catalog. Normal action investigate returns
{"outcome":"model_not_configured","model_calls":0}; no fake AI answer. Explicit
change, restart or remediate actions return approval_required and model_calls 0
before any model construction. No shell, arbitrary URL, file or write tools.
Require exact loopback Origin, reject missing or foreign Origin, validate the
body/schema and enforce a bounded body size below 70,000 bytes with HTTP 413.
Reject unsupported services. Add synthetic event records describing the actual
checks; never invent remote spans, tokens or costs. This is a local teaching
boundary, not production user authentication.

Add meaningful unittest tests for policy-before-model, invalid bodies, body size,
Origin checks and honest missing configuration. Run the tests. Write README launch,
test and curl commands plus a capability list. Do not start a background process.
Explain which backend/telemetry gates remain unverified. Then stop.
PROMPT
codex exec --ignore-user-config --ephemeral --skip-git-repo-check \
  --sandbox workspace-write \
  -C local/private/codex-opsdesk \
  --output-last-message "$PWD/local/private/codex-opsdesk/local-result.md" \
  - < local/private/codex-opsdesk/TASK.md
```

The result path points inside your private app folder. The task is a starting instruction, not a guarantee
that generated source meets it. Inspect the actual files and tests before running.
The pre-existing builder prompt is also available at
[prompts/04-codex-build.md](prompts/04-codex-build.md).

## 4. Inspect source and execute the generated tests

From the repository root:

```sh
find local/private/codex-opsdesk -maxdepth 2 -type f
sed -n '1,240p' local/private/codex-opsdesk/app.py
(
  cd local/private/codex-opsdesk
  python3.12 -m unittest discover -s tests -v
)
```

Review more than the first 240 lines if the file is longer. Check the actual
request path → validation → policy stop → result. Confirm there are no outbound
network/model calls, secret reads, shell tools, package install hooks or background
processes. Confirm the server binds only to loopback and accepts `--port`.
Do not run unfamiliar generated code just because its tests are green.

## 5. Rehearse the reviewed local server automatically

The repository supplies `scripts/rehearse_demo_cli.py`. It sends only loopback
requests to the reviewed source. It starts one owned foreground child process,
checks the page and eight API cases, records private results and stops only that
child. It does not contact a model or export telemetry. Its default entry is
`app.py`; use `--entry server.py` only if that is the reviewed top-level filename.

First calculate the source fingerprint. This is **not** approval by itself:

```sh
python3.12 scripts/rehearse_demo_cli.py \
  --app-dir local/private/codex-opsdesk --fingerprint
```

After inspecting the exact source, copy the printed SHA-256 into the command.
Choose a new output path each time; existing evidence is never overwritten.

```sh
python3.12 scripts/rehearse_demo_cli.py \
  --app-dir local/private/codex-opsdesk \
  --reviewed-sha256 '<SHA256_FROM_YOUR_REVIEW>' \
  --output local/private/codex-rehearsal-01
```

Expected local gates:

| Case | Required result |
| --- | --- |
| App page | HTTP 200 |
| Normal investigation | `model_not_configured`, zero model calls |
| Explicit restart | `approval_required`, zero model calls |
| Unsupported service, malformed JSON or unexpected field | HTTP 400 or 422 |
| Foreign or missing Origin | HTTP 400 or 403 |
| Oversized body | HTTP 413 |

The private receipt records observed HTTP statuses and response bodies. It is
local evidence only. A mismatch stops the rehearsal; inspect the source and
explain it instead of weakening the checks. Do not commit raw receipts or logs.

## 6. Run the visible app and demonstrate the same journey

Use a foreground terminal:

```sh
python3.12 local/private/codex-opsdesk/app.py --port 8788
```

Open `http://127.0.0.1:8788/`. In another terminal, inspect the page and exercise
the two teaching actions. These are local synthetic requests, not OCI operations:

```sh
curl --fail-with-body http://127.0.0.1:8788/
curl --include http://127.0.0.1:8788/api/investigate \
  -H 'Content-Type: application/json' \
  -H 'Origin: http://127.0.0.1:8788' \
  --data '{"service":"payments","action":"investigate"}'
curl --include http://127.0.0.1:8788/api/investigate \
  -H 'Content-Type: application/json' \
  -H 'Origin: http://127.0.0.1:8788' \
  --data '{"service":"payments","action":"restart"}'
```

Create a synthetic ticket, search for it, filter by priority and select another
ticket. Explain why the normal action is disconnected and the change action is
blocked. Stop your own foreground server with Ctrl-C. Reload/restart may reset
in-memory tickets; that is not persistent storage.

## 7. Add the authenticated agent and OpenTelemetry to the same app

The disconnected baseline above is deliberately small. The next capability is
source-backed in the portable
[Codex app reference](https://github.com/adibirzu/opsdesk-agent-academy/tree/main/examples/codex-opsdesk).
Its presence in GitHub does **not** prove live inference or a deployed app.

Keep the same learner project and ask Codex to extend it, using that reference as
a contract. Do not blindly replace your working baseline or copy presenter values:

> Read my APP-PLAN.md and working OpsDesk source. Preserve its inbox and visible
> controls. Adapt the reviewed examples/codex-opsdesk server contract into this same
> app: authenticated session, strict Origin and input validation, server-owned Sol
> model selection, only service_health/release_diff synthetic read-only tools,
> at most three total model calls, an optional reviewer with separate context and
> no tools, per-role reported usage and clearly estimated costs. Add atomic hosted
> quota reservation; serverless must fail closed without it. Add isolated
> OpenTelemetry metadata export to this app's separate Langfuse project. Never put
> keys or account data in browser code. Keep real model calls, keys, cloud changes,
> publishing and deployment outside this implementation task. Run isolated tests,
> record the exact commands and report unresolved provider acceptance. Stop for
> review before any live call or deployment.

The portable reference supplies `app.py`, `engine.py`, `security.py`, `telemetry.py`,
`static/`, pinned `requirements.txt`, isolated tests, `prepare_deploy.py`, a
default-deny `.vercelignore` and Vercel configuration. Carry that reviewed
deployment-packaging boundary into the same app too. Use
its README and inspect the final generated app before installing dependencies.
The local baseline rehearsal runner is for the earlier disconnected contract;
after authentication is added, use the upgraded app's tests and authenticated
checks instead of loosening the old runner.

From your upgraded private app folder, after source/dependency review:

```sh
cd local/private/codex-opsdesk
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```

These are explicit learner-local dependency installs. They do not install global
tools or call the model. If the generated project has a different layout or no
reviewed requirements file, stop and reconcile it with the reference first.
For an inspection-only fallback, the same commands can be run from
`examples/codex-opsdesk`; label that as the authored reference, not your generated
app. Preserve which source was actually tested.

### Configure private local values without shell arguments

Give each independent app/runtime a **separate Langfuse project**. In your own
Langfuse account, create/select the intended CLI project and its suitably scoped
server ingestion keys. This is a persistent access action: do it only with the
project owner's approval. Do not silently reuse another app's keypair.

From the repository root, this setup prompt writes a new ignored JSON file with
mode `0600`. It reads values privately and prints no keys. Leave a value blank to
keep that integration unconfigured. Use your own authorized model/Redis bindings;
this prompt activates no service or API billing.

```sh
python3.12 - <<'PYCONFIG'
import getpass, json, os, secrets
from pathlib import Path
path = Path('local/private/codex-runtime.json')
path.parent.mkdir(parents=True, exist_ok=True)
if path.exists():
    raise SystemExit('Private config exists. Review it locally; do not overwrite.')
password = getpass.getpass('Private workshop passphrase (at least 32 characters): ')
if len(password) < 32 or password != getpass.getpass('Repeat private passphrase: '):
    raise SystemExit('Passphrase must match and contain at least 32 characters.')
values = {'WORKSHOP_LOGIN_SECRET': password,
          'SESSION_SIGNING_SECRET': secrets.token_urlsafe(48),
          'LOCAL_SINGLE_PROCESS_QUOTA': '1'}
for name in ('AI_GATEWAY_API_KEY', 'LANGFUSE_BASE_URL', 'LANGFUSE_PUBLIC_KEY',
             'LANGFUSE_SECRET_KEY', 'UPSTASH_REDIS_REST_URL',
             'UPSTASH_REDIS_REST_TOKEN', 'QUOTA_NAMESPACE'):
    value = getpass.getpass(name + ' (blank leaves unconfigured): ')
    if value:
        values[name] = value
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as stream:
    json.dump(values, stream)
print('Private runtime file created. No secret values printed.')
PYCONFIG
```

`LOCAL_SINGLE_PROCESS_QUOTA=1` is only for the explicit one-process local rehearsal.
It must **not** be copied to the deployed environment as a serverless fallback.
For the current reference, hosted inference needs the owned Redis REST URL/token
and a unique quota namespace; a missing atomic quota blocks inference.

Launch from the repository root with the private JSON loaded only into the server:

```sh
python3.12 - <<'PYLAUNCH'
import json, os
from pathlib import Path
root = Path.cwd()
config = json.loads((root / 'local/private/codex-runtime.json').read_text())
if not isinstance(config, dict) or any(not isinstance(v, str) for v in config.values()):
    raise SystemExit('Expected a private string-valued configuration object.')
app = root / 'local/private/codex-opsdesk'
python = app / '.venv/bin/python'
env = {k: os.environ[k] for k in ('PATH', 'TMPDIR', 'SYSTEMROOT', 'WINDIR') if k in os.environ}
env.update(config)
os.chdir(app)
os.execve(str(python.resolve()), [str(python), 'app.py', '--port', '8000'], env)
PYLAUNCH
```

Open `http://127.0.0.1:8000/`. Enter the workshop passphrase in the app's protected
sign-in form with recording paused. This reference uses a short-lived authenticated
workshop session; it is **not** enterprise SSO or per-student identity management.
Builder Google SSO and app authentication are separate boundaries.

**Expected before a live canary:** unauthenticated inference is rejected; wrong
Origin/invalid input is rejected; an explicit change returns
`approval_required` with zero calls; missing model/quota configuration is visible.
The model key is server-only. Do not record private setup, account controls,
passphrase entry, raw URLs or trace identifiers.

### Verify the CLI app's own Langfuse project

After the exact synthetic model run is authorized, select a ticket and investigate
once. There is no automatic retry. The app should show the actual model, tool
events, elapsed time, reported usage and export result. If a provider or quota
fails, retain that failure and stop; do not silently switch model or destination.

In Langfuse, independently find the **exact** trace and session from this run in
the CLI app's intended project. Check agent, generation and tool spans; verify
that prompt/answer text and account identity are absent. An acknowledgment in the
app is not independent readback. Follow [Connect Langfuse](langfuse.html) and
[Read a trace](langfuse-basics.html). Missing readback stays unverified.

## 8. Review and deploy the same app to Vercel

Deployment is a separate, consequential step. Stop until the owner has approved
the exact account/scope, dedicated project, source, secrets, quota store, expected
cost, access protection, retention and rollback/cleanup plan. A logged-in CLI or a
broad account role is not approval to modify an existing shared app.

The installed presenter CLI supports the commands below. Check your version's
help first. Use learner-owned placeholders and keep link metadata, environment
files, credentials and logs private. Never pass a secret with `--value`, `--env`,
`--build-env` or `--token`; those values could enter command history or recordings.

```sh
vercel --version
vercel env add --help
vercel deploy --help
```

### Required: prepare runtime-only source first

**Never run Vercel against your original working app folder.** It may contain
private settings, notes or recordings. `.gitignore` alone is not the upload
boundary. After source review, the upgraded app must contain the reviewed
`prepare_deploy.py` and default-deny `.vercelignore` from the portable reference.
If they are absent or changed unexpectedly, stop and reconcile that source first.

From the repository root, enter the same app's source folder and prepare a **new**
copy containing only the explicit runtime allowlist:

```sh
cd local/private/codex-opsdesk
python3.12 prepare_deploy.py --output local/private/vercel-source-01
cat local/private/vercel-source-01/DEPLOYMENT-SOURCE.json
cat local/private/vercel-source-01/.vercelignore
cd local/private/vercel-source-01
```

**Expected:** eleven reviewed runtime files are copied, with their SHA-256 values
in `DEPLOYMENT-SOURCE.json`; its status is `prepared_source_not_deployed`. The
helper refuses an existing output directory and does not scan/copy private local
settings, keys, virtual environments, notes, recordings, logs or caches. Inspect
the helper and manifest; do not treat the status as a deployment receipt.

The `.vercelignore` starts with `*` and selectively permits only the four runtime
Python modules, dependency/entrypoint configuration and three exact static files.
It excludes the manifest and all unlisted files from the CLI upload. The server
`excludeFiles` configuration is a second layer, not a substitute for preparing
this clean source. Do not add credentials or private notes to the prepared folder.

This is a packaged snapshot of **the same app**, not a new development project.
Keep editing/testing the original app, then prepare a fresh numbered folder when
its source changes. Keep its private settings outside the upload. Record which
manifest/source snapshot passed review and which one was actually deployed.

From this point onward, run **all Vercel commands from the prepared source
folder**. First inspect the prospective upload without deploying:

```sh
vercel deploy --dry
```

Review every selected file in that output against the runtime allowlist.
Private settings JSON, `.env*`, `.venv`, `.vercel` metadata, private notes,
screenshots, test receipts, logs and credentials must not upload. Stop on any
unexpected file; do not loosen the filter to make a dry run pass. A dry run does
not create a working preview and is not independent deployment acceptance.

Only after scoped approval, link **this prepared source folder** to the approved
dedicated project. Review the CLI prompts; never select another owner's existing
project. Keep the prepared folder selected for every command below:

```sh
vercel link \
  --project '<YOUR_OWNED_WORKSHOP_PROJECT>' --scope '<YOUR_APPROVED_SCOPE>'
```

Add each authorized server secret through the CLI's protected value prompt, with
recording paused. These commands create persistent access/configuration and need
the approved project binding. Do not use `--force` to overwrite existing values.

```sh
vercel env add WORKSHOP_LOGIN_SECRET preview --sensitive
vercel env add SESSION_SIGNING_SECRET preview --sensitive
vercel env add AI_GATEWAY_API_KEY preview --sensitive
vercel env add LANGFUSE_BASE_URL preview --sensitive
vercel env add LANGFUSE_PUBLIC_KEY preview --sensitive
vercel env add LANGFUSE_SECRET_KEY preview --sensitive
vercel env add UPSTASH_REDIS_REST_URL preview --sensitive
vercel env add UPSTASH_REDIS_REST_TOKEN preview --sensitive
vercel env add QUOTA_NAMESPACE preview --sensitive
```

Keep the CLI's selected scope/project bound to the reviewed target. The reference
can derive its exact HTTPS origin from Vercel's server-owned `VERCEL_URL` when
`PUBLIC_ORIGIN` is absent. If you use a stable custom host, configure its exact
`PUBLIC_ORIGIN` deliberately and test it; never accept a browser-supplied origin.
Do not copy the local quota switch into Vercel.

From the **same prepared source folder**, create a preview only after approval:

```sh
vercel deploy \
  --project '<YOUR_OWNED_WORKSHOP_PROJECT>' --scope '<YOUR_APPROVED_SCOPE>'
```

Do not add `--prod`, publish a new custom domain or disable deployment protection
to work around an authentication problem. A preview URL and successful build are
not end-to-end acceptance. In the actual preview, repeat authenticated create →
search/filter → select → investigate → policy stop; then match its exact trace in
the correct Langfuse project. Record model/quota/export failures separately.
Keep private preview URLs, project IDs and account names out of public recordings.

## 9. Add the reviewer and explain the measured cost

The portable harness exposes a `review` boolean on the authenticated investigation
request. In the app, enable its reviewer control for the same synthetic incident.
The investigator may call only the two allowlisted read-only tools. The reviewer
gets a **separate context with no tools**, the synthetic evidence and the draft
as untrusted data. This is two roles in one bounded harness, not two unbounded
agents with general system access.

Ask Codex to explain the implemented path in `engine.py`:

> Show investigator messages → validated tool calls → grounded draft → optional
> reviewer handoff → separate reviewer context → response. Point to the shared
> three-call budget, timeout and output limits. Show the actual per-role usage
> extraction and cost calculation. Do not invent a reviewer run when the remaining
> budget or configuration prevents one. Explain how uncertain causation and
> untrusted text are handled.

The reviewer consumes the **same total call budget**, so it may report
`not_run_budget`. A displayed reviewer label does not prove a second model call.
Accept the reviewer only when an authorized actual run returns its result and
matching provider observations. Local model doubles prove contracts, not live
multi-agent behavior.

Show input/output tokens per actual role and the total. The example estimate uses
source-dated model rates and labels the basis; it is not a billing receipt or a
complete hosting cost. Missing usage, unknown model identity or unsupported rate
conditions must remain unknown. Do not silently change models to make a cost
comparison. The selected reference profile is Sol; a new model needs an explicit
selection and capability/rate check.

## 10. Carry this app into the next lesson

Keep a private handoff note with the baseline revision or source copy, launch and
test commands, deployment manifest/snapshot reference, actual checks, unresolved
evidence and next task. Preserve the same
inbox and session contract when adding capabilities. Use the
[planning worksheet](CODEX-PLANNING-WORKSHEET.md) to update the acceptance table.

Do not infer OCI APM, Log Analytics or cloud deployment success from local tests,
a source configuration, a reachable page or a successful Langfuse trace.
