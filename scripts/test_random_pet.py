#!/usr/bin/env python3
"""Run this template's complete Random module suite in an isolated directory."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "child-modules/random-pet"
TEST_FILE = "tests/random_pet.tftest.hcl"
RUNS = {
    "defaults", "custom_inputs", "minimum_length", "zero_length",
    "negative_length", "generated_output",
}


def check_results(output, tool):
    """Both CLIs emit final status events; Terraform also emits progress events."""
    versions = []
    runs = []
    summaries = []
    files = []
    for line in output.splitlines():
        event = json.loads(line)
        if event.get("@level") == "error":
            raise ValueError("The test command reported an error diagnostic.")
        if event.get("type") == "version":
            versions.append(event)
        if event.get("type") == "test_run":
            run = event["test_run"]
            if "status" in run:
                if run["path"] != TEST_FILE or run["status"] != "pass":
                    raise ValueError(f"Unexpected or unsuccessful run: {run}")
                runs.append(run["run"])
        elif event.get("type") == "test_file" and "status" in event["test_file"]:
            files.append(event["test_file"])
        elif event.get("type") == "test_summary":
            summaries.append(event["test_summary"])
    if len(versions) != 1 or tool not in versions[0]:
        raise ValueError(f"Expected test output from {tool}, not another executable.")
    if len(runs) != len(RUNS) or set(runs) != RUNS:
        raise ValueError(f"Expected all six named runs exactly once; received {runs}.")
    if len(files) != 1 or files[0]["path"] != TEST_FILE or files[0]["status"] != "pass":
        raise ValueError("Expected one successfully completed test file.")
    if len(summaries) != 1 or summaries[0] != {
        "status": "pass", "passed": 6, "failed": 0, "errored": 0, "skipped": 0,
    }:
        raise ValueError(f"Incomplete or unsuccessful test summary: {summaries}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tool", choices=("terraform", "tofu"))
    parser.add_argument("--binary", help="Executable path, e.g. from aqua which terraform")
    args = parser.parse_args()
    if args.binary is not None and not args.binary.strip():
        raise ValueError("The explicit binary path is empty; check aqua which first.")
    binary = shutil.which(args.binary if args.binary is not None else args.tool)
    if not binary:
        raise ValueError(f"Cannot find {args.binary or args.tool}; install the Aqua tools first.")
    binary = str(Path(binary).absolute())
    if not (MODULE / TEST_FILE).is_file():
        raise ValueError(f"Missing required test file: {TEST_FILE}")
    # Variable files silently replace the module defaults we intend to test.
    if any(MODULE.glob("*.tfvars")) or any(MODULE.glob("*.tfvars.json")):
        raise ValueError("Remove module variable files before testing the defaults.")
    with tempfile.TemporaryDirectory(prefix=f"random-pet-{args.tool}-") as directory:
        work = Path(directory) / "module"
        shutil.copytree(MODULE, work, ignore=shutil.ignore_patterns(
            ".terraform", ".terraform.lock.hcl", "*.tfstate*",
        ))
        shutil.copyfile(MODULE / f"tests/locks/{args.tool}.lock.hcl", work / ".terraform.lock.hcl")
        # Ignore local variable/CLI overrides, workspaces, and provider dev overrides.
        env = {k: v for k, v in os.environ.items() if not k.startswith(("TF_", "TOFU_"))}
        config = Path(directory) / "cli.tfrc"
        config.write_text("")
        env.update(TF_IN_AUTOMATION="1", TF_INPUT="0", TF_CLI_CONFIG_FILE=str(config))

        def run(*command):
            print(f"+ {args.tool} {' '.join(command)}", flush=True)
            result = subprocess.run(
                [binary, *command], cwd=work, env=env, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=240,
            )
            print(result.stdout, end="", flush=True)
            print(result.stderr, end="", file=sys.stderr, flush=True)
            if result.returncode:
                raise subprocess.CalledProcessError(result.returncode, command)
            return result.stdout

        run("version")
        run("init", "-backend=false", "-input=false", "-lockfile=readonly", "-no-color")
        run("validate", "-no-color")
        check_results(run("test", "-json"), args.tool)
    print(f"PASS: {args.tool}: all six runs passed; temporary directory removed.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        print(f"FAIL: command exited {error.returncode}: {error.cmd}", file=sys.stderr)
        sys.exit(error.returncode if error.returncode > 0 else 1)
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
