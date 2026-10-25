#!/usr/bin/env python3
"""Replay the persisted ASTRA 1M telemetry through the exact Q117 AMD05 guard."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
TASK118 = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-118"
TASK117 = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-117"
TRACE = TASK117 / "runs/astra-1m-seed-2026103-attempt05/memory-monitor.jsonl"
RUN_RECEIPT = TASK117 / "runs/astra-1m-seed-2026103-attempt05/receipt.json"
RESULT_RECEIPT = TASK117 / "receipts/q117-amd05-result.json"
GUARD = TASK117 / "scripts/q117_pressure_guard_attempt05.py"
RUNNER = TASK117 / "scripts/run_context_holdout_attempt05.py"
EXPECTED_HASHES = {
    TRACE: "fb369806324110e6bb20a2a2a681af3cdf9b36583a6e1ccfc02b9e0eba1d6dd1",
    GUARD: "b4d42302e7d405abd5c59df5aa86bb7de6ef3bb91aef487b49acbebd1d24270e",
    RUNNER: "24435c412cc791d47687199fb7ab765c7a52aed6b189ac4598eea8dd9d8822b1",
}
GIB = 1024 ** 3


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def import_guard():
    spec = importlib.util.spec_from_file_location("q117_amd05_guard_replay", GUARD)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load the pinned AMD05 guard module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    fingerprints = {str(path.relative_to(ROOT)): sha256(path) for path in EXPECTED_HASHES}
    fingerprint_match = all(sha256(path) == expected for path, expected in EXPECTED_HASHES.items())
    runner_text = RUNNER.read_text(encoding="utf-8")
    exact_import = "from q117_pressure_guard_attempt05 import read_sample, evaluate, evaluate_worker_cgroup"
    generic_import = "from q117_pressure_guard import read_sample, evaluate, evaluate_worker_cgroup"
    import_match = exact_import in runner_text and generic_import not in runner_text

    guard = import_guard()
    run = json.loads(RUN_RECEIPT.read_text(encoding="utf-8"))
    q117 = json.loads(RESULT_RECEIPT.read_text(encoding="utf-8"))
    trace_hash = sha256(TRACE)
    q117_trace_hash = json.loads((TASK117 / "receipts/q117-amd05-result.json").read_text(encoding="utf-8"))["monitorSha256"]
    expected_run = q117["memory"]

    rows = [json.loads(line) for line in TRACE.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise RuntimeError("persisted telemetry trace is empty")
    baseline_oom = expected_run["globalOomBaseline"]
    counters = guard.initial_counts()
    global_stops = []
    global_warnings = []
    worker_stops = []
    cgroup_psi_severe_diagnostic_samples = []
    max_host_psi = {"some": 0.0, "full": 0.0}
    max_worker_psi = {"some": 0.0, "full": 0.0}
    min_available = float("inf")
    max_rss = 0
    host_oom_values = []

    first_run_cgroup = rows[0]["cgroup_memory"]["run"]
    worker_baseline_oom = first_run_cgroup["memory_events"]
    worker_baseline_swap = first_run_cgroup["memory_swap_current_bytes"]

    for index, row in enumerate(rows, 1):
        host_psi = row["memoryPsiAvg10Pct"]
        sample = {
            "memAvailableGiB": row["memAvailableGiB"],
            "memoryPsiAvg10Pct": host_psi,
            "oomKill": row["oomKill"],
        }
        stop, counters, warning = guard.evaluate(sample, baseline_oom, counters)
        if stop:
            global_stops.append({"sample": index, "reason": stop})
        if warning:
            global_warnings.append(index)
        min_available = min(min_available, float(row["memAvailableGiB"]))
        host_oom_values.append(row["oomKill"])
        for metric in ("some", "full"):
            max_host_psi[metric] = max(max_host_psi[metric], float(host_psi[metric]))
            worker_psi = row["cgroup_memory"]["run"]["psi"][metric]["avg10"]
            max_worker_psi[metric] = max(max_worker_psi[metric], float(worker_psi))
        max_rss = max(max_rss, int(row.get("process_tree_rss_bytes", 0)))

        run_cgroup = row["cgroup_memory"]["run"]
        worker_reason, worker_diagnostic, _ = guard.evaluate_worker_cgroup(
            run_cgroup, worker_baseline_oom, worker_baseline_swap
        )
        if worker_reason:
            worker_stops.append({"sample": index, "reason": worker_reason})
        if worker_diagnostic["severeDiagnostic"]:
            cgroup_psi_severe_diagnostic_samples.append(index)

    observed_min_rss_gib = max_rss / GIB
    receipt_min_available = expected_run["minMemAvailableGiB"]
    receipt_max_rss = expected_run["peakProcessTreeRssGiB"]
    receipt_max_psi = expected_run["peakGlobalPsiAvg10Pct"]
    observed_max_psi = max(max_host_psi.values())
    checks = {
        "inputFingerprintsMatchPreregistration": fingerprint_match,
        "liveRunnerImportedAttempt05NotGenericSibling": import_match,
        "traceHashMatchesQ117ResultReceipt": trace_hash == q117_trace_hash,
        "sampleCountMatchesReceipt": len(rows) == expected_run["sampleCount"],
        "minimumMemAvailableMatchesReceipt": abs(min_available - receipt_min_available) < 1e-6,
        "maximumRssMatchesReceipt": abs(observed_min_rss_gib - receipt_max_rss) < 1e-6,
        "maximumHostPsiMatchesReceipt": abs(observed_max_psi - receipt_max_psi) < 1e-6,
        "globalGuardNeverStopped": not global_stops,
        "workerOomOrSwapGuardNeverStopped": not worker_stops,
        "globalOomCounterNeverIncreased": min(host_oom_values) == max(host_oom_values) == baseline_oom,
        "successfulRunHadNoGuardAbort": run["monitor_abort_reason"] is None,
        "successfulRunHadNoWorkerSwapDelta": run["run_cgroup_memory_swap_delta_bytes"] == 0,
    }
    result = {
        "taskId": "Q-20261025-VF-ITERATION-118",
        "amendment": "AMD05-LIVE-TRACE-REPLAY",
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "checksPassed": sum(bool(value) for value in checks.values()),
        "checksTotal": len(checks),
        "sourceFingerprints": fingerprints,
        "trace": {
            "path": str(TRACE.relative_to(ROOT)),
            "sha256": trace_hash,
            "samples": len(rows),
            "minMemAvailableGiB": min_available,
            "maxProcessTreeRssGiB": observed_min_rss_gib,
            "maxHostPsiAvg10Pct": max_host_psi,
            "maxWorkerCgroupPsiAvg10Pct": max_worker_psi,
            "firstAndLastGlobalOomKill": [host_oom_values[0], host_oom_values[-1]],
            "firstModerateWarningSample": global_warnings[0] if global_warnings else None,
            "warningSamples": len(global_warnings),
            "globalStops": global_stops,
            "workerStops": worker_stops,
            "workerCgroupSeverePsiWasDiagnosticAtSamples": len(cgroup_psi_severe_diagnostic_samples),
            "firstWorkerCgroupSeverePsiSample": cgroup_psi_severe_diagnostic_samples[0] if cgroup_psi_severe_diagnostic_samples else None,
        },
        "runtime": {
            "modelOrServerStarted": False,
            "gpuUsed": False,
            "networkUsed": False,
            "artificialMemoryGiB": 0,
            "productionChanged": False,
            "sourceTraceModified": False,
        },
    }
    output = TASK118 / "receipts/q118-amd05-live-trace-replay.json"
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    for name, passed in checks.items():
        print(("PASS" if passed else "FAIL"), name)
    print(f"Trace replay: {result['checksPassed']}/{result['checksTotal']}")
    print(f"Samples={len(rows)} RSSmax={observed_min_rss_gib:.6f} GiB MemAvailableMin={min_available:.6f} GiB hostPSImax={observed_max_psi:.2f}%")
    print(f"Worker cgroup PSI severe samples={len(cgroup_psi_severe_diagnostic_samples)}; hard stops={len(global_stops) + len(worker_stops)}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
