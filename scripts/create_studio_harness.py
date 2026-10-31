#!/usr/bin/env python3
"""Create a fresh native-tool learner or explicitly labelled instructor workspace."""

import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "workshops/local-ai-studio/harness"


def create(output, reference=False):
    out = Path(output).expanduser()
    if out.is_symlink():
        raise ValueError("Output must not be symlinked")
    out = out.resolve()
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    for name in ("AGENTS.md", "TASKS.md"):
        shutil.copyfile(SOURCE / name, out / name)
    (out / "tests").mkdir()
    shutil.copyfile(SOURCE / "contracts/test_agent.py", out / "tests/test_agent.py")
    shutil.copytree(SOURCE / "prompts", out / "prompts")
    (out / "progress.md").write_text(
        "# Progress\n\nCore: pending. Live model: unverified. Backend readback: unverified.\n"
    )
    (out / ".gitignore").write_text(
        "local/\n.env\n.env.*\n*.log\n__pycache__/\n*.pyc\n"
    )
    (out / "init.sh").write_text(
        '#!/bin/sh\nset -eu\ncd "$(dirname "$0")"\nPYTHONPATH='
        + shlex.quote(str(out) + ":" + str(ROOT / "src"))
        + " exec "
        + shlex.quote(sys.executable)
        + " -m unittest discover -s tests -v\n"
    )
    (out / "init.sh").chmod(0o700)
    if reference:
        shutil.copyfile(SOURCE / "reference/agent.py", out / "agent.py")
    record = {
        "lane": "instructor_reference" if reference else "learner_empty",
        "agent_present": reference,
        "autonomous_coding_verified": False,
        "live_inference_verified": False,
        "provider_verified": False,
        "contract_sha256": hashlib.sha256(
            (out / "tests/test_agent.py").read_bytes()
        ).hexdigest(),
    }
    (out / "workspace.json").write_text(json.dumps(record, indent=2))
    (out / "workspace.json").chmod(0o600)
    return record


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True)
    p.add_argument("--reference", action="store_true")
    a = p.parse_args()
    try:
        print(json.dumps(create(a.output, a.reference)))
    except (OSError, ValueError) as e:
        p.exit(
            1,
            "Workspace creation failed: "
            + type(e).__name__
            + "; existing work preserved.\n",
        )
