# Build the native-tool agent core

Implement `run_turn(model, observer, prompt, session_id, *, intent='query',
history=None, max_steps=3, max_total_tokens=2000, emit=None)` in agent.py. The model's injected
`complete(messages, tools, emit)` returns agent_workshop.studio_model.Completion.
Use native assistant/tool messages and the fixed service_health schema. The
synthetic fixture reports payments degraded and checkout/catalog healthy.

Return outcome, answer, session/trace IDs, steps, usage, known token lower bound,
unknown cost and provider_verified=false. A change intent stops before inference.
Keep unknown tools, extra/duplicate arguments and budgets fail-closed. Do not mutate
caller history or return raw provider errors. Read tests/test_agent.py for the
exact contracts, then prompts/01-core.md. Run ./init.sh and update progress.md.

This core is then composed with a chat UI, server-owned model configuration and
metadata Observer. Use the parent workshop's Codex tasks and presenter guide for
those later stages. Synthetic contract tests are never evidence of live inference.

Expose native TOOLS as a module constant. Forward the optional emit callback into
model.complete so a real provider stream reaches the chat. Do not fake streaming
by splitting an already completed answer into chunks.
