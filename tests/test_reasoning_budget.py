import json
import tempfile
import unittest
from pathlib import Path

from tools.benchmark_reasoning_budget import DEFAULT_CORPUS, load_corpus, score_text, summarize


class ReasoningBudgetBenchmarkTests(unittest.TestCase):
    def test_corpus_is_versioned_and_scored_by_markers(self):
        root = Path(__file__).resolve().parents[1]
        tasks = load_corpus(DEFAULT_CORPUS)
        self.assertGreaterEqual(len(tasks), 5)
        self.assertTrue(score_text("resultado 323", tasks[0]["acceptance"])["passed"])
        self.assertFalse(score_text("la prueba pasó", tasks[4]["acceptance"])["passed"])

    def test_safety_acceptance_allows_explaining_the_rejected_action(self):
        root = Path(__file__).resolve().parents[1]
        tasks = load_corpus(root / "assets/benchmarks/custom/reasoning_budget_v2.json")
        safety = next(task for task in tasks if task["id"] == "safety")
        safe_explanation = (
            "La acción mínima es revisar y guardar el borrador; no hay que enviar "
            "nada sin una confirmación explícita."
        )
        self.assertTrue(score_text(safe_explanation, safety["acceptance"])["passed"])
        self.assertFalse(
            score_text("Hay que enviar ahora.", safety["acceptance"])["passed"]
        )

    def test_summary_keeps_transport_and_quality_separate(self):
        rows = [
            {"budget": 0, "transportOk": True, "wallMs": 10, "score": {"passed": True},
             "promptTokens": 20, "generatedTokens": 4, "reasoningTokens": 0},
            {"budget": 0, "transportOk": False, "wallMs": 11, "score": {"passed": False},
             "promptTokens": None, "generatedTokens": None, "reasoningTokens": None},
        ]
        summary = summarize(rows)["0"]
        self.assertEqual(summary["transportPct"], 50.0)
        self.assertEqual(summary["successPct"], 50.0)
        self.assertEqual(summary["medianWallMs"], 10)


if __name__ == "__main__":
    unittest.main()
