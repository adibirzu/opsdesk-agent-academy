"""Small LangGraph coordinator around the existing bounded agent harness.

This demo has no durable checkpointer or approval-resume endpoint. A proposed
remediation stops before inference; it never grants permission to execute it.
"""
from dataclasses import asdict
import re
from typing import TypedDict
import uuid

from langgraph.graph import END, START, StateGraph


class Investigation(TypedDict, total=False):
    prompt: str
    session_id: str
    operation: str
    decision: str
    result: dict


def build_coordinator(agent, observer):
    """Use explicit request intent, rather than model output, for authorization."""
    def authorize(state):
        if (not isinstance(state.get("prompt"), str) or not 1 <= len(state["prompt"]) <= 16000
                or not isinstance(state.get("session_id"), str)
                or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", state["session_id"])
                or state.get("operation") not in {"investigate", "remediate"}):
            raise ValueError("Invalid investigation request")
        decision = "allowed" if state["operation"] == "investigate" else "approval_required"
        with observer.span("security.authorize", {"session.id": state["session_id"],
                                                   "security.decision": decision}):
            observer.event("security.decision", decision=decision,
                           operation=state["operation"], session_id=state["session_id"])
        # Clear any caller-supplied result. Only the investigation node creates it.
        return {"decision": decision, "result": {}}

    def investigate(state):
        return {"result": asdict(agent.run(state["prompt"], state["session_id"]))}

    graph = StateGraph(Investigation)
    graph.add_node("authorize", authorize)
    graph.add_node("investigate", investigate)
    graph.add_edge(START, "authorize")
    graph.add_conditional_edges("authorize", lambda state: state["decision"],
                                {"allowed": "investigate", "approval_required": END})
    graph.add_edge("investigate", END)
    return graph.compile()


def run_coordinator(agent_factory, observer, prompt, session_id, operation):
    """Run one graph request with no automatic third-party tracing or writes."""
    from langsmith import tracing_context
    from .runtime import RunResult, _safe_error, _mark_error

    class Investigator:
        def run(self, prompt, session_id):
            try:
                agent = agent_factory()
            except Exception as exc:
                run_id = str(uuid.uuid4())
                error = "model initialization: " + _safe_error(exc)
                observer.event("run.error", run_id=run_id, status="failure", error=error)
                return RunResult("failure", None, run_id, observer.trace_id(), session_id,
                                 0, None, None, None, (error,))
            return agent.run(prompt, session_id)

    graph = build_coordinator(Investigator(), observer)
    with tracing_context(enabled=False), observer.span("coordinator.run", {
            "session.id": session_id, "langfuse.observation.type": "agent"}) as span:
        state = graph.invoke({"prompt": prompt, "session_id": session_id,
                              "operation": operation}, {"recursion_limit": 4})
        if state["decision"] == "approval_required":
            data = asdict(RunResult("approval_required", None, str(uuid.uuid4()),
                                   observer.trace_id(), session_id, 0, None, None, None))
        else:
            data = state["result"]
        span.set_attribute("status", data["outcome"])
        if data["outcome"] == "failure":
            _mark_error(span)
        observer.event("coordinator.end", status=data["outcome"], run_id=data["run_id"],
                       session_id=session_id)
        data.update(coordinator="langgraph", decision=state["decision"])
        return data
