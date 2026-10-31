# Explain the harness by following one turn

A model proposes text or a tool call. The **harness** supplies context, validates
that proposal, performs an allowed action, feeds back its observation, decides
whether to continue and records what happened. It is ordinary, inspectable code.
The model does not obtain capabilities merely by naming them.

## Two harnesses in this workshop

| Layer | What it controls | What it does not establish |
|---|---|---|
| Coding harness: Codex + learner workspace | Task instructions, file edits, tests, host tools and approval policy | Application authorization, provider acceptance or a secure deployment |
| Runtime harness: the local app | Session/history, model selection, tool schemas, budgets, policy and telemetry | OS isolation, arbitrary-code safety, cloud IAM or durable state |

AGENTS.md tells a coding agent how to work. Fixed contracts give concrete
feedback. The host sandbox and approval system govern its actual permissions.
The runtime tool registry gives the deployed model a much smaller interface.
Keep these two permission systems distinct when narrating the demo.

## The pieces participants create

1. **Intent and system instructions.** Define the job and evidence boundaries.
   Instructions guide behavior; they do not replace authorization in code.
2. **Conversation state.** Build model messages from the current server-owned
   session. Keep browser session IDs opaque; do not accept caller-supplied history
   from another session. The reference retains twelve messages in memory.
3. **Model adapter.** `StreamingModel.complete(messages, tools, emit)` binds an
   explicit endpoint/model/key reference and returns `Completion`. Streaming
   transports tokens and native tool-call fragments; it is not the harness.
4. **Tool registry and schemas.** Name, description, strict parameters and a
   reviewed handler. Reject an unknown name or invalid/duplicate argument before
   invoking a handler. There is no generic shell or credential reader.
5. **Control loop.** Append native assistant/tool messages, validate the next
   action and stop on a final answer or failure. Bound steps, calls, response bytes
   and reported tokens. Tool evidence is untrusted context, not new authority.
6. **Authorization.** Evaluate explicit request intent before model use. The
   change path returns `approval_required`; the agent cannot approve its own work.
   This example has no approval-resume or infrastructure-write endpoint.
7. **Observer and evidence.** Record causal spans and bounded metadata while
   keeping content/keys out of exports. A failed tool remains failed even if the
   model later writes a useful explanation.

## Source map for a live code walkthrough

```sh
rg -n 'class StreamingModel|def complete' src/agent_workshop/studio_model.py
rg -n 'SCHEMAS|def tool|class Studio|def run|security.authorize|_unique_fields' \
  src/agent_workshop/studio.py
rg -n 'class LearnerStudio|class LazyModel|run_turn' \
  src/agent_workshop/learner_studio.py
rg -n 'def run_turn|model.complete|Unknown tool|Token budget' \
  workshops/local-ai-studio/harness/reference/agent.py
rg -n 'langfuse.observation.type|api/public/otel|def flush' \
  src/agent_workshop/observability.py
```

Use symbols rather than memorized line numbers. In the build lane, inspect the
participant's agent.py for the same boundaries. The complete Studio is a reference
implementation; selecting `--learner-agent` routes through that file's run_turn
instead of the reference loop. The reusable web shell remains server-owned.

## Walk a native tool round trip

```text
User: inspect payments
  → authorize(query)
  → model.complete(system + user, native tool schemas)
  ← assistant tool_call(service_health, {service: payments})
  → validate name, exact arguments and remaining budget
  → execute reviewed synthetic handler
  ← {source: synthetic, status: degraded, ...}
  → append tool message tied to the call ID
  → model.complete(previous messages + untrusted observation)
  ← assistant final answer
  → retain history, close spans, write private receipt
```

The tool handler is deterministic here; the model selection and answer are not.
Seeing “payments is degraded” in prose does not prove the tool ran. Inspect the
call ID, actual observation and matching span/event. Show the data provenance.

## Streaming, memory and concurrency

SSE carries tokens and lifecycle events to the browser. It is not a task queue,
durable checkpoint or proof that a response is correct. The transport assembles
native tool-call fragments before execution; partial arguments never run.

Sessions are independent in-memory conversations. A new conversation gets a new
cookie/session; a new turn gets a new trace. Restart clears history. Same-session
turns are serialized, and the HTTP server has a finite connection-thread ceiling.
Those controls do not establish separate OS users or cloud principals. API keys
remain process secrets shared by the trusted app, not participant model inputs.

## Budgets and cost

A step cap limits loop iterations; response bounds limit data; a reported-token
budget checks available usage. Preserve a known lower bound when one side is
missing. Unknown usage cannot be turned into a zero price. The provider can spend
tokens before returning usage, so these controls are not invoice hard caps.

The reference can estimate uncached input/output charges only with explicit rates
and a matching returned model. It does not price GPU power, gateways, caches,
builds, network, taxes or telemetry storage. Codex coding-account usage is separate
from the application's runtime model usage.

## Framework choice

Start with one small native-tool loop for this lesson: its branches and failure
paths fit on a screen. A graph becomes useful when the task needs explicit
multiple paths, managed handoffs or separately designed persistence. LangGraph
is used elsewhere in this repository's OCI coordinator examples; importing it
would not automatically grant this local app durable memory, isolation or IAM.

Prefer the smallest design that makes the required guarantees visible and
executable. Add components because the workload needs them, then test the new
boundary. An impressive architecture picture is not runtime evidence.
