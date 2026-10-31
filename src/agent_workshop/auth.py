"""Process-scoped OCI workload identity; no copied user credentials."""
from functools import lru_cache


@lru_cache(maxsize=1)
def oke_signer():
    import oci
    return oci.auth.signers.get_oke_workload_identity_resource_principal_signer()
