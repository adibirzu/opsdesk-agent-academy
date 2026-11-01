"""Privacy upload boundary and actual UI delayed-response regression checks."""
import json
from pathlib import Path
import shutil
import importlib.util
import tempfile
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DeliveryTests(unittest.TestCase):
    def test_deployment_default_deny_and_bundle_private_exclusions(self):
        rules = [line.strip() for line in (ROOT / '.vercelignore').read_text().splitlines()
                 if line.strip() and not line.startswith('#')]
        self.assertEqual(rules[0], '*')
        self.assertEqual(set(rules[1:]), {'!app.py', '!engine.py', '!security.py', '!telemetry.py',
            '!requirements.txt', '!pyproject.toml', '!vercel.json', '!static/',
            '!static/index.html', '!static/app.js', '!static/style.css'})
        exclude = json.loads((ROOT / 'vercel.json').read_text())['functions']['app.py']['excludeFiles']
        for pattern in ('local/**', '.venv/**', '.vercel/**', '__pycache__/**', 'secrets/**', 'credentials/**', '.env*'):
            self.assertIn(pattern, exclude)

    @unittest.skipUnless(shutil.which('node'), 'Node is required for the actual browser-source regression')
    def test_delayed_response_does_not_misattribute_result(self):
        result = subprocess.run(['node', str(ROOT / 'tests/selection_contract.cjs')], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_deployment_export_never_reads_or_copies_private_sentinel(self):
        spec = importlib.util.spec_from_file_location('prepare_deploy', ROOT / 'prepare_deploy.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            source, output = Path(temp) / 'source', Path(temp) / 'prepared'
            source.mkdir()
            for name in module.RUNTIME_FILES:
                path = source / name; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('reviewed synthetic runtime source')
            for name in ('local/private/settings.json', '.env.production', '.venv/private', '.vercel/project.json',
                         'credentials/key.json', 'static/private-settings.json'):
                path = source / name; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('synthetic credential sentinel must never leave source')
            manifest = module.prepare(output, source)
            exported = {str(p.relative_to(output)) for p in output.rglob('*') if p.is_file()}
            self.assertEqual(exported, set(module.RUNTIME_FILES) | {'DEPLOYMENT-SOURCE.json'})
            self.assertEqual({row['file'] for row in manifest}, set(module.RUNTIME_FILES))
            for path in output.rglob('*'):
                if path.is_file(): self.assertNotIn('credential sentinel', path.read_text())
            with self.assertRaises(ValueError): module.prepare(output, source)

    def test_deployment_export_refuses_symlink_runtime(self):
        spec = importlib.util.spec_from_file_location('prepare_deploy', ROOT / 'prepare_deploy.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'source'; source.mkdir()
            for name in module.RUNTIME_FILES:
                path = source / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('safe')
            external = Path(temp) / 'external'; external.write_text('unreviewed')
            (source / 'engine.py').unlink(); (source / 'engine.py').symlink_to(external)
            with self.assertRaises(ValueError): module.prepare(Path(temp) / 'prepared', source)
            self.assertFalse((Path(temp) / 'prepared').exists())

    @unittest.skipUnless(shutil.which('vercel') and shutil.which('node'), 'Optional installed CLI filter unavailable; mandatory source-export/privacy gates still run')
    def test_optional_installed_vercel_upload_filter(self):
        executable = Path(shutil.which('vercel')).resolve()
        chunks = next((parent / 'dist/chunks' for parent in list(executable.parents)[:4]
                       if (parent / 'dist/chunks').is_dir()), None)
        if chunks is None: self.skipTest('Installed CLI chunk layout differs')
        result = subprocess.run(['node', str(ROOT / 'tests/vercel_ignore_contract.cjs'), str(chunks)],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        if 'OPTIONAL_HELPER_UNAVAILABLE' in result.stdout:
            self.skipTest('Installed CLI pure-filter export differs; mandatory privacy gates still run')



if __name__ == '__main__': unittest.main()
