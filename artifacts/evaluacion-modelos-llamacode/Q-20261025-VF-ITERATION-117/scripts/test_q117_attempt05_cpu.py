#!/usr/bin/env python3
"""CPU-only AMD05 regressions: pressure/headroom gate and worker isolation."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

TASK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK / "scripts"))
from resource_isolation_attempt05 import calculate_worker_limits, systemd_properties
from run_context_holdout_attempt05 import append_monitor_sample, verify_managed_oom_policy
from q117_pressure_guard_attempt05 import (
    evaluate as evaluate_guard, initial_counts, telemetry,
    evaluate_worker_cgroup,
)


def check(name, condition):
    return {"name": name, "passed": bool(condition)}


def sample(available=110.0, full=0.0, some=0.0, oom=0, rss_gib=None):
    value = {"memAvailableGiB": available,
             "memoryPsiAvg10Pct": {"some": some, "full": full},
             "oomKill": oom}
    if rss_gib is not None:
        value["processTreeRssGiB"] = rss_gib
    return value


def replay(series, initial_oom=0):
    counts = initial_counts()
    warnings = []
    for index, item in enumerate(series, 1):
        stop, counts, warning = evaluate_guard(item, initial_oom, counts)
        if warning:
            warnings.append(index)
        if stop:
            return {"stopSample": index, "stopReason": stop, "warningSamples": warnings}
    return {"stopSample": None, "stopReason": None, "warningSamples": warnings}


def main():
    cases = []
    prior_ast = replay([sample(available=55.64, full=34.72, rss_gib=51.14) for _ in range(30)])
    cases.append(check("historical ASTRA 1M high RSS and moderate PSI continue; warning remains advisory at sample 30", prior_ast["stopSample"] is None and prior_ast["warningSamples"] == [30]))

    amd04_like = replay([sample(available=77.065, full=63.11) for _ in range(30)])
    cases.append(check("AMD04-like severe global PSI at 77 GiB available does not stop", amd04_like["stopSample"] is None))

    historical_floor = replay([sample(available=55.64, full=60.0) for _ in range(30)])
    cases.append(check("severe global PSI at the successful ASTRA 1M memory floor continues", historical_floor["stopSample"] is None))

    below_threshold = replay([sample(available=47.99, full=60.0) for _ in range(14)])
    cases.append(check("severe PSI with MemAvailable below 48 GiB does not stop before 15 samples", below_threshold["stopSample"] is None))
    exact_stop = replay([sample(available=47.99, some=80.0) for _ in range(15)])
    cases.append(check("severe PSI plus MemAvailable below 48 GiB stops exactly at sample 15", exact_stop["stopSample"] == 15 and "MemAvailable <48 GiB" in (exact_stop["stopReason"] or "")))

    reset = replay([sample(available=77.0, full=60.0) for _ in range(10)]
                   + [sample(available=47.0, full=0.0)]
                   + [sample(available=47.0, full=60.0) for _ in range(14)])
    cases.append(check("high-memory severe streak does not carry across a normal sample into low headroom", reset["stopSample"] is None))

    immediate_low = replay([sample(available=31.99, full=60.0)])
    cases.append(check("MemAvailable below 32 GiB remains an immediate hard stop", immediate_low["stopSample"] == 1))
    global_oom = replay([sample(oom=1)], initial_oom=0)
    cases.append(check("global oom_kill increase remains an immediate hard stop", global_oom["stopSample"] == 1))
    try:
        evaluate_guard({"memAvailableGiB": 100.0, "oomKill": 0}, 0, initial_counts())
    except telemetry.TelemetryError:
        missing_host_telemetry = True
    else:
        missing_host_telemetry = False
    cases.append(check("required global telemetry still fails closed", missing_host_telemetry))

    cgroup_psi = evaluate_worker_cgroup(
        {"memory_events": {"oom": 0, "oom_kill": 0}, "memory_swap_current_bytes": 0,
         "psi": {"some": {"avg10": 92.0}, "full": {"avg10": 90.0}}},
        {"oom": 0, "oom_kill": 0}, 0)
    cases.append(check("high worker-cgroup PSI remains diagnostic without host low-headroom conjunction", cgroup_psi[0] is None and cgroup_psi[1]["hardStop"] is False))
    cgroup_oom = evaluate_worker_cgroup(
        {"memory_events": {"oom": 1, "oom_kill": 0}, "memory_swap_current_bytes": 0,
         "psi": {"some": {"avg10": 0.0}, "full": {"avg10": 0.0}}},
        {"oom": 0, "oom_kill": 0}, 0)
    cases.append(check("worker cgroup OOM remains a hard stop", cgroup_oom[0] == "worker cgroup OOM event counter increased"))
    cgroup_swap = evaluate_worker_cgroup(
        {"memory_events": {"oom": 0, "oom_kill": 0}, "memory_swap_current_bytes": 4 * 1024 * 1024 + 1,
         "psi": {"some": {"avg10": 0.0}, "full": {"avg10": 0.0}}},
        {"oom": 0, "oom_kill": 0}, 0)
    cases.append(check("worker cgroup swap growth above 4 MiB remains a hard stop", cgroup_swap[0] is not None))
    try:
        evaluate_worker_cgroup({"memory_events": {}, "memory_swap_current_bytes": 0, "psi": {}}, {"oom": 0, "oom_kill": 0}, 0)
    except telemetry.TelemetryError:
        missing_cgroup_telemetry = True
    else:
        missing_cgroup_telemetry = False
    cases.append(check("missing worker cgroup telemetry still fails closed", missing_cgroup_telemetry))

    meminfo = """MemTotal: 129507668 kB
MemAvailable: 112107668 kB
SwapFree: 5741164 kB
"""
    limits = calculate_worker_limits(meminfo)
    props = systemd_properties(limits)
    cases.append(check("AMD05 opts out of systemd-oomd PSI kill enrollment", limits["managed_oom_memory_pressure"] == "auto" and limits["managed_oom_memory_pressure_limit"] == "0%" and "--property=ManagedOOMMemoryPressure=auto" in props and not any("ManagedOOMMemoryPressureLimit" in x for x in props)))
    cases.append(check("AMD05 preserves cgroup memory/swap hard caps and kernel OOM containment", all(any(x.startswith(prefix) for x in props) for prefix in ("--property=MemoryHigh=", "--property=MemoryMax=", "--property=MemorySwapMax=", "--property=OOMPolicy=kill", "--property=KillMode=control-group"))))

    def ok_runner(args, **kwargs):
        return SimpleNamespace(returncode=0, stdout="ManagedOOMMemoryPressure=auto\nManagedOOMMemoryPressureLimit=0\n", stderr="")

    verified = verify_managed_oom_policy("/background.slice/llamacode-q117-context-1048576-seed-2026103-a05.service", runner=ok_runner)
    cases.append(check("worker preflight accepts effective ManagedOOMMemoryPressure=auto", verified["ManagedOOMMemoryPressure"] == "auto" and verified["ManagedOOMMemoryPressureLimit"] == "0"))

    def bad_runner(args, **kwargs):
        return SimpleNamespace(returncode=0, stdout="ManagedOOMMemoryPressure=kill\nManagedOOMMemoryPressureLimit=80%\n", stderr="")
    try:
        verify_managed_oom_policy("/background.slice/llamacode-q117-context-1048576-seed-2026103-a05.service", runner=bad_runner)
    except RuntimeError:
        bad_policy_rejected = True
    else:
        bad_policy_rejected = False
    cases.append(check("worker preflight fails closed if oomd PSI kill is re-enabled", bad_policy_rejected))

    with tempfile.TemporaryDirectory(prefix="q117-amd05-jsonl-") as tmp:
        path = Path(tmp) / "memory-monitor.jsonl"
        append_monitor_sample(path, {"sample": 1, "memAvailableGiB": 109.4})
        append_monitor_sample(path, {"sample": 2, "memAvailableGiB": 55.6})
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        cases.append(check("monitor appends and flushes each JSONL sample immediately", rows == [{"sample": 1, "memAvailableGiB": 109.4}, {"sample": 2, "memAvailableGiB": 55.6}]))

    runner = (TASK / "scripts/run_context_holdout_attempt05.py").read_text(encoding="utf-8")
    supervisor = (TASK / "scripts/q117_supervisor_attempt05.py").read_text(encoding="utf-8")
    cases.append(check("AMD05 uses the tested oomd verifier before server startup and flushes monitor samples", "oomd_policy = verify_managed_oom_policy(process_cgroup)" in runner and "monitor = Monitor(args.out_dir / \"memory-monitor.jsonl\")" in runner and "run_context_holdout_attempt05.py" in supervisor))
    cases.append(check("AMD05 runner imports the separate PSI-plus-headroom guard", "from q117_pressure_guard_attempt05 import read_sample, evaluate, evaluate_worker_cgroup" in runner))
    cases.append(check("AMD05 oomd verifier binds to the AMD05 unit prefix and requires a service suffix", "seed-2026103-a05" in runner and 'unit.endswith(".service")' in runner and "seed-2026103-a04" not in runner))

    result = {
        "taskId": "Q-20261025-VF-ITERATION-117",
        "amendment": "AMD05",
        "status": "pass" if all(row["passed"] for row in cases) else "fail",
        "checksPassed": sum(row["passed"] for row in cases),
        "checksTotal": len(cases),
        "modelOrServerStarted": False,
        "gpuUsed": False,
        "networkUsed": False,
        "cases": cases,
    }
    output = TASK / "receipts/q117-amd05-cpu-tests.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for row in cases:
        print(("PASS" if row["passed"] else "FAIL") + " " + row["name"])
    print(f"AMD05 CPU checks: {result['checksPassed']}/{result['checksTotal']}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
