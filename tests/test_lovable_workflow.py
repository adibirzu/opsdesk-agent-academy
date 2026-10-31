"""The actual builder route must be complete without exposing operator bindings."""

import json
from pathlib import Path
import unittest

COURSE = Path(__file__).resolve().parents[1] / "workshops/app-first"


class LovableWorkflowTests(unittest.TestCase):
    def test_all_build_prompts_and_native_controls_are_in_one_route(self):
        page = (COURSE / "lovable.html").read_text()
        self.assertEqual(page.count('class="training-task"'), 10)
        for name in ("01-build-app.md", "07-lovable-native.md", "06-langfuse-simple.md"):
            self.assertIn(name, page)
            self.assertIn((COURSE / "prompts" / name).read_text().strip(), (COURSE / "LOVABLE-WORKFLOW.md").read_text())
        for text in ("two sign-ins", "sign-in", "944 tokens", "zero model calls", "server Secrets", "independent", "50,000"):
            self.assertIn(text.lower(), page.lower())
        self.assertNotIn("{{", page)
        for text in ("Your shortest route", "WHERE ·", "git clone https://github.com/adibirzu/opsdesk-agent-academy.git", "data-copy-label", "bun run test"):
            self.assertIn(text, page)

    def test_selected_capture_and_provider_acceptance_have_explicit_boundaries(self):
        page = (COURSE / "lovable.html").read_text()
        self.assertIn("independently found in Langfuse", page)
        manifest = json.loads((COURSE / "EVIDENCE.json").read_text())
        entry = next(i for i in manifest["artifacts"] if i["file"] == "evidence/lovable-rehearsal.jpg")
        self.assertTrue(entry["pixels_reviewed"])
        for forbidden in ("__lovable_token=", "__lovable_receipt=", "lovable.dev/projects/", "sk-lf-", "pk-lf-"):
            self.assertNotIn(forbidden, page)


if __name__ == "__main__":
    unittest.main()
