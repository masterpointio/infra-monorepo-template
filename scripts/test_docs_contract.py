"""Documentation boundaries and index preservation; no downloaded tools required."""

from contextlib import redirect_stderr, redirect_stdout
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import docs
from module_checks import run_process


class DocumentationContract(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='docs-contract-')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for name in (*docs.CONFIGS, *docs.HELPERS):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((docs.ROOT / name).read_bytes())
        self.authored = 'Authored café\r\nkeep this\n' + docs.BEGIN
        for module in docs.INVENTORY:
            path = self.root / module
            path.mkdir(parents=True)
            (path / 'main.tf').write_bytes(b'variable "original" {}\r\n')
            (path / 'README.md').write_bytes((self.authored + '\n\nstale\n\n' + docs.END + '\r\nTail\n').encode())
        self.git('init', '-q')
        # Highest-precedence, repository-private attributes keep these raw-byte
        # fixtures independent of global autocrlf, attributes and clean filters.
        # They affect only this disposable repository and are never staged.
        self.attributes = self.root / '.git/info/attributes'
        self.attributes.parent.mkdir(exist_ok=True)
        self.attributes.write_text('* -text -eol -ident -filter -working-tree-encoding\n')
        self.git('add', '.')

    def git(self, *args):
        return docs.command(['git', *args], self.root, os.environ.copy(), 10)

    def snapshot(self, staged=False):
        return docs.snapshot(self.root, docs.index_entries(self.root, os.environ.copy(), 10),
                             staged, os.environ.copy(), 10)

    def cli(self, *args):
        with patch.object(docs, 'ROOT', self.root), patch.object(sys, 'argv', ['docs.py', *args]), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return docs.entrypoint()

    def test_staged_bytes_and_working_changes_are_distinct(self):
        staged = self.snapshot(True)
        for name, original in staged.items():
            self.assertEqual(original.encode(), (self.root / name).read_bytes())
        source = next(name for name in staged if name.endswith('.tf'))
        (self.root / source).write_text('variable "working" {}\n')
        self.assertEqual(self.snapshot(True), staged)
        self.assertNotEqual(self.snapshot()[source], staged[source])

    def test_normalized_index_differs_from_unchanged_working_bytes(self):
        working = self.snapshot()
        # Deliberately opt these inputs into Git normalization after the raw
        # fixture was staged; --renormalize forces Git to reapply clean rules.
        with self.attributes.open('a') as attributes:
            attributes.write('*.tf text eol=lf\nREADME.md text eol=lf\n')
        self.git('add', '--renormalize', '.')
        index_before = self.git('ls-files', '--stage')
        staged = self.snapshot(True)
        for name, original in working.items():
            if name.endswith(('.tf', '/README.md')):
                with self.subTest(name=name):
                    self.assertIn('\r\n', original)
                    self.assertEqual(staged[name], original.replace('\r\n', '\n'))
                    self.assertNotEqual(staged[name], original)
        self.assertEqual(self.snapshot(), working)
        self.assertEqual(self.git('ls-files', '--stage'), index_before)

    def test_untracked_source_is_checked_but_staged_mode_uses_index(self):
        module = next(iter(docs.INVENTORY))
        name = module + '/new.tf.json'
        (self.root / name).write_text('{"variable":{"new":{"type":"string"}}}')
        self.assertIn(name, self.snapshot())
        self.assertNotIn(name, self.snapshot(True))

    def test_missing_untracked_and_symlink_readme_fail(self):
        name = next(iter(docs.INVENTORY)) + '/README.md'
        path = self.root / name
        path.unlink()
        with self.assertRaisesRegex(ValueError, 'Missing'):
            self.snapshot()
        path.symlink_to(self.root / 'aqua.yaml')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.snapshot()
        path.unlink()
        path.write_text('untracked')
        self.git('rm', '--cached', '-f', name)
        with self.assertRaisesRegex(ValueError, 'untracked'):
            self.snapshot()

    def test_unknown_json_module_and_engine_shadow_fail(self):
        path = self.root / 'root-modules/unknown/main.tf.json'
        path.parent.mkdir()
        path.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'coverage mismatch'):
            self.snapshot()
        path.unlink()
        shadow = self.root / next(iter(docs.INVENTORY)) / 'main.tofu'
        shadow.write_text('')
        with self.assertRaises(ValueError):
            self.snapshot()

    def test_marker_failures_and_authored_bytes(self):
        original = self.authored + '\nbody\n' + docs.END + '\r\nTail\n'
        before, _, after = docs.split_managed(original, 'README')
        self.assertEqual(before, self.authored)
        self.assertEqual(after, docs.END + '\r\nTail\n')
        for broken in (original.replace(docs.BEGIN, ''), original + docs.END,
                       docs.END + '\n' + docs.BEGIN, original.replace(docs.END, 'inline' + docs.END)):
            with self.subTest(broken=broken), self.assertRaises(ValueError):
                docs.split_managed(broken, 'README')

    def test_config_cannot_replace_documentation_with_static_content(self):
        files = self.snapshot()
        original = files['.terraform-docs.yaml']
        attacks = ['content: |\n  ## Requirements\n  constant', '"content": "constant"',
                   '"cont\\u0065nt": "constant"', 'content: &template constant',
                   'content: !!str constant', 'settings:\n  escape: false',
                   'footer-from: /tmp/private', 'output-values:\n  enabled: true']
        for attack in attacks:
            files['.terraform-docs.yaml'] = original + '\n' + attack + '\n'
            with self.subTest(attack=attack), self.assertRaises(ValueError):
                docs.check_config(files)
        files['.terraform-docs.yaml'] = original.replace('{{ .Content }}', '{{ include "private" }}')
        with self.assertRaises(ValueError):
            docs.check_config(files)
        files['.terraform-docs.yaml'] = '# ordinary comment\n' + original + '\nsort:\n  enabled: true # comment\n  by: required\n'
        docs.check_config(files)

    def test_prettier_plugins_and_secondary_configs_fail(self):
        files = self.snapshot()
        files['.prettierrc.json'] = '{"endOfLine":"lf","plugins":["outside"]}'
        with self.assertRaisesRegex(ValueError, 'plugins'):
            docs.check_config(files)
        (self.root / '.prettierrc.js').write_text('throw new Error("do not execute")')
        with self.assertRaisesRegex(ValueError, 'additional Prettier'):
            self.snapshot()

    def test_stale_index_fails_even_with_fresh_working_readme(self):
        name = next(iter(docs.INVENTORY)) + '/README.md'
        staged = self.snapshot(True)
        fresh = staged[name].replace('stale', 'fresh')
        (self.root / name).write_bytes(fresh.encode())
        index_before = self.git('ls-files', '--stage')
        with patch.object(docs, 'generate', return_value={name: fresh}):
            self.assertEqual(self.cli('--staged'), 1)
            self.assertEqual(self.cli(), 0)
        self.assertEqual(self.git('ls-files', '--stage'), index_before)
        self.assertEqual((self.root / name).read_bytes(), fresh.encode())

    def test_write_is_managed_only_idempotent_and_never_stages(self):
        staged = self.snapshot(True)
        generated = {name: text.replace('stale', 'fresh') for name, text in staged.items() if name.endswith('README.md')}
        index_before = self.git('ls-files', '--stage')
        with patch.object(docs, 'generate', return_value=generated):
            self.assertEqual(self.cli('--write'), 0)
            first = self.snapshot()
            self.assertEqual(self.cli('--write'), 0)
            self.assertEqual(self.snapshot(), first)
        self.assertEqual(self.git('ls-files', '--stage'), index_before)
        for name, text in generated.items():
            self.assertEqual(docs.split_managed(text, name)[::2], docs.split_managed(staged[name], name)[::2])

    def test_unstaged_helper_change_blocks_commit(self):
        (self.root / 'scripts/docs.py').write_text('# different implementation\n')
        with patch.object(docs, 'generate') as generate:
            self.assertEqual(self.cli('--staged'), 1)
            generate.assert_not_called()

    def test_failed_generation_never_partially_writes(self):
        before = self.snapshot()
        with patch.object(docs, 'generate', side_effect=ValueError('generator failed')):
            self.assertEqual(self.cli('--write'), 1)
        self.assertEqual(self.snapshot(), before)

    def test_concurrent_source_or_index_change_blocks(self):
        def changing_generation(files, *args):
            path = self.root / next(iter(docs.INVENTORY)) / 'main.tf'
            path.write_text('variable "changed" {}\n')
            if staged:
                self.git('add', str(path))
            return {}
        for staged in (False, True):
            with patch.object(docs, 'generate', side_effect=changing_generation):
                self.assertEqual(self.cli(*(['--staged'] if staged else [])), 1)
            self.git('checkout', '--', '.')


class BinaryCaptureContract(unittest.TestCase):
    def test_git_style_capture_preserves_mixed_newlines(self):
        result = run_process([sys.executable, '-c', 'import sys; sys.stdout.buffer.write(b"a\\r\\nb\\n")'],
                             cwd=docs.ROOT, env=os.environ.copy(), timeout=5, text=False)
        self.assertEqual(result.stdout, b'a\r\nb\n')
        self.assertEqual(result.stderr, b'')

    def test_binary_timeout_keeps_diagnostic_without_decode_failure(self):
        stream = io.StringIO()
        with redirect_stdout(stream), redirect_stderr(stream), self.assertRaises(subprocess.TimeoutExpired):
            run_process([sys.executable, '-c', 'import sys,time; sys.stdout.buffer.write(b"diagnostic\\xff\\r\\n"); sys.stdout.flush(); time.sleep(60)'],
                        cwd=docs.ROOT, env=os.environ.copy(), timeout=0.2, text=False)
        self.assertIn('diagnostic', stream.getvalue())


if __name__ == '__main__':
    unittest.main()
