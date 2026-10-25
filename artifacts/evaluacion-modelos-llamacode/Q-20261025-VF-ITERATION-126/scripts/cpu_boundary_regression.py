#!/usr/bin/env python3
"""Focused CPU-only AMD05 PSI/headroom boundary regression; no system sampling."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
Q117 = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-117"
PINS = {
    Q117 / "scripts/q117_pressure_guard_attempt05.py": "b4d42302e7d405abd5c59df5aa86bb7de6ef3bb91aef487b49acbebd1d24270e",
    Q117 / "guard_sources/q108_guard_core.py": "832c6661692fa9c6e45d209be5c4201a1ad796bfe66bec92cf947151e6988b4b",
}
for path, expected in PINS.items():
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f"PIN MISMATCH: {path}: expected {expected}, got {actual}")

sys.path.insert(0, str(Q117 / "scripts"))
from q117_pressure_guard_attempt05 import evaluate, initial_counts  # noqa: E402


def sample(index: int, available: float, oom: int = 0) -> dict:
    # Alternation makes only one side of the OR severe at each sample.
    psi = {"full": 60.0, "some": 0.0} if index % 2 else {"full": 0.0, "some": 80.0}
    return {"memAvailableGiB": available, "memoryPsiAvg10Pct": psi, "oomKill": oom}


def normal(available: float) -> dict:
    return {"memAvailableGiB": available,
            "memoryPsiAvg10Pct": {"full": 0.0, "some": 0.0}, "oomKill": 0}


def replay(series: list[dict]) -> dict:
    counters = initial_counts()
    for n, item in enumerate(series, 1):
        stop, counters, warning = evaluate(item, 0, counters)
        if stop:
            return {"stopSample": n, "stopReason": stop, "warning": warning}
    return {"stopSample": None, "stopReason": None, "warning": None}


def main() -> None:
    below = replay([sample(i, 47.99) for i in range(1, 15)])
    below_15 = replay([sample(i, 47.99) for i in range(1, 16)])
    exact_boundary = replay([sample(i, 48.00) for i in range(1, 31)])
    reset = replay([sample(i, 47.99) for i in range(1, 15)]
                   + [normal(47.99)]
                   + [sample(i, 47.99) for i in range(1, 16)])
    cases = [
        {"id": "A-before-boundary", "passed": below["stopSample"] is None,
         "expectedStopSample": None, **below},
        {"id": "A-at-boundary", "passed": below_15["stopSample"] == 15
         and "MemAvailable <48 GiB" in (below_15["stopReason"] or ""),
         "expectedStopSample": 15, **below_15},
        {"id": "B-strict-48GiB-boundary", "passed": exact_boundary["stopSample"] is None,
         "expectedStopSample": None, **exact_boundary},
        {"id": "C-normal-sample-resets-low-headroom-streak",
         "passed": reset["stopSample"] == 30
         and "MemAvailable <48 GiB" in (reset["stopReason"] or ""),
         "expectedStopSample": 30, **reset},
    ]
    result = {
        "taskId": "Q-20261025-VF-ITERATION-126",
        "mode": "CPU-only synthetic fixture; no /proc reads, model, server, CUDA, GPU or memory allocation",
        "sourcePins": {str(p.relative_to(ROOT)): h for p, h in PINS.items()},
        "cases": cases,
        "passed": all(case["passed"] for case in cases),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
