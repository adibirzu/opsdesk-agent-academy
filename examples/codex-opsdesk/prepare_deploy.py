"""Copy only reviewed runtime source into a NEW deployment folder; never scans private files."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
RUNTIME_FILES = (
    '.vercelignore', 'app.py', 'engine.py', 'security.py', 'telemetry.py',
    'requirements.txt', 'pyproject.toml', 'vercel.json',
    'static/index.html', 'static/style.css', 'static/app.js',
)


def prepare(output, source=ROOT):
    output, source = Path(output), Path(source)
    if output.exists() or output.is_symlink():
        raise ValueError('Choose a new deployment folder; existing files are never overwritten.')
    reviewed = []
    for name in RUNTIME_FILES:
        path = source / name
        ancestors = [path, *path.parents][:len(Path(name).parts)]
        if not path.is_file() or any(p.is_symlink() for p in ancestors):
            raise ValueError('Runtime source must be reviewed regular files, not symlinks: ' + name)
        reviewed.append((name, path))
    output.mkdir(parents=True, exist_ok=False)
    manifest = []
    for name, path in reviewed:
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        manifest.append({'file': name, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
    (output / 'DEPLOYMENT-SOURCE.json').write_text(json.dumps({
        'status': 'prepared_source_not_deployed', 'files': manifest,
        'excludes': 'All files outside the explicit runtime allowlist, including local settings, credentials, virtual environments and caches.'}, indent=2) + '\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        manifest = prepare(args.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f'Prepared {len(manifest)} reviewed runtime files in a new folder; no credentials, link, upload, build or deployment performed.')


if __name__ == '__main__': main()
