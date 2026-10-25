#!/usr/bin/env python3
"""CPU-only regression checks; no inference, GPU, build, network, or memory allocation."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-117"
sys.path.insert(0, str(TASK / "scripts"))
from q117_pressure_guard import evaluate, initial_counts, cgroup_psi_diagnostic, evaluate_worker_cgroup
from q117_pressure_guard import telemetry


def sample(available=110.0, full=0.0, some=0.0, oom=0, rss_gib=None):
    value = {
        "memAvailableGiB": available,
        "memoryPsiAvg10Pct": {"some": some, "full": full},
        "oomKill": oom,
    }
    if rss_gib is not None:
        # Deliberately diagnostic-only. RSS must not enter the stop decision.
        value["processTreeRssGiB"] = rss_gib
    return value


def replay(series, initial_oom=0):
    counts = initial_counts()
    warnings = []
    stop = None
    for index, item in enumerate(series, 1):
        stop, counts, warning = evaluate(item, initial_oom, counts)
        if warning:
            warnings.append(index)
        if stop:
            return {"stopSample": index, "stopReason": stop, "warningSamples": warnings}
    return {"stopSample": None, "stopReason": None, "warningSamples": warnings}


def alternating(n):
    return [sample(full=60.0) if i % 2 == 0 else sample(some=80.0) for i in range(n)]


def stable(n, metric, value):
    return [sample(**{metric: value}) for _ in range(n)]


def main():
    cases = []

    high_rss = replay([sample(available=55.64, full=34.72, rss_gib=51.14) for _ in range(30)])
    cases.append({"name": "ASTRA 1M historical RSS 51.14 GiB / MemAvailable 55.64 GiB continues; PSI moderate warns at 30", "expectedStop": None, "expectedWarnings": [30], **high_rss, "passed": high_rss["stopSample"] is None and high_rss["warningSamples"] == [30]})

    full = replay(stable(15, "full", 60.0))
    cases.append({"name": "stable global full=60% stops at sample 15", "expectedStop": 15, "expectedWarnings": [], **full, "passed": full["stopSample"] == 15})

    some = replay(stable(15, "some", 80.0))
    cases.append({"name": "stable global some=80% stops at sample 15", "expectedStop": 15, "expectedWarnings": [], **some, "passed": some["stopSample"] == 15})

    alternating_case = replay(alternating(15))
    cases.append({"name": "composite severe OR alternation stops at sample 15", "expectedStop": 15, "expectedWarnings": [], **alternating_case, "passed": alternating_case["stopSample"] == 15})

    reset = replay(alternating(14) + [sample()] + alternating(15))
    cases.append({"name": "normal sample resets composite severe streak", "expectedStop": 30, "expectedWarnings": [], **reset, "passed": reset["stopSample"] == 30})

    low = replay([sample(available=31.99)])
    cases.append({"name": "MemAvailable below 32 GiB stops immediately", "expectedStop": 1, "expectedWarnings": [], **low, "passed": low["stopSample"] == 1})

    oom = replay([sample(oom=1)], initial_oom=0)
    cases.append({"name": "new global oom_kill stops immediately", "expectedStop": 1, "expectedWarnings": [], **oom, "passed": oom["stopSample"] == 1})

    try:
        telemetry.evaluate_sample({"memAvailableGiB": 100.0, "oomKill": 0}, 0, 0)
    except telemetry.TelemetryError:
        missing_telemetry_fails_closed = True
    else:
        missing_telemetry_fails_closed = False
    cases.append({"name": "missing PSI telemetry fails closed", "passed": missing_telemetry_fails_closed})

    cgroup_only = evaluate_worker_cgroup(
        {"memory_events": {"oom": 0, "oom_kill": 0}, "memory_swap_current_bytes": 4096,
         "psi": {"some": {"avg10": 81.53}, "full": {"avg10": 0.0}}},
        {"oom": 0, "oom_kill": 0}, 4096
    )
    global_normal = evaluate(sample(available=71.864), 0, initial_counts())
    cases.append({"name": "Monitor worker-cgroup decision path: cgroup-only PSI 81.53% is diagnostic, not a stop", "passed": cgroup_only[0] is None and cgroup_only[1]["severeDiagnostic"] is True and cgroup_only[1]["hardStop"] is False and cgroup_only[2] == 0 and global_normal[0] is None})

    cgroup_oom = evaluate_worker_cgroup(
        {"memory_events": {"oom": 1, "oom_kill": 0}, "memory_swap_current_bytes": 0,
         "psi": {"some": {"avg10": 0.0}, "full": {"avg10": 0.0}}},
        {"oom": 0, "oom_kill": 0}, 0
    )
    cases.append({"name": "worker cgroup OOM increase remains a hard stop", "passed": cgroup_oom[0] == "worker cgroup OOM event counter increased"})

    cgroup_swap = evaluate_worker_cgroup(
        {"memory_events": {"oom": 0, "oom_kill": 0}, "memory_swap_current_bytes": 4 * 1024 * 1024 + 1,
         "psi": {"some": {"avg10": 0.0}, "full": {"avg10": 0.0}}},
        {"oom": 0, "oom_kill": 0}, 0
    )
    cases.append({"name": "worker cgroup swap increase >4 MiB remains a hard stop", "passed": cgroup_swap[0] == "worker cgroup swap current increased by more than 4194304 bytes"})

    try:
        evaluate_worker_cgroup({"memory_events": {}, "memory_swap_current_bytes": 0, "psi": {}}, {"oom": 0, "oom_kill": 0}, 0)
    except telemetry.TelemetryError:
        cgroup_missing_fails_closed = True
    else:
        cgroup_missing_fails_closed = False
    cases.append({"name": "missing worker cgroup telemetry fails closed", "passed": cgroup_missing_fails_closed})

    runner_source = (TASK / "scripts/run_context_holdout.py").read_text(encoding="utf-8")
    cases.append({"name": "Monitor.sample uses the tested cgroup decision helper with no stale run_psi_stop reference", "passed": "evaluate_worker_cgroup(" in runner_source and "run_psi_stop" not in runner_source})

    result = {
        "taskId": "Q-20261025-VF-ITERATION-117",
        "status": "pass" if all(case["passed"] for case in cases) else "fail",
        "checksPassed": sum(case["passed"] for case in cases),
        "checksTotal": len(cases),
        "modelOrServerStarted": False,
        "gpuUsed": False,
        "networkUsed": False,
        "artificialMemoryGiB": 0,
        "productionChanged": False,
        "cases": cases,
    }
    output = TASK / "receipts/q117-cpu-guard-tests.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for case in cases:
        print(("PASS" if case["passed"] else "FAIL"), case["name"])
    print(f"Q117 CPU guard checks: {result['checksPassed']}/{result['checksTotal']}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
