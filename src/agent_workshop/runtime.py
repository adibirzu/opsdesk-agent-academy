"""Small standard-library agent runtime for the workshop."""
from __future__ import annotations

import json
import re
import math
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Protocol


@dataclass(frozen=True)
class ModelReply:
    text: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_details: dict | None = None


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Any]


@dataclass(frozen=True)
class RunResult:
    outcome: str
    answer: str | None
    run_id: str
    trace_id: str | None
    session_id: str
    steps: int
    input_tokens: int | None
    output_tokens: int | None
    model: str | None
    errors: tuple[str, ...] = ()
    estimated_cost_usd: float | None = None

    @property
    def usage(self) -> dict[str, int] | None:
        if self.input_tokens is None or self.output_tokens is None:
            return None
        return {"input_tokens": self.input_tokens, "output_tokens": self.output_tokens}


class Model(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> ModelReply: ...


class _NullSpan:
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def set_attribute(self, *_): return None


class _NullObserver:
    def span(self, name, attributes): return _NullSpan()
    def event(self, name, **fields): return None
    def trace_id(self): return None


def _validate(value: Any, schema: dict[str, Any], path: str = "arguments") -> None:
    typ = schema.get("type")
    if typ not in {"object", "string", "integer", "number", "boolean"}:
        raise ValueError("unsupported schema type")
    valid = {"object": isinstance(value, dict), "string": isinstance(value, str),
             "integer": isinstance(value, int) and not isinstance(value, bool),
             "number": isinstance(value, (int, float)) and not isinstance(value, bool),
             "boolean": isinstance(value, bool)}
    if typ in valid and not valid[typ]:
        raise ValueError(f"{path} must be {typ}")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{path} must be finite")
    if isinstance(value, str) and "maxLength" in schema and len(value) > schema["maxLength"]:
        raise ValueError(f"{path} exceeds maximum length")
    if isinstance(value, (int, float)) and "minimum" in schema and value < schema["minimum"]:
        raise ValueError(f"{path} below minimum")
    if isinstance(value, (int, float)) and "maximum" in schema and value > schema["maximum"]:
        raise ValueError(f"{path} above maximum")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path} is not an allowed value")
    if typ == "object":
        props = schema.get("properties", {})
        required = schema.get("required", [])
        missing = [key for key in required if key not in value]
        if missing:
            raise ValueError(f"missing required argument: {missing[0]}")
        if schema.get("additionalProperties") is False:
            extra = set(value) - set(props)
            if extra:
                raise ValueError(f"unknown argument: {sorted(extra)[0]}")
        for key, item in value.items():
            if key in props:
                _validate(item, props[key], f"{path}.{key}")


def _validate_schema(schema: Any) -> None:
    if not isinstance(schema, dict) or schema.get("type") not in {"object", "string", "integer", "number", "boolean"}:
        raise ValueError("unsupported schema type")
    if schema.get("type") == "object":
        props = schema.get("properties", {})
        if not isinstance(props, dict): raise ValueError("invalid properties schema")
        for child in props.values(): _validate_schema(child)


def _safe_error(exc: Exception) -> str:
    category = type(exc).__name__.lower().replace("error", "") or "failure"
    return f"{category} failure"


def _mark_error(span: Any) -> None:
    """Mark a span failed without putting exception details into telemetry."""
    if span is None:
        return
    try:
        span.set_attribute("status", "error")
    except Exception:
        pass
    try:
        from opentelemetry.trace import Status, StatusCode
        span.set_status(Status(StatusCode.ERROR))
    except (ImportError, AttributeError, TypeError):
        pass


class Agent:
    def __init__(self, model: Model, tools: list[Tool], observer: Any = None,
                 max_steps: int = 6, max_output_chars: int = 8000,
                 instructions: str = "Return strict JSON with either answer or tool and arguments.",
                 max_total_tokens: int | None = None, stop_on_tool_error: bool = False):
        if max_steps < 1 or max_output_chars < 1 or (max_total_tokens is not None and max_total_tokens < 1):
            raise ValueError("runtime limits must be positive")
        if len({t.name for t in tools}) != len(tools) or any(not t.name for t in tools):
            raise ValueError("tool names must be unique and non-empty")
        for tool in tools:
            _validate_schema(tool.parameters)
        self.model, self.tools, self.observer = model, {t.name: t for t in tools}, observer or _NullObserver()
        self.max_steps, self.max_output_chars = max_steps, max_output_chars
        self.instructions, self.max_total_tokens = instructions, max_total_tokens
        self.stop_on_tool_error = stop_on_tool_error

    def run(self, prompt: str, session_id: str, history: list[dict[str, str]] | None = None) -> RunResult:
        run_id = str(uuid.uuid4())
        trace_id = None
        errors: list[str] = []
        in_tokens = out_tokens = None
        model_name = None
        usage_available = True
        known_total_tokens = 0
        steps = 0
        root = None
        run_started = time.monotonic()
        if not isinstance(prompt, str) or len(prompt) > 16000 or not isinstance(session_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", session_id):
            return RunResult("failure", None, run_id, None, session_id, 0, None, None, None, ("invalid input",))
        total_cost, cost_available = 0.0, True
        messages = [{"role": "system", "content": self.instructions}]
        messages.extend(history or [])
        messages.append({"role": "user", "content": prompt})
        try:
            with self.observer.span("agent.run", {"session.id": session_id, "workshop.run_id": run_id, "langfuse.observation.type": "agent", "status": "running"}) as root:
                trace_id = self.observer.trace_id()
                root.set_attribute("trace.id", trace_id)
                root.set_attribute("session.id", session_id)
                root.set_attribute("workshop.run_id", run_id)
                self.observer.event("run.start", session_id=session_id, run_id=run_id, trace_id=trace_id)
                for steps in range(1, self.max_steps + 1):
                    started = time.monotonic()
                    self.observer.event("step.start", step=steps, run_id=run_id)
                    span = None
                    try:
                        with self.observer.span("llm.complete", {"step": steps, "status": "running"}) as span:
                            try:
                                reply = self.model.complete(messages)
                                if not isinstance(reply, ModelReply):
                                    raise TypeError("model returned invalid reply")
                                for tokens in (reply.input_tokens, reply.output_tokens):
                                    if tokens is not None and (isinstance(tokens, bool) or not isinstance(tokens, int) or not 0 <= tokens <= 1_000_000_000):
                                        raise ValueError("invalid model usage")
                                span.set_attribute("langfuse.observation.type", "generation")
                                span.set_attribute("gen_ai.request.model", reply.model)
                                span.set_attribute("gen_ai.response.model", reply.model)
                                span.set_attribute("status", "success")
                                if reply.input_tokens is not None:
                                    span.set_attribute("gen_ai.usage.input_tokens", reply.input_tokens)
                                if reply.output_tokens is not None:
                                    span.set_attribute("gen_ai.usage.output_tokens", reply.output_tokens)
                                if reply.cost_details is None:
                                    cost_available = False
                                else:
                                    cost = reply.cost_details
                                    if (not isinstance(cost, dict) or any(isinstance(cost.get(k), bool) or
                                            not isinstance(cost.get(k), (int, float)) or not math.isfinite(cost[k]) or cost[k] < 0
                                            for k in ("input", "output", "total")) or
                                            not math.isclose(cost["total"], cost["input"] + cost["output"], rel_tol=1e-9, abs_tol=1e-12)):
                                        raise ValueError("invalid model cost estimate")
                                    total_cost += cost["total"]
                                    span.set_attribute("langfuse.observation.cost_details", json.dumps({k: cost[k] for k in ("input", "output", "total")}))
                                    span.set_attribute("workshop.cost.basis", cost["basis"])
                                    span.set_attribute("workshop.cost.provider_billed", False)
                                    span.set_attribute("workshop.pricing.source", cost["source"])
                                    span.set_attribute("workshop.pricing.as_of", cost["as_of"])
                                self.observer.event("llm.usage", model=reply.model, step=steps,
                                    input_tokens=reply.input_tokens, output_tokens=reply.output_tokens,
                                    estimated_cost_usd=reply.cost_details["total"] if reply.cost_details else None,
                                    cost_basis="configured_uncached_text_rates" if reply.cost_details else "unavailable")
                                if getattr(self.observer, "capture_content", False):
                                    content = getattr(self.observer, "content_attribute", None)
                                    encode = content or (lambda value: json.dumps(value, default=str)[:4000])
                                    span.set_attribute("langfuse.observation.input", encode(messages))
                                    span.set_attribute("langfuse.observation.output", encode(reply.text))
                                model_name = reply.model
                            except Exception:
                                _mark_error(span)
                                _mark_error(root)
                                raise
                    except Exception as exc:
                        cost_available = False
                        errors.append("model error: " + _safe_error(exc))
                        self.observer.event("step.error", step=steps, run_id=run_id, error=errors[-1])
                        break
                    known_total_tokens += (reply.input_tokens or 0) + (reply.output_tokens or 0)
                    if reply.input_tokens is None or reply.output_tokens is None:
                        usage_available = False
                    elif usage_available and (in_tokens is not None or out_tokens is not None):
                        in_tokens = (in_tokens or 0) + reply.input_tokens
                        out_tokens = (out_tokens or 0) + reply.output_tokens
                    elif usage_available:
                        in_tokens, out_tokens = reply.input_tokens, reply.output_tokens
                    if self.max_total_tokens is not None and known_total_tokens > self.max_total_tokens:
                        errors.append("token budget exhausted")
                        break
                    try:
                        action = json.loads(reply.text, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid JSON number")))
                        if not isinstance(action, dict) or set(action) not in ({"answer"}, {"tool", "arguments"}):
                            raise ValueError("model output must contain answer or tool and arguments")
                        if "answer" in action:
                            if not isinstance(action["answer"], str): raise ValueError("answer must be a string")
                            answer = action["answer"][:self.max_output_chars]
                            self.observer.event("run.end", status="success", steps=steps, run_id=run_id, trace_id=trace_id, duration_ms=int((time.monotonic()-run_started)*1000))
                            if not usage_available:
                                in_tokens = out_tokens = None
                            root.set_attribute("status", "success")
                            return RunResult("success", answer, run_id, trace_id, session_id, steps, in_tokens, out_tokens, reply.model,
                                             estimated_cost_usd=round(total_cost, 12) if cost_available else None)
                        name, args = action["tool"], action["arguments"]
                        if name not in self.tools: raise ValueError("unknown tool")
                        if not isinstance(args, dict): raise ValueError("arguments must be an object")
                        tool = self.tools[name]
                        _validate(args, tool.parameters)
                    except Exception as exc:
                        _mark_error(root)
                        errors.append("invalid action: " + _safe_error(exc))
                        self.observer.event("run.error", status="failure", run_id=run_id, error=errors[-1])
                        break
                    try:
                        with self.observer.span("tool." + name, {"tool.name": name, "step": steps, "status": "running"}) as tool_span:
                            self.observer.event("tool.start", tool=name, step=steps, status="running")
                            try:
                                observation = tool.handler(**args)
                            except Exception as exc:
                                _mark_error(tool_span)
                                content = json.dumps({"ok": False, "error": _safe_error(exc)})
                                self.observer.event("tool.error", tool=name, status="failure", step=steps, duration_ms=0)
                                if self.stop_on_tool_error:
                                    errors.append("tool execution failed")
                                    _mark_error(root)
                                    break
                            else:
                                content = json.dumps({"ok": True, "result": observation}, default=str)[:self.max_output_chars]
                                self.observer.event("tool.end", tool=name, status="success", step=steps, duration_ms=0)
                    except Exception as exc:
                        _mark_error(root)
                        errors.append("tool telemetry failure")
                        break
                    messages.append({"role": "assistant", "content": reply.text})
                    messages.append({"role": "user", "content": "Untrusted tool observation: " + content})
                else:
                    errors.append("step budget exhausted")
                self.observer.event("run.end", status="failure", steps=steps, run_id=run_id, trace_id=trace_id, duration_ms=int((time.monotonic()-run_started)*1000))
                _mark_error(root)
        except Exception as exc:
            _mark_error(root)
            errors.append("observer or runtime error: " + _safe_error(exc))
        if not usage_available:
            in_tokens = out_tokens = None
        return RunResult("failure", None, run_id, trace_id, session_id, steps, in_tokens, out_tokens, model_name, tuple(errors),
                         estimated_cost_usd=round(total_cost, 12) if cost_available else None)
