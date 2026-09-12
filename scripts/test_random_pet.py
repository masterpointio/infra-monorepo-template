#!/usr/bin/env python3
"""Run this template's complete Random module suite in an isolated directory."""

import argparse
import json
import os
import signal
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
    """Require the original coverage and every discovered run, including added tests."""
    versions, summaries, manifests, files, runs = [], [], [], [], []
    for line in output.splitlines():
        event = json.loads(line)
        if event.get("@level") == "error":
            raise ValueError("The test command reported an error diagnostic.")
        kind = event.get("type")
        if kind == "version":
            versions.append(event)
        elif kind == "test_abstract":
            manifests.append(event["test_abstract"])
        elif kind == "test_run" and "status" in event["test_run"]:
            run = event["test_run"]
            if run["status"] != "pass":
                raise ValueError(f"Unsuccessful run: {run}")
            runs.append((run["path"], run["run"]))
        elif kind == "test_file" and "status" in event["test_file"]:
            file = event["test_file"]
            if file["status"] != "pass":
                raise ValueError(f"Unsuccessful test file: {file}")
            files.append(file["path"])
        elif kind == "test_summary":
            summaries.append(event["test_summary"])
    if len(versions) != 1 or tool not in versions[0]:
        raise ValueError(f"Expected test output from {tool}, not another executable.")
    if len(manifests) != 1:
        raise ValueError("Missing or duplicated test discovery event.")
    discovered = [(path, name) for path, names in manifests[0].items() for name in names]
    required = {(TEST_FILE, name) for name in RUNS}
    if not required.issubset(runs):
        raise ValueError(f"Missing required coverage: {sorted(required - set(runs))}")
    if len(runs) != len(set(runs)) or sorted(runs) != sorted(discovered):
        raise ValueError("Not every discovered test completed exactly once.")
    if sorted(files) != sorted(manifests[0]):
        raise ValueError("Not every discovered test file completed exactly once.")
    expected = {"status": "pass", "passed": len(runs), "failed": 0, "errored": 0, "skipped": 0}
    if len(summaries) != 1 or any(summaries[0].get(k) != v for k, v in expected.items()):
        raise ValueError(f"Incomplete or unsuccessful test summary: {summaries}")
    return len(runs)


def run_process(command, *, cwd, env, timeout):
    """Capture a command; stop its whole process group on timeout or cancellation."""
    process = subprocess.Popen(
        command, cwd=cwd, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=(os.name == "posix"),
    )

    def stop(force=False):
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL if force else signal.SIGINT)
            elif force:
                process.kill()
            else:
                process.terminate()
        except ProcessLookupError:
            pass  # The command may have finished between timeout and cleanup.

    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        stop()
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            stop(force=True)
            stdout, stderr = process.communicate()
        finally:
            # A descendant can outlive its parent even after closing its pipes.
            stop(force=True)
        print(stdout, end="", flush=True)
        print(stderr, end="", file=sys.stderr, flush=True)
        raise
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tool", choices=("terraform", "tofu"))
    parser.add_argument("--binary", help="Executable path, e.g. from aqua which terraform")
    parser.add_argument("--timeout", type=int, default=240, help="Seconds per native command (default: 240)")
    parser.add_argument("--verbose", action="store_true", help="Print raw machine-readable test output")
    args = parser.parse_args()
    if args.timeout <= 0:
        raise ValueError("--timeout must be a positive number of seconds.")
    if args.binary is None:
        if not shutil.which("aqua"):
            raise ValueError("Install Aqua, then run aqua -c scripts/aqua.yaml install; or supply --binary /path/to/CLI.")
        lookup = run_process(
            ["aqua", "-c", str(ROOT / "scripts/aqua.yaml"), "which", args.tool],
            cwd=ROOT, env=os.environ.copy(), timeout=args.timeout,
        )
        print(lookup.stderr, end="", file=sys.stderr, flush=True)
        lookup.check_returncode()
        args.binary = lookup.stdout.strip()
    if args.binary is not None and not args.binary.strip():
        raise ValueError("The explicit binary path is empty; check aqua which first.")
    binary = shutil.which(args.binary if args.binary is not None else args.tool)
    if not binary:
        raise ValueError(f"Cannot find {args.binary or args.tool}; install the Aqua tools first.")
    binary = str(Path(binary).absolute())
    if not (MODULE / TEST_FILE).is_file():
        raise ValueError(f"Missing required test file: {TEST_FILE}")
    # Variable files silently replace the module defaults we intend to test.
    autoloaded = ("terraform.tfvars", "terraform.tfvars.json", "*.auto.tfvars", "*.auto.tfvars.json")
    if any(list(MODULE.glob(pattern)) for pattern in autoloaded):
        raise ValueError("Move auto-loaded variable files out of this child module before testing defaults. Named example .tfvars files are fine.")
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
            result = run_process([binary, *command], cwd=work, env=env, timeout=args.timeout)
            stdout, stderr = result.stdout, result.stderr
            if command[0] == "test" and not args.verbose:
                for line in stdout.splitlines():
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        print(line, flush=True)
                        continue
                    if event.get("@message"):
                        print(event["@message"], flush=True)
                    diagnostic = event.get("diagnostic", {})
                    if diagnostic.get("detail"):
                        print(diagnostic["detail"], flush=True)
            else:
                print(stdout, end="", flush=True)
            print(stderr, end="", file=sys.stderr, flush=True)
            result.check_returncode()
            return stdout

        run("version")
        run("init", "-backend=false", "-input=false", "-lockfile=readonly", "-no-color")
        run("validate", "-no-color")
        count = check_results(run("test", "-json"), args.tool)
    print(f"PASS: {args.tool}: {count} runs passed; temporary directory removed.")


if __name__ == "__main__":
    try:
        main()
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
