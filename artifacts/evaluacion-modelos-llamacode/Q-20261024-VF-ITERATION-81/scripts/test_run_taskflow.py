#!/usr/bin/env python3
"""CPU-only regressions for Q81's TaskFlow timeout and cancellation path."""
import importlib.util
import pathlib
import unittest
from unittest.mock import Mock, patch


SCRIPT = pathlib.Path(__file__).with_name("run_taskflow.py")
SPEC = importlib.util.spec_from_file_location("q81_run_taskflow", SCRIPT)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class TaskFlowTimeoutTests(unittest.TestCase):
    def test_profile_fingerprint_gate_requires_exact_match(self):
        coverage = [
            {"profileId": "off", "profileConfigFingerprint": "off-sha"},
            {"profileId": "on", "profileConfigFingerprint": "on-sha"},
        ]
        self.assertTrue(runner.profile_fingerprint_matches(coverage, "on", "on-sha"))
        self.assertFalse(runner.profile_fingerprint_matches(coverage, "on", "off-sha"))
        self.assertFalse(runner.profile_fingerprint_matches(coverage, "missing", "off-sha"))

    def test_max_wait_invokes_cancel_and_confirms_finalization(self):
        recorder = Mock()
        with patch.object(runner, "invoke", return_value={"ok": True}) as invoke, \
                patch.object(runner, "prop", return_value=False), \
                patch.object(runner.time, "monotonic", side_effect=[0, 0, 0, 0.1]):
            result = runner.wait_for_benchmark("http://127.0.0.1", 0, 1, 1, recorder)

        self.assertEqual(result, {"runner_timed_out": True, "cancel_confirmed": True})
        invoke.assert_called_once_with("http://127.0.0.1", "cancelBenchmark", [])
        self.assertTrue(any(call.args[0] == "benchmark_max_wait_reached"
                            for call in recorder.call_args_list))
        self.assertTrue(any(call.args[0] == "benchmark_cancel_finalized"
                            and call.kwargs["confirmed"] is True
                            for call in recorder.call_args_list))

    def test_unconfirmed_cancel_is_bounded_and_reported(self):
        recorder = Mock()
        with patch.object(runner, "invoke", return_value={"ok": True}) as invoke, \
                patch.object(runner, "prop", return_value=True), \
                patch.object(runner.time, "monotonic", side_effect=[0, 0, 0, 0, 1]), \
                patch.object(runner.time, "sleep") as sleep:
            result = runner.wait_for_benchmark("http://127.0.0.1", 0, 1, 1, recorder)

        self.assertEqual(result, {"runner_timed_out": True, "cancel_confirmed": False})
        invoke.assert_called_once_with("http://127.0.0.1", "cancelBenchmark", [])
        sleep.assert_called_once_with(1)
        self.assertTrue(any(call.args[0] == "benchmark_cancel_finalized"
                            and call.kwargs["confirmed"] is False
                            for call in recorder.call_args_list))


if __name__ == "__main__":
    unittest.main()
