#!/usr/bin/env python3
"""Regenerate the bounded checked-in Pages mirror; never copy operator files."""

import importlib.util
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    load("build_training_course").build()
    exporter = load("build_student_site")
    allowed = set(exporter.FILES) | {".nojekyll", "site-manifest.json"}
    docs = ROOT / "docs"
    for path in docs.rglob("*"):
        if path.is_symlink() or (path.is_file() and str(path.relative_to(docs)) not in allowed):
            raise ValueError("Review unexpected content in docs before refreshing")
    with tempfile.TemporaryDirectory() as temp:
        output = Path(temp) / "site"
        exporter.build(output)
        for name in sorted(allowed):
            target = docs / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(output / name, target)
    print(f"Refreshed {len(allowed)} reviewed student files; no publication performed.")


if __name__ == "__main__":
    main()
