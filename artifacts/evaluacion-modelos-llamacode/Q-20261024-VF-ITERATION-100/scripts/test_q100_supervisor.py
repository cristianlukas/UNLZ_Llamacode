#!/usr/bin/env python3
"""CPU-only regression tests for Q100 supervision decisions."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location(
    "q100_supervised_fanout", SCRIPT_DIR / "q100_supervised_fanout.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load Q100 supervisor")
SUPERVISOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUPERVISOR)


class Q100SupervisorTests(unittest.TestCase):
    def test_missing_result_is_not_a_quality_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(SUPERVISOR.first_quality_failure(Path(tmp) / "missing.json"))

    def test_incomplete_run_is_not_treated_as_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp) / "result.json"
            result.write_text(json.dumps({"runs": [{"started": True, "seed": 5051}]}))
            self.assertIsNone(SUPERVISOR.first_quality_failure(result))

    def test_first_completed_quality_failure_is_returned(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp) / "result.json"
            result.write_text(json.dumps({"runs": [
                {"started": True, "seed": 5051, "policy": "serial", "qualityPassed": False,
                 "acceptedTasks": 0, "taskCards": []}
            ]}))
            failure = SUPERVISOR.first_quality_failure(result)
            self.assertEqual(failure, {"seed": 5051, "policy": "serial",
                                       "acceptedTasks": 0, "taskCards": [], "error": None})

    def test_fixture_error_also_stops_unreachable_screen(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp) / "result.json"
            result.write_text(json.dumps({"runs": [
                {"started": True, "seed": 5051, "policy": "serial",
                 "error": "fixture write failed", "acceptedTasks": 0}
            ]}))
            failure = SUPERVISOR.first_quality_failure(result)
            self.assertEqual(failure, {"seed": 5051, "policy": "serial",
                                       "acceptedTasks": 0, "taskCards": None,
                                       "error": "fixture write failed"})

    def test_nested_temp_project_gets_its_own_git_worktree(self):
        with tempfile.TemporaryDirectory(dir=SUPERVISOR.TASK / "runs") as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            marker = project / "marker-alpha.txt"
            marker.write_text("Q100_FIXTURE_MARKER\n")
            env = SUPERVISOR.isolated_git_environment()
            self.assertEqual(env["GIT_CEILING_DIRECTORIES"], str(SUPERVISOR.ROOT.resolve()))

            parent_repo_probe = subprocess.run(
                ["git", "-C", str(project), "rev-parse", "--is-inside-work-tree"],
                env=env, capture_output=True, text=True)
            self.assertNotEqual(parent_repo_probe.returncode, 0)
            subprocess.run(["git", "-C", str(project), "init", "-q"], env=env, check=True)
            subprocess.run(["git", "-C", str(project), "add", "-A"], env=env, check=True)
            subprocess.run(["git", "-C", str(project), "-c", "user.email=q100@test",
                            "-c", "user.name=Q100", "commit", "-qm", "fixture"],
                           env=env, check=True)

            worktree = Path(tmp) / "llamacode-worktrees" / "call-fixture"
            subprocess.run(["git", "-C", str(project), "worktree", "add", "-qb",
                            "q100-fixture-test", str(worktree), "HEAD"], env=env, check=True)
            self.assertEqual((worktree / marker.name).read_text(), "Q100_FIXTURE_MARKER\n")
            subprocess.run(["git", "-C", str(project), "worktree", "remove", "--force",
                            str(worktree)], env=env, check=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
