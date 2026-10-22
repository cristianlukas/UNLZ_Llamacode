#!/usr/bin/env python3
"""Regression checks for the Q35 pre-OOMd pressure guard."""
import importlib.util
import pathlib
import unittest
from unittest.mock import patch
import resource_isolation

RUNNER = pathlib.Path(__file__).with_name("run_context_holdout.py")
spec = importlib.util.spec_from_file_location("q35_runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
SUPERVISOR = pathlib.Path(__file__).with_name("run_all_context_holdout.py")
supervisor_spec = importlib.util.spec_from_file_location("q35_supervisor", SUPERVISOR)
supervisor = importlib.util.module_from_spec(supervisor_spec)
supervisor_spec.loader.exec_module(supervisor)


def sample_state(manager_some=0.0, manager_full=0.0, run_some=0.0, run_full=0.0):
    return {
        "process_cgroup": "/user.slice/user-1000.slice/user@1000.service/background.slice/llamacode-q35-context-test.service",
        "run": {"path": "/test/run", "memory_current_bytes": 0, "memory_max_bytes": "max",
                "psi": {"some": {"avg10": run_some}, "full": {"avg10": run_full}}},
        "user_manager": {"path": "/test/user", "memory_current_bytes": 0, "memory_max_bytes": "max",
                         "psi": {"some": {"avg10": manager_some}, "full": {"avg10": manager_full}}},
    }


def memory_state():
    return {
        "memory": {"MemAvailable": 100 * runner.GIB, "SwapFree": 8 * runner.GIB},
        "vmstat_pages": {"pswpin": 0, "pswpout": 0},
        "psi": {"some": {"avg10": 0.0}, "full": {"avg10": 0.0}},
    }


class PressureMonitorTests(unittest.TestCase):
    def collect(self, cgroup, samples=5):
        monitor = runner.Monitor()
        with patch.object(runner, "system_memory", return_value=memory_state()), \
             patch.object(runner, "cgroup_memory_state", return_value=cgroup), \
             patch.object(runner, "gpu_snapshot", return_value=[]):
            for _ in range(samples):
                monitor.sample()
        return monitor

    def test_user_manager_gate_precedes_oomd_threshold(self):
        below = self.collect(sample_state(manager_some=34.9))
        self.assertIsNone(below.abort_reason)
        at_gate = self.collect(sample_state(manager_some=35.0))
        self.assertIn("35% guard", at_gate.abort_reason)

    def test_run_cgroup_gate_is_isolated(self):
        monitor = self.collect(sample_state(run_some=80.0), samples=15)
        self.assertIn("run-cgroup memory PSI", monitor.abort_reason)

    def test_normal_pressure_does_not_abort(self):
        monitor = self.collect(sample_state(manager_some=12.0, run_some=10.0))
        self.assertIsNone(monitor.abort_reason)

    def test_pre_request_receipt_does_not_mark_fixture_complete(self):
        row = {
            "run_directory": "/run/131072/2026101", "receipt": "/run/receipt.json",
            "request_sent": False, "classification": "invalid infrastructure", "return_code": 2,
        }
        self.assertFalse(supervisor.has_valid_result(row, "/run/131072/2026101"))

    def test_valid_quality_receipt_marks_fixture_complete(self):
        row = {
            "run_directory": "/run/131072/2026101", "receipt": "/run/receipt.json",
            "request_sent": True, "classification": "valid quality", "return_code": 0,
        }
        self.assertTrue(supervisor.has_valid_result(row, "/run/131072/2026101"))

    def test_missing_response_keeps_quality_metrics_null(self):
        score = runner.score_response(None, {"answer": "known"}, None, [])
        self.assertEqual(score, {
            "exact_matches": None,
            "correct": None,
            "total": None,
            "strict_output_valid": None,
            "quality_score": None,
        })

    def test_received_response_scores_exact_match(self):
        score = runner.score_response(
            {"choices": []}, {"answer": "known"}, {"answer": "known"}, []
        )
        self.assertEqual(score["exact_matches"], {"answer": True})
        self.assertEqual(score["correct"], 1)
        self.assertEqual(score["total"], 1)
        self.assertTrue(score["strict_output_valid"])
        self.assertEqual(score["quality_score"]["percent"], 100.0)


class ResourceIsolationTests(unittest.TestCase):
    def test_worker_budget_keeps_host_headroom_without_changing_model_settings(self):
        meminfo = "MemTotal: 131072000 kB\nMemAvailable: 115343360 kB\nSwapFree: 6000000 kB\n"
        limits = resource_isolation.calculate_worker_limits(meminfo)
        self.assertEqual(limits["memory_max_bytes"], 94 * resource_isolation.GIB)
        self.assertEqual(limits["memory_high_bytes"], 86 * resource_isolation.GIB)
        self.assertEqual(limits["memory_swap_max_bytes"], 4 * resource_isolation.GIB)
        self.assertEqual(limits["oom_score_adjust"], 900)
        self.assertEqual(limits["oom_policy"], "kill")

    def test_insufficient_safe_budget_blocks_before_inference(self):
        meminfo = "MemTotal: 131072000 kB\nMemAvailable: 70000000 kB\nSwapFree: 6000000 kB\n"
        with self.assertRaisesRegex(RuntimeError, "before model startup"):
            resource_isolation.calculate_worker_limits(meminfo)

    def test_systemd_unit_is_hard_limited_and_group_killed(self):
        limits = resource_isolation.calculate_worker_limits(
            "MemTotal: 131072000 kB\nMemAvailable: 115343360 kB\nSwapFree: 6000000 kB\n"
        )
        props = resource_isolation.systemd_properties(limits)
        self.assertIn(f"--property=MemoryMax={limits['memory_max_bytes']}", props)
        self.assertIn("--property=OOMScoreAdjust=900", props)
        self.assertIn("--property=OOMPolicy=kill", props)
        self.assertIn("--property=KillMode=control-group", props)
        self.assertIn("--property=ManagedOOMMemoryPressure=kill", props)


if __name__ == "__main__":
    unittest.main()
