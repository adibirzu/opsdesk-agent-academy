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
                if path.suffix == ".jpg":
                    record = reviewed[name]
                    self.assertTrue(record["pixels_reviewed"])
                    self.assertEqual(hashlib.sha256(payload).hexdigest(), record["sha256"])
                else:
                    text = payload.decode("utf-8")
                    self.assertIsNone(re.search(r"(?:sk|pk)-lf-[a-zA-Z0-9-]{20,}|__lovable_(?:token|receipt)=|/Users/[^/]+/", text), name)

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
