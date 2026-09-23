"""Comparative analysis helpers for the Qwen/NInfer post campaign.

The module is deliberately runtime-agnostic.  It does not pretend that a
configured context is the same thing as an allocated KV cache, and it never
turns a missing or infrastructure-failed run into a quality score.

It accepts compact JSON records from real server/harness runs and produces a
decision that can be audited alongside the raw receipts.  The same functions
are used by the unit tests and by the optional command-line report generator.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics
from typing import Any, Iterable, Mapping, Sequence


SCHEMA = "llamacode-post-comparison-v1"
POLICIES = {"stable-turn", "rolling-tool"}


class ComparisonError(ValueError):
    """Raised for malformed campaign input."""


def _finite_numbers(values: Iterable[Any]) -> list[float]:
    result: list[float] = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            result.append(number)
    return result


def _percent_delta(candidate: float | None, baseline: float | None) -> float | None:
    if candidate is None or baseline in (None, 0):
        return None
    return (candidate - baseline) / baseline * 100.0


def summarize_checkpoint_sequence(
    checkpoints: Sequence[int], prompt_tokens: Sequence[int] | None = None
) -> dict[str, Any]:
    """Summarize server restore checkpoints without assuming a runtime.

    ``checkpoints`` is the token position restored before each continuation.
    If prompt positions are supplied, the uncached suffix is computed for each
    request.  A checkpoint can advance, plateau, or regress; regressions are
    reported rather than hidden because they are the signal the post claims
    ``rolling-tool`` fixes.
    """
    if not checkpoints:
        raise ComparisonError("checkpoint sequence must not be empty")
    if any(int(value) < 0 for value in checkpoints):
        raise ComparisonError("checkpoint positions must be non-negative")
    values = [int(value) for value in checkpoints]
    if prompt_tokens is not None:
        if len(prompt_tokens) != len(values):
            raise ComparisonError("prompt_tokens must match checkpoints")
        prompts = [int(value) for value in prompt_tokens]
        if any(value < 0 for value in prompts):
            raise ComparisonError("prompt positions must be non-negative")
        suffixes = [max(0, prompt - checkpoint)
                    for prompt, checkpoint in zip(prompts, values)]
    else:
        suffixes = []

    advances = sum(right > left for left, right in zip(values, values[1:]))
    plateaus = sum(right == left for left, right in zip(values, values[1:]))
    regressions = sum(right < left for left, right in zip(values, values[1:]))
    result: dict[str, Any] = {
        "count": len(values),
        "first": values[0],
        "last": values[-1],
        "advances": advances,
        "plateaus": plateaus,
        "regressions": regressions,
        "monotonic": regressions == 0,
    }
    if suffixes:
        result.update({
            "uncachedSuffixTokens": suffixes,
            "uncachedSuffixP50": statistics.median(suffixes),
            "uncachedSuffixMax": max(suffixes),
        })
    return result


def summarize_metric(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, Any]:
    """Summarize one metric while preserving missing values as missing."""
    values = _finite_numbers(row.get(key) for row in rows)
    if not values:
        return {"count": 0, "median": None, "min": None, "max": None}
    return {
        "count": len(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
    }


def compare_metric_rows(
    baseline: Sequence[Mapping[str, Any]],
    candidate: Sequence[Mapping[str, Any]],
    metrics: Sequence[str] = ("ttftMs", "promptTps", "decodeTps", "vramMb"),
) -> dict[str, Any]:
    """Compare paired rows by id, never pairing unrelated tasks by position."""
    left = {str(row.get("id")): row for row in baseline if row.get("id") is not None}
    right = {str(row.get("id")): row for row in candidate if row.get("id") is not None}
    paired_ids = sorted(set(left) & set(right))
    pairs: list[dict[str, Any]] = []
    for row_id in paired_ids:
        item: dict[str, Any] = {"id": row_id}
        for metric in metrics:
            base_value = left[row_id].get(metric)
            candidate_value = right[row_id].get(metric)
            try:
                base_number = float(base_value)
                candidate_number = float(candidate_value)
            except (TypeError, ValueError):
                base_number = candidate_number = None
            if (base_number is not None and not math.isfinite(base_number)) or (
                    candidate_number is not None and not math.isfinite(candidate_number)):
                base_number = candidate_number = None
            item[f"baseline{metric[0].upper()}{metric[1:]}"] = base_number
            item[f"candidate{metric[0].upper()}{metric[1:]}"] = candidate_number
            item[f"{metric}DeltaPct"] = _percent_delta(candidate_number, base_number)
        pairs.append(item)

    summary: dict[str, Any] = {
        "pairCount": len(pairs),
        "unmatchedBaseline": sorted(set(left) - set(right)),
        "unmatchedCandidate": sorted(set(right) - set(left)),
        "pairs": pairs,
    }
    for metric in metrics:
        deltas = _finite_numbers(row[f"{metric}DeltaPct"] for row in pairs)
        summary[metric] = {
            "count": len(deltas),
            "medianDeltaPct": statistics.median(deltas) if deltas else None,
        }
    return summary


def assess_candidate(
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    min_speed_gain_pct: float = 5.0,
    max_quality_loss: int = 0,
    max_vram_increase_pct: float = 5.0,
) -> dict[str, Any]:
    """Apply the campaign's promotion gates to aggregate run summaries.

    Quality is expressed as passed cases out of the same suite.  A missing
    quality result, missing performance metric, or infrastructure failure is
    ``inconclusive`` rather than a pass or a zero.
    """
    required = ("qualityPassed", "qualityTotal", "decodeTps", "vramMb")
    missing = [key for key in required if key not in baseline or key not in candidate]
    if missing:
        return {"verdict": "inconclusive", "reason": "missing metrics", "missing": missing}
    if baseline.get("status") in {"infra-failed", "blocked"} or candidate.get("status") in {"infra-failed", "blocked"}:
        return {"verdict": "inconclusive", "reason": "infrastructure or blocked run"}

    try:
        base_quality = int(baseline["qualityPassed"])
        candidate_quality = int(candidate["qualityPassed"])
        total = int(candidate["qualityTotal"])
        base_speed = float(baseline["decodeTps"])
        candidate_speed = float(candidate["decodeTps"])
        base_vram = float(baseline["vramMb"])
        candidate_vram = float(candidate["vramMb"])
    except (TypeError, ValueError):
        return {"verdict": "inconclusive", "reason": "non-numeric metrics"}
    if total <= 0 or min(base_speed, candidate_speed) <= 0 or base_vram <= 0:
        return {"verdict": "inconclusive", "reason": "invalid metrics"}

    quality_delta = candidate_quality - base_quality
    speed_delta = _percent_delta(candidate_speed, base_speed)
    vram_delta = _percent_delta(candidate_vram, base_vram)
    quality_ok = quality_delta >= -max_quality_loss
    speed_ok = speed_delta is not None and speed_delta >= min_speed_gain_pct
    memory_ok = vram_delta is not None and vram_delta <= max_vram_increase_pct
    verdict = "promote" if quality_ok and speed_ok and memory_ok else "reject"
    return {
        "verdict": verdict,
        "qualityDelta": quality_delta,
        "speedDeltaPct": speed_delta,
        "vramDeltaPct": vram_delta,
        "gates": {"quality": quality_ok, "speed": speed_ok, "memory": memory_ok},
        "thresholds": {
            "minSpeedGainPct": min_speed_gain_pct,
            "maxQualityLoss": max_quality_loss,
            "maxVramIncreasePct": max_vram_increase_pct,
        },
        "quality": {"baseline": base_quality, "candidate": candidate_quality, "total": total},
    }


def campaign_plan() -> dict[str, Any]:
    """Return the machine-readable campaign definition used by the report."""
    return {
        "schema": SCHEMA,
        "gates": {
            "quality": "same HE0 -> HE20 -> BCB suite; no infrastructure failures counted as zero",
            "speed": "candidate decode median >= baseline +5%",
            "memory": "candidate peak VRAM <= baseline +5%",
            "rollingTool": "checkpoint advances, zero regressions, and lower uncached suffix",
        },
        "tracks": [
            {"id": "harness-prefix", "cases": ["stable-turn", "rolling-tool"],
             "metrics": ["checkpoint advances", "plateaus", "regressions", "uncached suffix", "TTFT"]},
            {"id": "runtime-context", "cases": ["8k", "32k", "64k", "131k"],
             "metrics": ["startup", "promptTps", "decodeTps", "TTFT", "peakVram", "MTP acceptance"]},
            {"id": "vision", "cases": ["no-image", "single-image", "historical-images-plus-new"],
             "metrics": ["visual exactness", "fresh media charged", "TTFT", "peakVram"]},
            {"id": "agent-quality", "cases": ["HE0", "HE20", "BCB8"],
             "metrics": ["first-attempt", "repairs", "tool success", "quality", "wall time"]},
        ],
    }


def _load_json_value(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ComparisonError(f"cannot read JSON {path}: {exc}") from exc


def _rows_from_json(value: Any) -> list[Mapping[str, Any]]:
    if isinstance(value, list):
        rows = value
    elif isinstance(value, dict):
        rows = value.get("rows", value.get("results", value.get("records")))
    else:
        rows = None
    if not isinstance(rows, list) or any(not isinstance(row, Mapping) for row in rows):
        raise ComparisonError("metric JSON must be a list or an object containing rows/results/records")
    return rows


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--plan", action="store_true", help="print the campaign plan")
    modes.add_argument("--compare", nargs=2, type=Path, metavar=("BASELINE", "CANDIDATE"),
                       help="compare paired metric rows from two JSON files")
    modes.add_argument("--assess", nargs=2, type=Path, metavar=("BASELINE", "CANDIDATE"),
                       help="apply promotion gates to two aggregate JSON objects")
    modes.add_argument("--checkpoints", type=Path,
                       help="JSON object with checkpoints and optional promptTokens")
    parser.add_argument("--out", type=Path, help="write JSON instead of stdout")
    args = parser.parse_args()
    try:
        if args.plan:
            result: dict[str, Any] = campaign_plan()
        elif args.checkpoints:
            payload = _load_json_value(args.checkpoints)
            result = summarize_checkpoint_sequence(
                payload["checkpoints"], payload.get("promptTokens"))
        elif args.compare:
            result = compare_metric_rows(
                _rows_from_json(_load_json_value(args.compare[0])),
                _rows_from_json(_load_json_value(args.compare[1])),
            )
        elif args.assess:
            baseline = _load_json_value(args.assess[0])
            candidate = _load_json_value(args.assess[1])
            if not isinstance(baseline, Mapping) or not isinstance(candidate, Mapping):
                raise ComparisonError("assess JSON roots must be objects")
            result = assess_candidate(baseline, candidate)
        else:
            return 2  # argparse enforces the mutually exclusive group.
    except (KeyError, TypeError, ComparisonError) as exc:
        print(f"ERROR: {exc}")
        return 2
    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        args.out.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
