import unittest
import json
from io import StringIO
from agent_workshop.models import PricedModel
from agent_workshop.runtime import Agent, ModelReply, Tool
from agent_workshop.observability import Observer
from agent_workshop.costs import estimate_cost, validate_pricing


class CostTests(unittest.TestCase):
    def test_multistep_cost_totals_and_partial_usage_remains_unknown(self):
        for unknown in (False, True):
            class Model:
                def __init__(self): self.step = 0
                def complete(self, messages):
                    self.step += 1
                    return ModelReply('{"tool":"status","arguments":{}}' if self.step == 1 else '{"answer":"fixture"}',
                        "fixture-model", None if unknown and self.step == 1 else self.step*100, self.step*10)
            stream = StringIO();observer = Observer(stream=stream)
            tool = Tool("status", "fixture", {"type": "object", "properties": {}, "additionalProperties": False}, lambda: {"source": "synthetic"})
            result = Agent(PricedModel(Model(), self.rates()), [tool], observer).run("fixture", "costs")
            self.assertEqual(result.outcome, "success")
            self.assertEqual(result.estimated_cost_usd, None if unknown else .00078)
            usage = [json.loads(line) for line in stream.getvalue().splitlines() if json.loads(line)["event"] == "llm.usage"]
            self.assertEqual(len(usage), 2)
            self.assertEqual(usage[0]["cost_basis"], "unavailable" if unknown else "configured_uncached_text_rates")
    def rates(self):
        return {"model_id": "fixture-model", "currency": "USD", "input_usd_per_million": 2,
                "output_usd_per_million": 6, "source": "https://pricing.example/rates", "as_of": "2026-10-29"}

    def test_estimate_is_explicit_and_preserves_unknown_usage(self):
        result = estimate_cost(self.rates(), "fixture-model", 1000, 500)
        self.assertAlmostEqual(result["total"], .005)
        self.assertEqual(result["basis"], "configured_uncached_text_rates")
        self.assertFalse(result["provider_billed"])
        self.assertIsNone(estimate_cost(self.rates(), "fixture-model", None, 10))
        self.assertIsNone(estimate_cost(self.rates(), "different-model", 100, 10))

    def test_invalid_rate_and_usage_do_not_become_free_cost(self):
        for value in (-1, float("nan"), float("inf"), True, "oops"):
            with self.assertRaises(ValueError): validate_pricing({**self.rates(), "input_usd_per_million": value}, "fixture-model")
        for value in (-1, True, 1.5):
            with self.assertRaises(ValueError): estimate_cost(self.rates(), "fixture-model", value, 10)
        with self.assertRaises(ValueError): validate_pricing({**self.rates(), "source": "http://pricing.example"}, "fixture-model")
        with self.assertRaises(ValueError): validate_pricing({**self.rates(), "as_of": "yesterday"}, "fixture-model")


if __name__ == "__main__": unittest.main()
