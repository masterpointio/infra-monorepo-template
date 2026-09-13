"""Boundary regressions that must fail before any provider/tool can execute."""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from example_policy import CHILD, ROOT_MODULE, inspect_tree, stage
from test_examples import tool_policy

REPO = Path(__file__).resolve().parents[1]


class ExampleBoundary(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for category in ("child-modules", "root-modules"):
            shutil.copytree(REPO / category, self.root / category)

    def test_unknown_modules_and_json_modules_fail_before_execution(self):
        for category, filename in (("child-modules", "main.tf"), ("root-modules", "main.tf.json")):
            with self.subTest(category=category):
                extra = self.root / category / "unreviewed"
                extra.mkdir()
                (extra / filename).write_text('{}')
                with self.assertRaisesRegex(ValueError, "unregistered"):
                    inspect_tree(self.root)
                shutil.rmtree(extra)

    def test_ambient_variables_and_masked_defaults(self):
        for module, folder in ((CHILD, ""), (CHILD, "tests"), (ROOT_MODULE, ""), (ROOT_MODULE, "tests/defaults"), (ROOT_MODULE, "tests/dev")):
            for filename in ("terraform.tfvars", "terraform.tfvars.json", "hidden.auto.tfvars", "hidden.auto.tfvars.json"):
                with self.subTest(module=module, folder=folder, filename=filename):
                    path = self.root / module / folder / filename
                    path.write_text('{}')
                    with self.assertRaisesRegex(ValueError, "auto-loaded"):
                        inspect_tree(self.root)
                    path.unlink()
        path = self.root / ROOT_MODULE / "tests/defaults/defaults.tftest.hcl"
        for addition in ('variables { length = 2 }\n',):
            path.write_text(addition + path.read_text())
            with self.assertRaisesRegex(ValueError, "masks"):
                inspect_tree(self.root)

    def test_copy_uses_dirty_source_and_excludes_private_artifacts(self):
        base = self.root / ROOT_MODULE
        source = base / "main.tf"
        source.write_text(source.read_text() + '\n# uncommitted source edit\n')
        for filename in ("terraform.tfstate", "plan.bin", "private.txt", ".terraform.lock.hcl"):
            (base / filename).write_text('must not copy')
        (base / ".terraform").mkdir()
        (base / ".terraform/private.tf").write_text('must not copy')
        selected = inspect_tree(self.root)
        with tempfile.TemporaryDirectory() as out:
            work = stage(self.root, Path(out), selected, ROOT_MODULE, "defaults", "terraform")
            self.assertIn('uncommitted source edit', (work / "main.tf").read_text())
            self.assertFalse((work / "example.auto.tfvars").exists())
            self.assertTrue((Path(out) / CHILD / "main.tf").is_file())
            self.assertNotIn('must not copy', (work / ".terraform.lock.hcl").read_text())
            self.assertFalse((work / "terraform.tfstate").exists())
            self.assertFalse((work / "private.txt").exists())
            self.assertFalse((work / ".terraform").exists())

    def test_source_escape_and_execution_policy(self):
        main = self.root / ROOT_MODULE / "main.tf"
        original = main.read_text()
        for replacement in ('/tmp/escape', '../../../escape', 'git::https://example.invalid/repo'):
            main.write_text(original.replace('../../child-modules/random-pet', replacement))
            with self.assertRaisesRegex(ValueError, "unregistered source"):
                inspect_tree(self.root)
        main.write_text(original)
        extra = self.root / ROOT_MODULE / "escape.tf"
        for text in ('resource "aws_instance" "x" {}', 'data "external" "x" {}', 'resource "random_pet" "x" { provisioner "local-exec" { command = "false" } }', 'locals { secret = file("/tmp/private") }', 'locals { secret = filesha256("/tmp/private") }', 'locals { secret = "${file(\"/tmp/private\")}" }'):
            extra.write_text(text)
            with self.assertRaisesRegex(ValueError, "review|policy"):
                inspect_tree(self.root)
        extra.unlink()
        extra.symlink_to(main)
        with self.assertRaisesRegex(ValueError, "symlink"):
            inspect_tree(self.root)

    def test_fixture_omission_and_extra_tests(self):
        extra = self.root / ROOT_MODULE / "tests/defaults/extra.tftest.hcl"
        extra.write_text('run "extra" { command = plan }')
        self.assertIn(extra, inspect_tree(self.root)[ROOT_MODULE])
        folder = extra.parent / "unregistered"
        folder.mkdir()
        (folder / extra.name).write_text(extra.read_text())
        with self.assertRaisesRegex(ValueError, "Unregistered test directory"):
            inspect_tree(self.root)

    def test_engine_specific_sources_are_never_silently_omitted(self):
        for module in (CHILD, ROOT_MODULE, "child-modules/unregistered", "root-modules/unregistered"):
            folders = ("",) if "unregistered" in module else ("", "tests", "tests/new-fixture")
            for folder in folders:
                for filename in ("main.tofu", "extra.tofu", "main.tofu.json", "extra.tofu.json", "extra.tofutest.hcl", "extra.tofutest.json"):
                    with self.subTest(module=module, folder=folder, filename=filename):
                        path = self.root / module / folder / filename
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text('{}')
                        with self.assertRaisesRegex(ValueError, "Engine-specific.*shared"):
                            inspect_tree(self.root)
                        path.unlink()

    def test_both_entrypoints_reject_shadows_before_binary_lookup(self):
        shutil.copytree(REPO / "scripts", self.root / "scripts", ignore=shutil.ignore_patterns('__pycache__'))
        (self.root / ROOT_MODULE / "main.tofu").write_text('unshared source')
        # No configs/tools are present in this fixture. The source diagnostic
        # must win over both tool-policy and executable resolution failures.
        for script in ('test_examples.py', 'test_random_pet.py'):
            for engine in ('terraform', 'tofu'):
                with self.subTest(script=script, engine=engine):
                    result = subprocess.run(
                        [sys.executable, str(self.root / 'scripts' / script), engine,
                         '--binary', str(self.root / 'does-not-exist')],
                        capture_output=True, text=True, timeout=10,
                    )
                    self.assertEqual(result.returncode, 1)
                    self.assertIn('Engine-specific source/test shadow', result.stderr)

    def write_tool_configs(self, terraform, tofu, registry):
        aqua = f"registries:\n  - type: standard\n    ref: {registry}\npackages:\n  - name: hashicorp/terraform@v{terraform}\n  - name: opentofu/opentofu@v{tofu}\n"
        for name in ("aqua.yaml", "scripts/aqua.yaml"):
            path = self.root / name
            path.parent.mkdir(exist_ok=True)
            path.write_text(aqua)
        trunk = self.root / ".trunk/trunk.yaml"
        trunk.parent.mkdir(exist_ok=True)
        trunk.write_text(f"lint:\n  enabled:\n    - tofu@{tofu}\n")

    def test_tool_drift(self):
        # Synthetic selections, not assertions about today's production versions
        # or about whether these versions exist. Coordinated updates need no edits.
        for terraform, tofu, registry in (("1.2.3", "1.4.5", "v2.3.4"), ("2.3.4", "2.5.6", "v3.4.5")):
            self.write_tool_configs(terraform, tofu, registry)
            self.assertEqual(tool_policy(self.root), {"terraform": terraform, "tofu": tofu})
            for name, old, new in (("aqua.yaml", f"terraform@v{terraform}", "terraform@v9.9.9"),
                                   ("scripts/aqua.yaml", f"opentofu@v{tofu}", "opentofu@v9.9.9"),
                                   ("aqua.yaml", registry, "v9.9.9"),
                                   (".trunk/trunk.yaml", f"tofu@{tofu}", "tofu@9.9.9")):
                with self.subTest(config=name, selection=(terraform, tofu, registry)):
                    path = self.root / name
                    original = path.read_text()
                    self.assertIn(old, original)
                    path.write_text(original.replace(old, new))
                    with self.assertRaisesRegex(ValueError, "Align"):
                        tool_policy(self.root)
                    path.write_text(original)

    def test_live_repository_pins_are_aligned(self):
        # Separate live coherence check; expected versions come from config.
        self.assertEqual(set(tool_policy(REPO)), {"terraform", "tofu"})
