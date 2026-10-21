import json
import os
import pathlib
import subprocess
import sys
import unittest

TASK = pathlib.Path(__file__).resolve().parents[1]
REPO = pathlib.Path(__file__).resolve().parents[4]
ADAPTER = TASK / "work/run_source23_mmap_arm.py"
LOCK_TOKEN = "50d8dfb3-511a-48b2-a253-2cd6197cee17"
ORIGINAL_CONFIGS = REPO / "artifacts/evaluacion-modelos-llamacode/Q-20261020-VF-20261019-01/work/source23/configs"


class Source23MmapAdapterTests(unittest.TestCase):
    def test_stock_config_changes_only_by_mmap_flag(self):
        original = json.loads((ORIGINAL_CONFIGS / "stock.json").read_text())
        adapted = json.loads((TASK / "work/source23/configs/stock.json").read_text())
        expected = dict(original)
        expected["args"] = [*original["args"], "--mmap-experts"]
        self.assertEqual(adapted, expected)

    def test_fp8_config_changes_only_by_mmap_flag(self):
        original = json.loads((ORIGINAL_CONFIGS / "fp8.json").read_text())
        adapted = json.loads((TASK / "work/source23/configs/fp8.json").read_text())
        expected = dict(original)
        expected["args"] = [*original["args"], "--mmap-experts"]
        self.assertEqual(adapted, expected)

    def test_stock_dry_run_targets_q20_and_unused_paths(self):
        result = self._dry_run("stock", 23999)
        self.assertEqual(result["status"], "dry_run_pass")
        self.assertEqual(result["taskId"], "Q-20261021-VF-ITERATION-20")
        self.assertEqual(result["port"], 8355)
        self.assertTrue(result["mmapExperts"] and result["lockOwned"] and result["outputsUnused"])
        self.assertFalse(result["gpuStarted"])
        self.assertIn("Q-20261021-VF-ITERATION-20", result["result"])

    def test_fp8_dry_run_has_distinct_outputs(self):
        result = self._dry_run("fp8", 23999)
        self.assertTrue(result["gpuStarted"] is False)
        self.assertIn("fp8-seed-23999.json", result["result"])

    def test_wrong_lock_token_is_rejected_before_gpu(self):
        env = dict(os.environ, LCA_WORK_QUEUE_LOCK_TOKEN="wrong-token")
        result = subprocess.run(
            [sys.executable, str(ADAPTER), "--arm", "stock", "--seed", "23003", "--dry-run"],
            env=env, capture_output=True, text=True, timeout=10,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("lock ownership mismatch", result.stderr)

    def _dry_run(self, arm, seed):
        env = dict(os.environ, LCA_WORK_QUEUE_LOCK_TOKEN=LOCK_TOKEN)
        result = subprocess.run(
            [sys.executable, str(ADAPTER), "--arm", arm, "--seed", str(seed), "--dry-run"],
            env=env, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
