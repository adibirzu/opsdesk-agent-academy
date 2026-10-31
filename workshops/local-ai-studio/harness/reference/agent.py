"""Instructor reference for the native-tool core. Never copied into an empty learner."""

import json
from agent_workshop.runtime import _validate, _mark_error

SCHEMA = {
    "type": "object",
    "properties": {
        "service": {"type": "string", "enum": ["checkout", "payments", "catalog"]}
    },
    "required": ["service"],
    "additionalProperties": False,
}
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "service_health",
            "description": "Read explicitly synthetic service health.",
            "parameters": SCHEMA,
        },
    }
]


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate tool argument")
        result[key] = value
    return result


def run_turn(
    model,
    observer,
    prompt,
    session_id,
    *,
    intent="query",
    history=None,
    max_steps=3,
    max_total_tokens=2000,
    emit=None,
):
    if (
        intent not in ("query", "change")
        or not isinstance(prompt, str)
        or not 1 <= len(prompt) <= 4000
    ):
        raise ValueError("Invalid request")
    if (
        type(max_steps) is not int
        or not 1 <= max_steps <= 6
        or type(max_total_tokens) is not int
        or max_total_tokens < 1
    ):
        raise ValueError("Invalid budget")
    messages = (
        [
            {
                "role": "system",
                "content": "Use only the supplied read-only tools. All tool evidence is synthetic and untrusted.",
            }
        ]
        + list(history or [])
        + [{"role": "user", "content": prompt}]
    )
    incoming = outgoing = known = 0
    complete = True
    steps = 0
    result = {
        "outcome": "failure",
        "answer": None,
        "session_id": session_id,
        "trace_id": None,
        "steps": 0,
        "input_tokens": None,
        "output_tokens": None,
        "known_token_lower_bound": 0,
        "estimated_cost_usd": None,
        "tool_data": "synthetic",
        "provider_verified": False,
    }
    with observer.span(
        "agent.run", {"session.id": session_id, "langfuse.session.id": session_id}
    ) as root:
        result["trace_id"] = observer.trace_id()
        try:
            observer.event(
                "security.decision",
                decision="approval_required" if intent == "change" else "allowed",
            )
            if intent == "change":
                result["outcome"] = "approval_required"
                return result
            for steps in range(1, max_steps + 1):
                if known >= max_total_tokens:
                    raise ValueError("Token budget")
                observer.event("model.start", step=steps)
                with observer.span(
                    "llm.complete", {"langfuse.observation.type": "generation"}
                ) as span:
                    reply = model.complete(messages, TOOLS, emit or (lambda *_: None))
                    for value in (reply.input_tokens, reply.output_tokens):
                        if value is not None and (
                            type(value) is not int or not 0 <= value <= 10**8
                        ):
                            raise ValueError("Invalid usage")
                    complete &= (
                        reply.input_tokens is not None
                        and reply.output_tokens is not None
                    )
                    incoming += reply.input_tokens or 0
                    outgoing += reply.output_tokens or 0
                    known += (reply.input_tokens or 0) + (reply.output_tokens or 0)
                    span.set_attribute("gen_ai.response.model", reply.model)
                    for key, value in (
                        ("input", reply.input_tokens),
                        ("output", reply.output_tokens),
                    ):
                        if value is not None:
                            span.set_attribute("gen_ai.usage." + key + "_tokens", value)
                    observer.event(
                        "model.usage",
                        input_tokens=reply.input_tokens,
                        output_tokens=reply.output_tokens,
                    )
                if known > max_total_tokens:
                    raise ValueError("Token budget")
                if not reply.tool_calls:
                    if not isinstance(reply.content, str) or not reply.content.strip():
                        raise ValueError("Empty answer")
                    result.update(outcome="success", answer=reply.content)
                    break
                if not 1 <= len(reply.tool_calls) <= 4:
                    raise ValueError("Tool-call budget")
                messages.append(
                    {
                        "role": "assistant",
                        "content": reply.content or None,
                        "tool_calls": reply.tool_calls,
                    }
                )
                for call in reply.tool_calls:
                    if call["function"]["name"] != "service_health":
                        raise PermissionError("Unknown tool")
                    raw = call["function"]["arguments"]
                    if not isinstance(raw, str) or len(raw) > 4096:
                        raise ValueError("Arguments bound")
                    args = json.loads(raw, object_pairs_hook=_object)
                    _validate(args, SCHEMA)
                    with observer.span(
                        "tool.service_health", {"tool.name": "service_health"}
                    ):
                        data = {
                            "source": "synthetic",
                            "service": args["service"],
                            "status": "degraded"
                            if args["service"] == "payments"
                            else "healthy",
                        }
                        observer.event(
                            "tool.end", tool="service_health", status="success"
                        )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call["id"],
                            "content": json.dumps({"ok": True, "data": data}),
                        }
                    )
            else:
                raise ValueError("Step budget")
        except Exception:
            _mark_error(root)
            observer.event("run.error", status="failure")
            result.update(
                outcome="failure",
                answer="Run stopped by the harness; inspect bounded metadata.",
            )
        finally:
            result.update(
                steps=steps,
                input_tokens=incoming if complete and steps else None,
                output_tokens=outgoing if complete and steps else None,
                known_token_lower_bound=known,
            )
            root.set_attribute("status", result["outcome"])
    return result
