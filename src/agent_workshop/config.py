"""Private TOML configuration; credentials are environment references only."""
from dataclasses import dataclass, field
from pathlib import Path
import os
import re
import tomllib
from urllib.parse import urlsplit


def _allowed_hosts(value):
    if not isinstance(value, list) or not value or any(not isinstance(host, str) for host in value):
        raise ValueError("Exact allowed_hosts list is required")
    hosts = []
    for host in value:
        normalized = host.lower()
        if (not normalized or normalized in hosts or "*" in normalized or normalized.startswith(".") or
                any(ch in normalized for ch in "/?#{}<> ") or not re.fullmatch(r"[A-Za-z0-9.:-]+", normalized)):
            raise ValueError("allowed_hosts must contain exact hostnames")
        hosts.append(normalized)
    return hosts


def endpoint(value: str, *, local: bool = False, allowed_hosts=None) -> str:
    p = urlsplit(value)
    if p.username or p.password or p.query or p.fragment or not p.hostname or "{" in value or "}" in value:
        raise ValueError("Endpoint must have a host and no credentials, query or fragment")
    if any(ch in p.hostname for ch in "{}<> ") or not re.fullmatch(r"[A-Za-z0-9.:-]+", p.hostname):
        raise ValueError("Endpoint hostname must be fully resolved")
    try:
        port = p.port
    except ValueError:
        raise ValueError("Endpoint port is invalid") from None
    if p.scheme == "https" and port not in (None, 443):
        raise ValueError("HTTPS endpoints must use port 443")
    if p.scheme != "https" and not (local and p.scheme == "http" and p.hostname.lower() in {"localhost", "127.0.0.1", "::1"}):
        raise ValueError("Remote endpoints require HTTPS")
    if allowed_hosts is not None and p.hostname.lower() not in _allowed_hosts(allowed_hosts):
        raise ValueError("Endpoint hostname is not in exact allowed_hosts")
    return value.rstrip("/")


def secret(name: str) -> str:
    if not re.fullmatch(r"[A-Z][A-Z0-9_]{2,127}", name):
        raise ValueError("Expected a secret environment-variable name")
    value = os.getenv(name, "")
    if not value:
        raise ValueError(f"Required environment reference is unset: {name}")
    return value


@dataclass
class Config:
    model: dict = field(default_factory=dict)
    telemetry: dict = field(default_factory=dict)
    oci: dict = field(default_factory=dict)
    limits: dict = field(default_factory=dict)


def load(path: str) -> Config:
    p = Path(path).expanduser()
    if p.is_symlink() or not p.is_file():
        raise ValueError("Configuration must be a regular file")
    # System service config may be root-owned and group-readable, inside a
    # root-owned directory; the service's mount namespace keeps it read-only.
    mode = p.stat().st_mode & 0o777
    if mode != 0o600 and not (mode == 0o640 and p.stat().st_uid == 0):
        raise ValueError("Private configuration must have mode 0600")
    data = tomllib.loads(p.read_text())
    if set(data) - {"model", "telemetry", "oci", "limits"}:
        raise ValueError("Unknown configuration section")
    if any(not isinstance(v, dict) for v in data.values()):
        raise ValueError("Configuration sections must be tables")
    c = Config(**data)
    if c.model.get("kind") not in {"oci", "openai", "vertex"}:
        raise ValueError("Model kind must be oci, openai or vertex")
    if not c.model.get("model_id"):
        raise ValueError("Explicit model_id is required")
    if "json_mode" in c.model and not isinstance(c.model["json_mode"], bool):
        raise ValueError("json_mode must be a boolean")
    max_output = c.model.get("max_output_tokens", 700)
    if isinstance(max_output, bool) or not isinstance(max_output, int) or not 1 <= max_output <= 4096:
        raise ValueError("Model max_output_tokens must be 1..4096")
    model_hosts = _allowed_hosts(c.model.get("allowed_hosts"))
    endpoint(c.model.get("endpoint", ""), allowed_hosts=model_hosts)
    if "pricing" in c.model:
        from .costs import validate_pricing
        validate_pricing(c.model["pricing"], c.model["model_id"])
    if "capture_content" in c.telemetry and not isinstance(c.telemetry["capture_content"], bool):
        raise ValueError("capture_content must be a boolean")
    telemetry_hosts = c.telemetry.get("allowed_hosts")
    if telemetry_hosts is not None:
        telemetry_hosts = _allowed_hosts(telemetry_hosts)
    for name in ("apm_endpoint", "langfuse_endpoint"):
        if c.telemetry.get(name):
            if not telemetry_hosts:
                raise ValueError("Telemetry endpoints require exact allowed_hosts")
            endpoint(c.telemetry[name], local=name == "langfuse_endpoint", allowed_hosts=telemetry_hosts)
    for name, maximum in (("max_steps", 20), ("max_total_tokens", 100000), ("max_output_chars", 32000)):
        value = c.limits.get(name, {"max_steps": 6, "max_total_tokens": 8000, "max_output_chars": 8000}[name])
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
            raise ValueError(f"Invalid limit: {name}")
    return c
