"""Guard the checker with captured Terraform 1.13.3 / OpenTofu 1.12.6 events."""

import copy
from contextlib import nullcontext
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
import unittest

from test_random_pet import check_results


class RunnerContract(unittest.TestCase):
    def test_native_streams_and_adoption(self):
        for tool in ("terraform", "tofu"):
            original = json.loads((Path(__file__).parent / f"fixtures/{tool}-test-events.json").read_text())

            def check(events):
                return check_results("\n".join(json.dumps(e) for e in events), tool)

            with self.subTest(tool=tool, case="captured success"):
                self.assertEqual(check(original), 6)
            added = copy.deepcopy(original)
            next(e["test_abstract"] for e in added if e["type"] == "test_abstract")["tests/extra.tftest.hcl"] = ["new_case"]
            added.extend([
                {"type": "test_run", "test_run": {"path": "tests/extra.tftest.hcl", "run": "new_case", "status": "pass"}},
                {"type": "test_file", "test_file": {"path": "tests/extra.tftest.hcl", "status": "pass"}},
            ])
            next(e["test_summary"] for e in added if e["type"] == "test_summary")["passed"] = 7
            with self.subTest(tool=tool, case="additional passing test"):
                self.assertEqual(check(added), 7)
            for attack in ("missing run", "duplicate run", "skip", "truncated", "error after success", "wrong tool", "undisclosed missing run"):
                events = copy.deepcopy(original)
                final = next(e for e in events if e["type"] == "test_run" and e["test_run"].get("status") == "pass")
                if attack == "missing run":
                    events.remove(final)
                elif attack == "duplicate run":
                    events.append(final)
                elif attack == "skip":
                    final["test_run"]["status"] = "skip"
                elif attack == "truncated":
                    events = [e for e in events if e["type"] != "test_summary"]
                elif attack == "error after success":
                    events.append({"@level": "error", "type": "diagnostic"})
                elif attack == "wrong tool":
                    del next(e for e in events if e["type"] == "version")[tool]
                else:
                    next(e["test_abstract"] for e in events if e["type"] == "test_abstract")["tests/random_pet.tftest.hcl"].append("never_completed")
                with self.subTest(tool=tool, case=attack), self.assertRaises(ValueError):
                    check(events)


def assert_stopped(test, pid):
    """Allow reaping delay; a Linux zombie is terminated, not a running child."""
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        stat = Path(f"/proc/{pid}/stat")
        try:
            if stat.read_text().split()[2] == "Z":
                return
        except FileNotFoundError:
            pass
        time.sleep(0.02)
    test.fail(f"Process {pid} survived cleanup")


@unittest.skipUnless(os.name == "posix", "POSIX process-group regression")
class AquaLookupCleanup(unittest.TestCase):
    def exercise_lookup(self, mode):
        """Own both Aqua's group and the runner even when a test assertion fails."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            probe, aqua_probe = root / "child.pid", root / "aqua.pid"
            aqua = root / "aqua"
            aqua.write_text("#!" + sys.executable + "\n" + '''import os, subprocess, sys, time
from pathlib import Path
Path(os.environ["TASK_AQUA_PROBE_FILE"]).write_text(str(os.getpid()))
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
Path(os.environ["TASK_PROBE_FILE"]).write_text(str(child.pid))
time.sleep(60)
''')
            aqua.chmod(0o755)
            runner = Path(__file__).parent / "test_random_pet.py"
            process = subprocess.Popen(
                [sys.executable, str(runner), "terraform", "--timeout", "1" if mode == "timeout" else "30"],
                env={**os.environ, "PATH": directory + os.pathsep + os.environ.get("PATH", ""),
                     "TASK_PROBE_FILE": str(probe), "TASK_AQUA_PROBE_FILE": str(aqua_probe)},
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            expected = self.assertRaisesRegex(AssertionError, "intentional setup failure") if mode == "early failure" else nullcontext()
            with expected:
                try:
                    deadline = time.monotonic() + 5
                    while not probe.exists() and time.monotonic() < deadline:
                        time.sleep(0.02)
                    self.assertTrue(probe.exists(), "Aqua stand-in did not start")
                    if mode == "early failure":
                        self.fail("intentional setup failure before communicate")
                    if mode == "interrupt":
                        process.send_signal(signal.SIGINT)
                    _, stderr = process.communicate(timeout=10)
                    self.assertEqual(process.returncode, 130 if mode == "interrupt" else 1, stderr)
                    assert_stopped(self, int(probe.read_text()))
                finally:
                    if process.poll() is None:
                        process.kill()
                    # Aqua owns a different session and may retain the captured
                    # pipes when setup fails before the runner can clean it up.
                    if aqua_probe.exists():
                        try:
                            os.killpg(int(aqua_probe.read_text()), signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    if probe.exists():
                        try:
                            os.kill(int(probe.read_text()), signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    process.communicate(timeout=5)
            for marker in (probe, aqua_probe):
                if marker.exists():
                    assert_stopped(self, int(marker.read_text()))

    def test_default_lookup_cleans_children(self):
        for mode in ("timeout", "interrupt"):
            with self.subTest(mode=mode):
                self.exercise_lookup(mode)

    def test_failed_setup_does_not_mask_assertion_or_leave_aqua(self):
        self.exercise_lookup("early failure")


@unittest.skipUnless(os.name == "posix", "POSIX process-group regression")
class SuccessfulCommandCleanup(unittest.TestCase):
    def test_success_stops_descendant_that_closed_captured_pipes(self):
        """A successful parent must not leave a detached helper running."""
        from module_checks import run_process
        command = [sys.executable, "-c", '''import subprocess, sys
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print(child.pid)
''']
        result = run_process(command, cwd=Path(__file__).parent, env=os.environ.copy(), timeout=5)
        self.assertEqual(result.returncode, 0)
        pid = int(result.stdout.strip())
        try:
            assert_stopped(self, pid)
        finally:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
