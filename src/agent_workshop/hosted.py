"""OCI hosted-runtime bootstrap; Vault supplies the private runtime bundle."""
import base64
import json
import os
from pathlib import Path
import stat

from .config import load


_RUNTIME_DIR = Path("/tmp/agent-workshop")
_MAX_BUNDLE_BYTES = 128 * 1024
_ALLOWED_PAYLOAD_KEYS = frozenset({"config_toml", "environment", "ca_pem"})
_ALLOWED_SECRET_ENV = frozenset({
    "WORKSHOP_APM_KEY",
    "WORKSHOP_LANGFUSE_PUBLIC_KEY",
    "WORKSHOP_LANGFUSE_SECRET_KEY",
    "WORKSHOP_SERVICE_TOKEN",
    "WORKSHOP_MODEL_API_KEY",
})


def _resource_principal_signer():
    import oci
    return oci.auth.signers.get_resource_principals_signer()


def _vault_client(signer):
    import oci
    region = os.getenv("OCI_REGION") or os.getenv("OCI_RESOURCE_PRINCIPAL_REGION") or getattr(signer, "region", None)
    settings = {"region": region} if region else {}
    return oci.secrets.SecretsClient(settings, signer=signer, timeout=(5, 20),
                                    retry_strategy=oci.retry.NoneRetryStrategy())


def _certifi_roots() -> str:
    import certifi
    return Path(certifi.where()).read_text()


def _decode_bundle(response) -> dict:
    try:
        content = response.data.secret_bundle_content.content
        if not isinstance(content, str):
            raise ValueError
        if len(content) > ((_MAX_BUNDLE_BYTES + 2) // 3) * 4:
            raise ValueError
        raw = base64.b64decode(content.encode("ascii"), validate=True)
        if len(raw) > _MAX_BUNDLE_BYTES:
            raise ValueError
        payload = json.loads(raw.decode("utf-8"))
    except (AttributeError, UnicodeError, ValueError, json.JSONDecodeError):
        raise ValueError("Hosted runtime secret bundle is invalid") from None
    if not isinstance(payload, dict) or set(payload) - _ALLOWED_PAYLOAD_KEYS:
        raise ValueError("Hosted runtime secret bundle is invalid")
    if not isinstance(payload.get("config_toml"), str) or not isinstance(payload.get("environment"), dict):
        raise ValueError("Hosted runtime secret bundle is invalid")
    if "ca_pem" in payload and not isinstance(payload["ca_pem"], str):
        raise ValueError("Hosted runtime secret bundle is invalid")
    environment = payload["environment"]
    if (set(environment) - _ALLOWED_SECRET_ENV or
            any(not isinstance(value, str) or not value for value in environment.values())):
        raise ValueError("Hosted runtime secret bundle is invalid")
    return payload


def _private_directory(runtime_dir: Path) -> Path:
    runtime_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if runtime_dir.is_symlink() or not stat.S_ISDIR(runtime_dir.stat().st_mode):
        raise ValueError("Hosted runtime directory is invalid")
    runtime_dir.chmod(0o700)
    return runtime_dir


def _write_private(path: Path, content: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
        with os.fdopen(descriptor, "w") as output:
            output.write(content)
        path.chmod(0o600)
    except OSError:
        raise ValueError("Hosted runtime file cannot be written") from None


def load_runtime_config(*, signer_factory=_resource_principal_signer,
                        vault_client_factory=_vault_client, runtime_dir=_RUNTIME_DIR,
                        ca_roots=_certifi_roots, auth_type="RESOURCE_PRINCIPAL"):
    """Fetch, validate, and materialize a Vault bundle without logging its contents."""
    if auth_type not in {"RESOURCE_PRINCIPAL", "OKE_WORKLOAD_IDENTITY"}:
        raise ValueError("Unsupported runtime bootstrap identity")
    secret_id = os.getenv("WORKSHOP_RUNTIME_SECRET_ID")
    if not isinstance(secret_id, str) or not secret_id or len(secret_id) > 1024:
        raise ValueError("WORKSHOP_RUNTIME_SECRET_ID is required")
    signer = signer_factory()
    response = vault_client_factory(signer).get_secret_bundle(secret_id, stage="CURRENT")
    payload = _decode_bundle(response)
    runtime = _private_directory(Path(runtime_dir))
    config_path = runtime / "workshop.toml"
    _write_private(config_path, payload["config_toml"])
    config = load(str(config_path))
    config.oci["auth_type"] = auth_type
    if "ca_pem" in payload:
        ca_path = runtime / "ca-bundle.pem"
        roots = ca_roots()
        if not isinstance(roots, str):
            raise ValueError("Hosted certificate roots are invalid")
        _write_private(ca_path, roots + payload["ca_pem"])
        os.environ["REQUESTS_CA_BUNDLE"] = str(ca_path)
    os.environ.update(payload["environment"])
    return config


def serve(config, bind="0.0.0.0", port=8080):
    if bind != "0.0.0.0" or port != 8080:
        raise ValueError("Hosted listener must use the platform contract")
    from .service import handler, WorkshopHTTPServer
    handler_class = handler(config)
    server = WorkshopHTTPServer((bind, port), handler_class)
    try: server.serve_forever(poll_interval=.5)
    finally:
        server.server_close()
        handler_class.close_telemetry()


def main() -> int:
    config = load_runtime_config()
    os.chdir(_RUNTIME_DIR)
    serve(config, bind="0.0.0.0", port=8080)
    return 0


def entrypoint(start):
    """Bootstrap errors must not print provider identifiers or secret details."""
    import sys
    try:
        return start()
    except Exception as exc:
        print(json.dumps({"outcome": "failure", "stage": "runtime_bootstrap",
                          "error_type": type(exc).__name__}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(entrypoint(main))
