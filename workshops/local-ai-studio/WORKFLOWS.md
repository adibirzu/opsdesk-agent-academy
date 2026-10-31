# Workflow demonstrations and replay commands

Use one configured real model alias, such as `local`. The following commands
contact only the selected loopback chat server; that server calls the configured
real model for query scenarios. No provider key is passed to this CLI. Each
scenario starts a fresh cookie/session; the conversation case keeps two turns in
one session. Receipts/SSE are private files, not proof of external ingestion.

```sh
.venv/bin/python scripts/studio_demo.py --list
```

| Scenario | Show | Mechanical check | Human check |
|---|---|---|---|
| greeting | Real streamed model text | Successful terminal receipt | Is this the selected backend? |
| learner-health | Initial learner's one native tool | service_health completed | Does the answer cite synthetic evidence? |
| investigation | Health + runbook multi-step flow | Both required tool names completed | Were both services read and conclusions grounded? |
| conversation | Server-side context across two turns | Same session, different traces | Did the follow-up use the right prior topic? |
| injection | Untrusted instructions in a retrieved document | Runbook call; outcome retained | Did the model ignore the text or propose a denied action? |
| policy | Explicit change intent | approval_required and zero model steps | Distinguish application policy from cloud IAM |
| failure | Real failed tool in an agent turn | tool.error and completed_with_tool_error | Does the answer acknowledge missing evidence? |

## Run one case

```sh
.venv/bin/python scripts/studio_demo.py --scenario learner-health --model local \
  --output "local/private/demo-health-$(date +%Y%m%d-%H%M%S)"
.venv/bin/python scripts/studio_demo.py --scenario investigation --model local \
  --output "local/private/demo-investigation-$(date +%Y%m%d-%H%M%S)"
.venv/bin/python scripts/studio_demo.py --scenario conversation --model local \
  --output "local/private/demo-conversation-$(date +%Y%m%d-%H%M%S)"
```

The initial learner has only health. Use the investigation/injection/failure cases
after extending that core, or explicitly select the complete instructor Studio.
Unsupported tools must stay unavailable; do not call an instructor case a learner
feature. A model alias is mandatory for query cases and never silently substituted.

```sh
.venv/bin/python scripts/studio_demo.py --scenario injection --model local \
  --output "local/private/demo-injection-$(date +%Y%m%d-%H%M%S)"
.venv/bin/python scripts/studio_demo.py --scenario failure --model local \
  --output "local/private/demo-failure-$(date +%Y%m%d-%H%M%S)"
.venv/bin/python scripts/studio_demo.py --scenario policy \
  --output "local/private/demo-policy-$(date +%Y%m%d-%H%M%S)"
```

Use `--base-url http://127.0.0.1:PORT` for another owned listener. No public or
arbitrary remote chat origin is accepted. Add `--show-answer` only for reviewed
synthetic exercise content; control characters are stripped from terminal output.
Raw model/SSE content remains private on disk by default. No automatic retry is
made after provider failure, incomplete streaming or a failed mechanical check.

## Read the artifacts

- `turn-N-input.json`: the exact public exercise input and selected alias.
- `turn-N.sse`: the response stream, including model content; private0600.
- `turn-N-checks.json`: the server receipt and mechanical outcomes.
- `summary.json`: count/correlation checks, file hashes, human-review requirement.

The app separately records events/receipts under its private output directory.
Do not overwrite failed attempts. A CLI mechanical pass is not model-quality,
semantic injection-safety, provider-billing or telemetry-readback acceptance.

## Compare models honestly

Run the same investigation once with two configured aliases and keep both output
directories:

```sh
.venv/bin/python scripts/studio_demo.py --scenario investigation --model local \
  --output "local/private/compare-a-$(date +%Y%m%d-%H%M%S)"
.venv/bin/python scripts/studio_demo.py --scenario investigation --model alternate \
  --output "local/private/compare-b-$(date +%Y%m%d-%H%M%S)"
```

Replace both aliases with entries you actually configured. Compare task outcome, actual returned model, tool selections,
latency, reported usage, configured cost and the evidence quality. Note differing
output limits, context and cache state. A one-shot demonstration is not a
performance benchmark; a cheap fluent answer can still fail grounding.

## Rehearse the local contracts without a model

```sh
PYTHONPATH=src .venv/bin/python scripts/rehearse_studio_workshop.py \
  --output "local/private/course-check-$(date +%Y%m%d-%H%M%S)"
```

This executes the expected empty-learner RED, the labelled instructor reference's
fourteen contracts, the composition/security tests, and the actual zero-model
policy path over temporary loopback HTTP. It creates no coding-model session,
performs no inference/export and cannot close those live acceptance gates.

Before the event, separately execute the actual Codex creation commands, review
that generated source, run a real model/tool scenario and query the exact backend
trace/session. If any is blocked, state the missing receipt and continue only
independent exercises. Do not replay a failed model call just to check ingestion.

## Incident story: was it the release?

See [MISSION-BRIEF.md](MISSION-BRIEF.md) and the
[presenter talk track](SHOW-RUN.md). The completed instructor app includes
`release_diff(service)` with strict enum arguments and synthetic release data.
The initial learner does not: extend it with `prompts/04-release.md`, or state
explicitly that you are selecting the completed instructor implementation.

```sh
.venv/bin/python scripts/studio_demo.py --scenario incident --model local \
  --output "local/private/incident-$(date +%Y%m%d-%H%M%S)"
```

This uses the real model bound to `local`. It mechanically checks completion of
service_health and release_diff; manually inspect both services' observations,
release correlation, grounded output and absence of a causal/rollback claim.
No deployment, rollback or actual service telemetry is returned by these tools.
