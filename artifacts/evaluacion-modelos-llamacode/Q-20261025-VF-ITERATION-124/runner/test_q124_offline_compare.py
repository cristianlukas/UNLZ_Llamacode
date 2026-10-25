from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from q124_offline_compare import build_comparison


class OfflineCompareTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="q124-offline-compare-")
        self.root = Path(self.temp.name)
        self.attempt_dir = self.root / "attempt"
        self.receipts = self.attempt_dir / "receipts"
        self.outputs = self.attempt_dir / "model-outputs"
        self.receipts.mkdir(parents=True)
        self.outputs.mkdir()
        self.manifest_path = self.root / "manifest.json"
        self.manifest = {"selected": []}
        self.pages = []
        self.baseline_cases = []
        self.candidate_cases = []
        self.worker_pages = [[], []]
        for index in range(12):
            image_id = f"page-{index:02d}"
            raw = f"ocr-output-{image_id}".encode()
            output_hash = hashlib.sha256(raw).hexdigest()
            (self.outputs / f"{image_id}.txt").write_bytes(raw)
            image_hash = hashlib.sha256(f"image-{image_id}".encode()).hexdigest()
            self.manifest["selected"].append({"id": image_id, "image": f"{image_id}.jpg", "imageSha256": image_hash})
            self.baseline_cases.append({"id": image_id, "cer": 0.25, "wordRecall": {"recall": 0.8}})
            self.candidate_cases.append({"id": image_id, "cer": 0.20, "wordRecall": {"recall": 0.9}, "rawOutputSha256": output_hash})
            self.worker_pages[index // 6].append({
                "id": image_id,
                "imageSha256": image_hash,
                "outputSha256": output_hash,
                "seconds": float(index + 1),
            })
        self.manifest_path.write_text(json.dumps(self.manifest), encoding="utf-8")
        self.manifest_sha = hashlib.sha256(self.manifest_path.read_bytes()).hexdigest()
        self.worker_paths = []
        physical_runs = []
        for gpu, pages in enumerate(self.worker_pages):
            receipt = {
                "status": "completed",
                "manifestSha256": self.manifest_sha,
                "pages": pages,
            }
            path = self.receipts / f"worker-gpu{gpu}.json"
            path.write_text(json.dumps(receipt), encoding="utf-8")
            self.worker_paths.append(path)
            physical_runs.append({
                "physicalGpu": gpu,
                "sampleIds": [page["id"] for page in pages],
                "workerReceipt": str(path),
                "returnCode": 0,
                "status": "completed",
            })
        self.baseline = {
            "status": "completed",
            "manifestSha256": self.manifest_sha,
            "cases": self.baseline_cases,
            "meanCer": 0.25,
            "medianCer": 0.25,
            "meanWordRecall": 0.8,
            "meanSeconds": 1.0,
        }
        self.candidate = {
            "status": "completed",
            "manifestSha256": self.manifest_sha,
            "cases": self.candidate_cases,
            "meanCer": 0.20,
            "medianCer": 0.20,
            "meanWordRecall": 0.9,
        }
        self.guard = {
            "status": "completed",
            "manifestSha256": self.manifest_sha,
            "physicalGpuRuns": physical_runs,
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def compare(self):
        return build_comparison(
            baseline=self.baseline,
            candidate=self.candidate,
            guard=self.guard,
            manifest=self.manifest,
            manifest_sha256=self.manifest_sha,
            manifest_path=self.manifest_path,
            output_dir=self.outputs,
            attempt_dir=self.attempt_dir,
            attempt="fixture",
            recorded_at_utc="2026-01-01T00:00:00Z",
        )

    def test_joins_per_page_times_without_recalculating_cer(self):
        result = self.compare()
        self.assertEqual(result["pageCount"], 12)
        self.assertEqual(result["perPage"][0]["candidateSeconds"], 1.0)
        self.assertEqual(result["perPage"][6]["candidateSeconds"], 7.0)
        self.assertEqual(result["candidate"]["meanSeconds"], 6.5)
        self.assertEqual(result["candidate"]["meanCer"], 0.20)
        self.assertAlmostEqual(result["relativeMeanCerReduction"], 0.20, places=14)
        self.assertEqual(result["pairedPageWins"], 12)
        self.assertEqual(result["decision"], "advance-to-larger-holdout")
        self.assertFalse(result["parserOrScoresRecomputed"])

    def test_rejects_missing_sample_id(self):
        self.guard["physicalGpuRuns"][0]["sampleIds"].pop()
        with self.assertRaisesRegex(ValueError, "six unique"):
            self.compare()

    def test_rejects_missing_worker_page(self):
        self.worker_pages[0].pop()
        self.worker_paths[0].write_text(json.dumps({
            "status": "completed", "manifestSha256": self.manifest_sha,
            "pages": self.worker_pages[0],
        }), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "six pages"):
            self.compare()

    def test_rejects_duplicate_worker_page_id(self):
        self.worker_pages[0][-1] = dict(self.worker_pages[0][0])
        self.worker_paths[0].write_text(json.dumps({
            "status": "completed", "manifestSha256": self.manifest_sha,
            "pages": self.worker_pages[0],
        }), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate ID"):
            self.compare()

    def test_rejects_candidate_output_hash_mismatch(self):
        self.candidate_cases[0]["rawOutputSha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "hashes disagree"):
            self.compare()

    def test_rejects_missing_page_time(self):
        del self.worker_pages[0][0]["seconds"]
        self.worker_paths[0].write_text(json.dumps({
            "status": "completed", "manifestSha256": self.manifest_sha,
            "pages": self.worker_pages[0],
        }), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "timing missing"):
            self.compare()


if __name__ == "__main__":
    unittest.main(verbosity=2)
