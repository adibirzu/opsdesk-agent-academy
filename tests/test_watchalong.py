"""Watch-along timing, release boundaries and anonymous opening-poll contracts."""

from html.parser import HTMLParser
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
COURSE = ROOT / "workshops/app-first"


class Inputs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.fields = []

    def handle_starttag(self, tag, attrs):
        if tag == "input":

            if "data-presenter-config" not in dict(attrs):
                self.fields.append(dict(attrs))


class WatchalongTests(unittest.TestCase):
    def test_chapters_cover_one_continuous_45_minute_app_journey(self):
        data = json.loads((COURSE / "watchalong.json").read_text())
        self.assertEqual(data["duration_seconds"], 45 * 60)
        self.assertEqual(data["chapters"][0]["start"], 0)
        self.assertEqual(data["chapters"][-1]["end"], 2700)
        for i, chapter in enumerate(data["chapters"]):
            self.assertGreater(chapter["end"], chapter["start"])
            self.assertTrue(chapter["tasks"])
            self.assertTrue(chapter["links"])
            if i:
                self.assertEqual(chapter["start"], data["chapters"][i - 1]["end"])
        by_id = {c["id"]: c for c in data["chapters"]}
        self.assertIn("reviewed app and trace checkpoints", by_id["lovable"]["status"])
        for name in ("v0", "base44"):
            self.assertIn("pending", by_id[name]["status"])

    def test_opening_poll_is_prominent_on_the_live_homepage(self):
        page = (COURSE / "index.html").read_text()
        self.assertIn('id="session-start"', page)
        self.assertIn("Open the audience poll", page)
        self.assertIn('href="watchalong.html"', page)

    def test_unreleased_media_is_not_a_broken_or_fabricated_recording(self):
        page = (COURSE / "watchalong.html").read_text()
        self.assertIn("Recording availability:", page)
        self.assertIn("not the final recording transcript", page)
        self.assertIn('id="watch-video"', page)
        self.assertIn('poster="screenshots/lovable-sol-trace.png"', page)
        self.assertIn("never uploaded", page)
        self.assertIn("CODEX-CLI-DEMO.md", page)
        for chapter in json.loads((COURSE / "watchalong.json").read_text())["chapters"]:
            self.assertIn('id="chapter-' + chapter["id"] + '"', page)
            self.assertIn('data-seek="' + str(chapter["start"]) + '"', page)
            if chapter.get("media", {}).get("src"):
                self.assertIn('href="' + chapter["media"]["src"] + '" download', page)
                self.assertIn('href="' + chapter["media"]["captions"] + '" download', page)

    def test_poll_has_only_bounded_anonymous_choices_and_honest_collection_status(self):
        page = (COURSE / "poll.html").read_text()
        parser = Inputs()
        parser.feed(page)
        self.assertTrue(parser.fields)
        self.assertTrue(all(f.get("type") in {"radio", "checkbox"} for f in parser.fields))
        self.assertEqual({f["name"] for f in parser.fields}, {"experience", "daily", "frequency", "outcome", "format"})
        for phrase in ("sends nothing to a server", "no shared tally", "show of hands", "No names or email"):
            self.assertIn(phrase, page)
        script = (COURSE / "poll.js").read_text()
        for prohibited in ("fetch(", "XMLHttpRequest", "sendBeacon", "localStorage", "sessionStorage"):
            self.assertNotIn(prohibited, script)

    def test_live_form_configuration_rejects_editor_links_and_unreviewed_bindings(self):
        spec = importlib.util.spec_from_file_location("poll_config_builder", ROOT / "scripts/build_training_course.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            module.COURSE = Path(temp)
            config = {"service_name": "Google Forms", "respond_url": "https://docs.google.com/forms/d/e/example/viewform", "public_results_url": None, "reviewed": True}
            path = module.COURSE / "poll-config.json"
            path.write_text(json.dumps(config))
            self.assertEqual(module.reviewed_form_config("poll-config.json")["respond_url"], config["respond_url"])
            for change in ({"reviewed": False}, {"respond_url": "https://docs.google.com/forms/d/example/edit#responses"}, {"public_results_url": "https://docs.google.com/forms/d/example/edit"}, {"qr_target_url": "https://example.invalid/"}):
                path.write_text(json.dumps({**config, **change}))
                with self.assertRaises(ValueError):
                    module.reviewed_form_config("poll-config.json")

    def test_task_playlist_requires_complete_reviewed_chapter_assets(self):
        spec = importlib.util.spec_from_file_location("chapter_builder", ROOT / "scripts/build_training_course.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        data = json.loads((COURSE / "watchalong.json").read_text())
        with tempfile.TemporaryDirectory() as temp:
            module.COURSE = Path(temp)
            for media in (
                {"reviewed": False, "src": "media/task.mp4", "captions": "media/task.vtt", "transcript_file": "media/task.txt"},
                {"reviewed": True, "src": "media/task.mp4", "captions": None, "transcript_file": "media/task.txt"},
                {"reviewed": True, "src": "https://example.invalid/task.mp4", "captions": "media/task.vtt", "transcript_file": "media/task.txt"},
            ):
                data["chapters"][0]["media"] = media
                (module.COURSE / "watchalong.json").write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    module.build_watchalong()

    def test_released_chapter_renders_exact_transcript_and_playlist_metadata(self):
        spec = importlib.util.spec_from_file_location("released_chapter_builder", ROOT / "scripts/build_training_course.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        data = json.loads((COURSE / "watchalong.json").read_text())
        for chapter in data["chapters"]:
            chapter["media"] = {"src": None, "captions": None, "transcript_file": None, "reviewed": False}
        with tempfile.TemporaryDirectory() as temp:
            module.COURSE = Path(temp)
            media = module.COURSE / "media"
            media.mkdir()
            # These bytes test generator wiring only; no playable-video acceptance claim.
            (media / "task.mp4").write_bytes(b"isolated media fixture")
            (media / "task.vtt").write_text("WEBVTT\n\n00:00.000 --> 00:01.000\nExact recorded words.\n")
            (media / "task.txt").write_text("Exact recorded words.")
            data["chapters"][0]["media"] = {"reviewed": True, "src": "media/task.mp4", "captions": "media/task.vtt", "transcript_file": "media/task.txt"}
            (module.COURSE / "watchalong.json").write_text(json.dumps(data))
            shutil.copyfile(COURSE / "poll-content.html", module.COURSE / "poll-content.html")
            shutil.copyfile(COURSE / "poll-config.json", module.COURSE / "poll-config.json")
            for chapter in data["chapters"]:
                if chapter.get("prompt_file"):
                    target = module.COURSE / chapter["prompt_file"]
                    target.parent.mkdir(exist_ok=True)
                    shutil.copyfile(COURSE / chapter["prompt_file"], target)
            module.build_watchalong()
            page = (module.COURSE / "watchalong.html").read_text()
            self.assertIn("Recorded transcript", page)
            self.assertIn("Exact recorded words.", page)
            self.assertIn('id="watch-playlist"', page)
            self.assertIn('src="media/task.mp4"', page)
            self.assertIn("Prepared narration summary", page)

    @unittest.skipUnless(shutil.which("node"), "Node is required for the isolated event-level player checks")
    def test_playlist_events_and_global_local_time_mapping(self):
        result = subprocess.run([shutil.which("node"), str(ROOT / "tests/watchalong_player_contract.cjs"), str(COURSE / "watchalong.js")], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("autoplay rejection", result.stdout)

    def test_release_rejects_remote_or_unreviewed_video(self):
        spec = importlib.util.spec_from_file_location("watchalong_builder", ROOT / "scripts/build_training_course.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        data = json.loads((COURSE / "watchalong.json").read_text())
        with tempfile.TemporaryDirectory() as temp:
            module.COURSE = Path(temp)
            for reviewed, source in ((False, "media/recording.mp4"), (True, "https://example.invalid/private.mp4")):
                data["media"] = {"reviewed": reviewed, "src": source, "captions": None}
                (module.COURSE / "watchalong.json").write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    module.build_watchalong()


if __name__ == "__main__":
    unittest.main()
