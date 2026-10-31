"""Reproduce disconnect/configuration/proxy failures without provider traffic."""

import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.cookiejar import CookieJar
from http.client import RemoteDisconnected
from urllib.request import HTTPCookieProcessor, ProxyHandler, Request, build_opener

from agent_workshop.learner_studio import LearnerStudio, load_learner
from agent_workshop.studio import Session, Settings, Studio, make_server
from agent_workshop.studio_model import StreamingModel

ROOT = Path(__file__).resolve().parents[1]


class RecoveryTests(unittest.TestCase):
    def test_sse_header_disconnect_releases_conversation_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            studio = Studio(Settings({"test": {"model_id": "test"}}), Path(tmp) / "out")
            server = make_server(studio, 0)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
            origin = "http://127.0.0.1:" + str(server.server_address[1])
            client = build_opener(HTTPCookieProcessor(CookieJar()))
            with client.open(origin + "/api/config") as response:
                response.read()
            respond = server.RequestHandlerClass.respond

            def fail_headers(handler, status, kind, token=None):
                if kind == "text/event-stream":
                    raise BrokenPipeError("synthetic disconnect")
                return respond(handler, status, kind, token)

            def request(path, body):
                return Request(
                    origin + path,
                    data=json.dumps(body).encode(),
                    headers={"Content-Type": "application/json", "Origin": origin},
                )

            with patch.object(server.RequestHandlerClass, "respond", fail_headers):
                with self.assertRaises(RemoteDisconnected):
                    client.open(
                        request(
                            "/api/chat",
                            {"message": "hi", "model": "test", "intent": "query"},
                        )
                    )
            with client.open(request("/api/new", {})) as response:
                self.assertTrue(json.load(response)["reset"])

    def test_observer_initialization_failure_finishes_both_runtime_lanes(self):
        for learner in (False, True):
            with self.subTest(learner=learner), tempfile.TemporaryDirectory() as tmp:
                settings = Settings({"test": {"model_id": "test"}}, {"enabled": True})
                if learner:
                    core = load_learner(
                        ROOT / "workshops/local-ai-studio/harness/reference/agent.py"
                    )
                    app = LearnerStudio(
                        settings,
                        Path(tmp) / "out",
                        core,
                        model_factory=lambda _: self.fail(
                            "Model must not be constructed"
                        ),
                    )
                    target = "agent_workshop.learner_studio.Observer.__init__"
                else:
                    app = Studio(
                        settings,
                        Path(tmp) / "out",
                        model_factory=lambda _: self.fail(
                            "Model must not be constructed"
                        ),
                    )
                    target = "agent_workshop.studio.Observer.__init__"
                events = []
                session = Session()
                with patch(
                    target,
                    side_effect=ValueError("synthetic-secret-that-must-not-leak"),
                ):
                    receipt = app.run(
                        session,
                        "hi",
                        "test",
                        "query",
                        lambda n, d: events.append((n, d)),
                    )
                self.assertEqual(receipt["outcome"], "failure")
                self.assertEqual(receipt["steps"], 0)
                self.assertFalse(receipt["delivery"]["flush_ok"])
                self.assertEqual(events[-1][0], "finish")
                self.assertNotIn(receipt["trace_id"], session.traces)
                self.assertEqual(session.history, [])
                self.assertEqual(len(list(app.output.glob("*/receipt.json"))), 1)
                text = (
                    json.dumps(events)
                    + next(app.output.glob("*/receipt.json")).read_text()
                )
                self.assertNotIn("synthetic-secret-that-must-not-leak", text)

    def test_enabled_telemetry_requires_key_environment_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "studio.toml"
            file.write_text(
                '[models.local]\nendpoint="http://127.0.0.1:11434/v1"\nallowed_hosts=["127.0.0.1"]\nmodel_id="test"\n[telemetry]\nenabled=true\nlangfuse_endpoint="https://example.invalid"\nallowed_hosts=["example.invalid"]\n'
            )
            file.chmod(0o600)
            with self.assertRaises(ValueError):
                Settings.load(file)

    def test_private_http_never_uses_environment_proxy(self):
        class Response:
            headers = {"Content-Type": "text/event-stream"}

            def __enter__(self):
                return self

            def __exit__(self, *_):
                pass

            def readline(self, _):
                if not getattr(self, "sent", False):
                    self.sent = True
                    return b'data: {"choices":[{"delta":{"content":"synthetic"}}]}\n\n'
                return b"data: [DONE]\n\n"

        class Opener:
            def open(self, *a, **k):
                return Response()

        with patch(
            "agent_workshop.studio_model.build_opener", return_value=Opener()
        ) as factory:
            model = StreamingModel(
                {
                    "endpoint": "http://lan-gateway.example:4000/v1",
                    "allowed_hosts": ["lan-gateway.example"],
                    "allow_private_http": True,
                    "api_key_env": "TEST_CLIENT_KEY",
                    "model_id": "test",
                }
            )
            with patch("agent_workshop.studio_model.secret", return_value="synthetic"):
                model.complete([], [], lambda *_: None)
        proxies = [h for h in factory.call_args.args if isinstance(h, ProxyHandler)]
        self.assertEqual(len(proxies), 1)
        self.assertEqual(proxies[0].proxies, {})


if __name__ == "__main__":
    unittest.main()
