"""Prepare a new private JSON binding interactively; never prints a credential."""
import argparse
import getpass
import json
import os
from pathlib import Path
import secrets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='New private JSON file; existing files are never overwritten')
    args = parser.parse_args()
    path = Path(args.output).expanduser()
    if not path.parent.is_dir() or path.parent.is_symlink():
        parser.error('Create the private parent directory first; symlink parents are not accepted.')
    values = {
        'WORKSHOP_LOGIN_SECRET': secrets.token_urlsafe(32),
        'SESSION_SIGNING_SECRET': secrets.token_urlsafe(32),
        'LOCAL_SINGLE_PROCESS_QUOTA': '1',
    }
    key = getpass.getpass('Approved AI Gateway key (blank leaves the app model disconnected): ').strip()
    if key: values['AI_GATEWAY_API_KEY'] = key
    print('Optional Langfuse binding: use your own project; leave all three blank to disable export.')
    base = input('Langfuse HTTPS origin (blank disables export): ').strip()
    if base:
        values.update(LANGFUSE_BASE_URL=base,
                      LANGFUSE_PUBLIC_KEY=getpass.getpass('Project public key (hidden): ').strip(),
                      LANGFUSE_SECRET_KEY=getpass.getpass('Ingestion secret (hidden): ').strip())
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as target:
        json.dump(values, target, indent=2); target.write('\n')
    print('Saved a private settings file. No key, login secret or derived Authorization value was printed.')
    print('Open it privately to copy WORKSHOP_LOGIN_SECRET into your app sign-in form. Exclude that step from recordings.')


if __name__ == '__main__': main()
