"""Teaching graphs must preserve capability and evidence boundaries."""

from pathlib import Path
import unittest

COURSE = Path(__file__).resolve().parents[1] / "workshops/app-first"


class AgentMapTests(unittest.TestCase):
    def test_map_is_present_in_course_engine_and_original_agent_lesson(self):
        for name in ("relationships.html", "part-2-agent-engine.html", "index.html"):
            text = (COURSE / name).read_text()
            self.assertEqual(text.count('class="agent-map"'), 1, name)
            self.assertIn('src="agent-map.js"', text)
            self.assertIn('href="agent-map.css"', text)
            self.assertIn("Illustration, not execution", text)
            self.assertIn("RAG is an optional extension", text)
        self.assertIn('href="relationships.html"', (COURSE / "course.html").read_text())

    def test_diagram_has_no_network_storage_or_untrusted_html_sink(self):
        js = (COURSE / "agent-map.js").read_text()
        for forbidden in ("fetch(", "XMLHttpRequest", "localStorage", "sessionStorage", "innerHTML", ".html(", "setInterval", "eval("):
            self.assertNotIn(forbidden, js)
        for required in ("ResizeObserver", "event.key==='Enter'", "event.key===' '", "aria-pressed", "approval_required", "data-map-back", "data-map-next", "data-map-reset"):
            self.assertIn(required, js)
        self.assertIn("prefers-reduced-motion", (COURSE / "agent-map.css").read_text())

    def test_waterfall_distinguishes_events_from_unmeasured_durations(self):
        for name in ("relationships.html", "part-4-follow-the-evidence.html"):
            text = (COURSE / name).read_text()
            self.assertIn('class="waterfall"', text)
            self.assertIn("durations were not measured", text)
            self.assertIn("not Langfuse/APM readback", text)
            self.assertIn("952 reported tokens", text)
            self.assertIn("Cost: unknown", text)
        js = (COURSE / "agent-map.js").read_text()
        self.assertIn("point:1832", js)
        self.assertIn("end:5218", js)

    def test_rag_mission_requires_scoping_sources_and_honest_status(self):
        mission = (COURSE / "RAG-MISSION.md").read_text()
        for required in ("not part of the verified Lovable baseline", "document-access filtering", "no-result", "source label", "untrusted context", "new provider"):
            self.assertIn(required, mission)


if __name__ == "__main__":
    unittest.main()
