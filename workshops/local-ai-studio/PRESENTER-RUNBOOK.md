# Presenter runbook: from an empty file to an observable agent

The audience leaves with an app they can change, a native-tool loop they can
explain, and a repeatable way to distinguish a good-looking answer from evidence.
The session is applied engineering. Use one synthetic incident throughout:
**payments is slow; investigate safely, explain the evidence, and stop at changes.**

## Prepare and choose the lane

Use Python3.12+, the repository's locked `studio` extra, Codex access, a working
tool-capable LLM and optional own-project Langfuse keys. Run a small real model
turn before the event; discovery/health alone is insufficient. Never test new
GPU weights, infrastructure, billing or credentials for the first time on stage.

Two honest lanes are available:

- **Build lane:** create an empty workspace, run its expected RED, let Codex create
  agent.py, review the diff, run the contracts, then execute that exact file through
  `--learner-agent`. Keep the coding transcript and app hash privately.
- **Instructor lane:** explicitly create `--reference` in a different directory.
  Explain that its contracts exercise the completed core. This lane does not prove
  Codex created anything or that a live provider works.

Use [WORKSHOP.html](WORKSHOP.html) as the visual teaching guide,
[HARNESS.md](HARNESS.md) for explanations, [WORKFLOWS.md](WORKFLOWS.md) for replayable
scenarios and [RECOMMENDATIONS.md](RECOMMENDATIONS.md) for tradeoffs. The generated
learner is not copied into the published reference app and is not auto-published.

## 00–05 — Define the job and the two harnesses

Show [creation flow](diagrams/01-creation.svg). Say: “We are going to create a
small agent, not give a model control of a terminal.” Define input/output, one
read-only tool, a finite budget, and what must never happen. Contrast the coding
harness (Codex may edit/test files under host policy) with the runtime harness
(the app can call only registered functions). A prompt cannot grant itself a tool.

```sh
uv sync --frozen --extra studio
export LAB="local/private/agent-studio-$(date +%Y%m%d-%H%M%S)"
.venv/bin/python scripts/create_studio_harness.py --output "$LAB/learner"
"$LAB/learner/init.sh"
```

Expected RED: missing module `agent`. Show the fourteen fixed contracts and absent
agent.py. This is a specified starting state, not a broken installation. Keep the
same terminal for `$LAB`; commands in a second terminal use the separate scenario
output paths below.

## 05–14 — Create the agent core with Codex

Show AGENTS.md, TASKS.md and prompts/01-core.md. Keep the instructor reference
closed. Let the audience see the small dependency contract: `Completion` carries
content, native tool_calls, actual model ID and optional reported usage.

```sh
codex exec --ignore-user-config --sandbox workspace-write \
  -c sandbox_workspace_write.network_access=false \
  --skip-git-repo-check --ephemeral -C "$LAB/learner" --json \
  - < "$LAB/learner/prompts/01-core.md" \
  > "$LAB/codex-core.jsonl" 2> "$LAB/codex-core.stderr"
"$LAB/learner/init.sh"
```

Codex model traffic uses the coding account. Workspace network restrictions do
not mean the coding model runs on the laptop. Never disable the host approval
policy for this demo. If the installed Codex flags differ, inspect `codex exec
--help`; do not replace a denied action with an unrestricted session.

Expected GREEN: fourteen unchanged contracts. Inspect the generated code, imports,
tool registry and diff. Confirm no key files, shell tool, URL fetcher, hidden
fallback or cloud writes. Do not continue to live credentials merely because tests
are green. If generation fails, keep the failed evidence and use a separately
labelled reference; do not copy it into the learner as a fake success.

## 14–23 — Put that exact agent behind the chat

Use the existing private studio configuration prepared before the hour. Launch
from the repository root in the terminal where `$LAB` was defined:

```sh
PYTHONPATH=src .venv/bin/python -m agent_workshop.studio \
  --config local/private/studio/studio.toml \
  --learner-agent "$LAB/learner/agent.py" \
  --output "$LAB/chat-evidence" --port 8770
```

Add `--secrets /private/path/studio.env` only when needed. Stop another owned
listener on that port first, or choose another loopback port and pass the same
origin to the CLI. The learner flag imports reviewed local Python: it is not a
code sandbox. The web shell owns HTTP, sessions, configuration and transport;
the selected learner file owns the loop and tools. A lazy model binding lets
change intent terminate before constructing a model.

Open http://127.0.0.1:8770. Initial learner core: `service_health` only. Cards for
runbook injection/tool failure stay disabled until those tools are added. Ask:
“Use service_health for payments. Explain the synthetic result and do not change
anything.” Observe actual streamed text, tool choice and the returned evidence.
A model answer without the requested tool is a failed grounding exercise.

In a second terminal:

```sh
.venv/bin/python scripts/studio_demo.py --list
.venv/bin/python scripts/studio_demo.py --scenario learner-health --model local \
  --output "local/private/health-$(date +%Y%m%d-%H%M%S)"
```

Replace `local` with the exact configured alias. This command makes real model
requests. A transport fixture or page render cannot satisfy it. Show the separate
runtime model configuration and explain why its key is not in Codex's prompt.

## 23–32 — Add a tool, then introduce untrusted context

Use prompts/02-tools.md and [CODEX-TASKS.md](CODEX-TASKS.md). Add bounded
`search_runbook(query)` and its negative tests. The adversarial document is data:
it requests a credential-export function that is not registered. Display the
actual validation point, not just the instruction that says “be safe.”

Restart the app after reviewing/testing the changed source, using a **new** output
directory. The browser tool cards come from the selected core's native TOOLS
list. Repeat the same question before/after the addition. Do not label the
instructor app's tools as learner-created capabilities.

## 32–42 — Make execution observable

Show [telemetry lineage](diagrams/04-telemetry.svg) and instrument with
prompts/03-observe.md. Explain `session_id` (conversation), `run_id` (one
execution) and `trace_id` (one causal span tree). Show `agent.run`,
`security.authorize`, generation and tool spans, metadata events and receipts.
The minimal learner core's event/span granularity must be enhanced as specified;
it does not inherit every span from the complete reference automatically.

Inspect actual model usage. Missing or partial counts remain unknown. Enforce a
known lower bound plus step/output/time bounds; none is a provider billing cap.
Only explicit matching model rates produce an estimate. A local GPU has costs,
but this workshop does not invent their price or treat them as a measured USD0.

With approved Langfuse configuration, send a fresh turn, inspect exporter status
and click **Verify trace in Langfuse**. Check that the exact session/trace match.
Local file → exporter delivery → backend readback are three separate receipts.
If ingestion is unavailable, demonstrate the honest failure and keep acceptance
pending. Do not change network/edge/IAM settings live as an unplanned workaround.

## 42–50 — Show controls that do not depend on a persuasive prompt

Show [security flow](diagrams/03-security.svg). In the browser, tick **Request a
change**. Ask to restart a service. Show the policy decision and zero model steps.
From a second terminal, this same control can be exercised without inference:

```sh
.venv/bin/python scripts/studio_demo.py --scenario policy \
  --output "local/private/policy-$(date +%Y%m%d-%H%M%S)"
```

Then run the injection and controlled-failure scenarios only after the learner
implements them, or explicitly switch to the completed instructor app. The model
may behave differently each time. Retain the actual reply, call history and
failure; a safe answer to one injected prompt is not general immunity.

The tool registry is the capability boundary. The application policy stop is not
OCI IAM, a cloud security event or an OS sandbox. The same trust principle applies
when later adding real service reads, but those need their own scope/identity.

## 50–56 — Fail honestly and compare

Exercise the controlled-failure tool and retain its failed span, even when the
model answers afterward. Show the actual output rather than replacing it with a
successful transcript.

## 56–60 — Explain and hand off

Choose another explicitly configured model and repeat the same question. Check
its native tool support and actual returned model ID. Show outcome, time, usage,
error recovery and evidence quality; one unpaired result is not a benchmark.
Finish with each participant explaining model → harness → tool → observation →
answer, and locating one exact trace or stating the missing backend gate.

Keep progress.md, private receipts and the actual reviewed source hash. Do not
turn a handoff file into a claim of durable checkpointing. Leave external gates
unverified when the provider, network, quota, model or identity is unavailable.

## Close and retention

Ctrl-C the owned local server and verify its listener is gone when the exercise
ends. Keep the task-specific evidence privately under the participant's retention
policy. Model unloading, server stop, credential rotation and cloud teardown are
separate owned actions; this workshop does not perform them automatically.

## Engagement edition

Use [SHOW-RUN.md](SHOW-RUN.md) for the opening minute, audience questions and
closing recap. [MISSION-BRIEF.md](MISSION-BRIEF.md) gives one consistent synthetic
incident across all eight labs. The visual guide supports **Present one lab**,
manual predictions, evidence reveals and a timer; these controls never invoke a
model or certify a result. Existing scrollable mode stays available.

For the 23–32 minute tool exercise, add `release_diff` using prompts/04-release.md
before the runbook extension if pacing allows. The completed instructor app has
the tool already, but the learner starts with health only. The original fourteen
contracts remain unchanged; add negative tests for the new registry entry.

Live coding command after review of the first core:

```sh
codex exec --ignore-user-config --sandbox workspace-write \
  -c sandbox_workspace_write.network_access=false \
  --skip-git-repo-check --ephemeral -C "$LAB/learner" --json \
  - < "$LAB/learner/prompts/04-release.md" \
  > "$LAB/codex-release.jsonl" 2> "$LAB/codex-release.stderr"
"$LAB/learner/init.sh"
```

Review the diff and new tests, restart with a fresh evidence directory, then run
the actual incident scenario. Use the runbook/injection extension next if there
is time; do not claim the learner has every instructor capability by default.
