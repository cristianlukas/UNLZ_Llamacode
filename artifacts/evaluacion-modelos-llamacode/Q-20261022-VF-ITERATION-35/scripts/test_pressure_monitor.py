#!/usr/bin/env python3
"""Regression checks for the Q35 pre-OOMd pressure guard."""
import importlib.util
import hashlib
import json
import os
import pathlib
import socket
import subprocess
import tempfile
import time
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


def sample_state(manager_some=0.0, manager_full=0.0, run_some=0.0, run_full=0.0,
                 run_swap_bytes=0):
    return {
        "process_cgroup": "/user.slice/user-1000.slice/user@1000.service/background.slice/llamacode-q35-context-test.service",
        "run": {"path": "/test/run", "memory_current_bytes": 0,
                "memory_swap_current_bytes": run_swap_bytes, "memory_max_bytes": "max",
                "psi": {"some": {"avg10": run_some}, "full": {"avg10": run_full}}},
        "user_manager": {"path": "/test/user", "memory_current_bytes": 0,
                         "memory_swap_current_bytes": 0, "memory_max_bytes": "max",
                         "psi": {"some": {"avg10": manager_some}, "full": {"avg10": manager_full}}},
    }


def memory_state(available=100 * runner.GIB, pswpout=0, some=0.0, full=0.0):
    return {
        "memory": {"MemAvailable": available, "SwapFree": 8 * runner.GIB},
        "vmstat_pages": {"pswpin": 0, "pswpout": pswpout},
        "psi": {"some": {"avg10": some}, "full": {"avg10": full}},
    }


class PressureMonitorTests(unittest.TestCase):
    def collect(self, cgroup, samples=5, mem=None):
        monitor = runner.Monitor()
        with patch.object(runner, "system_memory", return_value=mem or memory_state()), \
             patch.object(runner, "cgroup_memory_state", return_value=cgroup), \
             patch.object(runner, "gpu_snapshot", return_value=[]):
            for _ in range(samples):
                monitor.sample()
        return monitor

    def test_user_manager_pressure_alone_does_not_abort_with_plenty_of_ram(self):
        monitor = self.collect(sample_state(manager_some=63.3), samples=20,
                               mem=memory_state(available=117 * runner.GIB))
        self.assertIsNone(monitor.abort_reason)

    def test_low_available_memory_still_aborts(self):
        monitor = self.collect(sample_state(), mem=memory_state(available=19 * runner.GIB))
        self.assertIn("below 20 GiB", monitor.abort_reason)

    def test_global_swap_out_is_telemetry_not_an_abort(self):
        monitor = runner.Monitor()
        with patch.object(runner, "system_memory", side_effect=[memory_state(), memory_state(pswpout=1025)]), \
             patch.object(runner, "cgroup_memory_state", return_value=sample_state()), \
             patch.object(runner, "gpu_snapshot", return_value=[]):
            monitor.sample()
            monitor.sample()
        self.assertIsNone(monitor.abort_reason)
        self.assertEqual(monitor.rows[-1]["swap_telemetry"]["host_pswpout_delta_pages"], 1025)
        self.assertEqual(monitor.rows[-1]["swap_telemetry"]["run_cgroup_memory_swap_delta_bytes"], 0)

    def test_run_cgroup_swap_out_still_aborts(self):
        monitor = runner.Monitor()
        with patch.object(runner, "system_memory", return_value=memory_state()), \
             patch.object(runner, "cgroup_memory_state", side_effect=[
                 sample_state(run_swap_bytes=0),
                 sample_state(run_swap_bytes=4 * 1024 * 1024 + 1),
             ]), \
             patch.object(runner, "gpu_snapshot", return_value=[]):
            monitor.sample()
            monitor.sample()
        self.assertIn("run-cgroup swap-out exceeded", monitor.abort_reason)
        self.assertEqual(
            monitor.rows[-1]["swap_telemetry"]["run_cgroup_memory_swap_delta_bytes"],
            4 * 1024 * 1024 + 1,
        )

    def test_run_cgroup_gate_is_isolated(self):
        monitor = self.collect(sample_state(run_some=80.0), samples=15)
        self.assertIn("run-cgroup memory PSI", monitor.abort_reason)

    def test_system_psi_gate_still_aborts(self):
        monitor = self.collect(sample_state(), samples=15,
                               mem=memory_state(some=80.0))
        self.assertIn("sustained memory PSI", monitor.abort_reason)

    def test_only_system_background_cgroup_is_accepted(self):
        self.assertTrue(runner.is_isolated_system_cgroup(
            "/background.slice/llamacode-q35-context-131072-seed-2026101-a01.service"
        ))
        self.assertFalse(runner.is_isolated_system_cgroup(
            "/user.slice/user-1000.slice/user@1000.service/background.slice/"
            "llamacode-q35-context-131072-seed-2026101-a01.service"
        ))

    def test_normal_pressure_does_not_abort(self):
        monitor = self.collect(sample_state(manager_some=12.0, run_some=10.0))
        self.assertIsNone(monitor.abort_reason)

    def test_monitor_lifecycle_has_start_and_stop(self):
        monitor = runner.Monitor()
        with patch.object(monitor, "sample") as sample, \
             patch.object(runner.threading, "Thread") as thread_class:
            thread = thread_class.return_value
            monitor.start()
            monitor.stop()
        self.assertEqual(sample.call_count, 2)
        thread.start.assert_called_once()
        thread.join.assert_called_once_with(timeout=3)

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
        self.assertTrue(supervisor.has_terminal_result(row, "/run/131072/2026101"))

    def test_complete_incomplete_response_is_terminal_without_retry(self):
        row = {
            "run_directory": "/run/131072/2026103", "receipt": "/run/receipt.json",
            "request_sent": True, "model_loaded": True, "http_status": 200,
            "response_present": True, "finish_reason": "length",
            "prompt_tokens": 125113, "minimum_prompt_tokens_95pct": 124519,
            "classification": "incomplete", "return_code": 2,
            "transport_error": None, "monitor_abort_reason": None,
        }
        self.assertTrue(supervisor.has_terminal_result(row, "/run/131072/2026103"))

    def test_incomplete_response_without_full_prompt_is_not_terminal(self):
        row = {
            "run_directory": "/run/131072/2026103", "receipt": "/run/receipt.json",
            "request_sent": True, "model_loaded": True, "http_status": 200,
            "response_present": True, "finish_reason": "length",
            "prompt_tokens": 100000, "minimum_prompt_tokens_95pct": 124519,
            "classification": "incomplete", "return_code": 2,
            "transport_error": None, "monitor_abort_reason": None,
        }
        self.assertFalse(supervisor.has_terminal_result(row, "/run/131072/2026103"))

    def test_pre_request_infrastructure_failure_is_not_terminal(self):
        row = {
            "run_directory": "/run/131072/2026103", "receipt": "/run/receipt.json",
            "request_sent": False, "model_loaded": False, "http_status": None,
            "response_present": False, "finish_reason": None,
            "prompt_tokens": None, "minimum_prompt_tokens_95pct": 124519,
            "classification": "incomplete", "return_code": 2,
            "transport_error": "port is occupied", "monitor_abort_reason": None,
        }
        self.assertFalse(supervisor.has_terminal_result(row, "/run/131072/2026103"))

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


class PortBindabilityTests(unittest.TestCase):
    def test_active_listener_still_blocks_the_task_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            port = listener.getsockname()[1]
            with self.assertRaisesRegex(RuntimeError, "already occupied"):
                runner.assert_port_bindable(port)

    @unittest.skipUnless(os.path.exists("/proc/net/tcp"), "Linux TCP state table required")
    def test_time_wait_from_completed_request_does_not_block_next_seed(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            port = listener.getsockname()[1]
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                client.connect(("127.0.0.1", port))
                conn, _ = listener.accept()
                conn.shutdown(socket.SHUT_WR)
                conn.close()
                self.assertEqual(client.recv(1), b"")
            listener.close()

        port_hex = f"{port:04X}"
        deadline = time.monotonic() + 2
        in_time_wait = False
        while time.monotonic() < deadline:
            for line in pathlib.Path("/proc/net/tcp").read_text().splitlines()[1:]:
                fields = line.split()
                if fields[1].rsplit(":", 1)[-1].upper() == port_hex and fields[3] == "06":
                    in_time_wait = True
                    break
            if in_time_wait:
                break
            time.sleep(0.02)
        if not in_time_wait:
            self.skipTest("kernel did not retain a TIME_WAIT socket for the fixture")

        # This matches the Linux Strata server, which sets SO_REUSEADDR.
        runner.assert_port_bindable(port)


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
        self.assertIn("--property=ManagedOOMMemoryPressureLimit=80%", props)


class SystemdLaunchTests(unittest.TestCase):
    def test_fixture_manifest_hashes_accept_exact_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture_dir = pathlib.Path(temp_dir)
            prompt = b"holdout fixture\n"
            expected = {"case-01": "approved"}
            expected_bytes = (json.dumps(expected, ensure_ascii=False, indent=2) + "\n").encode()
            (fixture_dir / "probe-prompt.txt").write_bytes(prompt)
            (fixture_dir / "probe-expected.json").write_bytes(expected_bytes)
            spec = {
                "fixture_dir": str(fixture_dir),
                "prompt_sha256": hashlib.sha256(prompt).hexdigest(),
                "expected_sha256": hashlib.sha256(
                    json.dumps(expected, ensure_ascii=False, sort_keys=True).encode()
                ).hexdigest(),
            }
            self.assertEqual(supervisor.verify_fixture_hashes(spec), {
                "prompt_sha256": spec["prompt_sha256"],
                "expected_sha256": spec["expected_sha256"],
            })

    def test_fixture_manifest_hashes_reject_changed_prompt_and_answer(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture_dir = pathlib.Path(temp_dir)
            expected = {"case-01": "approved"}
            prompt = b"holdout fixture\n"
            (fixture_dir / "probe-prompt.txt").write_bytes(prompt)
            (fixture_dir / "probe-expected.json").write_text(json.dumps(expected), encoding="utf-8")
            spec = {
                "fixture_dir": str(fixture_dir),
                "prompt_sha256": hashlib.sha256(prompt).hexdigest(),
                "expected_sha256": hashlib.sha256(
                    json.dumps(expected, ensure_ascii=False, sort_keys=True).encode()
                ).hexdigest(),
            }
            (fixture_dir / "probe-prompt.txt").write_bytes(b"changed prompt\n")
            with self.assertRaisesRegex(RuntimeError, "fixture prompt hash mismatch"):
                supervisor.verify_fixture_hashes(spec)
            (fixture_dir / "probe-prompt.txt").write_bytes(prompt)
            (fixture_dir / "probe-expected.json").write_text(
                json.dumps({"case-01": "changed"}), encoding="utf-8"
            )
            with self.assertRaisesRegex(RuntimeError, "fixture expected-answer hash mismatch"):
                supervisor.verify_fixture_hashes(spec)

    def test_resume_can_keep_batch_id_separate_from_queue_lock_id(self):
        with patch.dict(os.environ, {"LLAMACODE_TASK_ID": "Q-20261022-VF-ITERATION-37"}):
            self.assertEqual(supervisor.queue_lock_task_id(), "Q-20261022-VF-ITERATION-37")

    def test_inference_worker_uses_system_manager_outside_user_slice(self):
        calls = []

        def fake_run(command, **kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        limits = resource_isolation.calculate_worker_limits(
            "MemTotal: 131072000 kB\nMemAvailable: 115343360 kB\nSwapFree: 6000000 kB\n"
        )
        spec = {"config_path": "/tmp/config.json", "fixture_dir": "/tmp/fixture",
                "run_dir": "/tmp/run"}
        with patch.object(supervisor.subprocess, "run", side_effect=fake_run):
            unit, result, journal = supervisor.run_service(spec, 131072, 2026101, 1,
                                                           limits, "test-token")

        command = calls[0]
        self.assertEqual(command[:5], ["sudo", "-n", "systemd-run", "--system", "--quiet"])
        self.assertIn(f"--uid={os.getuid()}", command)
        self.assertIn(f"--gid={os.getgid()}", command)
        self.assertIn("--slice=background.slice", command)
        self.assertNotIn("--user", command)
        self.assertEqual(unit, "llamacode-q35-context-131072-seed-2026101-a01")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(journal, "")


if __name__ == "__main__":
    unittest.main()
