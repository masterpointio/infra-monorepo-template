#!/usr/bin/env python3
"""Check or regenerate only the two examples' managed README sections."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile

from example_policy import INVENTORY, SOURCE, reject_engine_sources
from module_checks import run_process

ROOT = Path(__file__).resolve().parents[1]
BEGIN = '<!-- BEGINNING OF PRE-COMMIT-TERRAFORM DOCS HOOK -->'
END = '<!-- END OF PRE-COMMIT-TERRAFORM DOCS HOOK -->'
CONFIGS = ('.terraform-docs.yaml', '.prettierrc.json', 'aqua.yaml', '.trunk/trunk.yaml')
HELPERS = ('scripts/docs.py', 'scripts/module_checks.py', 'scripts/example_policy.py', 'scripts/example_syntax.py')
SECTIONS = ('Requirements', 'Providers', 'Modules', 'Resources', 'Inputs', 'Outputs')


def command(args, root, env, timeout):
    # Git blobs must not undergo universal-newline conversion. Use the same raw
    # capture for tool output; decoding UTF-8 does not alter CRLF or mixed bytes.
    result = run_process(args, cwd=root, env=env, timeout=timeout, text=False)
    if result.returncode:
        print(result.stdout.decode('utf-8', errors='replace'), end='', file=sys.stderr)
        print(result.stderr.decode('utf-8', errors='replace'), end='', file=sys.stderr)
        result.check_returncode()
    return result.stdout.decode('utf-8')


def index_entries(root, env, timeout):
    entries = {}
    for entry in command(['git', 'ls-files', '--stage', '-z'], root, env, timeout).split('\0'):
        if not entry:
            continue
        metadata, name = entry.split('\t', 1)
        mode, oid, stage = metadata.split()
        if stage != '0':
            raise ValueError('Resolve Git index conflicts before checking documentation.')
        entries[name] = (mode, oid)
    return entries


def checked_read(root, name):
    path = root / name
    if (path.is_symlink() or any(p.is_symlink() for p in path.parents if root in p.parents)
            or not path.is_file() or not path.stat().st_mode & 0o444):
        raise ValueError(f'Missing, unreadable or symlinked documentation input: {path}')
    return path.read_bytes().decode('utf-8')


def snapshot(root, entries, staged, env, timeout):
    if staged:
        names = set(entries)
    else:
        names = set(CONFIGS) | {p.name for p in root.iterdir()}
        for category in ('child-modules', 'root-modules'):
            parent = root / category
            if parent.is_symlink() or not parent.is_dir():
                raise ValueError(f'Missing or symlinked module directory: {parent}')
            for module in parent.iterdir():
                if module.is_symlink():
                    raise ValueError(f'Symlink outside documentation copy boundary: {module}')
                if module.is_dir():
                    names.update(p.relative_to(root).as_posix() for p in module.iterdir())
    discovered = set()
    sources = set()
    for name in names:
        parts = Path(name).parts
        if name != '.prettierrc.json' and (parts[-1].startswith('.prettierrc') or parts[-1].startswith('prettier.config.')):
            raise ValueError(f'{name}: additional Prettier config requires a documentation-pipeline review.')
        if len(parts) == 3 and parts[0] in ('child-modules', 'root-modules'):
            reject_engine_sources(Path(*parts[:2]), [parts[2]])
            if name.endswith(SOURCE):
                discovered.add('/'.join(parts[:2]))
                sources.add(name)
    if discovered != set(INVENTORY):
        raise ValueError(f'Documentation coverage mismatch: expected {sorted(INVENTORY)}, found {sorted(discovered)}. '
                         'Review and register new modules before documenting them.')
    selected = sources | set(CONFIGS) | {name + '/README.md' for name in INVENTORY}
    result = {}
    for name in sorted(selected):
        if name.endswith('/README.md') and name not in entries:
            raise ValueError(f'Missing or untracked required README: {name}; restore it or stage its intentional addition.')
        if staged:
            if name not in entries or entries[name][0] not in ('100644', '100755'):
                raise ValueError(f'Missing or non-file staged documentation input: {name}')
            result[name] = command(['git', 'cat-file', 'blob', entries[name][1]], root, env, timeout)
        else:
            result[name] = checked_read(root, name)
    return result


def split_managed(text, name):
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise ValueError(f'{name}: require exactly one intact BEGIN/END terraform-docs marker pair.')
    for marker in (BEGIN, END):
        if not re.search(r'^' + re.escape(marker) + r'\r?$', text, re.MULTILINE):
            raise ValueError(f'{name}: documentation markers must occupy their own lines.')
    before, remaining = text.split(BEGIN)
    if END not in remaining:
        raise ValueError(f'{name}: documentation markers are reversed.')
    managed, after = remaining.split(END)
    return before + BEGIN, managed, END + after


def versions(files):
    def pin(pattern, name):
        matches = re.findall(pattern, files[name])
        if len(matches) != 1:
            raise ValueError(f'{name}: require one unambiguous documentation-tool pin.')
        return matches[0]
    return (pin(r'terraform-docs/terraform-docs@v([\d.]+)', 'aqua.yaml'),
            pin(r'- prettier@([\d.]+)', '.trunk/trunk.yaml'))


def check_config(files):
    # Deliberately accept only this config's plain literal YAML mapping. Reject
    # custom content, includes, aliases, escaped/quoted keys and other YAML forms
    # before the native parser sees them; a headings-only template is not docs.
    allowed = {
        'version': r'\d+\.\d+\.\d+', 'formatter': r'markdown table',
        'recursive.enabled': r'false', 'output.file': r'README\.md', 'output.mode': r'inject',
        'sort.enabled': r'true|false', 'sort.by': r'name|required|type',
        **{f'settings.{name}': r'true|false' for name in
           ('anchor', 'html', 'escape', 'default', 'hide-empty', 'required', 'sensitive', 'type', 'read-comments')},
        'settings.lockfile': r'false',
    }
    lines = [line.split(' #', 1)[0].rstrip() for line in files['.terraform-docs.yaml'].splitlines()
             if line.strip() and not line.lstrip().startswith('#')]
    seen, section, i = set(), '', 0
    while i < len(lines):
        match = re.fullmatch(r'( {2})?([a-z][a-z-]*):(?: (.+))?', lines[i])
        if not match:
            raise ValueError('Unsupported .terraform-docs.yaml syntax; keep plain literal mappings or review the copy boundary.')
        indent, name, value = match.groups()
        key = f'{section}.{name}' if indent else name
        if key in seen:
            raise ValueError(f'Duplicate terraform-docs configuration key: {key}')
        seen.add(key)
        if not indent and value is None and name in ('settings', 'recursive', 'output', 'sort'):
            section = name
        elif key == 'output.template' and value == '|-':
            if lines[i + 1:i + 4] != ['    ' + BEGIN, '    {{ .Content }}', '    ' + END]:
                raise ValueError('Keep the existing terraform-docs output template and markers; custom content requires review.')
            i += 3
        elif key not in allowed or value is None or not re.fullmatch(allowed[key], value):
            raise ValueError(f'Unsupported terraform-docs configuration {key}; custom content/paths require review.')
        i += 1
    if not {'version', 'formatter', 'output.template', 'recursive.enabled'} <= seen:
        raise ValueError('Incomplete terraform-docs configuration; restore the version, formatter, template and recursion policy.')
    # No executable Prettier configs/plugins; only literal formatting options.
    prettier = json.loads(files['.prettierrc.json'])
    allowed = {'printWidth', 'tabWidth', 'useTabs', 'proseWrap', 'endOfLine'}
    if not isinstance(prettier, dict) or not set(prettier) <= allowed or prettier.get('endOfLine') != 'lf':
        raise ValueError('Use the reviewed JSON Prettier formatting options and LF newlines; plugins require review.')


def generate(files, root, env, timeout, binary=None, formatter=None):
    expected_docs, expected_prettier = versions(files)
    check_config(files)
    readmes = {name + '/README.md': split_managed(files[name + '/README.md'], name) for name in INVENTORY}
    with tempfile.TemporaryDirectory(prefix='example-docs-') as directory:
        work = Path(directory)
        for name, text in files.items():
            path = work / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode('utf-8'))
        if binary is None:
            if not shutil.which('aqua', path=env.get('PATH')):
                raise ValueError('Install Aqua and run aqua install; or use --binary /path/to/terraform-docs.')
            binary = command(['aqua', '-c', str(work / 'aqua.yaml'), 'which', 'terraform-docs'], root, env, timeout).strip()
        formatter = formatter or str(root / '.trunk/tools/prettier')
        if not binary or not shutil.which(binary, path=env.get('PATH')):
            raise ValueError('Missing terraform-docs binary; run aqua install.')
        if not shutil.which(formatter, path=env.get('PATH')):
            raise ValueError('Missing Trunk Prettier; run trunk install before documentation checks.')
        actual = command([binary, '--version'], work, env, timeout).strip()
        if not actual.startswith(f'terraform-docs version v{expected_docs} '):
            raise ValueError(f'Expected terraform-docs {expected_docs}; got {actual}. Run aqua install.')
        actual = command([formatter, '--version'], work, env, timeout).strip()
        if actual != expected_prettier:
            raise ValueError(f'Expected Prettier {expected_prettier}; got {actual}. Run trunk install for the selected config.')
        generated = {}
        header = work / 'empty-header.md'
        header.write_text('')
        for name, (before, _, after) in readmes.items():
            module = work / Path(name).parent
            output = command([
                binary, 'markdown', 'table', '--config', str(work / '.terraform-docs.yaml'),
                '--recursive=false', '--lockfile=false', '--output-values=false', '--output-values-from', '',
                '--header-from', str(header), '--footer-from', '', '--output-file', '',
                '--type=true', '--default=true', '--required=true', '--sensitive=true', '--indent', '2',
                '--show', ','.join(s.lower() for s in SECTIONS), str(module),
            ], work, env, timeout)
            if any(f'## {section}\n' not in output for section in SECTIONS):
                raise ValueError(f'{name}: generator returned incomplete documentation; check source and config.')
            # Format generated text alone; authored prose never enters a formatter.
            rendered = work / 'generated.md'
            rendered.write_text(output)
            command([formatter, '--config', str(work / '.prettierrc.json'), '--no-editorconfig',
                     '--parser', 'markdown', '--write', str(rendered)], work, env, timeout)
            content = rendered.read_text().strip()
            if any(f'## {section}\n' not in content + '\n' for section in SECTIONS):
                raise ValueError(f'{name}: formatter returned incomplete documentation.')
            generated[name] = before + '\n\n' + content + '\n\n' + after
        return generated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--write', action='store_true', help='Replace managed sections in the working tree; never stage')
    mode.add_argument('--staged', action='store_true', help='Check the Git index for the pre-commit hook; never write')
    parser.add_argument('--timeout', type=int, default=240, help='Seconds per command, including lookup (default: 240)')
    parser.add_argument('--binary', help='Explicit pinned terraform-docs executable')
    parser.add_argument('--formatter', help='Explicit pinned Prettier executable; normally installed by Trunk')
    args = parser.parse_args()
    if args.timeout <= 0:
        raise ValueError('--timeout must be positive.')
    env = {k: v for k, v in os.environ.items() if not k.startswith(('TF_', 'TOFU_', 'TFDOCS_'))}
    entries = index_entries(ROOT, env, args.timeout)
    if args.staged:
        for name in HELPERS:
            if name not in entries or checked_read(ROOT, name) != command(['git', 'cat-file', 'blob', entries[name][1]], ROOT, env, args.timeout):
                raise ValueError(f'{name}: executing helper differs from the index. Review and stage helper changes, then retry the commit.')
    files = snapshot(ROOT, entries, args.staged, env, args.timeout)
    generated = generate(files, ROOT, env, args.timeout, args.binary, args.formatter)
    if args.staged:
        if index_entries(ROOT, env, args.timeout) != entries:
            raise ValueError('Git index changed during documentation checking; review changes and retry the commit.')
    elif snapshot(ROOT, index_entries(ROOT, env, args.timeout), False, env, args.timeout) != files:
        raise ValueError('Documentation inputs changed during generation; retry without simultaneous edits.')
    changed = [name for name, content in generated.items() if content != files[name]]
    if changed and not args.write:
        detail = ' in the staged snapshot' if args.staged else ''
        raise ValueError(f'Documentation drift{detail}: {", ".join(changed)}. '
                         'Run python3 scripts/docs.py --write, review and stage matching source/config and generated sections; retry the check/commit.')
    if args.write:
        for name in changed:
            (ROOT / name).write_bytes(generated[name].encode('utf-8'))
    if args.write:
        print(f'PASS: documentation for {", ".join(INVENTORY)}; {len(changed)} managed sections updated; nothing staged.')
    else:
        source = 'index' if args.staged else 'working tree'
        print(f'PASS: documentation for {", ".join(INVENTORY)} matches the {source}; no files staged or changed.')


def entrypoint():
    def cancel(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, cancel)
    try:
        main()
    except KeyboardInterrupt:
        print('CANCELLED: stopped documentation commands and removed the temporary copy.', file=sys.stderr)
        return 130
    except subprocess.TimeoutExpired as error:
        print(f'FAIL: documentation command timed out after {error.timeout}s; check downloads or increase --timeout.', file=sys.stderr)
        return 1
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(entrypoint())
