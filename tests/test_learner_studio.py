"""Composed learner-core/real-chat shell tests with explicit model doubles."""

import json
from pathlib import Path
import tempfile
import types
import unittest
from agent_workshop.learner_studio import LearnerStudio, load_learner
from agent_workshop.studio import Session, Settings
from agent_workshop.studio_model import Completion

ROOT = Path(__file__).resolve().parents[1]


class Transport:
    def __init__(self):
        self.calls = 0

    def complete(self, messages, tools, emit):
        self.calls += 1
        if self.calls == 1:
            return Completion(
                "",
                [
                    {
                        "id": "test-call",
                        "type": "function",
                        "function": {
                            "name": "service_health",
                            "arguments": '{"service":"payments"}',
                        },
                    }
                ],
                "synthetic-transport-test-double",
                10,
                5,
            )
        emit("token", {"text": "Synthetic test answer"})
        return Completion(
            "Synthetic test answer", [], "synthetic-transport-test-double", 10, 5
        )


class LearnerCompositionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.model = Transport()
        self.created = 0

        def factory(_):
            self.created += 1
            return self.model

        self.learner = load_learner(
            ROOT / "workshops/local-ai-studio/harness/reference/agent.py"
        )
        self.studio = LearnerStudio(
            Settings({"test": {"model_id": "test"}}),
            Path(self.tmp.name) / "out",
            self.learner,
            model_factory=factory,
        )
        self.session = Session()
        self.messages = []

    def emit(self, event, data):
        self.messages.append((event, data))

    def test_ui_shell_executes_the_selected_learner_core(self):
        receipt = self.studio.run(
            self.session, "Inspect status", "test", "query", self.emit
        )
        self.assertEqual(receipt["outcome"], "success")
        self.assertEqual(self.model.calls, 2)
        self.assertEqual(receipt["implementation"], "explicit_learner_core")
        self.assertEqual(self.studio.available_tools, ["service_health"])
        self.assertTrue(
            any(
                name == "token" and row["text"] == "Synthetic test answer"
                for name, row in self.messages
            )
        )
        self.assertEqual(self.session.history[-1]["content"], "Synthetic test answer")
        text = "".join(p.read_text() for p in self.studio.output.rglob("*.json*"))
        self.assertNotIn("Synthetic test answer", text)

    def test_policy_stops_before_constructing_the_model(self):
        receipt = self.studio.run(self.session, "Restart", "test", "change", self.emit)
        self.assertEqual(receipt["outcome"], "approval_required")
        self.assertEqual(self.created, 0)

    def test_invalid_learner_result_becomes_a_failed_private_receipt(self):
        self.studio.learner = types.SimpleNamespace(run_turn=lambda *a, **k: {})
        receipt = self.studio.run(self.session, "Hi", "test", "query", self.emit)
        self.assertEqual(receipt["outcome"], "failure")
        self.assertFalse(receipt["provider_verified"])
        self.assertFalse(receipt["observed_trace"])
        self.assertNotIn(receipt["trace_id"], self.session.traces)
        starts = [row for name, row in self.messages if name == "start"]
        self.assertEqual(starts[0]["trace_id"], receipt["trace_id"])
        self.assertEqual(starts[0]["trace_origin"], "local_failure_identifier_no_span")
        self.assertTrue(list(self.studio.output.glob("*/receipt.json")))

    def test_observer_trace_matches_the_receipt_and_session(self):
        receipt = self.studio.run(self.session, "Status", "test", "query", self.emit)
        rows = [
            json.loads(line)
            for line in next(self.studio.output.glob("*/events.jsonl"))
            .read_text()
            .splitlines()
        ]
        self.assertTrue(
            any(
                row["trace_id"] == receipt["trace_id"]
                and row["session.id"] == self.session.id
                for row in rows
            )
        )


if __name__ == "__main__":
    unittest.main()
