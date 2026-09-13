"""Contributor syntax and real declaration boundaries, without executing HCL."""

import json
from pathlib import Path
import tempfile
import unittest

from example_policy import CHILD, ROOT_MODULE, inspect_source, reject_masked_inputs


class DeclarationBoundary(unittest.TestCase):
    def check_source(self, source, accepted, extension='.tf', module=ROOT_MODULE):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ('case' + extension)
            path.write_text(json.dumps(source) if isinstance(source, dict) else source)
            if accepted:
                inspect_source(path, module, 'tftest' in extension)
            else:
                with self.assertRaises(ValueError):
                    inspect_source(path, module, 'tftest' in extension)

    def test_harmless_hcl_values_labels_comments_and_expressions(self):
        cases = [
            'locals { note = "resource" }',
            'locals { provider = "random" }',
            'locals { source = "ordinary text" }',
            'locals { labels = { resource = "pet", provider = "random", data = "text", source = "docs" } }',
            'output "resource" { value = "provider" }',
            'variable "provider" { default = "random" }',
            'locals {\n values = [\n "resource",\n "provider",\n ]\n}',
            'locals { note = join(",", ["resource", "provider"]) }',
            r'locals { note = "file(\"ordinary text\")" }',
            r'locals { note = "$${file(\"ordinary text\")}" }',
            r'locals { note = "%%{ if file(\"ordinary text\") }" }',
            'locals { note = "%{ if true }resource%{ endif }" }',
            '# example syntax <<EOF\n/* provider "aws" {} */\nlocals { note = "safe" }',
            'resource "random_pet" "extra" { length = 1 }',
            'provider "random" { alias = "extra" }',
            'module "pet" { source = "../../child-modules/random-pet" }',
            'locals { note = "${join(",", ["resource", "provider"])}" }',
            'locals { note = "%{ if true }${"resource"}%{ endif }" }',
        ]
        for source in cases:
            with self.subTest(source=source):
                self.check_source(source, True)

    def test_real_hcl_declarations_and_copy_dependencies_are_rejected(self):
        cases = [
            'resource "aws_instance" "x" {}', 'provider "aws" {}',
            'data "external" "x" {}', 'terraform { backend "s3" {} }',
            'terraform { cloud {} }',
            'resource "random_pet" "x" { provisioner "local-exec" { command = "false" } }',
            'module "x" { source = "git::https://example.invalid/repo" }',
            'module "x" { source = "hashicorp/random" }',
            'module "x" { source = local.source }',
            'terraform { required_providers { random = { source = "elsewhere/random" } } }',
            'terraform { required_providers { other = { source = "hashicorp/random" } } }',
            'terraform { required_providers { random = local.provider } }',
            'locals { text = file("/not-read") }',
            'locals { text = "${file("/not-read")}" }',
            'locals { text = "%{ if fileexists("/not-read") }x%{ endif }" }',
            'locals { text = "${"${filesha256("/not-read")}"}" }',
            'locals { text = "${join("", [templatefile("/not-read", {})])}" }',
            'locals { text = "$${literal} ${file("/not-read")}" }',
            'locals { text = "%%{literal} %{ if fileexists("/not-read") }x%{ endif }" }',
        ]
        for source in cases:
            with self.subTest(source=source):
                self.check_source(source, False)
        self.check_source('module "pet" { source = "../../child-modules/random-pet" }', False, module=CHILD)

    def test_json_declarations_have_context_and_template_expressions(self):
        accepted = [
            {'locals': {'provider': 'random', 'source': 'ordinary text', 'data': {}, 'resource': 'pet'}},
            {'locals': {'labels': {'backend': 'text', 'source': 'docs'}}},
            {'output': {'resource': {'value': 'provider'}}},
            {'variable': {'resource': {'default': '${file("literal text")}'}}},
            {'output': {'resource': {'value': 'provider', 'description': '${file("literal text")}'}}},
            {'locals': {'text': 'file("ordinary text")'}},
            {'locals': {'text': '$${file("ordinary text")}', 'directive': '%%{ if file("text") }'}},
            {'locals': {'text': '%{ if true }resource%{ endif }'}},
            {'resource': {'random_pet': {'x': {'length': 1}}}},
            {'provider': {'random': [{'alias': 'extra'}]}},
            {'terraform': {'required_providers': {'random': {'source': 'hashicorp/random'}}}},
            {'//': '${file("comment only")}'},
        ]
        rejected = [
            {'module': {'x': {'source': 'git::https://example.invalid/repo'}}},
            {'resource': {'random_pet': {'x': {}}, 'aws_instance': {'x': {}}}},
            {'terraform': {'backend': {'s3': {}}}},
            {'terraform': {'encryption': {'key_provider': {'unreviewed': {}}}}},
            {'data': {'external': {'x': {}}}},
            {'locals': {'text': '${file("/not-read")}' }},
            {'locals': {'text': '%{ if fileexists("/not-read") }x%{ endif }'}},
            {'locals': {'text': {'${file("/not-read")}': 'value'}}},
            {'terraform': {'required_providers': {'random': {'source': 'elsewhere/random'}}}},
            {'resource': [{'aws_instance': {'x': {}}}]},
        ]
        for expected, cases in ((True, accepted), (False, rejected)):
            for source in cases:
                with self.subTest(source=source):
                    self.check_source(source, expected, '.tf.json')

    def test_malformed_or_ambiguous_boundaries_fail_closed(self):
        for source in ('locals { note = "unterminated }', '/* unterminated',
                       'locals { note = [1, 2) }', 'locals { note = "${true" }',
                       'locals { note = "${true}"', 'locals { note = <<EOF\ntext\nEOF\n}',
                       'locals { note = 1 provider = "random" }',
                       'locals { note = 1\nnote = 2 }',
                       'module "x" { source = "${local.source}" }'):
            with self.subTest(source=source):
                self.check_source(source, False)
        self.check_source('{"resource":{},"resource":{"aws_instance":{"x":{}}}}', False, '.tf.json')
        self.check_source('locals { note = ' + '[' * 66 + '0' + ']' * 66 + ' }', False)

    def test_test_blocks_and_default_masking_use_declarations(self):
        for source in ('run "x" { module { source = "../../child-modules/random-pet" } }',
                       'mock_provider "random" {}', 'override_resource { target = random_pet.x }'):
            self.check_source(source, False, '.tftest.hcl')
        for extension, harmless, masked in (
            ('.tftest.hcl', 'run "defaults" {\n assert {\n condition = true\nerror_message = "variables provider resource"\n }\n}',
             ['variables { length = 2 }\nrun "defaults" {}', 'run "defaults" { variables { length = 2 } }']),
            ('.tftest.json', {'run': {'defaults': {'assert': {'condition': True, 'error_message': 'variables provider resource'}}}},
             [{'variables': {'length': 2}}, {'run': {'defaults': {'variables': {'length': 2}}}}]),
        ):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / ('case' + extension)
                path.write_text(json.dumps(harmless) if isinstance(harmless, dict) else harmless)
                inspect_source(path, ROOT_MODULE, True)
                reject_masked_inputs(path, {'defaults'})
                for source in masked:
                    path.write_text(json.dumps(source) if isinstance(source, dict) else source)
                    with self.assertRaisesRegex(ValueError, 'masks'):
                        reject_masked_inputs(path, {'defaults'})
