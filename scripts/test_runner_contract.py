"""Guard the checker with captured Terraform 1.13.3 / OpenTofu 1.12.6 events."""

import copy
import json
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
