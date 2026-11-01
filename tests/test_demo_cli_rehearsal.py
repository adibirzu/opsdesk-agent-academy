"""Rehearsal gates must preserve evidence and never relabel a stub as live AI."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('demo_cli_rehearsal', ROOT / 'scripts/rehearse_demo_cli.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class CliRehearsalTests(unittest.TestCase):
    def test_guide_keeps_planning_local_checks_and_cloud_acceptance_separate(self):
        course = ROOT / 'workshops/app-first'
        guide = (course / 'CODEX-CLI-DEMO.md').read_text()
        for phrase in ('APP-PLAN.md', 'prompts/08-codex-plan.md', 'CODEX-PLANNING-WORKSHEET.md',
                       'separate Langfuse project', 'vercel env add', '--sensitive',
                       '--dry', 'investigator', 'reviewer', 'not a billing receipt'):
            self.assertIn(phrase, guide)
        self.assertIn('not a filmed planning', guide)
        self.assertIn('Do not add `--prod`', guide)
        self.assertNotIn('/Users/', guide)
        self.assertNotIn('sk-lf-', guide)
        prompt = (course / 'prompts/08-codex-plan.md').read_text()
        self.assertIn('Do not implement', prompt)
        self.assertIn('Then show me the plan for review', prompt)
        self.assertIn('separate context with no tools', prompt)
        worksheet = (course / 'CODEX-PLANNING-WORKSHEET.md').read_text()
        self.assertIn('Exact trace/session', worksheet.replace('exact trace/session', 'Exact trace/session'))
        self.assertIn('optional', worksheet.lower())

    def test_deployment_commands_require_the_runtime_only_source_folder(self):
        guide = (ROOT / 'workshops/app-first/CODEX-CLI-DEMO.md').read_text()
        self.assertIn('prepare_deploy.py --output local/private/vercel-source-01', guide)
        self.assertIn('DEPLOYMENT-SOURCE.json', guide)
        self.assertIn('cat local/private/vercel-source-01/.vercelignore', guide)
        self.assertIn('cd local/private/vercel-source-01', guide)
        self.assertNotIn('vercel deploy local/private/codex-opsdesk', guide)
        self.assertNotIn('vercel link --cwd local/private/codex-opsdesk', guide)
        self.assertNotIn('--sensitive --cwd local/private/codex-opsdesk', guide)
        self.assertLess(guide.index('prepare_deploy.py --output'), guide.index('vercel deploy --dry'))
        self.assertIn('Never run Vercel against your original working app folder', guide)
        self.assertIn('packaged snapshot of **the same app**', guide)

    def test_fingerprint_changes_on_selected_source_change_but_skips_env(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / 'app.py').write_text('print("local")\n')
            first, files = runner.fingerprint(source)
            (source / '.env').write_text('DO_NOT_READ=private\n')
            self.assertEqual(runner.fingerprint(source)[0], first)
            self.assertEqual(files, ['app.py'])
            (source / 'app.py').write_text('print("changed")\n')
            self.assertNotEqual(runner.fingerprint(source)[0], first)

    def test_symlink_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / 'app.py').write_text('pass\n')
            (source / 'linked.py').symlink_to(source / 'app.py')
            with self.assertRaisesRegex(ValueError, 'Symlinks'):
                runner.fingerprint(source)

    def test_review_mismatch_prevents_execution_and_output_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source'
            source.mkdir()
            (source / 'app.py').write_text('raise RuntimeError("must not execute")\n')
            output = Path(directory) / 'receipt'
            with self.assertRaisesRegex(ValueError, 'does not match'):
                runner.run(source, output, 'not-the-reviewed-fingerprint')
            self.assertFalse(output.exists())

    def test_existing_evidence_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source'
            source.mkdir()
            (source / 'app.py').write_text('pass\n')
            output = Path(directory) / 'receipt'
            output.mkdir()
            (output / 'existing.txt').write_text('preserve')
            with self.assertRaisesRegex(ValueError, 'existing evidence'):
                runner.run(source, output, runner.fingerprint(source)[0])
            self.assertEqual((output / 'existing.txt').read_text(), 'preserve')

    def test_normal_ai_success_cannot_satisfy_the_disconnected_gate(self):
        self.assertFalse(runner.check_response('disconnected', 200, {'outcome': 'success', 'model_calls': 0}))
        self.assertTrue(runner.check_response('disconnected', 503, {'outcome': 'model_not_configured', 'model_calls': 0}))

    def test_policy_must_stop_before_any_model_call(self):
        self.assertTrue(runner.check_response('policy_stop', 200, {'outcome': 'approval_required', 'model_calls': 0}))
        self.assertFalse(runner.check_response('policy_stop', 200, {'outcome': 'approval_required', 'model_calls': 1}))
        self.assertFalse(runner.check_response('policy_stop', 200, {'outcome': 'approval_required'}))

    def test_nested_teaching_event_requires_no_model_construction(self):
        accepted = {'outcome': 'approval_required', 'event': {'model_calls': 0, 'model_constructed': False}}
        self.assertTrue(runner.check_response('policy_stop', 200, accepted))
        accepted['event']['model_constructed'] = True
        self.assertFalse(runner.check_response('policy_stop', 200, accepted))

    def test_cross_origin_and_missing_origin_cannot_be_success(self):
        for case in ('cross_origin', 'missing_origin'):
            self.assertFalse(runner.check_response(case, 200, {}))
            self.assertTrue(runner.check_response(case, 403, {}))

    def test_oversized_request_requires_413(self):
        self.assertFalse(runner.check_response('oversized_body', 200, {}))
        self.assertTrue(runner.check_response('oversized_body', 413, {}))

    def test_escaping_entry_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / 'app.py').write_text('pass\n')
            with self.assertRaisesRegex(ValueError, 'top-level'):
                runner.run(source, source / 'receipt', runner.fingerprint(source)[0], '../app.py')

    def test_startup_failure_keeps_failed_receipt_and_cleans_owned_child(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source'
            source.mkdir()
            (source / 'app.py').write_text('raise RuntimeError("expected test-only startup failure")\n')
            output = Path(directory) / 'receipt'
            with self.assertRaisesRegex(RuntimeError, 'server exited'):
                runner.run(source, output, runner.fingerprint(source)[0])
            receipt = json.loads((output / 'receipt.json').read_text())
            self.assertEqual(receipt['evidence_class'], 'local_check_failed')
            self.assertTrue(receipt['process_cleanup'])
            self.assertEqual(receipt['live_ai_acceptance'], 'unverified')

    def test_receipt_private_write_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'receipt.json'
            runner.private_write(target, json.dumps({'synthetic': True}))
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                runner.private_write(target, 'replacement')


if __name__ == '__main__':
    unittest.main()
