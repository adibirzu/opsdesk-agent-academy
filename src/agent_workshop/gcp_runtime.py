"""Cloud Run entry point using an explicitly mounted private runtime bundle."""
import base64
import json
import os
from functools import partial
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace

from . import hosted, service
from .config import load

_MAX_BUNDLE_BYTES = 128 * 1024
_BUNDLE_ENV = "WORKSHOP_GCP_BUNDLE_FILE"
_SCRIPTED_ENV = "WORKSHOP_GCP_SCRIPTED"
_CLOUD_RUN_BUNDLE = Path("/secrets/workshop/bundle.json")


def _bundle_mode_allowed(path: Path, mode: int) -> bool:
    return mode == 0o600 or (path == _CLOUD_RUN_BUNDLE and mode == 0o444)


def _bundle_path() -> Path:
    raw = os.environ.get(_BUNDLE_ENV)
    if not raw or not Path(raw).is_absolute():
        raise ValueError("GCP runtime bundle path is required")
    supplied = Path(raw)
    if ".." in supplied.parts:
        raise ValueError("GCP runtime bundle path is invalid")
    current = Path(supplied.anchor)
    for part in supplied.parts[1:]:
        current = current / part
        # macOS exposes the standard temporary directory through /var; permit
        # that platform alias while rejecting caller-controlled symlinks.
        if current.is_symlink() and current not in {Path("/var"), Path("/tmp")}:
            raise ValueError("GCP runtime bundle path is invalid")
    return supplied


def load_config():
    """Load a bounded JSON bundle without logging configuration or secret values."""
    path = _bundle_path()
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or not _bundle_mode_allowed(path, metadata.st_mode & 0o777):
            raise ValueError
        if metadata.st_size > _MAX_BUNDLE_BYTES:
            raise ValueError
        with os.fdopen(descriptor, "rb") as source:
            descriptor = -1
            raw = source.read(_MAX_BUNDLE_BYTES + 1)
        if len(raw) > _MAX_BUNDLE_BYTES:
            raise ValueError
        # Reuse the established hosted payload contract and environment allowlist.
        payload = hosted._decode_bundle(SimpleNamespace(data=SimpleNamespace(secret_bundle_content=
            SimpleNamespace(content=base64.b64encode(raw).decode("ascii")))))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError, AttributeError):
        raise ValueError("GCP runtime bundle is invalid") from None
    finally:
        if "descriptor" in locals() and descriptor >= 0:
            os.close(descriptor)
    descriptor, config_name = tempfile.mkstemp(prefix="gcp-workshop-config-", suffix=".toml")
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w") as output:
            output.write(payload["config_toml"])
        config = load(config_name)
    finally:
        try:
            os.unlink(config_name)
        except OSError:
            pass
    if config.model.get("kind") not in {"openai", "vertex"}:
        raise ValueError("GCP runtime supports only OpenAI or Vertex models")
    if config.oci.get("log_namespace"):
        raise ValueError("OCI log upload is not configured for GCP runtime")
    if config.telemetry.get("capture_content", False):
        raise ValueError("GCP runtime requires metadata-only telemetry")
    token_ref = config.telemetry.get("service_token_env")
    token = payload["environment"].get(token_ref) if token_ref else None
    if not token and token_ref:
        token = os.environ.get(token_ref)
    if not isinstance(token, str) or not token:
        raise ValueError("GCP runtime requires an application access token")
    os.environ.update(payload["environment"])
    return config


def _scripted() -> bool:
    value = os.environ.get(_SCRIPTED_ENV, "")
    if value not in {"", "1"}:
        raise ValueError("GCP scripted mode switch is invalid")
    return value == "1"


def main() -> int:
    scripted = _scripted()
    config = load_config()
    if scripted:
        # Keep the application token reference for HTTP auth; no exporter config is used.
        token_ref = config.telemetry["service_token_env"]
        config.telemetry = {"service_token_env": token_ref}
    original_execute = service.execute
    service.execute = partial(original_execute, stream=sys.stdout, scripted=scripted)
    try:
        hosted.serve(config, bind="0.0.0.0", port=8080)
    finally:
        service.execute = original_execute
    return 0


def entrypoint(start=main) -> int:
    try:
        return start()
    except Exception as exc:
        print(json.dumps({"outcome": "failure", "stage": "runtime_bootstrap",
                          "error_type": type(exc).__name__}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(entrypoint())
