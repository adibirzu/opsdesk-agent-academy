#!/usr/bin/env python3
"""Build a deterministic, source-only workshop archive."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import sys
import zipfile

INCLUDED = ("src", "pyproject.toml", "uv.lock", "README.md", "docs", "workshop.toml.example")
EXCLUDED_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".tox", "node_modules"}
EXCLUDED_NAMES = {".env", ".env.local", ".env.production", "SPEAKER.md"}


def _files(root: Path):
    for entry in INCLUDED:
        path = root / entry
        if not path.exists() or path.is_symlink():
            raise ValueError(f"required package path is missing or symlinked: {entry}")
        if path.is_file():
            yield path, Path(entry)
            continue
        for current, dirs, names in os.walk(path, followlinks=False):
            current_path = Path(current)
            for directory in list(dirs):
                candidate = current_path / directory
                if candidate.is_symlink():
                    raise ValueError(f"symlinks are not packageable: {candidate.relative_to(root)}")
            dirs[:] = sorted(dirs)
            for name in sorted(names):
                candidate = current_path / name
                relative = candidate.relative_to(root)
                if candidate.is_symlink():
                    raise ValueError(f"symlinks are not packageable: {relative}")
                if any(part in EXCLUDED_PARTS or part in EXCLUDED_NAMES for part in relative.parts):
                    continue
                if not candidate.is_file():
                    raise ValueError(f"non-regular package path: {relative}")
                yield candidate, relative


def package(root: str | Path, output: str | Path) -> str:
    root_path = Path(root).resolve()
    output_path = Path(output).expanduser().resolve()
    files = sorted(_files(root_path), key=lambda item: item[1].as_posix())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source, relative in files:
            info = zipfile.ZipInfo(relative.as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())
    return hashlib.sha256(output_path.read_bytes()).hexdigest()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        print(package(args.root, args.output))
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
