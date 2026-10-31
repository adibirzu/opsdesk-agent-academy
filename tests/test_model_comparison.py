import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from agent_workshop.config import Config

spec = importlib.util.spec_from_file_location("compare_models", Path(__file__).resolve().parents[1]/"scripts/compare_models.py")
module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class ComparisonTests(unittest.TestCase):
    def test_fixture_has_no_live_model_or_invented_cost(self):
        with TemporaryDirectory() as tmp, patch("agent_workshop.cli.live_model", side_effect=AssertionError("no live call")):
            result = module.compare([("a", Config()), ("b", Config())], Path(tmp).resolve()/"result", "test", scripted=True)
            self.assertTrue(result["all_runs_succeeded"])
            self.assertFalse(result["multiple_live_models"])
            self.assertIsNone(result["estimated_total_usd"])

    def test_invalid_or_content_capturing_configuration_rejected_before_execute(self):
        with TemporaryDirectory() as tmp, patch.object(module, "execute") as execute:
            with self.assertRaises(ValueError): module.compare([("a", Config())], Path(tmp)/"result", "test")
            with self.assertRaises(ValueError): module.compare([("a", Config(telemetry={"capture_content": True})), ("b", Config())], Path(tmp)/"result", "test")
            execute.assert_not_called()
