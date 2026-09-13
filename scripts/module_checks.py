#!/usr/bin/env python3
"""Shared native-result validation and subprocess cleanup."""

import json
import os
import signal
import subprocess
import sys

TEST_FILE = "tests/random_pet.tftest.hcl"
RUNS = {
    "defaults", "custom_inputs", "minimum_length", "zero_length",
    "negative_length", "generated_output",
}


def check_results(output, tool, required=None):
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
    if any(not names for names in manifests[0].values()):
        raise ValueError("Discovered an empty test file.")
    discovered = [(path, name) for path, names in manifests[0].items() for name in names]
    if required is None:
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
    stop(force=True)  # Do not leave detached descendants after a successful parent exit.
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
