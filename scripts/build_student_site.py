#!/usr/bin/env python3
"""Export a deliberately bounded static student site; never walk the repository."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "workshops/app-first"
FILES = [
    "index.html",
    "course.html",
    "help.html",
    "course.json",
    "results.json",
    "lovable.html",
    "LOVABLE-WORKFLOW.md",
    "prompts/07-lovable-native.md",
    "evidence/lovable-rehearsal.jpg",
    "evidence/langfuse-eu-setup.jpg",
    "evidence/langfuse-trace-tree.jpg",
    "relationships.html",
    "agent-map.css",
    "agent-map.js",
    "RAG-MISSION.md",
    "VISUALS.md",
    "showcase.html",
    "workflows.html",
    "WORKFLOWS.md",
    "APP-REHEARSAL.md",
    "agent-briefs/workflow-business.md",
    "agent-briefs/workflow-it-starter.md",
    "agent-briefs/workflow-ai-engineer.md",
    "agent-briefs/part-1-first-app.md",
    "agent-briefs/part-2-agent-engine.md",
    "agent-briefs/part-3-models-and-cost.md",
    "agent-briefs/part-4-follow-the-evidence.md",
    "agent-briefs/part-5-secure-by-construction.md",
    "agent-briefs/part-6-ready-for-oci.md",
    "lesson-help.json",
    "training.css",
    "training.js",
    "course-visuals.js",
    "guardrails.js",
    "GUARDRAILS.md",
    "replicate.html",
    "langfuse.html",
    "langfuse-basics.html",
    "langfuse-basics.js",
    "LANGFUSE-BASICS.md",
    "evidence/langfuse-timeline.jpg",
    "evidence/lovable-agent-trace-policy.jpg",
    "course-doctor.py",
    "personas.html",
    "personas.json",
    "personas.js",
    "evidence.html",
    "EVIDENCE.json",
    "evidence/lovable-inbox.jpg",
    "evidence/lovable-ai.jpg",
    "evidence/lovable-policy.jpg",
    "telemetry.example.toml",
    "WORKBOOK.md",
    "DELIVERY-CHECKLIST.md",
    "part-1-first-app.html",
    "part-2-agent-engine.html",
    "part-3-models-and-cost.html",
    "part-4-follow-the-evidence.html",
    "part-5-secure-by-construction.html",
    "part-6-ready-for-oci.html",
    "meet-your-agent.html",
    "inside-the-engine.html",
    "guide.css",
    "guide.js",
    "explorers.js",
    "preview.html",
    "preview.js",
    "public-theme.css",
    "tools.json",
    "vendor/d3-7.9.0.min.js",
    "vendor/D3-LICENSE",
    "README.md",
    "BUILDERS.md",
    "APP-CAPABILITIES.md",
    "API-CONTRACT.md",
    "OTEL-LANGFUSE.md",
    "OCI-HOSTING.md",
    "ARCHITECTURE.md",
    "REFERENCES.md",
    "PAGES.md",
    "prompts/01-build-app.md",
    "prompts/02-connect-agent.md",
    "prompts/03-add-observability.md",
    "prompts/04-codex-build.md",
    "prompts/05-codex-oci.md",
    "prompts/06-langfuse-simple.md",
    "diagrams/architecture.svg",
    "diagrams/architecture.drawio",
    "diagrams/architecture.excalidraw",
    "diagrams/architecture.mmd",
    "diagrams/architecture.json",
]

FILES += [
    f"agent-briefs/persona-{profile}-part-{part}.md"
    for profile in ("business", "it-starter", "ai-engineer")
    for part in range(1, 7)
]


def build(destination):
    destination = Path(destination).resolve()
    # Fresh output only: never delete, overwrite or merge a directory.
    destination.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for name in FILES:
        source = SOURCE / name
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"Not a regular allowlisted source: {name}")
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix == ".html":
            text = source.read_text().replace("redwood/styles.css", "public-theme.css")
            text = text.replace(
                'aria-label="Oracle Redwood mosaic"', 'aria-label="Workshop journey"'
            )
            text = text.replace(
                '<img class="oracle-logo" src="assets/oracle-logo-red.svg" alt="Oracle">',
                "<strong>OpsDesk</strong>",
            )
            # Keep the original interactive D3 diagrams; omit copied video figures.
            import re

            text = re.sub(
                r'<figure><img src="assets/oracle-[\s\S]*?</figure>', "", text
            )
            text = text.replace(
                "Selected Oracle source assets are reused for this local presentation; no unrestricted brand-asset redistribution is implied.",
                "Independent educational workshop; not an official Oracle product or endorsement.",
            )
            target.write_text(text)
        elif name == "README.md":
            target.write_text(source.read_text().replace("../local-ai-studio/README.md", "replicate.html"))
        elif name == "guide.css":
            target.write_text(
                source.read_text().replace(
                    "url('assets/brand-mosaic-stone.jpg')", "none"
                )
            )
        else:
            shutil.copyfile(source, target)
        hashes[name] = hashlib.sha256(target.read_bytes()).hexdigest()
    (destination / ".nojekyll").write_text("")
    (destination / "site-manifest.json").write_text(
        json.dumps({"files": [{"path": name, "sha256": digest} for name, digest in hashes.items()], "mode": "static-guide-no-backend", "schema_version": 2}, indent=2)
        + "\n"
    )
    return {"files": len(hashes), "output": str(destination)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", required=True, help="New, nonexistent export directory"
    )
    print(json.dumps(build(parser.parse_args().output)))
