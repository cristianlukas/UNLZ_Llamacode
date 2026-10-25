#!/usr/bin/env python3
"""CPU-only tests for a versioned composite-OR PSI gate candidate."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-116"
CANDIDATE = TASK / "candidate/q116_composite_psi.py"
PREREG = TASK / "receipts/preregistration.json"
RESULT = TASK / "receipts/q116-composite-candidate.json"
pre = json.loads(PREREG.read_text())
expected_hashes = pre["candidateSourcesSha256"]
actual_hashes = {
    "helper": hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(),
    "runner": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
}
if actual_hashes != expected_hashes:
    raise SystemExit("candidate source hash differs from preregistration")

spec = importlib.util.spec_from_file_location("q116_candidate", CANDIDATE)
candidate = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(candidate)

def initial():
    return {"warning_full20": 0, "warning_some70": 0, "severe_full60": 0, "severe_some80": 0, "severe_any": 0}

def sample(psi, state):
    counts, warning, stop = candidate.pressure_gate_transition(psi, state)
    return {"counts": counts, "warning": warning, "stop": stop, "psi": psi}

def replay(series):
    state = initial()
    trace = []
    for index, psi in enumerate(series, 1):
        result = sample(psi, state)
        result["sample"] = index
        trace.append(result)
        state = result["counts"]
        if result["stop"]:
            break
    return trace

def alternating(n):
    return [{"full": 60.0, "some": 0.0} if i % 2 == 0 else {"full": 0.0, "some": 80.0} for i in range(n)]

def stable(n, metric, value):
    return [{"full": value if metric == "full" else 0.0, "some": value if metric == "some" else 0.0} for _ in range(n)]

cases = []
for name, series, expected_stop in (
    ("stable full=60 stops at 15", stable(15, "full", 60.0), 15),
    ("stable some=80 stops at 15", stable(15, "some", 80.0), 15),
    ("alternating severe OR stops at 15", alternating(15), 15),
    ("normal sample resets composite run; 14+normal+15 stops at absolute sample30", alternating(14)+[{"full": 0.0, "some": 0.0}]+alternating(15), 30),
    ("moderate full=46.52 warns at 30 without hard-stop", stable(30, "full", 46.52), None),
):
    trace = replay(series)
    stop_sample = next((row["sample"] for row in trace if row["stop"]), None)
    warnings = [row["sample"] for row in trace if row["warning"]]
    cases.append({"name": name, "expectedStopSample": expected_stop, "stopSample": stop_sample, "warningSamples": warnings, "passed": stop_sample == expected_stop and (not name.startswith("moderate") or warnings == [30]), "trace": trace})

assert all(case["passed"] for case in cases), cases
result = {
    "taskId": "Q-20261025-VF-ITERATION-116",
    "experimentId": "Q116-A2",
    "status": "pass",
    "checksPassed": sum(x["passed"] for x in cases),
    "checksTotal": len(cases),
    "sourceSha256": actual_hashes,
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
    print(("PASS" if case["passed"] else "FAIL"), case["name"], f"stop={case['stopSample']}")
print(f"Q116-A2 composite candidate: {result['checksPassed']}/{result['checksTotal']} PASS")
