# Agent Studio: build, observe and secure a real local AI chat

A separate hands-on local edition. Participants build an interactive chat app,
connect their own LLM, add constrained tools, inspect real request usage and test
security boundaries. No OCI tenancy, container engine or presenter credentials
are required. This is not the scripted volume-report rehearsal.

The reference app uses real OpenAI-compatible streaming and native function calls.
Ollama, LM Studio and LiteLLM are suitable when the selected model supports those
features. A compatible endpoint is not proof that a particular model supports tools.
The model can run on your laptop, your own LAN machine or your approved provider.

## What you will build

A small incident assistant with a streaming conversation, model selector and live
run inspector. The assistant can read synthetic service-health fixtures and retrieve
local runbook text. It cannot execute shell commands, read credentials, fetch
arbitrary URLs or modify infrastructure. One runbook contains an adversarial
instruction for the injection exercise. A separate training tool deliberately fails.

The inspector shows visible actions, authorization, tool results, reported token
usage, elapsed time and configured-rate cost estimates. It does not reveal hidden
model reasoning. Langfuse is optional; local metadata is always retained privately.

See the [architecture and trust boundaries](ARCHITECTURE.md) before adding tools.

## Before the hour

1. Obtain the workshop GitHub revision from the facilitator and clone it. Use an
   existing Python3.12+ and `uv`: `uv sync --frozen --extra studio`. This local
   extra installs telemetry support without the OCI SDK or LangGraph cloud path.
2. Have one working tool-capable model. For Ollama, start it yourself and use
   `ollama list` to select an already installed model. Model downloads, memory,
   licenses and provider costs belong to your own environment; this lab never
   downloads weights, starts remote services or selects a paid fallback for you.
3. For a remote gateway, obtain your own API key and exact model alias. Keep
   credentials in your shell or a private0600 env file, never a chat message or Git.
4. Optional: your own Langfuse deployment/project and API key pair. The application
   does not provision Langfuse or give you access to the presenter's instance.

### Start the runnable reference

From the repository root:

```sh
mkdir -p local/private/studio
cp workshops/local-ai-studio/studio.example.toml local/private/studio/studio.toml
chmod 600 local/private/studio/studio.toml
```

Edit `model_id` to your exact installed model. An unconfigured placeholder will
fail visibly; it never becomes a scripted answer. Then:

```sh
PYTHONPATH=src .venv/bin/python -m agent_workshop.studio \
  --config local/private/studio/studio.toml \
  --output "local/private/studio/run-$(date +%Y%m%d-%H%M%S)" --port 8770
```

Open **http://127.0.0.1:8770**. A page load makes no model call. Every submitted
turn uses the selected real backend. Model/provider failure is an explicit failed
run; no automatic retry or fallback exists. Ctrl-C stops the local server.

For optional credentials, add `--secrets /private/path/studio.env`. The env file
must be a regular file with mode0600. Only configured model-key names, configured
Langfuse-key names and the matching `LANGFUSE_BASE_URL` are accepted. It is parsed
as data, never sourced as shell code. The browser cannot see these values or set
an endpoint. HTTP is allowed for loopback; remote gateways require HTTPS by default.
A private-network HTTP gateway needs explicit `allow_private_http = true`, an exact
allowlist and an unprivileged port. This opt-in does not provide TLS encryption;
use only your approved trusted network/overlay, or prefer an SSH loopback forward.

## The 60-minute workshop

Start with the [visual workshop guide](WORKSHOP.html) and follow the
[presenter runbook](PRESENTER-RUNBOOK.md). The default build lane starts with
an empty learner workspace, fourteen fixed contracts and an expected RED.
Codex creates the core; `--learner-agent` runs that exact reviewed file behind
the chat. The completed instructor app remains a separate, labelled option.

| Time | Lab | Evidence |
|---|---|---|
| 00–05 | Define the job and scaffold | Empty learner; fixed contracts fail as expected |
| 05–14 | Create the core with Codex | Actual coding transcript, reviewed source, contracts GREEN |
| 14–23 | Compose the chat with that core | Real streaming/native tool call from selected LLM |
| 23–32 | Add tools and untrusted context | Strict schemas and negative tests |
| 32–42 | Observe the execution | Trace/session correlation, usage and delivery/readback |
| 42–50 | Show security boundaries | Pre-model policy stop; inspect injection behavior |
| 50–56 | Fail honestly and compare | Retained tool error; same-task model comparison |
| 56–60 | Explain and hand over | Repeatable commands, reviewed source and private evidence |

Use [HARNESS.md](HARNESS.md) for the coding/runtime harness explanation,
[WORKFLOWS.md](WORKFLOWS.md) for replayable scenarios and
[RECOMMENDATIONS.md](RECOMMENDATIONS.md) for provider and design choices.
Four editable [architecture diagrams](ARCHITECTURE.md#editable-diagram-set)
cover creation, runtime, security and telemetry.

The independent full-chat prompts below are an optional extension. For the
paced one-hour build, use the core-first workflow and prompts in the runbook.

### Lab1 — Build with Codex

Use [CODEX-TASKS.md](CODEX-TASKS.md). The first prompt creates the chat in a fresh
learner directory; the source under `src/agent_workshop/studio*.py` is the separate
runnable reference. Do not relabel reference code as a newly generated app.
Inspect the diff and run the stated contracts before execution. The coding agent
uses its own account; the application model is a separate explicitly selected LLM.

### Lab2 — Chat, then switch models

Send a greeting, then a follow-up referencing it. Check that the reply streams
from the actual backend. Press **New conversation** and verify that previous
context is absent. Configure a second model table, restart the app with a fresh
output directory and select it in the model picker. Compare the same task without
claiming that one unpaired run is a performance benchmark.

If a backend does not support native tools/streaming, select a supported model or
report that limitation. Do not silently change the protocol or model. Provider
usage can be missing; that remains unknown, not zero. Rates are optional, matched
to the actual returned model ID and exclude infrastructure/cache/tax/tool costs.

### Lab3 — Tool execution you can inspect

Use **Investigate a slow service**. Ask for payments and checkout health plus
runbook guidance. The model decides whether to invoke tools; the harness enforces
its allowlist and JSON schema. Inspect `service_health`/`search_runbook` spans.
Their data is explicitly synthetic. If the model invents evidence without calling
those tools, record that as a failed grounding exercise; text alone is not proof.

Add one small tool using the next Codex prompt. Require a constrained schema,
unit tests and an explicit return source. Re-run the same task and inspect the new
span; count tool failures separately from a fluent model answer.

### Lab4 — Local traces and optional Langfuse

Each turn writes `events.jsonl` and `receipt.json` in a new private directory.
Prompts, response content, tool arguments/results and keys are excluded from those
metadata artifacts. Conversations live in server memory and clear on restart;
the browser is a chat interface, not a telemetry credential store.

To export, set `telemetry.enabled = true`, uncomment the exact Langfuse endpoint,
allowlist and key environment names in your private config, then load your own
keys through the private env file. Restart with a new output directory. The same
Observer emits nested `agent.run`, `security.authorize`, generation and tool spans.
Langfuse OTLP uses project authentication and the v4 ingestion header. Exporter
success is delivery evidence; independently find the exact trace and session in
Langfuse before claiming backend verification. The browser always labels readback
as **Not verified** until an independent check is performed. **Verify trace in
Langfuse** queries only the current conversation's exact trace/session and reports
the actual result. A different browser session cannot verify someone else's trace.

Inspect latency, model ID, reported tokens, status and tool errors there. Content
capture remains off. OCI APM/Log Analytics are separate connected exercises in the
main workshop, not secretly simulated by the local edition.

### Lab5 — Security and honest failure

1. Use **Try a prompt injection**. Retrieve the adversarial runbook. The document
   tells the model to call a credential-export tool; that tool does not exist.
   Inspect the answer and calls. A compliant model is useful evidence for this
   prompt, not a guarantee against all prompt injection. Unknown tools fail closed.
2. Tick **Request a change** and ask to restart a service. The harness stops before
   creating a model: zero model steps, no write. This is application authorization,
   not a cloud IAM denial, and no approval-resume endpoint exists.
3. Use **Break a tool on purpose**. The tool span fails. A correct model should
   acknowledge missing evidence. Even if it recovers, the receipt remains
   `completed_with_tool_error`; a fluent response does not erase the failure.
4. Test an unsupported tool name, extra arguments and an exhausted token budget
   through the synthetic contracts. No secret/exfiltration endpoint is created.

## Validate and share

```sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_studio.py -v
node --check src/agent_workshop/web/studio.js
```

Synthetic tests validate implementation contracts; they do not prove a real LLM
or backend works. Keep your actual provider failure, stream, trace/session and
readback receipts separately. Review prompts and screenshots before sharing.
Only source, generic sample configuration and sanitized exercises belong in Git.
Do not publish private keys, receipts, provider endpoints, project IDs or recordings.

Public technical references: [Ollama compatibility](https://docs.ollama.com/api/openai-compatibility),
[MCP-independent Langfuse OTLP integration](https://langfuse.com/integrations/native/opentelemetry).
This is an independently authored workshop, not an official Oracle product lab.

## A story the audience can investigate

Start with the [synthetic incident brief](MISSION-BRIEF.md): payments is slow and
a nearby release changed a timeout. Build the health tool, add release_diff, then
ask whether a nearby change proves a cause. Follow the
[presenter talk track](SHOW-RUN.md) for prediction/reveal moments, the forged
runbook, a deterministic policy stop, failed evidence and model comparison.
The guide's presentation controls are local teaching aids, not model execution.
