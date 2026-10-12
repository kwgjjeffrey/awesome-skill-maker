import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from utils.skill_project_toolkit import initialize, build, install, rollback, validate, extract_archive, upgrade

ROOT = Path(__file__).resolve().parents[1]


class ArtifactLifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'source'
        initialize(self.repo, 'sample-skill', 'example/sample-skill', 'Sample capability')
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.com')
        self.commit()
        self.target = self.root / 'skills/sample-skill'
        self.store = self.root / 'state'

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.repo, stderr=subprocess.DEVNULL).decode().strip()

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-m', 'Test version')

    def artifact(self):
        m = build(self.repo)
        return self.repo / 'dist' / m['asset'], self.repo / 'dist/sample-skill-release.json'

    def test_installed_tools_build_another_project_without_source_checkout(self):
        archive, manifest = self.artifact()
        install(archive, manifest, self.target, self.store)
        shutil_source = self.root / 'source-hidden'
        self.repo.rename(shutil_source)
        result = subprocess.run([sys.executable, str(self.target / 'setup/scripts/manage_skill_installation.py'), 'check', '--target', str(self.target)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        # Maker's real artifact carries the initializer and reusable lifecycle resources.
        maker = self.root / 'maker'
        maker.mkdir()
        from utils.skill_project_toolkit import artifact_files, configuration
        import shutil
        for rel in artifact_files(ROOT, configuration(ROOT)):
            (maker / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, maker / rel)
        generated = self.root / 'from-artifact'
        result = subprocess.run([sys.executable, str(maker / 'project/scripts/initialize_skill_project.py'), '--destination', str(generated), '--name', 'artifact-child', '--repository', 'example/artifact-child', '--description', 'Child capability'], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(validate(generated)['ready'])
        self.assertFalse((self.target / 'AGENTS.md').exists())
        self.assertFalse((self.target / 'tests').exists())
        subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests'], cwd=generated, check=True, capture_output=True)
        subprocess.run(['git', 'init', '-b', 'main'], cwd=generated, check=True, capture_output=True)
        subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'add', '.'], cwd=generated, check=True)
        subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-m', 'Initialize'], cwd=generated, check=True, capture_output=True)
        result = subprocess.run([sys.executable, str(generated / 'release/scripts/build_skill_artifact.py'), '--repo', str(generated)], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_upgrade_rollback_and_corruption_preserve_external_state(self):
        archive, manifest = self.artifact()
        install(archive, manifest, self.target, self.store)
        previous = self.target.resolve()
        (self.store / 'user-config.json').write_text('{"keep":true}')
        config = json.loads((self.repo / 'skill-project.json').read_text())
        config['version'] = '0.1.1'
        (self.repo / 'skill-project.json').write_text(json.dumps(config))
        self.commit()
        archive, manifest = self.artifact()
        archive.write_bytes(archive.read_bytes() + b'bad')
        with self.assertRaises(ValueError):
            install(archive, manifest, self.target, self.store)
        self.assertEqual(self.target.resolve(), previous)
        archive.write_bytes(archive.read_bytes()[:-3])
        install(archive, manifest, self.target, self.store)
        self.assertNotEqual(self.target.resolve(), previous)
        rollback(self.target, self.store)
        self.assertEqual(self.target.resolve(), previous)
        self.assertEqual((self.store / 'user-config.json').read_text(), '{"keep":true}')

    def test_unmanaged_destination_and_concurrent_install_rejected(self):
        archive, manifest = self.artifact()
        self.target.mkdir(parents=True)
        (self.target / 'user.txt').write_text('preserve')
        with self.assertRaises(ValueError):
            install(archive, manifest, self.target, self.store)
        self.assertEqual((self.target / 'user.txt').read_text(), 'preserve')
        (self.store / '.installation-lock').mkdir()
        with self.assertRaises(ValueError):
            install(archive, manifest, self.target, self.store)

    def test_archive_links_and_traversal_rejected_before_any_write(self):
        for name, kind in [('package/../../escaped', tarfile.REGTYPE), ('package/link', tarfile.SYMTYPE)]:
            archive = self.root / 'bad.tgz'
            with tarfile.open(archive, 'w:gz') as bundle:
                item = tarfile.TarInfo(name)
                item.type = kind
                item.linkname = '/tmp/outside'
                if kind == tarfile.REGTYPE:
                    item.size = 1
                    bundle.addfile(item, io.BytesIO(b'x'))
                else:
                    bundle.addfile(item)
            stage = self.root / 'staging'
            with self.assertRaises(ValueError):
                extract_archive(archive, stage)
            self.assertFalse(stage.exists())

    def test_github_upgrade_checks_tag_and_current_version(self):
        archive, manifest = self.artifact()
        m = json.loads(manifest.read_text())
        base = 'https://api.github.com/repos/example/sample-skill'
        release = {'tag_name': 'v0.1.0', 'assets': [
            {'name': 'sample-skill-release.json', 'url': base + '/releases/assets/1'},
            {'name': 'sample-skill-0.1.0.tgz', 'url': base + '/releases/assets/2'}]}
        responses = {base + '/releases/latest': json.dumps(release).encode(),
                     base + '/releases/assets/1': manifest.read_bytes(),
                     base + '/releases/assets/2': archive.read_bytes(),
                     base + '/git/ref/tags/v0.1.0': json.dumps({'object': {'type': 'commit', 'sha': m['sourceCommit']}}).encode()}
        def fake_fetch(url, output, binary=False):
            Path(output).write_bytes(responses[url])
        with patch('utils.skill_project_toolkit.fetch', fake_fetch):
            result = upgrade('example/sample-skill', self.target, self.store)
            self.assertTrue(result['installed'])
            self.assertFalse(upgrade('example/sample-skill', self.target, self.store)['updated'])
            responses[base + '/git/ref/tags/v0.1.0'] = json.dumps({'object': {'type': 'commit', 'sha': '0' * 40}}).encode()
            before = self.target.resolve()
            with self.assertRaises(ValueError):
                upgrade('example/sample-skill', self.target, self.store)
            self.assertEqual(self.target.resolve(), before)

    def test_standalone_bootstrap_installs_verified_package(self):
        archive, manifest = self.artifact()
        result = subprocess.run([sys.executable, str(ROOT / 'setup/bootstrap_skill_installation.py'), '--archive', str(archive), '--manifest', str(manifest), '--target', str(self.target), '--store', str(self.store)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.target.is_symlink())

    def test_dirty_source_and_same_version_change_rejected(self):
        self.artifact()
        (self.repo / 'SKILL.md').write_text((self.repo / 'SKILL.md').read_text() + '\nChanged\n')
        with self.assertRaises(ValueError):
            build(self.repo)
        self.commit()
        with self.assertRaises(ValueError):
            build(self.repo)


if __name__ == '__main__':
    unittest.main()
