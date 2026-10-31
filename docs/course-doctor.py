#!/usr/bin/env python3
"""Read-only local prerequisite checks. No secrets, network or resource changes."""

import argparse
from importlib import metadata
import json
import shutil
import sys


def check(part):
    checks = [{"name": "python>=3.12", "ok": sys.version_info >= (3, 12)}]
    checks.extend(
        {"name": name, "ok": bool(shutil.which(name))} for name in ("git", "uv")
    )
    packages = ["opentelemetry-sdk", "opentelemetry-exporter-otlp-proto-http"]
    if part == 6:
        packages += ["oci", "langgraph"]
    for name in packages:
        try:
            metadata.version(name)
            ok = True
        except metadata.PackageNotFoundError:
            ok = False
        checks.append({"name": name, "ok": ok})
    return {
        "part": part,
        "local_prerequisites_ok": all(c["ok"] for c in checks),
        "checks": checks,
        "model_connection": "not_checked",
        "telemetry_readback": "not_checked",
        "cloud_access": "not_checked",
        "next": "Use your own model/config and complete the part acceptance checks. Self-hosted Langfuse additionally needs a reviewed container runtime/compose setup.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part", type=int, choices=range(1, 7), required=True)
    result = check(parser.parse_args().part)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["local_prerequisites_ok"] else 1)
