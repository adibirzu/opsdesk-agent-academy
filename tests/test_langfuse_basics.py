"""Learner trace lab must be exportable and distinguish evidence boundaries."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
COURSE = ROOT / 'workshops/app-first'


class LangfuseBasicsTests(unittest.TestCase):
    def test_trace_lab_has_complete_readonly_workflow_and_download(self):
        page = (COURSE / 'langfuse-basics.html').read_text()
        for anchor in ('find-run', 'read-tree', 'read-timeline', 'usage', 'privacy', 'diagnose'):
            self.assertIn(f'id="{anchor}"', page)
        for item in ('LANGFUSE-BASICS.md', 'evidence/langfuse-timeline.jpg', 'exact trace', 'ingestion-only', 'self-reported', 'not two agents'):
            self.assertIn(item, page)
        brief = (COURSE / 'LANGFUSE-BASICS.md').read_text()
        self.assertIn('do not generate', brief)
        self.assertIn('independent provider readback', brief)
        self.assertNotIn('<iframe', page)
        self.assertNotIn('LANGFUSE_SECRET_KEY=', page)

    def test_recorded_example_does_not_request_data_or_claim_live_connection(self):
        script = (COURSE / 'langfuse-basics.js').read_text()
        for forbidden in ('fetch(', 'XMLHttpRequest', 'WebSocket(', 'localStorage', 'sk-lf-', 'pk-lf-'):
            self.assertNotIn(forbidden, script)
        page = (COURSE / 'langfuse-basics.html').read_text()
        self.assertIn('Recorded example · no provider calls', page)
        self.assertIn('359', page)
        self.assertIn('589', page)
        self.assertIn('948', page)


if __name__ == '__main__':
    unittest.main()
