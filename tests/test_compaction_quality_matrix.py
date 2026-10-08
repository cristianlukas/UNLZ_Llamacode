import unittest

from tools.compaction_quality_matrix import MARKERS, marker_hits, summarize


class CompactionQualityMatrixTests(unittest.TestCase):
    def test_marker_hits_is_case_insensitive_but_keeps_canonical_labels(self):
        found = marker_hits("KEEP-01: No editar config/production.env\nKEEP-03: EJECUTAR tests/test_alpha.py")
        self.assertEqual(found, [MARKERS[0], MARKERS[2]])

    def test_summary_separates_raw_and_compacted_outcomes(self):
        raw = {
            "mode": "raw",
            "actions": [{"ok": True, "timing": {"wallMs": 10}}],
            "final": {"ok": True, "timing": {"wallMs": 20}},
        }
        compacted = {
            "mode": "compaction",
            "actions": [{"ok": True, "timing": {"wallMs": 30}}],
            "final": {"ok": False, "timing": {"wallMs": 40}},
        }
        report = summarize([raw, compacted])
        self.assertEqual(report["rawFinalRatePct"], 100.0)
        self.assertEqual(report["compactionFinalRatePct"], 0.0)
        self.assertEqual(report["compactionActionRatePct"], 100.0)


if __name__ == "__main__":
    unittest.main()
