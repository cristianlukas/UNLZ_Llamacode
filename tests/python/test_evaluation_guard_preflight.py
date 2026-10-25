#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools import evaluation_guard_preflight as preflight


Q117_SCRIPTS = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-117/scripts"
Q117_RUNNER = Q117_SCRIPTS / "run_context_holdout_attempt05.py"
Q117_GUARD = Q117_SCRIPTS / "q117_pressure_guard_attempt05.py"
Q97_SCRIPTS = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-97/scripts"
Q97_RUNNER = Q97_SCRIPTS / "q97_supervised_bcb.py"
Q97_GUARD = Q97_RUNNER
Q117_RUNNER_SHA = "24435c412cc791d47687199fb7ab765c7a52aed6b189ac4598eea8dd9d8822b1"
Q117_GUARD_SHA = "b4d42302e7d405abd5c59df5aa86bb7de6ef3bb91aef487b49acbebd1d24270e"


class EvaluationGuardPreflightTests(unittest.TestCase):
    def test_exact_q117_runner_and_amd05_guard_pass_preflight(self):
        result = preflight.verify_selection(
            Q117_RUNNER, Q117_GUARD, Q117_RUNNER_SHA, Q117_GUARD_SHA
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["guardModule"], "q117_pressure_guard_attempt05")
        self.assertEqual(Path(result["preimportedFrom"]), Q117_GUARD.resolve())
        self.assertTrue(result["monitorStartsBeforeServer"])

    def test_changed_runner_hash_is_rejected(self):
        with self.assertRaisesRegex(preflight.GuardSelectionError, "runner SHA-256 mismatch"):
            preflight.verify_selection(Q117_RUNNER, Q117_GUARD, "0" * 64, Q117_GUARD_SHA)

    def test_changed_guard_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            tmp = Path(temp)
            runner = tmp / Q117_RUNNER.name
            guard = tmp / Q117_GUARD.name
            runner.write_bytes(Q117_RUNNER.read_bytes())
            guard.write_bytes(Q117_GUARD.read_bytes() + b"\n# changed\n")
            altered_hash = hashlib.sha256(guard.read_bytes()).hexdigest()
            with self.assertRaisesRegex(preflight.GuardSelectionError, "not on the approved"):
                preflight.verify_selection(runner, guard, Q117_RUNNER_SHA, altered_hash)

    def test_legacy_q97_runner_and_guard_are_rejected(self):
        with self.assertRaises(preflight.GuardSelectionError):
            preflight.verify_selection(
                Q97_RUNNER, Q97_GUARD,
                preflight.sha256_file(Q97_RUNNER), preflight.sha256_file(Q97_GUARD)
            )

    def test_runner_without_pinned_import_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            tmp = Path(temp)
            runner = tmp / "runner.py"
            guard = tmp / Q117_GUARD.name
            runner.write_text(
                "import subprocess\nclass Monitor:\n def start(self): pass\n"
                "def main():\n monitor=Monitor(); monitor.start(); subprocess.Popen(['true'])\n",
                encoding="utf-8",
            )
            guard.write_bytes(Q117_GUARD.read_bytes())
            runner_hash = preflight.sha256_file(runner)
            with self.assertRaisesRegex(preflight.GuardSelectionError, "does not import"):
                preflight.verify_selection(runner, guard, runner_hash, Q117_GUARD_SHA)

    def test_runner_starting_server_before_monitor_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            tmp = Path(temp)
            runner = tmp / "runner.py"
            guard = tmp / Q117_GUARD.name
            runner.write_text(
                "from q117_pressure_guard_attempt05 import evaluate\nimport subprocess\n"
                "class Monitor:\n def start(self): pass\n"
                "def main():\n monitor=Monitor(); subprocess.Popen(['true']); monitor.start()\n",
                encoding="utf-8",
            )
            guard.write_bytes(Q117_GUARD.read_bytes())
            with self.assertRaisesRegex(preflight.GuardSelectionError, "monitor before"):
                preflight.verify_selection(
                    runner, guard, preflight.sha256_file(runner), Q117_GUARD_SHA
                )

    def test_invalid_guard_blocks_runner_launch(self):
        with patch.object(preflight.subprocess, "run") as run:
            with self.assertRaises(preflight.GuardSelectionError):
                preflight.run_guarded(
                    Q117_RUNNER, Q117_GUARD, "0" * 64, Q117_GUARD_SHA
                )
            run.assert_not_called()

    def test_valid_selection_dispatches_only_the_pinned_runner(self):
        completed = preflight.subprocess.CompletedProcess([], 0)
        with patch.object(preflight.subprocess, "run", return_value=completed) as run:
            result = preflight.run_guarded(
                Q117_RUNNER, Q117_GUARD, Q117_RUNNER_SHA, Q117_GUARD_SHA,
                runner_args=["--fixture-only"],
            )
        self.assertEqual(result, 0)
        run.assert_called_once_with(
            [sys.executable, str(Q117_RUNNER.resolve()), "--fixture-only"],
            cwd=str(Q117_RUNNER.resolve().parent), check=False,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
