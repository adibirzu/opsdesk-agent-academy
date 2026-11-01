"""Bounded static export, relative links and selected image integrity."""

import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("student_export", ROOT / "scripts/build_student_site.py")
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {"src", "href"} and value:
                self.paths.append(value)


class PublicSiteTests(unittest.TestCase):
    def test_menu_and_continuous_app_handoffs_are_available(self):
        course = ROOT / "workshops/app-first"
        for page in course.glob("part-*.html"):
            text = page.read_text()
            self.assertIn('class="resource-menu"', text)
            self.assertIn('aria-label="Six-part app journey"', text)
            self.assertEqual(text.count('aria-current="step"'), 1)
            self.assertIn('App continuity checkpoint', text)
            self.assertIn('repeat earlier checks', text)
        briefs = list((course / "agent-briefs").glob("*.md"))
        self.assertEqual(len(briefs), 27)
        for brief in briefs:
            text = brief.read_text()
            self.assertIn("## App continuity checkpoint", text)
            self.assertIn("private handoff note", text)
            self.assertIn("independent provider readback", text)
        home = (course / "index.html").read_text()
        self.assertIn('class="academy-header"', home)
        self.assertIn('class="resource-menu"', home)
        self.assertIn('src="training.js"', home)

    def test_export_has_only_selected_files_and_relative_links_resolve(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "site"
            exporter.build(out)
            self.assertEqual({str(p.relative_to(out)) for p in out.rglob("*") if p.is_file()}, set(exporter.FILES) | {".nojekyll", "site-manifest.json"})
            for page in out.glob("*.html"):
                parser = Links()
                parser.feed(page.read_text())
                for ref in parser.paths:
                    url = urlsplit(ref)
                    if url.scheme or url.netloc or not url.path:
                        continue
                    self.assertFalse(url.path.startswith("/"), (page.name, ref))
                    self.assertTrue((page.parent / unquote(url.path)).is_file(), (page.name, ref))

    def test_export_excludes_secret_files_and_checks_reviewed_images(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "site"
            exporter.build(out)
            reviewed = {item["file"]: item for item in json.loads((out / "EVIDENCE.json").read_text())["artifacts"]}
            for path in out.rglob("*"):
                if not path.is_file():
                    continue
                name = str(path.relative_to(out))
                self.assertFalse(any(part.startswith(".env") or part in {"secrets", "credentials", "local", "node_modules", "redwood", "assets"} for part in path.relative_to(out).parts))
                payload = path.read_bytes()
                if path.suffix in {".jpg", ".png", ".mp4"}:
                    record = reviewed[name]
                    self.assertTrue(record["pixels_reviewed"])
                    self.assertEqual(hashlib.sha256(payload).hexdigest(), record["sha256"])
                    if path.suffix == ".mp4":
                        self.assertTrue(record["audio_qa"]["full_stream_decode"])
                        self.assertTrue(record["audio_qa"]["narration_vtt_match"])
                        self.assertTrue(record["audio_qa"]["caption_timing_verified"])
                        self.assertIsInstance(record["audio_qa"]["human_listening_review"], bool)
                        self.assertTrue(record["audio_qa"]["scope"])
                        self.assertEqual(record["kind"], "narrated-task-video")
                else:
                    text = payload.decode("utf-8")
                    self.assertIsNone(re.search(r"(?:sk|pk)-lf-[a-zA-Z0-9-]{20,}|__lovable_(?:token|receipt)=|/Users/[^/]+/", text), name)

    def test_video_export_requires_matching_bytes_and_scoped_audio_qa(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "task.mp4"
            source.write_bytes(b"isolated-video-export-fixture")
            name = "media/task.mp4"
            record = {"kind": "narrated-task-video", "pixels_reviewed": True, "audio_qa": {"full_stream_decode": True, "narration_vtt_match": True, "caption_timing_verified": True, "human_listening_review": False, "scope": "Full decode and narration/caption verification; no full human listening review."}, "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
            exporter.validate_public_video(source, name, {name: record})
            for change in ({"audio_qa": {}}, {"audio_qa": {**record["audio_qa"], "full_stream_decode": False}}, {"pixels_reviewed": False}, {"sha256": "0" * 64}, {"kind": "continuous-screen-recording"}):
                with self.assertRaises(ValueError):
                    exporter.validate_public_video(source, name, {name: {**record, **change}})

    def test_all_persona_downloads_exist_and_no_live_acceptance_is_invented(self):
        source = ROOT / "workshops/app-first"
        for persona in ("business", "it-starter", "ai-engineer"):
            bundle = (source / f"agent-briefs/workflow-{persona}.md").read_text()
            for number in range(1, 7):
                brief = (source / f"agent-briefs/persona-{persona}-part-{number}.md").read_text()
                self.assertIn(brief.strip(), bundle)
        parts = json.loads((source / "results.json").read_text())["parts"]
        self.assertIn("independently verified in Langfuse", parts[3]["status"])
        self.assertIn("OCI APM and Log Analytics require separate", parts[3]["remaining"])
        reviewed = json.loads((source / "EVIDENCE.json").read_text())["artifacts"]
        for name in ("evidence/lovable-policy-trace-success.jpg", "evidence/langfuse-policy-tree.jpg"):
            record = next(item for item in reviewed if item["file"] == name)
            self.assertTrue(record["pixels_reviewed"])
            self.assertEqual(record["evidence_class"], "provider-verified")
            self.assertIn("OCI APM or Log Analytics delivery", record["does_not_prove"])
        self.assertIn("not live accepted", parts[5]["status"])

    def test_downloaded_markdown_links_resolve_in_the_public_site(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "site"
            exporter.build(out)
            for page in out.rglob("*.md"):
                for ref in re.findall(r"\]\(([^)]+)\)", page.read_text()):
                    url = urlsplit(ref)
                    if not (url.scheme or url.netloc) and url.path:
                        self.assertTrue((page.parent / unquote(url.path)).is_file(), (page.name, ref))


if __name__ == "__main__":
    unittest.main()
