#!/usr/bin/env python3
"""Reconcile Q124 OCR quality scores with timing/hash receipts, without inference."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _finite_nonnegative(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} is not numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"{label} must be finite and nonnegative")
    return result


def build_comparison(
    *,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    guard: dict[str, Any],
    manifest: dict[str, Any],
    manifest_sha256: str,
    manifest_path: Path,
    output_dir: Path,
    attempt_dir: Path,
    attempt: str,
    expected_pages: int = 12,
    recorded_at_utc: str | None = None,
) -> dict[str, Any]:
    """Validate a frozen run and pair its already-scored pages and worker times."""
    for label, report in (("baseline", baseline), ("candidate", candidate), ("guard", guard)):
        if report.get("status") != "completed":
            raise ValueError(f"{label} report is not completed")
        if report.get("manifestSha256") != manifest_sha256:
            raise ValueError(f"{label} manifest SHA-256 mismatch")
    if _sha256(manifest_path) != manifest_sha256:
        raise ValueError("frozen manifest file SHA-256 mismatch")

    selected = manifest.get("selected")
    if not isinstance(selected, list) or len(selected) != expected_pages:
        raise ValueError(f"manifest must contain exactly {expected_pages} selected pages")
    manifest_by_id = {row.get("id"): row for row in selected if isinstance(row, dict)}
    if len(manifest_by_id) != expected_pages or None in manifest_by_id:
        raise ValueError("manifest IDs are missing or duplicated")

    baseline_cases = baseline.get("cases")
    candidate_cases = candidate.get("cases")
    if not isinstance(baseline_cases, list) or not isinstance(candidate_cases, list):
        raise ValueError("baseline and candidate cases must be arrays")
    if len(baseline_cases) != expected_pages or len(candidate_cases) != expected_pages:
        raise ValueError(f"baseline and candidate must each contain {expected_pages} cases")

    def unique_rows(rows: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
        by_id: dict[str, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("id"), str):
                raise ValueError(f"{label} contains a case without an ID")
            if row["id"] in by_id:
                raise ValueError(f"{label} contains duplicate ID {row['id']}")
            by_id[row["id"]] = row
        return by_id

    base_by_id = unique_rows(baseline_cases, "baseline")
    candidate_by_id = unique_rows(candidate_cases, "candidate")
    expected_ids = set(manifest_by_id)
    if set(base_by_id) != expected_ids or set(candidate_by_id) != expected_ids:
        raise ValueError("manifest, baseline, and candidate IDs do not match exactly")

    gpu_runs = guard.get("physicalGpuRuns")
    if not isinstance(gpu_runs, list) or [row.get("physicalGpu") for row in gpu_runs] != [0, 1]:
        raise ValueError("guard receipt must show the preregistered serial GPU0 then GPU1 runs")
    timings: dict[str, float] = {}
    worker_pages: dict[str, dict[str, Any]] = {}
    worker_receipt_hashes: list[str] = []
    for gpu_run in gpu_runs:
        if gpu_run.get("status") != "completed" or gpu_run.get("returnCode") != 0:
            raise ValueError("a physical GPU worker did not complete with return code 0")
        sample_ids = gpu_run.get("sampleIds")
        if not isinstance(sample_ids, list) or len(sample_ids) != 6 or len(set(sample_ids)) != 6:
            raise ValueError("each GPU run must list six unique frozen sample IDs")
        receipt_path = Path(gpu_run.get("workerReceipt", "")).resolve()
        try:
            receipt_path.relative_to(attempt_dir.resolve())
        except ValueError as exc:
            raise ValueError("worker receipt escapes the frozen attempt directory") from exc
        worker = _read_json(receipt_path)
        if worker.get("status") != "completed" or worker.get("manifestSha256") != manifest_sha256:
            raise ValueError("worker receipt is incomplete or has a different manifest")
        pages = worker.get("pages")
        if not isinstance(pages, list) or len(pages) != 6:
            raise ValueError("each completed worker receipt must contain six pages")
        worker_receipt_hashes.append(_sha256(receipt_path))
        ids_for_gpu: list[str] = []
        for page in pages:
            if not isinstance(page, dict) or not isinstance(page.get("id"), str):
                raise ValueError("worker page has no ID")
            image_id = page["id"]
            if image_id in worker_pages:
                raise ValueError(f"workers contain duplicate ID {image_id}")
            if image_id not in expected_ids:
                raise ValueError(f"worker emitted unexpected ID {image_id}")
            seconds = page.get("seconds")
            if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
                raise ValueError(f"worker timing missing or nonnumeric for {image_id}")
            seconds = float(seconds)
            if not math.isfinite(seconds) or seconds <= 0:
                raise ValueError(f"worker timing must be finite and positive for {image_id}")
            if sample_ids.count(image_id) != 1:
                raise ValueError(f"worker sample ID list does not match page {image_id}")
            worker_pages[image_id] = page
            timings[image_id] = seconds
            ids_for_gpu.append(image_id)
        if set(ids_for_gpu) != set(sample_ids):
            raise ValueError("worker receipt pages disagree with its physical GPU sample IDs")
    if set(worker_pages) != expected_ids:
        raise ValueError("worker and manifest IDs do not match exactly")

    paired: list[dict[str, Any]] = []
    for baseline_case in baseline_cases:
        image_id = baseline_case["id"]
        candidate_case = candidate_by_id[image_id]
        worker_page = worker_pages[image_id]
        manifest_page = manifest_by_id[image_id]
        output_path = output_dir / f"{image_id}.txt"
        if not output_path.is_file():
            raise ValueError(f"retained OCR text missing for {image_id}")
        output_sha = _sha256(output_path)
        expected_sha = worker_page.get("outputSha256")
        if output_sha != expected_sha or candidate_case.get("rawOutputSha256") != expected_sha:
            raise ValueError(f"worker, candidate, and retained text hashes disagree for {image_id}")
        if worker_page.get("imageSha256") != manifest_page.get("imageSha256"):
            raise ValueError(f"worker image hash disagrees with frozen manifest for {image_id}")
        base_cer = _finite_nonnegative(baseline_case.get("cer"), f"baseline CER {image_id}")
        candidate_cer = _finite_nonnegative(candidate_case.get("cer"), f"candidate CER {image_id}")
        paired.append({
            "id": image_id,
            "tesseractCer": base_cer,
            "candidateCer": candidate_cer,
            "candidateWon": candidate_cer < base_cer,
            "candidateSeconds": timings[image_id],
            "outputSha256": expected_sha,
        })

    if len(paired) != expected_pages:
        raise ValueError(f"expected {expected_pages} paired pages, got {len(paired)}")
    baseline_mean = _finite_nonnegative(baseline.get("meanCer"), "baseline mean CER")
    candidate_mean = _finite_nonnegative(candidate.get("meanCer"), "candidate mean CER")
    baseline_calc = statistics.mean(row["tesseractCer"] for row in paired)
    candidate_calc = statistics.mean(row["candidateCer"] for row in paired)
    if not math.isclose(baseline_mean, baseline_calc, rel_tol=1e-12, abs_tol=1e-12):
        raise ValueError("baseline report mean CER disagrees with its page cases")
    if not math.isclose(candidate_mean, candidate_calc, rel_tol=1e-12, abs_tol=1e-12):
        raise ValueError("candidate report mean CER disagrees with its page cases")
    relative = (baseline_mean - candidate_mean) / baseline_mean if baseline_mean else 0.0
    wins = sum(row["candidateWon"] for row in paired)
    if relative >= 0.15 and wins >= 8:
        decision = "advance-to-larger-holdout"
    elif relative < 0.15 and wins < 8:
        decision = "do-not-integrate"
    else:
        decision = "inconclusive-preregister-extension"
    candidate_seconds = statistics.mean(timings.values())
    return {
        "taskId": "Q-20261025-VF-ITERATION-124",
        "amendment": "A19-offline-score-reconciliation",
        "attempt": attempt,
        "recordedAtUtc": recorded_at_utc or dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "dataset": "XFUND v1.0 es.val, 12 hash-selected pages",
        "manifestSha256": manifest_sha256,
        "sourceHashes": {
            "baseline": _sha256(Path(baseline["sourcePath"])) if baseline.get("sourcePath") else None,
            "candidateQualityReport": _sha256(Path(candidate["sourcePath"])) if candidate.get("sourcePath") else None,
            "guardReceipt": _sha256(Path(guard["sourcePath"])) if guard.get("sourcePath") else None,
            "workers": worker_receipt_hashes,
        },
        "baseline": {
            "meanCer": baseline_mean,
            "medianCer": baseline.get("medianCer"),
            "meanWordRecall": baseline.get("meanWordRecall"),
            "meanSeconds": baseline.get("meanSeconds"),
        },
        "candidate": {
            "meanCer": candidate_mean,
            "medianCer": candidate.get("medianCer"),
            "meanWordRecall": candidate.get("meanWordRecall"),
            "meanSeconds": candidate_seconds,
        },
        "relativeMeanCerReduction": relative,
        "pairedPageWins": wins,
        "pageCount": len(paired),
        "perPage": paired,
        "advanceGate": {"relativeCerReductionAtLeast": 0.15, "pairedWinsAtLeast": 8},
        "decision": decision,
        "timingSource": "completed serial worker receipts; seconds joined by frozen page ID",
        "parserOrScoresRecomputed": False,
        "inferenceRerun": False,
        "changesProduction": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--guard-receipt", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--attempt-dir", type=Path, required=True)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not args.attempt.replace("-", "").replace("_", "").isalnum():
        raise SystemExit("attempt must be alphanumeric with optional hyphens/underscores")
    manifest_sha256 = _sha256(args.manifest)
    baseline = _read_json(args.baseline)
    candidate = _read_json(args.candidate)
    guard = _read_json(args.guard_receipt)
    manifest = _read_json(args.manifest)
    baseline["sourcePath"] = str(args.baseline.resolve())
    candidate["sourcePath"] = str(args.candidate.resolve())
    guard["sourcePath"] = str(args.guard_receipt.resolve())
    comparison = build_comparison(
        baseline=baseline, candidate=candidate, guard=guard, manifest=manifest,
        manifest_sha256=manifest_sha256, manifest_path=args.manifest,
        output_dir=args.output_dir, attempt_dir=args.attempt_dir,
        attempt=args.attempt,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temp = args.out.with_suffix(args.out.suffix + ".tmp")
    temp.write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(args.out)
    print(json.dumps({
        "status": "completed",
        "pages": comparison["pageCount"],
        "baselineMeanCer": comparison["baseline"]["meanCer"],
        "candidateMeanCer": comparison["candidate"]["meanCer"],
        "relativeCerReduction": comparison["relativeMeanCerReduction"],
        "pairedWins": comparison["pairedPageWins"],
        "candidateMeanSeconds": comparison["candidate"]["meanSeconds"],
        "decision": comparison["decision"],
        "output": str(args.out),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "blocked_or_failed", "error": f"{type(exc).__name__}: {exc}"}), file=__import__("sys").stderr)
        raise SystemExit(2)
