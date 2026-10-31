import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zipfile
from contextlib import redirect_stderr
import io

from agent_workshop.config import Config
from agent_workshop.cloud_demo import run_check


class CloudReleaseTests(unittest.TestCase):
    def test_empty_readback_argument_never_runs_or_exports(self):
        from agent_workshop.cloud_app import main
        for receipt in ("", " "):
            for extra in ([], ["--agent", "--export"], ["--serve"]):
                with patch("agent_workshop.cloud_app.load") as load, patch("agent_workshop.cloud_app.run_check") as run, \
                        patch("agent_workshop.cloud_app.live_model") as model, redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as exc:
                        main(["--config", "fixture.toml", "--output", "unused", "--readback-only", receipt, *extra])
                    self.assertEqual(exc.exception.code, 2)
                    load.assert_not_called();run.assert_not_called();model.assert_not_called()

    def test_fresh_source_archive_runs_without_examples_or_network(self):
        from scripts.package_app import package
        root = Path(__file__).resolve().parents[1]
        with TemporaryDirectory() as tmp:
            path = Path(tmp).resolve()
            package(root, path / "release.zip")
            with zipfile.ZipFile(path / "release.zip") as archive:
                self.assertIn("src/agent_workshop/cloud_app.py", archive.namelist())
                archive.extractall(path / "release")
            result = subprocess.run([sys.executable, "-m", "agent_workshop.cloud_app", "--scripted",
                                     "--output", str(path / "evidence")], cwd=path / "release",
                env={"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(path / "release/src")},
                capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["observation"]["source"], "synthetic")

    def test_readback_only_preserves_original_without_inference_or_upload(self):
        from agent_workshop.cloud_demo import verify_saved_run
        config = Config(telemetry={"enabled": True})
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            run_check(config, root / "run", "demo", "compute", scripted=True)
            path = root / "run/result.json"
            data = json.loads(path.read_text())
            data.update(tool_data="oci_sdk", inference_mode="live", exported=True)
            data["observation"]["source"] = "oci_sdk"
            path.write_text(json.dumps(data))
            original = path.read_bytes()
            with patch("agent_workshop.backends.verify", return_value={"backend_verified": True}) as verify, \
                    patch("agent_workshop.backends.verify_metrics", return_value={"status": "verified"}), \
                    patch("agent_workshop.models.live_model", side_effect=AssertionError("inference forbidden")), \
                    patch("agent_workshop.backends.publish_events", side_effect=AssertionError("upload forbidden")):
                result = verify_saved_run(config, path, root / "readback")
            self.assertTrue(result["backend_verified"])
            self.assertEqual(result["mode"], "readback_only")
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(verify.call_args.args[1:3], (data["trace_id"], "demo"))

    def test_readback_rejects_changed_binding_fixture_and_public_receipt(self):
        from agent_workshop.cloud_demo import verify_saved_run
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            run_check(Config(), root / "run", "demo", "compute", scripted=True)
            source = root / "run/result.json"
            with patch("agent_workshop.backends.verify", side_effect=AssertionError("no provider access")):
                with self.assertRaises(ValueError): verify_saved_run(Config(), source, root / "fixture")
                data = json.loads(source.read_text());data.update(tool_data="oci_sdk", inference_mode="live", exported=True)
                data["observation"]["source"] = "oci_sdk";source.write_text(json.dumps(data))
                with self.assertRaises(ValueError): verify_saved_run(Config(oci={"region": "different"}), source, root / "binding")
                source.chmod(0o644)
                with self.assertRaises(ValueError): verify_saved_run(Config(), source, root / "public")
                source.chmod(0o600);data["outcome"] = {"untrusted": "content"};source.write_text(json.dumps(data))
                with self.assertRaises(ValueError): verify_saved_run(Config(), source, root / "bad-outcome")

    def test_readback_receipt_shapes_are_rejected_before_queries(self):
        from agent_workshop.cloud_demo import verify_saved_run
        with TemporaryDirectory() as tmp, patch("agent_workshop.backends.verify") as verify:
            root = Path(tmp).resolve()
            run_check(Config(), root / "run", "demo", "compute", scripted=True)
            source = root / "run/result.json";base = json.loads(source.read_text())
            base.update(tool_data="oci_sdk", inference_mode="live", exported=True)
            for changes in ({"trace_id": "0"*32}, {"session_id": "not a safe label"}, {"configuration_sha256": None}):
                source.write_text(json.dumps({**base, **changes}))
                with self.assertRaises(ValueError): verify_saved_run(Config(), source, root / "rejected")
            source.write_text(json.dumps(base));link = root / "symlink";link.symlink_to(source)
            with self.assertRaises(ValueError): verify_saved_run(Config(), link, root / "symlink-result")
            source.write_bytes(b" "*64001)
            with self.assertRaises(ValueError): verify_saved_run(Config(), source, root / "large")
            verify.assert_not_called()


if __name__ == "__main__": unittest.main()
