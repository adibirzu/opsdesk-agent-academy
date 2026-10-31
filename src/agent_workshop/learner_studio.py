"""Compose an explicitly reviewed learner core with the real chat/transport shell."""

import importlib.util
import json
import os
from pathlib import Path
import re
import time
import uuid
from .observability import Observer
from .studio import Studio


def load_learner(path):
    file = Path(path)
    if file.is_symlink() or not file.is_file() or file.suffix != ".py":
        raise ValueError("Select a reviewed regular learner Python file")
    spec = importlib.util.spec_from_file_location("workshop_learner_core", file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "run_turn", None)):
        raise ValueError("Learner must implement run_turn")
    tools = getattr(module, "TOOLS", None)
    if not isinstance(tools, list) or not 1 <= len(tools) <= 8:
        raise ValueError("Learner must expose1..8native TOOLS")
    names = [t["function"]["name"] for t in tools]
    if len(set(names)) != len(names) or any(
        not re.fullmatch(r"[A-Za-z0-9_]{1,64}", n) for n in names
    ):
        raise ValueError("Invalid learner tool names")
    return module


class LearnerStudio(Studio):
    def __init__(self, settings, output, learner, **kwargs):
        super().__init__(settings, output, **kwargs)
        self.learner = learner
        self.available_tools = [t["function"]["name"] for t in learner.TOOLS]

    def run(self, session, message, model_name, intent, emit):
        if (
            not isinstance(message, str)
            or not 1 <= len(message) <= 4000
            or model_name not in self.settings.models
            or intent not in ("query", "change")
        ):
            raise ValueError("Invalid learner chat request")
        start = time.monotonic()
        run_id = uuid.uuid4().hex
        folder = self.output / run_id
        folder.mkdir(mode=0o700)
        events = []
        started = False
        observed_trace = ""
        disconnected = False
        owner = self

        def send(name, data):
            nonlocal disconnected
            if disconnected:
                return
            try:
                emit(name, data)
            except (BrokenPipeError, ConnectionResetError):
                disconnected = True
                raise

        class Events(Observer):
            def event(self, name, **fields):
                nonlocal started, observed_trace
                super().event(name, **fields)
                if not started and self.trace_id():
                    started = True
                    observed_trace = self.trace_id()
                    send(
                        "start",
                        {
                            "trace_id": self.trace_id(),
                            "run_id": run_id,
                            "session_id": session.id,
                            "model": model_name,
                        },
                    )
                row = {
                    "event": name,
                    "elapsed_ms": round((time.monotonic() - start) * 1000),
                    **{
                        k: v
                        for k, v in fields.items()
                        if k
                        in (
                            "step",
                            "tool",
                            "status",
                            "decision",
                            "input_tokens",
                            "output_tokens",
                        )
                    },
                }
                events.append(row)
                send("stage", row)

        class LazyModel:
            instance = None
            calls = 0

            def complete(self, messages, tools, callback):
                if self.calls >= owner.settings.max_steps:
                    raise ValueError("Model call limit reached")
                self.calls += 1
                if self.instance is None:
                    self.instance = owner.model_factory(
                        owner.settings.models[model_name]
                    )
                return self.instance.complete(messages, tools, callback)

        try:
            observer = Events(self.settings.telemetry, folder / "events.jsonl")
        except Exception:
            return self.setup_failure(session, model_name, run_id, folder, send)
        result = None
        model = LazyModel()
        try:
            result = self.learner.run_turn(
                model,
                observer,
                message,
                session.id,
                intent=intent,
                history=[dict(row) for row in session.history],
                max_steps=self.settings.max_steps,
                max_total_tokens=self.settings.max_tokens,
                emit=send,
            )
            if (
                not isinstance(result, dict)
                or result.get("outcome")
                not in (
                    "success",
                    "failure",
                    "approval_required",
                    "completed_with_tool_error",
                )
                or not isinstance(result.get("trace_id"), str)
                or not re.fullmatch(r"[a-f0-9]{32}", result["trace_id"])
                or result["trace_id"] != observed_trace
                or type(result.get("steps")) is not int
                or result["steps"] != model.calls
            ):
                raise ValueError("Learner result contract failed")
            if result["outcome"] == "success":
                session.history.extend(
                    [
                        {"role": "user", "content": message},
                        {"role": "assistant", "content": result.get("answer") or ""},
                    ]
                )
                session.history = session.history[-12:]
            elif result["outcome"] == "approval_required":
                send(
                    "token",
                    {
                        "text": "The learner harness stopped this change before model invocation."
                    },
                )
            elif result["outcome"] == "failure":
                send(
                    "error",
                    {
                        "message": "The learner harness stopped this turn. Inspect its private events and contracts."
                    },
                )
        except Exception:
            result = {
                "outcome": "failure",
                "trace_id": observed_trace or uuid.uuid4().hex,
                "steps": model.calls,
                "input_tokens": None,
                "output_tokens": None,
                "known_token_lower_bound": 0,
                "estimated_cost_usd": None,
            }
            send(
                "error",
                {
                    "message": "The learner core failed its runtime contract. No automatic retry was made."
                },
            )
        finally:
            delivery = observer.close()
        if not started:
            send(
                "start",
                {
                    "trace_id": result["trace_id"],
                    "run_id": run_id,
                    "session_id": session.id,
                    "model": model_name,
                    "trace_origin": "local_failure_identifier_no_span",
                },
            )
        receipt = {
            key: result.get(key)
            for key in (
                "outcome",
                "trace_id",
                "steps",
                "input_tokens",
                "output_tokens",
                "known_token_lower_bound",
                "estimated_cost_usd",
            )
        }
        receipt.update(
            run_id=run_id,
            session_id=session.id,
            model=model_name,
            events=events,
            latency_ms=round((time.monotonic() - start) * 1000),
            cost_basis="learner_core_no_invoice_claim",
            tool_data="synthetic",
            inference_mode="live" if result.get("steps") else "not_invoked",
            provider_verified=False,
            delivery=delivery,
            implementation="explicit_learner_core",
            observed_trace=bool(observed_trace),
        )
        fd = os.open(
            folder / "receipt.json", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
        )
        with os.fdopen(fd, "w") as f:
            json.dump(receipt, f, indent=2)
        if observed_trace:
            session.traces[receipt["trace_id"]] = {
                "policy_stop": result["outcome"] == "approval_required",
                "steps": result["steps"],
            }
        while len(session.traces) > 20:
            session.traces.pop(next(iter(session.traces)))
        send("finish", receipt)
        return receipt
