"""Deterministic, local-only synthetic workshop tools."""
from __future__ import annotations

from .runtime import Tool


def _status(service: str):
    return {"service": service, "status": "healthy", "source": "synthetic", "region": "workshop-local"}


def _logs(query: str, limit: int = 5):
    if not isinstance(query, str) or len(query) > 256:
        raise ValueError("query exceeds limit")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 20:
        raise ValueError("limit out of range")
    rows = [
        {"timestamp": "2026-01-01T00:00:01Z", "service": "api", "message": "request completed"},
        {"timestamp": "2026-01-01T00:00:02Z", "service": "worker", "message": "timeout retry observed"},
        {"timestamp": "2026-01-01T00:00:03Z", "service": "api", "message": "request completed"},
    ]
    matches = [row for row in rows if query.lower() in row["message"].lower()]
    return {"query": query, "matches": matches[:limit], "source": "synthetic"}


def default_tools(fail_tool: bool = False) -> list[Tool]:
    tools = [
        Tool("service_status", "Read synthetic service status", {"type": "object", "properties": {"service": {"type": "string", "enum": ["api", "worker", "gateway"]}}, "required": ["service"], "additionalProperties": False}, _status),
        Tool("search_logs", "Search bounded synthetic logs", {"type": "object", "properties": {"query": {"type": "string", "maxLength": 256}, "limit": {"type": "integer", "minimum": 1, "maximum": 20}}, "required": ["query"], "additionalProperties": False}, _logs),
    ]
    if fail_tool:
        tools.append(Tool("controlled_failure", "Controlled test failure", {"type": "object", "properties": {}, "additionalProperties": False}, lambda: (_ for _ in ()).throw(RuntimeError("controlled failure"))))
    return tools
