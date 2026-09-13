#!/usr/bin/env python3
"""Validate and test the explicitly registered Random examples without checkout state."""

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

from example_policy import INVENTORY, inspect_tree, stage
from module_checks import check_results, run_process

ROOT = Path(__file__).resolve().parents[1]


def tool_policy(root):
    """Keep duplicate pins bounded; native init still checks module constraints."""
    pins = []
    for config in (root / "aqua.yaml", root / "scripts/aqua.yaml"):
        text = config.read_text()
        pins.append({name: re.findall(pattern, text) for name, pattern in {
            "terraform": r"hashicorp/terraform@v([\d.]+)",
            "tofu": r"opentofu/opentofu@v([\d.]+)",
            "registry": r"ref: (v[\d.]+)",
        }.items()})
    if pins[0] != pins[1] or any(len(v) != 1 for v in pins[0].values()):
        raise ValueError("Align the engine and registry pins in aqua.yaml and scripts/aqua.yaml.")
    tofu = re.findall(r"- tofu@([\d.]+)", (root / ".trunk/trunk.yaml").read_text())
    if tofu != pins[0]["tofu"]:
        raise ValueError("Align Trunk's tofu pin with both Aqua configurations.")
    return {tool: pins[0][tool][0] for tool in ("terraform", "tofu")}


def main(default_module=None):
    """Execute the complete selected inventory with an isolated copy per fixture."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tool", choices=("terraform", "tofu"))
    parser.add_argument("--module", choices=tuple(INVENTORY), default=default_module)
    parser.add_argument("--validate-only", action="store_true", help="Init/validate both examples without apply")
    parser.add_argument("--binary", help="Explicit executable path; must match the configured engine/version")
    parser.add_argument("--timeout", type=int, default=240, help="Seconds per command, including Aqua (default: 240)")
    parser.add_argument("--verbose", action="store_true", help="Print raw machine-readable test events")
    args = parser.parse_args()
    if args.timeout <= 0:
        raise ValueError("--timeout must be a positive number of seconds.")
    selected = inspect_tree(ROOT)  # Fail unknown coverage/escapes before executing any tool.
    versions = tool_policy(ROOT)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("TF_", "TOFU_"))}
    if args.binary is None:
        if not shutil.which("aqua"):
            raise ValueError("Install Aqua, then run aqua install; or supply --binary /path/to/CLI.")
        lookup = run_process(["aqua", "-c", str(ROOT / "scripts/aqua.yaml"), "which", args.tool],
                             cwd=ROOT, env=env, timeout=args.timeout)
        print(lookup.stderr, end="", file=sys.stderr, flush=True)
        lookup.check_returncode()
        args.binary = lookup.stdout.strip()
    if not args.binary.strip():
        raise ValueError("The binary path is empty; check aqua which first.")
    binary = shutil.which(args.binary)
    if not binary:
        raise ValueError(f"Cannot find {args.binary}; install the Aqua tools first.")
    binary = str(Path(binary).absolute())
    modules = [args.module] if args.module else list(INVENTORY)
    completed = []
    for module in modules:
        fixtures = INVENTORY[module]["fixtures"]
        if args.validate_only:
            fixtures = {"validation": ("tests", None, set(), None)}
        for mode, (testdir, filename, required, varfile) in fixtures.items():
            label = f"{args.tool} {module} [{mode}]"
            with tempfile.TemporaryDirectory(prefix=f"example-check-{args.tool}-") as directory:
                work = stage(ROOT, Path(directory), selected, module, mode, args.tool)
                config = Path(directory) / "cli.tfrc"
                config.write_text("")
                native_env = {**env, "TF_IN_AUTOMATION": "1", "TF_INPUT": "0", "TF_CLI_CONFIG_FILE": str(config)}

                def run(*command):
                    print(f"+ {label}: {' '.join(command)}", flush=True)
                    result = run_process([binary, *command], cwd=work, env=native_env, timeout=args.timeout)
                    if command[0] == "test" and not args.verbose:
                        for line in result.stdout.splitlines():
                            try:
                                event = json.loads(line)
                                print(event.get("@message", ""), flush=True)
                                detail = event.get("diagnostic", {}).get("detail")
                                if detail:
                                    print(detail, flush=True)
                            except (ValueError, AttributeError):
                                print(line, flush=True)
                    else:
                        print(result.stdout, end="", flush=True)
                    print(result.stderr, end="", file=sys.stderr, flush=True)
                    result.check_returncode()
                    return result.stdout

                version_lines = run("version").splitlines()
                if not version_lines:
                    raise ValueError("The executable returned no engine version output.")
                version = version_lines[0]
                expected_version = f"{'Terraform' if args.tool == 'terraform' else 'OpenTofu'} v{versions[args.tool]}"
                if version != expected_version:
                    raise ValueError(f"Expected {expected_version}; got {version}.")
                run("init", "-backend=false", "-input=false", "-lockfile=readonly", "-no-color")
                run("validate", "-no-color")
                count = 0
                if not args.validate_only:
                    command = ["test", "-json", f"-test-directory={testdir}"]
                    if varfile:
                        command.append(f"-var-file={varfile}")
                    count = check_results(run(*command), args.tool, {(f"{testdir}/{filename}", name) for name in required})
                completed.append((module, mode))
                print(f"PASS: {label}: validated; {count} runs passed; temporary directory removed on fixture exit.", flush=True)
    expected = [(module, mode) for module in modules for mode in
                (["validation"] if args.validate_only else INVENTORY[module]["fixtures"])]
    if completed != expected:
        raise ValueError(f"Incomplete fixture execution: {completed}; expected {expected}.")
    print(f"PASS: {args.tool}: all {len(completed)} module/fixture invocations completed; temporary directories removed.")


def entrypoint(default_module=None):
    """Preserve useful CLI exits and clean cancellation for both entry points."""
    def cancel(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, cancel)
    try:
        main(default_module)
    except KeyboardInterrupt:
        print("CANCELLED: stopped the command and removed the temporary directory.", file=sys.stderr)
        sys.exit(130)
    except subprocess.TimeoutExpired as error:
        print(f"FAIL: command timed out after {error.timeout}s. Check registry connectivity or increase --timeout.", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as error:
        print(f"FAIL: command exited {error.returncode}: {error.cmd}", file=sys.stderr)
        sys.exit(error.returncode if error.returncode > 0 else 1)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    entrypoint()
