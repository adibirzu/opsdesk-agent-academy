Read this workspace's AGENTS.md, TASKS.md and tests/test_agent.py. Create agent.py
from scratch implementing the native tool-call loop contract. Inspect the public
agent_workshop.studio_model.Completion and runtime._validate interfaces named in
init.sh, but do not read/copy the instructor reference or studio application.
Inject model and Observer. Expose only service_health with an enum and no extra
arguments. A change request must stop before model invocation. Reject unknown
tools, malformed/duplicate JSON arguments and invalid usage. Preserve partial
usage as unknown, while enforcing the known token lower bound before tool work.
Bound the loop, avoid mutating caller history and keep provider errors generic.
Use only standard-library code and the existing workshop dependency. Do not call
a provider, install, inspect credentials, use MCP, change infrastructure or Git.
Run ./init.sh without changing contracts. Update progress.md with actual results
and unresolved gaps. Stop after local verification; do not claim live acceptance.

Expose TOOLS and accept optional emit=None. Forward emit into model.complete; keep
token streaming genuine when later composed with the web shell.
