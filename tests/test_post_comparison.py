"""Regression tests for the post-comparison campaign analyzer."""

from __future__ import annotations

import unittest

from tools.post_comparison import (
    assess_candidate,
    campaign_plan,
    compare_metric_rows,
    summarize_checkpoint_sequence,
)


class PostComparisonTests(unittest.TestCase):
    def test_rolling_sequence_reports_advances_and_no_regressions(self):
        result = summarize_checkpoint_sequence(
            [19023, 21146, 24664, 26641],
            [21100, 23100, 26100, 30000],
        )
        self.assertEqual(result["advances"], 3)
        self.assertEqual(result["plateaus"], 0)
        self.assertEqual(result["regressions"], 0)
        self.assertEqual(result["uncachedSuffixMax"], 3359)

    def test_checkpoint_regression_is_not_hidden(self):
        result = summarize_checkpoint_sequence([100, 120, 110])
        self.assertEqual(result["regressions"], 1)
        self.assertFalse(result["monotonic"])

    def test_metric_comparison_pairs_by_id_and_keeps_unmatched_rows(self):
        result = compare_metric_rows(
            [{"id": "a", "decodeTps": 20}, {"id": "only-base", "decodeTps": 99}],
            [{"id": "a", "decodeTps": 25}, {"id": "only-candidate", "decodeTps": 99}],
            metrics=["decodeTps"],
        )
        self.assertEqual(result["pairCount"], 1)
        self.assertEqual(result["unmatchedBaseline"], ["only-base"])
        self.assertEqual(result["unmatchedCandidate"], ["only-candidate"])
        self.assertAlmostEqual(result["decodeTps"]["medianDeltaPct"], 25.0)

    def test_candidate_requires_quality_and_speed_without_memory_regression(self):
        result = assess_candidate(
            {"status": "complete", "qualityPassed": 8, "qualityTotal": 8,
             "decodeTps": 100, "vramMb": 16000},
            {"status": "complete", "qualityPassed": 8, "qualityTotal": 8,
             "decodeTps": 106, "vramMb": 16050},
        )
        self.assertEqual(result["verdict"], "promote")
        self.assertTrue(all(result["gates"].values()))

    def test_quality_regression_rejects_a_faster_candidate(self):
        result = assess_candidate(
            {"status": "complete", "qualityPassed": 8, "qualityTotal": 8,
             "decodeTps": 100, "vramMb": 16000},
            {"status": "complete", "qualityPassed": 7, "qualityTotal": 8,
             "decodeTps": 130, "vramMb": 16000},
        )
        self.assertEqual(result["verdict"], "reject")
        self.assertFalse(result["gates"]["quality"])

    def test_missing_or_blocked_run_is_inconclusive(self):
        result = assess_candidate(
            {"status": "complete", "qualityPassed": 8, "qualityTotal": 8,
             "decodeTps": 100, "vramMb": 16000},
            {"status": "blocked", "qualityPassed": 0, "qualityTotal": 8},
        )
        self.assertEqual(result["verdict"], "inconclusive")

    def test_plan_contains_all_four_tracks(self):
        plan = campaign_plan()
        self.assertEqual(plan["schema"], "llamacode-post-comparison-v1")
        self.assertEqual(
            {track["id"] for track in plan["tracks"]},
            {"harness-prefix", "runtime-context", "vision", "agent-quality"},
        )

    def test_assess_uses_the_same_quality_total_and_five_percent_speed_gate(self):
        result = assess_candidate(
            {"status": "complete", "qualityPassed": 2, "qualityTotal": 2,
             "decodeTps": 37.675589985, "vramMb": 19265},
            {"status": "complete", "qualityPassed": 2, "qualityTotal": 2,
             "decodeTps": 69.952271027, "vramMb": 20187},
        )
        self.assertEqual(result["verdict"], "promote")
        self.assertAlmostEqual(result["speedDeltaPct"], 85.68, places=1)
        self.assertLessEqual(result["vramDeltaPct"], 5.0)


if __name__ == "__main__":
    unittest.main()
