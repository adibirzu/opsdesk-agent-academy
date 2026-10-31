#!/usr/bin/env python3
"""Read-only OCI target preflight.

The command intentionally prints only status labels.  Target identifiers live in
the private vars file and are never copied into the result.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any, Mapping


REQUIRED_VARS = (
    "tenancy_ocid",
    "tenancy_name",
    "profile",
    "region",
    "parent_compartment_ocid",
    "availability_domain",
    "image_ocid",
)


class PreflightError(ValueError):
    """A safe, user-facing validation failure."""


def _private_file(path: Path) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode != 0o600:
        raise PreflightError("private vars file must have mode 0600")


def load_vars(path: str | os.PathLike[str]) -> dict[str, Any]:
    candidate = Path(path)
    try:
        if candidate.is_symlink() or not candidate.is_file():
            raise PreflightError("private vars path must be a regular file")
        _private_file(candidate)
        with candidate.open(encoding="utf-8") as stream:
            values = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise PreflightError("unable to read private vars file") from exc
    if not isinstance(values, dict):
        raise PreflightError("private vars must be a JSON object")
    missing = [key for key in REQUIRED_VARS if not isinstance(values.get(key), str) or not values[key].strip()]
    if missing:
        raise PreflightError("private vars are missing required fields")
    return values


def _value(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _items(result: Any) -> list[Any]:
    data = _value(result, "data", result)
    return list(data or [])


def _call(client: Any, method: str, **kwargs: Any) -> Any:
    try:
        return getattr(client, method)(**kwargs)
    except TypeError:
        # Small injected fakes often accept only the semantically relevant args.
        reduced = {key: value for key, value in kwargs.items() if value is not None}
        return getattr(client, method)(**reduced)
    except Exception as exc:  # OCI errors must not leak identifiers.
        raise PreflightError("OCI read-only inspection failed") from exc


def prove_membership(identity_client: Any, compartment_id: str, tenancy_ocid: str) -> bool:
    """Walk compartment parents until the configured tenancy is reached."""
    current = compartment_id
    seen: set[str] = set()
    for _ in range(64):
        if current == tenancy_ocid:
            return True
        if not current or current in seen:
            return False
        seen.add(current)
        compartment = _call(identity_client, "get_compartment", compartment_id=current)
        data = _value(compartment, "data", compartment)
        returned_id = _value(data, "id")
        if returned_id and returned_id != current:
            return False
        current = _value(data, "compartment_id")
    return False


def _check_target(clients: Mapping[str, Any], values: Mapping[str, Any]) -> dict[str, str]:
    identity = clients["identity"]
    compute = clients["compute"]
    tenancy = values["tenancy_ocid"]
    compartment = values["parent_compartment_ocid"]
    if not prove_membership(identity, compartment, tenancy):
        raise PreflightError("configured compartment is not below the configured tenancy")
    tenancy_response = _call(identity, "get_tenancy", tenancy_id=tenancy)
    tenancy_data = _value(tenancy_response, "data", tenancy_response)
    if _value(tenancy_data, "name") != values["tenancy_name"]:
        raise PreflightError("configured tenancy name does not match OCI")

    shape = values.get("shape", "VM.Standard.E4.Flex")
    shape_rows = _items(_call(
        compute,
        "list_shapes",
        compartment_id=compartment,
        availability_domain=values["availability_domain"],
        image_id=values["image_ocid"],
    ))
    matching_rows = [
        row for row in shape_rows
        if _value(row, "shape") == shape
        and _value(row, "image_id") in (None, values["image_ocid"])
        and _value(row, "availability_domain") in (None, values["availability_domain"])
    ]
    if not matching_rows:
        raise PreflightError("requested VM shape, image, and availability domain are incompatible")

    image = _call(compute, "get_image", image_id=values["image_ocid"])
    image_data = _value(image, "data", image)
    if _value(image_data, "lifecycle_state", "AVAILABLE") not in (None, "AVAILABLE"):
        raise PreflightError("configured image is not available")
    return {
        "membership": "passed",
        "shape_image_ad": "passed",
        "region": "passed",
        "profile": "passed",
    }


def run_preflight(values: Mapping[str, Any], profile: str, config: Mapping[str, Any], clients: Mapping[str, Any]) -> dict[str, str]:
    """Validate bindings and target compatibility using injected read-only clients."""
    if values.get("profile") != profile or config.get("profile") not in (None, profile):
        raise PreflightError("profile does not match private vars")
    if config.get("region") != values.get("region"):
        raise PreflightError("OCI config region does not match private vars")
    if config.get("tenancy") != values.get("tenancy_ocid"):
        raise PreflightError("OCI config tenancy does not match private vars")
    summary = _check_target(clients, values)
    return {"status": "passed", **summary}


def _live_clients(values: Mapping[str, Any], profile: str) -> tuple[dict[str, str], dict[str, Any]]:
    try:
        import oci  # type: ignore
    except ImportError as exc:
        raise PreflightError("OCI SDK is required for live preflight") from exc
    try:
        config = dict(oci.config.from_file(profile_name=profile))
        config["profile"] = profile
        clients = {
            "identity": oci.identity.IdentityClient(config),
            "compute": oci.core.ComputeClient(config),
        }
        return config, clients
    except Exception as exc:
        raise PreflightError("unable to initialize OCI read-only clients") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only OCI workshop target preflight")
    parser.add_argument("--vars", required=True, help="private JSON vars file (mode 0600)")
    parser.add_argument("--profile", default="DEFAULT")
    args = parser.parse_args(argv)
    try:
        values = load_vars(args.vars)
        config, clients = _live_clients(values, args.profile)
        summary = run_preflight(values, args.profile, config, clients)
    except PreflightError as exc:
        print(json.dumps({"status": "failed", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
