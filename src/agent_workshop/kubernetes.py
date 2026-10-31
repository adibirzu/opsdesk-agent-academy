"""OKE adapter for the same agent service and Vault runtime-bundle contract."""
import os

from .auth import oke_signer
from .hosted import _RUNTIME_DIR, load_runtime_config, serve, entrypoint


def main():
    if not os.getenv("OCI_REGION"):
        raise ValueError("OCI_REGION is required for OKE bootstrap")
    os.environ.setdefault("OCI_RESOURCE_PRINCIPAL_REGION", os.environ["OCI_REGION"])
    if os.environ["OCI_RESOURCE_PRINCIPAL_REGION"] != os.environ["OCI_REGION"]:
        raise ValueError("Workload identity region differs from deployment region")
    config = load_runtime_config(signer_factory=oke_signer, auth_type="OKE_WORKLOAD_IDENTITY")
    os.chdir(_RUNTIME_DIR)
    serve(config, bind="0.0.0.0", port=8080)
    return 0


if __name__ == "__main__":
    raise SystemExit(entrypoint(main))
