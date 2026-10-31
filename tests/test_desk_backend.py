"""Real loopback JSON action tests; model doubles are explicit, not live proof."""

from http.cookiejar import CookieJar
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPCookieProcessor, ProxyHandler
from agent_workshop.studio import Settings, Studio, make_server
from agent_workshop.studio_model import Completion


class DeskBackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.calls = 0
        self.last_messages = []
        owner = self

        class ModelDouble:
            def complete(self, messages, tools, emit):
                owner.calls += 1
                owner.last_messages = messages
                emit("token", {"text": "Synthetic test model answer"})
                return Completion(
                    "Synthetic test model answer", [], "test-double", 10, 5
                )

        self.app = Studio(
            Settings({"server-choice": {"model_id": "test-double"}}),
            Path(self.tmp.name) / "out",
            lambda _: ModelDouble(),
        )
        self.server = make_server(self.app, 0)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.origin = "http://127.0.0.1:" + str(self.server.server_address[1])
        self.client = self.client_for_session()

    def client_for_session(self):
        return build_opener(ProxyHandler({}), HTTPCookieProcessor(CookieJar()))

    def get(self, path, client=None):
        with (client or self.client).open(self.origin + path) as r:
            return json.load(r)

    def post(self, path, body, client=None, origin=None):
        req = Request(
            self.origin + path,
            data=json.dumps(body).encode(),
            headers={
                "Content-Type": "application/json",
                "Origin": origin or self.origin,
            },
        )
        with (client or self.client).open(req) as r:
            return json.load(r)

    def create(self):
        return self.post(
            "/api/tickets",
            {
                "title": "Synthetic personal ticket",
                "description": "Unique synthetic body not for telemetry",
                "service": "payments",
                "severity": "high",
            },
        )["ticket"]

    def test_ticket_creation_survives_same_session_reload_without_inference(self):
        rows = self.get("/api/tickets")["tickets"]
        self.assertEqual(len(rows), 3)
        ticket = self.create()
        listed = self.get("/api/tickets")["tickets"]
        self.assertEqual(len(listed), 4)
        self.assertIn(ticket, listed)
        self.assertEqual(self.calls, 0)
        self.assertEqual(list(self.app.output.iterdir()), [])

    def test_json_action_uses_server_ticket_and_model_and_writes_content_free_receipt(
        self,
    ):
        self.get("/api/tickets")
        ticket = self.create()
        result = self.post(
            "/api/analyze-ticket", {"ticket_id": ticket["id"], "intent": "query"}
        )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["answer"], "Synthetic test model answer")
        self.assertEqual(self.calls, 1)
        self.assertEqual(result["model"], "server-choice")
        self.assertFalse(result["backend_verified"])
        self.assertIn(ticket["description"], self.last_messages[-1]["content"])
        self.assertEqual(result["receipt"]["session_id"], result["session_id"])
        private = "".join(p.read_text() for p in self.app.output.rglob("*.json*"))
        self.assertNotIn(ticket["description"], private)
        self.assertNotIn(result["answer"], private)

    def test_change_intent_stops_before_model_factory(self):
        self.app.model_factory = lambda _: self.fail("Policy constructed a model")
        result = self.post(
            "/api/analyze-ticket", {"ticket_id": "TRAIN-101", "intent": "change"}
        )
        self.assertEqual(result["outcome"], "approval_required")
        self.assertEqual(result["receipt"]["steps"], 0)
        self.assertEqual(self.calls, 0)

    def test_created_ticket_and_trace_are_session_owned(self):
        ticket = self.create()
        other = self.client_for_session()
        self.assertEqual(len(self.get("/api/tickets", other)["tickets"]), 3)
        with self.assertRaises(HTTPError) as error:
            self.post(
                "/api/analyze-ticket",
                {"ticket_id": ticket["id"], "intent": "query"},
                other,
            )
        self.assertEqual(error.exception.code, 404)
        self.assertEqual(self.calls, 0)
        result = self.post(
            "/api/analyze-ticket", {"ticket_id": ticket["id"], "intent": "change"}
        )
        with self.assertRaises(HTTPError):
            self.post("/api/verify", {"trace_id": result["trace_id"]}, other)

    def test_browser_cannot_supply_endpoint_model_or_added_ticket_fields(self):
        for field in ("model", "endpoint", "session_id", "tenant"):
            with self.subTest(field=field), self.assertRaises(HTTPError):
                self.post(
                    "/api/analyze-ticket",
                    {"ticket_id": "TRAIN-101", "intent": "query", field: "untrusted"},
                )
        with self.assertRaises(HTTPError):
            self.post(
                "/api/tickets",
                {
                    "id": "chosen",
                    "title": "x",
                    "description": "x",
                    "service": "payments",
                    "severity": "high",
                },
            )
        with self.assertRaises(HTTPError):
            self.post(
                "/api/tickets",
                {
                    "title": "x" * 121,
                    "description": "x",
                    "service": "payments",
                    "severity": "high",
                },
            )
        with self.assertRaises(HTTPError):
            self.post(
                "/api/analyze-ticket",
                {"ticket_id": "TRAIN-101", "intent": "query"},
                origin="https://evil.invalid",
            )
        self.assertEqual(self.calls, 0)

    def test_active_run_rejects_second_ticket_action(self):
        self.get("/api/tickets")
        entered = threading.Event()
        release = threading.Event()

        def blocked(*_):
            entered.set()
            release.wait(3)
            raise RuntimeError("synthetic model failure")

        class Blocked:
            complete = blocked

        self.app.model_factory = lambda _: Blocked()
        failures = []

        def run():
            try:
                self.post(
                    "/api/analyze-ticket", {"ticket_id": "TRAIN-101", "intent": "query"}
                )
            except Exception as e:
                failures.append(type(e).__name__)

        thread = threading.Thread(target=run)
        thread.start()
        try:
            self.assertTrue(entered.wait(2))
            with self.assertRaises(HTTPError) as error:
                self.post(
                    "/api/analyze-ticket",
                    {"ticket_id": "TRAIN-102", "intent": "change"},
                )
            self.assertEqual(error.exception.code, 429)
        finally:
            release.set()
            thread.join(4)
        self.assertFalse(thread.is_alive())
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
