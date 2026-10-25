#!/usr/bin/env python3
"""CPU replay of Q97 severe PSI streaks, including alternating PSI dimensions."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-116"
Q97 = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-97/scripts/q97_supervised_bcb.py"
PREREG = TASK / "receipts/preregistration.json"
RESULT = TASK / "receipts/q116-mixed-severe-psi.json"

pre = json.loads(PREREG.read_text())
q97_hash = hashlib.sha256(Q97.read_bytes()).hexdigest()
runner_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
if pre["sourceSha256"].get("q97") != q97_hash:
    raise SystemExit("Q97 source hash differs from preregistration")
if pre["sourceSha256"].get("runner") != runner_hash:
    raise SystemExit("Q116 runner hash differs from preregistration")

spec = importlib.util.spec_from_file_location("q97_q116", Q97)
q97 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(q97)

def initial_counts():
    return {
        "warning_full20": 0,
        "warning_some70": 0,
        "severe_full60": 0,
        "severe_some80": 0,
    }

def replay(samples):
    counts = initial_counts()
    trace = []
    for index, psi in enumerate(samples, 1):
        counts, warning, stop = q97.pressure_gate_transition(psi, counts)
        trace.append({
            "sample": index,
            "globalPsi": psi,
            "warning": warning,
            "stop": stop,
            "counts": dict(counts),
            "compositeSevere": psi["full"] >= 60.0 or psi["some"] >= 80.0,
        })
        if stop:
            break
    return trace

def alternating(n):
    return [
        {"full": 60.0, "some": 0.0} if i % 2 == 0
        else {"full": 0.0, "some": 80.0}
        for i in range(n)
    ]

def stable(n, key, value):
    return [{"full": value if key == "full" else 0.0,
             "some": value if key == "some" else 0.0} for _ in range(n)]

cases = []
for name, series in (
    ("stable full=60 stops at its 15th sample", stable(15, "full", 60.0)),
    ("stable some=80 stops at its 15th sample", stable(15, "some", 80.0)),
    ("alternating OR-severe remains true for 15 samples", alternating(15)),
    ("one normal sample breaks a 14+14 alternating sequence", alternating(14) + [{"full": 0.0, "some": 0.0}] + alternating(14)),
):
    trace = replay(series)
    stop_sample = next((x["sample"] for x in trace if x["stop"]), None)
    cases.append({
        "name": name,
        "samplesSupplied": len(series),
        "stopSample": stop_sample,
        "warnings": [x["sample"] for x in trace if x["warning"]],
        "finalCounts": trace[-1]["counts"] if trace else initial_counts(),
        "compositeSevereRunAtEnd": sum(1 for x in trace if x["compositeSevere"]),
        "trace": trace,
    })

assert cases[0]["stopSample"] == 15, cases[0]
assert cases[1]["stopSample"] == 15, cases[1]
assert cases[2]["stopSample"] is None, cases[2]
assert cases[2]["compositeSevereRunAtEnd"] == 15, cases[2]
assert all(x["counts"]["severe_full60"] <= 1 and x["counts"]["severe_some80"] <= 1 for x in cases[2]["trace"])
assert cases[2]["finalCounts"]["severe_full60"] == 1
assert cases[2]["finalCounts"]["severe_some80"] == 0
assert cases[3]["stopSample"] is None, cases[3]

result = {
    "taskId": "Q-20261025-VF-ITERATION-116",
    "experimentId": "Q116-A1",
    "status": "behavior_observed",
    "caseCount": len(cases),
    "sourceSha256": {"q97": q97_hash, "runner": runner_hash},
    "policyWording": "global PSI full>=60% OR some>=80% for 15 consecutive samples",
    "compositeSevereStopsAt15": cases[2]["stopSample"] == 15,
    "gpuUsed": False,
    "twoRtx3090FixtureOnly": True,
    "modelOrServerStarted": False,
    "buildRun": False,
    "networkUsed": False,
    "artificialMemoryGiB": 0,
    "productionChanged": False,
    "cases": cases,
}
RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
for case in cases:
    print(f"OBSERVED {case['name']}: stopSample={case['stopSample']} finalCounts={case['finalCounts']}")
print(f"Q116-A1 replayed {len(cases)} cases; composite OR stop at sample 15: {result['compositeSevereStopsAt15']}")
