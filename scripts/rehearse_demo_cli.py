#!/usr/bin/env python3
"""Run a reviewed, isolated loopback OpsDesk rehearsal; never contact a model."""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Any

SOURCE_SUFFIXES = {'.py', '.html', '.css', '.js', '.md'}
EXCLUDED_PARTS = {'__pycache__', '.git', 'node_modules', '.venv'}
MAX_SOURCE_BYTES = 2_000_000
BODY_LIMIT_PROBE = 70_000


def fingerprint(app_dir: Path) -> tuple[str, list[str]]:
    """Hash selected local source bytes without opening secrets or following links."""
    app_dir = app_dir.resolve(strict=True)
    if not app_dir.is_dir():
        raise ValueError('App source must be a directory')
    digest = hashlib.sha256()
    names: list[str] = []
    total = 0
    for path in sorted(app_dir.rglob('*')):
        relative = path.relative_to(app_dir)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError('Symlinks are not accepted in the reviewed app source')
        if not path.is_file() or path.suffix not in SOURCE_SUFFIXES or path.name.startswith('.'):
            continue
        total += path.stat().st_size
        if total > MAX_SOURCE_BYTES:
            raise ValueError('App source exceeds the bounded rehearsal size')
        data = path.read_bytes()
        name = relative.as_posix()
        digest.update(name.encode() + b'\0' + hashlib.sha256(data).digest())
        names.append(name)
    if not names:
        raise ValueError('No selected source files found')
    return digest.hexdigest(), names


def private_write(path: Path, text: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(text)


def request(port: int, method: str, path: str, body: bytes | None = None,
            *, origin: str | None = None) -> tuple[int, Any]:
    """Only contact the owned loopback process. Never follow redirects."""
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
    headers = {'Content-Type': 'application/json'}
    if origin is not None:
        headers['Origin'] = origin
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read(100_001)
        if len(raw) > 100_000:
            raise ValueError('Unexpected oversized response')
        try:
            payload: Any = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            payload = {'non_json_response': True}
        return response.status, payload
    finally:
        connection.close()


def check_response(case: str, status: int, payload: Any) -> bool:
    """The normal case must stay disconnected, not be misreported as AI success."""
    if case == 'page':
        return status == 200
    if case in {'cross_origin', 'missing_origin'}:
        return status in {400, 403}
    if case in {'invalid_body', 'malformed_json', 'unexpected_field'}:
        return status in {400, 422}
    if case == 'oversized_body':
        return status == 413
    if not isinstance(payload, dict):
        return False
    outcome = payload.get('outcome', payload.get('status'))
    calls = payload.get('model_calls')
    event = payload.get('event')
    if calls is None and isinstance(event, dict) and event.get('model_constructed') is False:
        calls = event.get('model_calls')
    if case == 'policy_stop':
        return status in {200, 403} and outcome == 'approval_required' and type(calls) is int and calls == 0
    if case == 'disconnected':
        return status in {200, 503} and outcome == 'model_not_configured' and type(calls) is int and calls == 0
    raise ValueError('Unknown rehearsal case')


def run(app_dir: Path, output: Path, reviewed: str, entry: str = 'app.py') -> dict[str, Any]:
    app_dir = app_dir.resolve(strict=True)
    actual, names = fingerprint(app_dir)
    if reviewed != actual:
        raise ValueError('Reviewed source fingerprint does not match; inspect changed files before running')
    if Path(entry).name != entry or entry not in names or not entry.endswith('.py'):
        raise ValueError('Entry must be a reviewed top-level Python source filename')
    if output.exists() or output.is_symlink():
        raise ValueError('Choose a new private output directory; existing evidence is preserved')
    output.mkdir(parents=True, mode=0o700)
    os.chmod(output, 0o700)
    with socket.socket() as socket_probe:
        socket_probe.bind(('127.0.0.1', 0))
        port = socket_probe.getsockname()[1]
    origin = f'http://127.0.0.1:{port}'
    # Deliberately do not forward model keys, cloud variables, HOME or user Python settings.
    environment = {key: os.environ[key] for key in ('PATH', 'SYSTEMROOT', 'WINDIR', 'TMPDIR') if key in os.environ}
    environment.update({'PYTHONUNBUFFERED': '1', 'PYTHONUTF8': '1'})
    command = [sys.executable, '-E', '-s', entry, '--port', str(port)]
    private_write(output / 'command.json', json.dumps({'argv': command, 'source_sha256': actual, 'files': names}, indent=2) + '\n')
    log_fd = os.open(output / 'server.log', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    process = None
    checks = []
    completed = False
    try:
        with os.fdopen(log_fd, 'wb') as log:
            process = subprocess.Popen(command, cwd=app_dir, env=environment, stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + 15
            while True:
                if process.poll() is not None:
                    raise RuntimeError('Reviewed server exited; inspect private server.log')
                try:
                    status, data = request(port, 'GET', '/')
                    break
                except (ConnectionError, OSError):
                    if time.monotonic() >= deadline:
                        raise RuntimeError('Reviewed server did not become ready within fifteen seconds')
                    time.sleep(0.1)
            checks.append({'case': 'page', 'http_status': status, 'passed': check_response('page', status, data)})
            cases = [
                ('disconnected', b'{"service":"payments","action":"investigate"}', origin),
                ('policy_stop', b'{"service":"payments","action":"restart"}', origin),
                ('invalid_body', b'{"service":"not-a-permitted-service","action":"investigate"}', origin),
                ('malformed_json', b'{', origin),
                ('unexpected_field', b'{"service":"payments","action":"investigate","endpoint":"https://example.invalid"}', origin),
                ('cross_origin', b'{"service":"payments","action":"investigate"}', 'https://example.invalid'),
                ('missing_origin', b'{"service":"payments","action":"investigate"}', None),
                ('oversized_body', b'x' * BODY_LIMIT_PROBE, origin),
            ]
            for case, body, selected_origin in cases:
                status, payload = request(port, 'POST', '/api/investigate', body, origin=selected_origin)
                checks.append({'case': case, 'http_status': status, 'passed': check_response(case, status, payload),
                               'response': payload})
            completed = True
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        try:
            source_unchanged = fingerprint(app_dir)[0] == actual
        except (ValueError, OSError):
            source_unchanged = False
        result = {'evidence_class': 'locally_verified' if completed and source_unchanged and len(checks) == 9 and all(c['passed'] for c in checks) else 'local_check_failed',
                  'source_sha256': actual, 'source_unchanged': source_unchanged, 'checks': checks, 'provider_calls': 'not_requested_by_runner',
                  'telemetry_exports': 'not_requested_by_runner', 'live_ai_acceptance': 'unverified',
                  'process_cleanup': process is not None and process.poll() is not None,
                  'scope': 'isolated loopback teaching app; not production authentication'}
        private_write(output / 'receipt.json', json.dumps(result, indent=2) + '\n')
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-dir', type=Path, required=True)
    parser.add_argument('--fingerprint', action='store_true', help='Hash selected source only; execute nothing')
    parser.add_argument('--reviewed-sha256', help='Source fingerprint after human/agent source review')
    parser.add_argument('--entry', default='app.py')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        if args.fingerprint:
            digest, files = fingerprint(args.app_dir)
            print(json.dumps({'sha256': digest, 'files': files}, indent=2))
            return 0
        if not args.reviewed_sha256 or args.output is None:
            parser.error('--reviewed-sha256 and --output are required to execute the reviewed app')
        result = run(args.app_dir, args.output, args.reviewed_sha256, args.entry)
        print(json.dumps({key: result[key] for key in ('evidence_class', 'provider_calls', 'telemetry_exports', 'live_ai_acceptance', 'process_cleanup')}, indent=2))
        return 0 if result['evidence_class'] == 'locally_verified' else 1
    except (ValueError, RuntimeError, OSError, http.client.HTTPException) as exc:
        print(f'Rehearsal stopped: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
