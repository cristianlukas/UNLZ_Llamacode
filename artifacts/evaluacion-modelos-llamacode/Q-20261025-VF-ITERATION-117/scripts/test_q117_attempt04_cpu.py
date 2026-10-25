#!/usr/bin/env python3
"""CPU-only AMD04 regressions: isolate worker oomd policy and preserve samples."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

TASK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK / "scripts"))
from resource_isolation_attempt04 import calculate_worker_limits, systemd_properties
from run_context_holdout_attempt04 import append_monitor_sample, verify_managed_oom_policy


def check(name, condition):
    return {"name": name, "passed": bool(condition)}


def main():
    cases = []
    meminfo = """MemTotal: 129507668 kB
MemAvailable: 112107668 kB
SwapFree: 5741164 kB
"""
    limits = calculate_worker_limits(meminfo)
    props = systemd_properties(limits)
    cases.append(check("AMD04 opts out of systemd-oomd PSI kill enrollment", limits["managed_oom_memory_pressure"] == "auto" and limits["managed_oom_memory_pressure_limit"] == "0%" and "--property=ManagedOOMMemoryPressure=auto" in props and not any("ManagedOOMMemoryPressureLimit" in x for x in props)))
    cases.append(check("AMD04 preserves cgroup memory/swap hard caps and kernel OOM containment", all(any(x.startswith(prefix) for x in props) for prefix in ("--property=MemoryHigh=", "--property=MemoryMax=", "--property=MemorySwapMax=", "--property=OOMPolicy=kill", "--property=KillMode=control-group"))))

    def ok_runner(args, **kwargs):
        return SimpleNamespace(returncode=0, stdout="ManagedOOMMemoryPressure=auto\nManagedOOMMemoryPressureLimit=0\n", stderr="")

    verified = verify_managed_oom_policy("/background.slice/llamacode-q117-context-1048576-seed-2026103-a04.service", runner=ok_runner)
    cases.append(check("worker preflight accepts effective ManagedOOMMemoryPressure=auto", verified["ManagedOOMMemoryPressure"] == "auto" and verified["ManagedOOMMemoryPressureLimit"] == "0"))

    def bad_runner(args, **kwargs):
        return SimpleNamespace(returncode=0, stdout="ManagedOOMMemoryPressure=kill\nManagedOOMMemoryPressureLimit=80%\n", stderr="")
    try:
        verify_managed_oom_policy("/background.slice/llamacode-q117-context-1048576-seed-2026103-a04.service", runner=bad_runner)
    except RuntimeError:
        bad_policy_rejected = True
    else:
        bad_policy_rejected = False
    cases.append(check("worker preflight fails closed if oomd PSI kill is re-enabled", bad_policy_rejected))

    with tempfile.TemporaryDirectory(prefix="q117-amd04-jsonl-") as tmp:
        path = Path(tmp) / "memory-monitor.jsonl"
        append_monitor_sample(path, {"sample": 1, "memAvailableGiB": 109.4})
        append_monitor_sample(path, {"sample": 2, "memAvailableGiB": 55.6})
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        cases.append(check("monitor appends and flushes each JSONL sample immediately", rows == [{"sample": 1, "memAvailableGiB": 109.4}, {"sample": 2, "memAvailableGiB": 55.6}]))

    runner = (TASK / "scripts/run_context_holdout_attempt04.py").read_text(encoding="utf-8")
    supervisor = (TASK / "scripts/q117_supervisor_attempt04.py").read_text(encoding="utf-8")
    cases.append(check("AMD04 uses the tested oomd verifier before server startup and flushes monitor samples", "oomd_policy = verify_managed_oom_policy(process_cgroup)" in runner and "monitor = Monitor(args.out_dir / \"memory-monitor.jsonl\")" in runner and "run_context_holdout_attempt04.py" in supervisor))

    result = {
        "taskId": "Q-20261025-VF-ITERATION-117",
        "amendment": "AMD04",
        "status": "pass" if all(row["passed"] for row in cases) else "fail",
        "checksPassed": sum(row["passed"] for row in cases),
        "checksTotal": len(cases),
        "modelOrServerStarted": False,
        "gpuUsed": False,
        "networkUsed": False,
        "cases": cases,
    }
    output = TASK / "receipts/q117-amd04-cpu-tests.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for row in cases:
        print(("PASS" if row["passed"] else "FAIL") + " " + row["name"])
    print(f"AMD04 CPU checks: {result['checksPassed']}/{result['checksTotal']}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
