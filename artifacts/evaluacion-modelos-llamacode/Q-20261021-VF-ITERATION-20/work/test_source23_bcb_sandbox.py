import importlib.util
import json
import pathlib
import unittest

TASK = pathlib.Path(__file__).resolve().parents[1]
SCORER_PATH = TASK / "work/source23-run-bcb.py"
CONTROLLER_PATH = TASK / "work/source23-run-arm.py"
SPEC = importlib.util.spec_from_file_location("q20_source23_scorer_test", SCORER_PATH)
scorer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scorer)
CONTROLLER_SPEC = importlib.util.spec_from_file_location("q20_source23_controller_test", CONTROLLER_PATH)
controller = importlib.util.module_from_spec(CONTROLLER_SPEC)
CONTROLLER_SPEC.loader.exec_module(controller)


class Source23BcbSandboxTests(unittest.TestCase):
    def test_fenced_python_is_extracted_without_markers(self):
        self.assertEqual(scorer.candidate_code("```python\ndef task_func():\n    return 3\n```"),
                         "def task_func():\n    return 3")

    def test_unclosed_python_fence_from_truncated_answer_is_removed(self):
        self.assertEqual(scorer.candidate_code("```python\ndef task_func():\n    return 3"),
                         "def task_func():\n    return 3")

    def test_sandbox_can_run_with_pinned_venv_and_data_packages(self):
        code = (
            "import numpy as np\nimport pandas as pd\n"
            "def task_func():\n    return int(pd.Series(np.array([2])).sum())"
        )
        passed, detail = scorer.grade(code, "assert task_func() == 2")
        self.assertTrue(passed, detail)

    def test_fixed_fixture_has_eight_nonempty_test_suites(self):
        corpus = json.loads(scorer.PACK.read_text(encoding="utf-8"))
        self.assertEqual(len(corpus["items"]), 8)
        self.assertTrue(all(item.get("tests", "").strip() for item in corpus["items"]))

    def test_q20_controller_targets_the_q20_local_scorer(self):
        self.assertEqual(pathlib.Path(controller.RUNNER), SCORER_PATH)
        self.assertTrue(pathlib.Path(controller.RUNNER).is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
