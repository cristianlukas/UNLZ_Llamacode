import importlib.util
import pathlib
import tempfile
import unittest
from unittest import mock

MODULE_PATH = pathlib.Path(__file__).with_name("run_source23_guarded.py")
SPEC = importlib.util.spec_from_file_location("source23_guarded", MODULE_PATH)
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class Source23GuardTests(unittest.TestCase):
    def test_command_carries_lock_token_and_resource_limits(self):
        command = guard.build_command("q20-s23-stock-23003", "stock", 23003)
        self.assertIn(f"--setenv=LCA_WORK_QUEUE_LOCK_TOKEN={guard.TOKEN}", command)
        self.assertIn("--property=MemoryHigh=64G", command)
        self.assertIn("--property=MemoryMax=72G", command)
        self.assertEqual(command[-4:], ["--arm", "stock", "--seed", "23003"])

    def test_dry_run_never_launches_gpu_process(self):
        passing = {"status": "pass", "problems": [], "swapFreeBytes": 100, "oomKills": 0}
        with tempfile.TemporaryDirectory() as temp:
            task = pathlib.Path(temp)
            (task / "receipts").mkdir()
            (task / "work/source23/results").mkdir(parents=True)
            with mock.patch.object(guard, "TASK", task), \
                 mock.patch.object(guard, "preflight", return_value=passing), \
                 mock.patch.object(guard.subprocess, "Popen") as popen:
                rc = guard.run("stock", 23003, dry_run=True)
        self.assertEqual(rc, 0)
        popen.assert_not_called()

    def test_blocked_preflight_returns_before_gpu_or_receipt_collision(self):
        blocked = {"status": "blocked", "problems": ["inference process detected"]}
        with tempfile.TemporaryDirectory() as temp:
            task = pathlib.Path(temp)
            (task / "receipts").mkdir()
            (task / "work/source23/results").mkdir(parents=True)
            with mock.patch.object(guard, "TASK", task), \
                 mock.patch.object(guard, "preflight", return_value=blocked), \
                 mock.patch.object(guard.subprocess, "Popen") as popen:
                rc = guard.run("fp8", 23003, dry_run=False)
            saved = guard.json.loads((task / "receipts/preflight-fp8-seed-23003.json").read_text())
        self.assertEqual(rc, 2)
        self.assertEqual(saved["status"], "blocked")
        popen.assert_not_called()

    def test_stop_targets_only_the_named_q20_scope(self):
        with mock.patch.object(guard.subprocess, "run") as run:
            guard.stop_owned_scope("q20-s23-stock-23003")
        run.assert_called_once_with(
            ["systemctl", "--user", "stop", "q20-s23-stock-23003.scope"],
            capture_output=True, text=True, timeout=30, check=False,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
