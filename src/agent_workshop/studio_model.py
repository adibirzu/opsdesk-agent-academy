"""Bounded OpenAI-compatible SSE transport. No simulated responses or retries."""

from dataclasses import dataclass
import json
import re
import time
from urllib.request import Request, build_opener, ProxyHandler
from urllib.parse import urlsplit
from .config import endpoint, secret, _allowed_hosts
from .models import _NoRedirect


@dataclass
class Completion:
    content: str
    tool_calls: list
    model: str
    input_tokens: int | None
    output_tokens: int | None


class StreamingModel:
    def __init__(self, settings):
        self.settings = settings
        hosts = _allowed_hosts(settings.get("allowed_hosts"))
        if settings.get("api_key_env") and not re.fullmatch(
            r"[A-Z][A-Z0-9_]{2,127}", settings["api_key_env"]
        ):
            raise ValueError("Use a key environment reference, not a key value")
        raw = settings["endpoint"]
        parsed = urlsplit(raw)
        private = (
            settings.get("allow_private_http") is True
            and parsed.scheme == "http"
            and parsed.hostname
            and parsed.hostname in hosts
            and not (
                parsed.username or parsed.password or parsed.query or parsed.fragment
            )
            and parsed.port is not None
            and 1024 <= parsed.port <= 65535
            and parsed.path == "/v1"
        )
        self.base = (
            raw.rstrip("/")
            if private
            else endpoint(raw, local=True, allowed_hosts=hosts)
        )
        self.local = urlsplit(self.base).hostname in ("localhost", "127.0.0.1", "::1")
        self.direct = self.local or bool(private)
        if not self.local and not settings.get("api_key_env"):
            raise ValueError("Remote model requires an API key environment reference")

    def complete(self, messages, tools, emit):
        c = self.settings
        body = {
            "model": c["model_id"],
            "messages": messages,
            "tools": tools,
            "stream": True,
            "stream_options": {"include_usage": True},
            "temperature": 0,
            "max_tokens": c.get("max_output_tokens", 768),
        }
        headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
        if c.get("api_key_env"):
            headers["Authorization"] = "Bearer " + secret(c["api_key_env"])
        request = Request(
            self.base + "/chat/completions",
            data=json.dumps(body).encode(),
            headers=headers,
        )
        opener = (
            build_opener(ProxyHandler({}), _NoRedirect())
            if self.direct
            else build_opener(_NoRedirect())
        )
        content = ""
        calls = {}
        usage = {}
        model = c["model_id"]
        size = 0
        done = False
        deadline = time.monotonic() + 90
        try:
            with opener.open(request, timeout=30) as response:
                if not response.headers.get("Content-Type", "").startswith(
                    "text/event-stream"
                ):
                    raise ValueError("Provider did not return SSE")
                while raw := response.readline(64001):
                    size += len(raw)
                    if size > 262144 or len(raw) > 64000 or time.monotonic() > deadline:
                        raise ValueError("Provider stream exceeded bounds")
                    line = raw.decode("utf-8").strip()
                    if not line.startswith("data:"):
                        continue
                    text = line[5:].strip()
                    if text == "[DONE]":
                        done = True
                        break
                    row = json.loads(text)
                    if row.get("error"):
                        raise ValueError("Provider returned an error")
                    if row.get("model"):
                        model = row["model"]
                    if row.get("usage"):
                        usage = row["usage"]
                    for choice in row.get("choices", []):
                        if choice.get("index", 0) != 0:
                            continue
                        delta = choice.get("delta", {})
                        piece = delta.get("content")
                        if piece:
                            if (
                                not isinstance(piece, str)
                                or len(content) + len(piece) > 16000
                            ):
                                raise ValueError("Provider content exceeded bounds")
                            content += piece
                            emit("token", {"text": piece})
                        for fragment in delta.get("tool_calls", []):
                            index = fragment["index"]
                            if type(index) is not int or not 0 <= index < 4:
                                raise ValueError("Too many tools")
                            call = calls.setdefault(
                                index,
                                {
                                    "id": "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""},
                                },
                            )
                            call["id"] += fragment.get("id", "")
                            for key in ("name", "arguments"):
                                call["function"][key] += fragment.get(
                                    "function", {}
                                ).get(key, "")
                            if (
                                len(call["id"]) > 128
                                or len(call["function"]["name"]) > 80
                                or len(call["function"]["arguments"]) > 4096
                            ):
                                raise ValueError("Tool call exceeded bounds")
            if not done or not (content or calls):
                raise ValueError("Incomplete provider stream")
            tokens = []
            for key in ("prompt_tokens", "completion_tokens"):
                value = usage.get(key)
                if value is not None and (
                    type(value) is not int or not 0 <= value <= 10**8
                ):
                    raise ValueError("Invalid usage")
                tokens.append(value)
            return Completion(
                content, [calls[i] for i in sorted(calls)], model, *tokens
            )
        except Exception:
            raise RuntimeError(
                "Model stream failed. Check the selected server, model and credentials; no retry or fallback."
            ) from None
