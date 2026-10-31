"""Fixed learner contracts. Native model replies are synthetic test doubles only."""

import copy
from contextlib import contextmanager
import json
import unittest
import agent
from agent_workshop.studio_model import Completion


class Observer:
    def __init__(self):
        self.events = []

    def trace_id(self):
        return "a" * 32

    @contextmanager
    def span(self, *args):
        yield self

    def set_attribute(self, *_):
        pass

    def set_status(self, *_):
        pass

    def event(self, name, **fields):
        self.events.append((name, fields))


class Model:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def complete(self, messages, tools, emit):
        self.calls.append(copy.deepcopy(messages))
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def answer(text="Synthetic status explained", incoming=10, outgoing=5):
    return Completion(text, [], "synthetic-test-double", incoming, outgoing)


def action(
    name="service_health", arguments='{"service":"payments"}', incoming=10, outgoing=5
):
    return Completion(
        "",
        [
            {
                "id": "call-1",
                "type": "function",
                "function": {"name": name, "arguments": arguments},
            }
        ],
        "synthetic-test-double",
        incoming,
        outgoing,
    )


class LearnerContract(unittest.TestCase):
    def setUp(self):
        self.observer = Observer()

    def run_case(self, replies, **kwargs):
        model = Model(replies)
        r = agent.run_turn(
            model,
            self.observer,
            "Investigate training data",
            "learner-session",
            **kwargs,
        )
        return r, model

    def test_native_tool_roundtrip(self):
        r, m = self.run_case([action(), answer()])
        self.assertEqual(r["outcome"], "success")
        self.assertEqual(r["steps"], 2)
        self.assertEqual(m.calls[-1][-1]["role"], "tool")
        self.assertEqual(
            json.loads(m.calls[-1][-1]["content"])["data"]["source"], "synthetic"
        )

    def test_greeting_can_finish_without_a_tool(self):
        r, _ = self.run_case([answer("Hello")])
        self.assertEqual(r["answer"], "Hello")

    def test_authorization_stops_before_inference(self):
        r, m = self.run_case([], intent="change")
        self.assertEqual(r["outcome"], "approval_required")
        self.assertEqual(m.calls, [])
        self.assertEqual(r["steps"], 0)

    def test_unknown_tool_fails_closed(self):
        r, m = self.run_case([action("shell", '{"command":"whoami"}')])
        self.assertEqual(r["outcome"], "failure")
        self.assertEqual(len(m.calls), 1)

    def test_extra_arguments_fail(self):
        r, _ = self.run_case(
            [action(arguments='{"service":"payments","url":"https://example.invalid"}')]
        )
        self.assertEqual(r["outcome"], "failure")

    def test_duplicate_argument_keys_fail(self):
        r, _ = self.run_case(
            [action(arguments='{"service":"payments","service":"catalog"}')]
        )
        self.assertEqual(r["outcome"], "failure")

    def test_unknown_service_fails(self):
        r, _ = self.run_case([action(arguments='{"service":"other"}')])
        self.assertEqual(r["outcome"], "failure")

    def test_step_limit_is_enforced(self):
        r, m = self.run_case([action(), action(), answer()], max_steps=2)
        self.assertEqual(r["outcome"], "failure")
        self.assertEqual(len(m.calls), 2)

    def test_partial_usage_stays_unknown(self):
        r, _ = self.run_case([action(incoming=None), answer()])
        self.assertIsNone(r["input_tokens"])
        self.assertIsNone(r["estimated_cost_usd"])
        self.assertEqual(r["known_token_lower_bound"], 20)

    def test_known_token_lower_bound_stops_before_tool(self):
        r, m = self.run_case([action(incoming=None, outgoing=11)], max_total_tokens=10)
        self.assertEqual(r["outcome"], "failure")
        self.assertEqual(len(m.calls), 1)
        self.assertFalse(any(name == "tool.end" for name, _ in self.observer.events))

    def test_raw_provider_failure_is_not_returned(self):
        r, _ = self.run_case([RuntimeError("private-provider-error-marker")])
        self.assertEqual(r["outcome"], "failure")
        self.assertNotIn("private-provider-error-marker", str(r))

    def test_history_is_not_modified(self):
        history = [{"role": "user", "content": "Earlier turn"}]
        before = copy.deepcopy(history)
        self.run_case([answer()], history=history)
        self.assertEqual(history, before)

    def test_correlation_and_evidence_scope(self):
        r, _ = self.run_case([answer()])
        self.assertEqual(r["trace_id"], "a" * 32)
        self.assertEqual(r["session_id"], "learner-session")
        self.assertFalse(r["provider_verified"])

    def test_invalid_intent_fails_before_model(self):
        m = Model([])
        with self.assertRaises(ValueError):
            agent.run_turn(m, self.observer, "Hi", "session", intent="admin")
        self.assertEqual(m.calls, [])


if __name__ == "__main__":
    unittest.main()
