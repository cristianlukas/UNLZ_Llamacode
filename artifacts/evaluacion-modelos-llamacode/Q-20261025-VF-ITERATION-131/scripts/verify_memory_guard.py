#!/usr/bin/env python3
"""CPU-only replay of Q131's guard over successful ASTRA/SOL traces and pure fixtures."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TASK = Path(__file__).resolve().parents[1]
Q117 = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-117/runs/astra-1m-seed-2026103-attempt05/memory-monitor.jsonl"
Q127 = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-127/attempt01/runs/memory-trace.jsonl"
GIB = 1024 ** 3


def load_guard():
    path = TASK / "scripts/run_q4_screen.py"
    spec = importlib.util.spec_from_file_location("q131_controller", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lines(path):
    return [json.loads(row) for row in path.read_text(encoding="utf-8").splitlines() if row.strip()]


def normalize_astra(row):
    return {
        "mem": {"MemAvailable": row["memory"]["MemAvailable"]},
        "psi": row["psi"],
        "vmstat": {"oom_kill": row["oomKill"]},
        "processTreeRssBytes": None,
    }


def normalize_sol(row):
    return {
        "mem": {"MemAvailable": row["memAvailableBytes"]},
        "psi": {key: {"avg10": value} for key, value in row["psi"].items()},
        "vmstat": {"oom_kill": row["oomKill"]},
        "processTreeRssBytes": row.get("cgroup", {}).get("processTreeRssBytes"),
    }


def replay(module, rows, normalize):
    low = severe = 0
    first_reason = None
    baseline = rows[0]["oomKill"]
    for row in rows:
        low, severe, reason, _ = module.guard_transition(low, severe, normalize(row), baseline)
        if reason and first_reason is None:
            first_reason = reason
    return {"samples": len(rows), "firstStop": first_reason, "finalLowMemStreak": low,
            "finalSeverePsiStreak": severe, "noFalseStop": first_reason is None}


def snapshot(available_gib=80.0, some=0.0, full=0.0, oom=0, rss_gib=None):
    return {
        "mem": {"MemAvailable": int(available_gib * GIB)},
        "psi": {"some": {"avg10": some}, "full": {"avg10": full}},
        "vmstat": {"oom_kill": oom},
        "processTreeRssBytes": None if rss_gib is None else int(rss_gib * GIB),
    }


def main():
    module = load_guard()
    astra_rows = lines(Q117)
    sol_rows = lines(Q127)
    astra = replay(module, astra_rows, normalize_astra)
    sol = replay(module, sol_rows, normalize_sol)
    assert astra["samples"] == 707 and astra["noFalseStop"]
    assert sol["samples"] == 157 and sol["noFalseStop"]

    # Successful ASTRA used ~51 GiB RSS while maintaining ~58.7 GiB headroom.
    low, severe, reason, warnings = module.guard_transition(
        0, 0, snapshot(available_gib=58.6977, some=53.61, full=0.0, rss_gib=51.3056), 0)
    assert reason is None and low == 0 and severe == 0 and warnings
    high_rss = {"rssGiB": 51.3056, "memAvailableGiB": 58.6977,
                "moderateGlobalPsiPct": 53.61, "guardStopped": False}

    low = severe = 0
    stop_at = None
    for index in range(1, 16):
        some, full = (80.0, 0.0) if index % 2 else (0.0, 60.0)
        low, severe, reason, _ = module.guard_transition(
            low, severe, snapshot(available_gib=58.0, some=some, full=full), 0)
        if reason:
            stop_at = index
    assert stop_at == 15, f"alternating PSI must stop on sample15; got {stop_at}"

    low = severe = 0
    low_mem_stop = None
    for index in range(1, 16):
        low, severe, reason, _ = module.guard_transition(
            low, severe, snapshot(available_gib=19.9), 0)
        if reason:
            low_mem_stop = index
    assert low_mem_stop == 15

    _, _, oom_reason, _ = module.guard_transition(0, 0, snapshot(oom=1), 0)
    assert oom_reason == "system oom_kill counter increased"

    result = {
        "taskId": "Q-20261025-VF-ITERATION-131",
        "kind": "cpu_offline_memory_guard_validation",
        "result": "PASS",
        "newMemoryPressure": False,
        "modelInference": False,
        "historicalTraceReplays": {"ASTRA_DEFAULT_1M_Q117": astra, "SOL_TP2_Q127": sol},
        "highRssCase": high_rss,
        "syntheticInMemoryEdges": {
            "alternatingSomeFullSevereStopsAtSample": stop_at,
            "lowMemStopsAtSample": low_mem_stop,
            "oomStopsImmediately": oom_reason is not None,
        },
        "interpretation": "RSS/VRAM usage alone is not a stop condition; the tested Q131 guard continued both successful traces. This does not claim a general Codex crash detector.",
    }
    out = TASK / "receipts/q131-memory-guard-replay.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
