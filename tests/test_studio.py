"""Synthetic contracts only. These do not establish real model or Langfuse acceptance."""

import copy
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request, build_opener, HTTPCookieProcessor
from urllib.error import HTTPError
from http.cookiejar import CookieJar
from unittest.mock import patch
from agent_workshop.studio import Studio, Settings, Session, tool, make_server
from agent_workshop.studio_model import Completion, StreamingModel


class StubModel:
    def __init__(self, replies):
        self.replies = list(replies)
        self.messages = []

    def complete(self, messages, tools, emit):
        self.messages.append(copy.deepcopy(messages))
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        if r.content:
            emit("token", {"text": r.content})
        return r


def reply(content="Synthetic evidence summary", calls=None, incoming=20, outgoing=10):
    return Completion(content, calls or [], "test-model", incoming, outgoing)


def call(name, args):
    return {
        "id": "tool-1",
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(args)},
    }


class StudioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.model = StubModel([reply()])
        self.created = 0

        def factory(_):
            self.created += 1
            return self.model

        self.config = Settings(
            {
                "test": {
                    "model_id": "test-model",
                    "input_usd_per_million": 1.0,
                    "output_usd_per_million": 2.0,
                }
            }
        )
        self.studio = Studio(self.config, Path(self.tmp.name) / "evidence", factory)
        self.session = Session()
        self.events = []

    def run_chat(self, message="Compare the synthetic service status.", intent="query"):
        return self.studio.run(
            self.session,
            message,
            "test",
            intent,
            lambda event, data: self.events.append((event, data)),
        )

    def test_real_contract_multistep_tool_tokens_and_cost(self):
        self.model.replies = [
            reply("", [call("service_health", {"service": "payments"})]),
            reply(),
        ]
        r = self.run_chat()
        self.assertEqual(r["outcome"], "success")
        self.assertEqual(r["steps"], 2)
        self.assertEqual(r["input_tokens"], 40)
        self.assertAlmostEqual(r["estimated_cost_usd"], 0.00008)
        self.assertTrue(any(e["event"] == "tool.end" for e in r["events"]))
        self.assertFalse(r["provider_verified"])

    def test_policy_stops_before_model_construction(self):
        r = self.run_chat(intent="change")
        self.assertEqual(r["outcome"], "approval_required")
        self.assertEqual(self.created, 0)
        self.assertEqual(r["steps"], 0)

    def test_unknown_tool_denied_and_error_correlated(self):
        self.model.replies = [reply("", [call("shell", {"command": "cat ~/.env"})])]
        r = self.run_chat()
        self.assertEqual(r["outcome"], "failure")
        rows = [
            json.loads(l)
            for l in next(self.studio.output.glob("*/events.jsonl"))
            .read_text()
            .splitlines()
        ]
        self.assertTrue(
            any(
                x["event"] == "run.error" and x["trace_id"] == r["trace_id"]
                for x in rows
            )
        )

    def test_partial_usage_never_becomes_zero_or_complete(self):
        self.model.replies = [
            reply("", [call("service_health", {"service": "payments"})], None, 10),
            reply(),
        ]
        r = self.run_chat()
        self.assertIsNone(r["input_tokens"])
        self.assertIsNone(r["estimated_cost_usd"])
        self.assertEqual(r["known_token_lower_bound"], 40)

    def test_lower_bound_budget_stops_before_tool(self):
        self.config.max_tokens = 5
        self.model.replies = [
            reply("", [call("service_health", {"service": "payments"})], None, 10)
        ]
        r = self.run_chat()
        self.assertEqual(r["outcome"], "failure")
        self.assertFalse(any(e["event"] == "tool.start" for e in r["events"]))

    def test_failure_source_is_visible(self):
        self.model.replies = [
            reply("", [call("simulate_tool_failure", {})]),
            reply("The synthetic source failed; no health evidence is available."),
        ]
        r = self.run_chat()
        self.assertEqual(r["outcome"], "completed_with_tool_error")
        self.assertEqual(r["tool_errors"], 1)
        self.assertTrue(any(e["event"] == "tool.error" for e in r["events"]))

    def test_prompts_and_answers_absent_from_metadata(self):
        self.run_chat("secret-prompt-marker")
        text = "".join(p.read_text() for p in self.studio.output.rglob("*.json*"))
        self.assertNotIn("secret-prompt-marker", text)
        self.assertNotIn("Synthetic evidence summary", text)

    def test_browser_disconnect_preserves_a_failed_receipt(self):
        def disconnect(event, data):
            if event == "token":
                raise BrokenPipeError()

        result = self.studio.run(self.session, "hello", "test", "query", disconnect)
        self.assertEqual(result["outcome"], "failure")
        self.assertEqual(len(self.model.messages), 1)
        self.assertTrue(list(self.studio.output.glob("*/receipt.json")))
        self.assertEqual(self.session.history, [])

    def test_history_isolated_between_sessions(self):
        self.run_chat("first-session-marker")
        self.model.replies = [reply()]
        self.session = Session()
        self.run_chat("second-session")
        self.assertNotIn("first-session-marker", str(self.model.messages[-1]))

    def test_synthetic_injection_is_returned_as_untrusted_data(self):
        data = tool("search_runbook", {"query": "prompt injection"})
        self.assertEqual(data["trust"], "untrusted_tool_data")
        self.assertIn("export_credentials", data["text"])
        with self.assertRaises(PermissionError):
            tool("export_credentials", {})

    def test_duplicate_tool_arguments_stop_before_handler_execution(self):
        self.model.replies = [
            reply(
                "",
                [
                    {
                        "id": "test-call",
                        "type": "function",
                        "function": {
                            "name": "service_health",
                            "arguments": '{"service":"payments","service":"catalog"}',
                        },
                    }
                ],
            )
        ]
        result = self.run_chat()
        self.assertFalse(any(row["event"] == "tool.start" for row in result["events"]))

    def test_extra_tool_arguments_rejected(self):
        self.model.replies = [
            reply(
                "",
                [
                    call(
                        "service_health",
                        {"service": "payments", "url": "https://example.invalid"},
                    )
                ],
            )
        ]
        self.assertEqual(self.run_chat()["outcome"], "failure")

    def test_http_boundaries_cookie_reset_and_no_model_before_send(self):
        server = make_server(self.studio, 0)
        self.addCleanup(server.server_close)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        origin = "http://127.0.0.1:" + str(server.server_address[1])
        jar = CookieJar()
        client = build_opener(HTTPCookieProcessor(jar))
        with client.open(origin + "/api/config") as r:
            self.assertNotIn("api_key", r.read().decode())
        before = [x.value for x in jar]
        self.assertEqual(self.created, 0)
        bad = Request(
            origin + "/api/chat",
            data=b"{}",
            headers={
                "Content-Type": "application/json",
                "Origin": "https://evil.invalid",
            },
        )
        with self.assertRaises(HTTPError):
            client.open(bad)
        reset = Request(
            origin + "/api/new",
            data=b"{}",
            headers={"Content-Type": "application/json", "Origin": origin},
        )
        with client.open(reset) as r:
            self.assertTrue(json.load(r)["reset"])
        self.assertNotEqual(before, [x.value for x in jar])

    def test_network_endpoints_not_selected_by_browser_or_prompt(self):
        with self.assertRaises(ValueError):
            StreamingModel(
                {
                    "endpoint": "http://remote.example/v1",
                    "allowed_hosts": ["remote.example"],
                    "model_id": "x",
                    "api_key_env": "ANY_KEY",
                }
            )


class VerificationTests(unittest.TestCase):
    def test_mismatched_session_is_not_backend_acceptance(self):
        from agent_workshop.studio_langfuse import verify_trace

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                pass

            def read(self, _):
                return json.dumps(
                    {
                        "id": "a" * 32,
                        "sessionId": "other",
                        "observations": [{"traceId": "a" * 32, "type": "GENERATION"}],
                    }
                ).encode()

        class Opener:
            def open(self, *_, **__):
                return Response()

        telemetry = {
            "enabled": True,
            "langfuse_endpoint": "https://example.invalid",
            "allowed_hosts": ["example.invalid"],
            "langfuse_public_key_env": "TEST_LF_PUBLIC",
            "langfuse_secret_key_env": "TEST_LF_SECRET",
        }
        with (
            patch.dict(
                "os.environ",
                {"TEST_LF_PUBLIC": "synthetic", "TEST_LF_SECRET": "synthetic"},
            ),
            patch("agent_workshop.studio_langfuse.build_opener", return_value=Opener()),
        ):
            self.assertFalse(
                verify_trace(telemetry, "a" * 32, "expected", False)["backend_verified"]
            )

    def test_disabled_export_requires_no_credentials(self):
        from agent_workshop.studio_langfuse import verify_trace

        self.assertEqual(
            verify_trace({}, "a" * 32, "test", False)["status"], "unconfigured"
        )

    def test_readback_rejects_trace_owned_by_another_cookie(self):
        with tempfile.TemporaryDirectory() as tmp:
            studio = Studio(
                Settings({"test": {"model_id": "test-model"}}),
                Path(tmp) / "out",
                lambda _: StubModel([reply()]),
            )
            server = make_server(studio, 0)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                origin = "http://127.0.0.1:" + str(server.server_address[1])
                client = build_opener(HTTPCookieProcessor(CookieJar()))
                with client.open(origin + "/api/config") as response:
                    response.read()
                request = Request(
                    origin + "/api/chat",
                    data=json.dumps(
                        {"message": "hello", "model": "test", "intent": "query"}
                    ).encode(),
                    headers={"Origin": origin, "Content-Type": "application/json"},
                )
                with client.open(request) as response:
                    body = response.read().decode()
                trace = next(
                    json.loads(line[6:])["trace_id"]
                    for line in body.splitlines()
                    if line.startswith("data: ") and '"trace_id"' in line
                )
                verify = Request(
                    origin + "/api/verify",
                    data=json.dumps({"trace_id": trace}).encode(),
                    headers={"Origin": origin, "Content-Type": "application/json"},
                )
                other = build_opener(HTTPCookieProcessor(CookieJar()))
                with self.assertRaises(HTTPError):
                    other.open(verify)
                with client.open(verify) as response:
                    self.assertEqual(json.load(response)["status"], "unconfigured")
            finally:
                server.shutdown()
                server.server_close()


class StreamTests(unittest.TestCase):
    def test_tool_fragments_and_usage_join(self):
        rows = [
            {
                "choices": [
                    {
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "t1",
                                    "function": {
                                        "name": "service_",
                                        "arguments": '{"service":',
                                    },
                                }
                            ]
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "function": {
                                        "name": "health",
                                        "arguments": '"payments"}',
                                    },
                                }
                            ]
                        }
                    }
                ]
            },
            {"usage": {"prompt_tokens": 9, "completion_tokens": 4}, "choices": []},
        ]

        class Response:
            def readline(self, size):
                if not hasattr(self, "body"):
                    self.body = io.BytesIO(b"".join(iter(self)))
                return self.body.readline(size)

            headers = {"Content-Type": "text/event-stream"}

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def __iter__(self):
                return iter(
                    [("data: " + json.dumps(r) + "\n\n").encode() for r in rows]
                    + [b"data: [DONE]\n\n"]
                )

        class Opener:
            def open(self, *_, **__):
                return Response()

        with patch("agent_workshop.studio_model.build_opener", return_value=Opener()):
            r = StreamingModel(
                {
                    "endpoint": "http://127.0.0.1:11434/v1",
                    "allowed_hosts": ["127.0.0.1"],
                    "model_id": "test",
                }
            ).complete([], [], lambda *_: None)
        self.assertEqual(r.tool_calls[0]["function"]["name"], "service_health")
        self.assertEqual(r.input_tokens, 9)


if __name__ == "__main__":
    unittest.main()
