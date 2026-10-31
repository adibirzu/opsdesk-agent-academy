#!/usr/bin/env python3
"""Run the same synthetic task with 2–4 explicit model configurations."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time
import uuid

from agent_workshop.cli import execute
from agent_workshop.cloud_demo import _new_output, config_fingerprint
from agent_workshop.config import Config, load


def compare(configurations, output, session, *, scripted=False):
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", session): raise ValueError("Invalid session")
    if not 2 <= len(configurations) <= 4 or len({label for label, _ in configurations}) != len(configurations):
        raise ValueError("Choose 2–4 distinct model labels")
    if any(not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", label) for label, _ in configurations): raise ValueError("Invalid label")
    if any(config.telemetry.get("capture_content", False) for _, config in configurations):
        raise ValueError("Model comparison requires metadata-only tracing")
    destination = _new_output(output)
    report = {"mode": "scripted_rehearsal" if scripted else "live", "session_id": session,
              "provider_billed": False, "cost_basis": "configured_uncached_text_rates; discounts/taxes/cache/tool charges excluded",
              "provider_verified": False, "runs": []}
    for label, config in configurations:
        started = time.monotonic()
        result = execute(config, "Use search_logs to find timeout evidence and explain its synthetic source.",
                         session, destination / (label + ".jsonl"), scripted=scripted, agent_role="log_analyst")
        row = {key: result.get(key) for key in ("outcome", "model", "trace_id", "session_id", "input_tokens", "output_tokens", "steps", "estimated_cost_usd")}
        row.update(label=label, elapsed_ms=round((time.monotonic()-started)*1000), configuration_sha256=config_fingerprint(config))
        report["runs"].append(row)
        descriptor = os.open(destination / (label + "-result.json"), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as file: json.dump(result, file, indent=2)
    report["all_runs_succeeded"] = all(row["outcome"] == "success" for row in report["runs"])
    report["multiple_live_models"] = not scripted and len({row["model"] for row in report["runs"] if row["outcome"] == "success"}) >= 2
    report["estimated_total_usd"] = (round(sum(row["estimated_cost_usd"] for row in report["runs"]), 12)
                                     if all(row["estimated_cost_usd"] is not None for row in report["runs"]) else None)
    descriptor = os.open(destination / "comparison.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as file: json.dump(report, file, indent=2)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--scripted", action="store_true")
    mode.add_argument("--config", action="append", metavar="LABEL=PRIVATE_TOML")
    parser.add_argument("--output", required=True)
    parser.add_argument("--session", default="model-comparison-" + uuid.uuid4().hex[:12])
    args = parser.parse_args(argv)
    try:
        if args.scripted:
            configurations = [("fixture-a", Config()), ("fixture-b", Config())]
        else:
            configurations = []
            for item in args.config:
                label, separator, path = item.partition("=")
                if not separator: raise ValueError("Use LABEL=PRIVATE_TOML")
                config = load(path)
                configurations.append((label, config))
        report = compare(configurations, args.output, args.session, scripted=args.scripted)
        print(json.dumps(report, indent=2))
        return 0 if report["all_runs_succeeded"] and (args.scripted or report["multiple_live_models"]) else 1
    except Exception as exc:
        print(json.dumps({"outcome": "failure", "error_type": type(exc).__name__}), file=sys.stderr)
        return 1


if __name__ == "__main__": raise SystemExit(main())
