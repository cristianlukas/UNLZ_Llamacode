#!/usr/bin/env python3
"""CPU-only live integration audit for the strict Q108 memory guard core."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TASK_ID = "Q-20261024-VF-ITERATION-109"
TOKEN = "a58e3117-4c47-49a1-9110-5c189c287a25"
RUN_DIR = ROOT / "artifacts/evaluacion-modelos-llamacode" / TASK_ID / "runs/live-guard-integration-01"
CORE_DIR = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-108/runner"
sys.path.insert(0, str(CORE_DIR))
import q108_guard_core as core  # noqa: E402


def assert_lock() -> None:
    lock = json.loads((ROOT / "WORK_QUEUE.lock").read_text(encoding="utf-8"))
    if lock.get("task_id") != TASK_ID or lock.get("token") != TOKEN:
        raise RuntimeError("Q109 lock mismatch; refusing test")


def proc_alive(proc: subprocess.Popen) -> bool:
    return proc.poll() is None


def stop_owned(proc: subprocess.Popen) -> None:
    if proc_alive(proc):
        proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def main() -> int:
    assert_lock()
    if RUN_DIR.exists():
        raise SystemExit(f"refusing to overwrite {RUN_DIR}")
    RUN_DIR.mkdir(parents=True)
    stop_reason_normal = RUN_DIR / "normal-stop-reason.txt"
    stop_reason_missing = RUN_DIR / "missing-telemetry-stop-reason.txt"
    baseline = core.read_host_sample(Path("/proc"))
    baseline_oom = baseline["oomKill"]
    baseline_reason, _, baseline_warning = core.evaluate_sample(baseline, baseline_oom, 0)
    if baseline_reason:
        raise SystemExit(f"base host sample already requires stop: {baseline_reason}")

    normal = subprocess.Popen(["/bin/sleep", "60"])
    control = None
    missing = None
    normal_samples = []
    try:
        assert_lock()
        for index in range(3):
            reason, streak, warning = core.monitor_once(
                normal.pid,
                lambda: core.read_host_sample(Path("/proc")),
                baseline_oom,
                0,
                stop_reason_normal,
            )
            sample = core.read_host_sample(Path("/proc"))
            normal_samples.append({
                "index": index + 1,
                "reason": reason,
                "severeStreak": streak,
                "warning": warning,
                "candidateAlive": proc_alive(normal),
                "memAvailableGiB": round(sample["memAvailableGiB"], 3),
                "memoryPsiAvg10Pct": sample["memoryPsiAvg10Pct"],
                "oomKill": sample["oomKill"],
            })
            if reason or not proc_alive(normal):
                break
            time.sleep(1)

        control = subprocess.Popen(["/bin/sleep", "60"])
        missing = subprocess.Popen(["/bin/sleep", "60"])
        assert_lock()
        missing_proc_root = RUN_DIR / "intentionally-missing-procfs"
        reason, streak, warning = core.monitor_once(
            missing.pid,
            lambda: core.read_host_sample(missing_proc_root),
            baseline_oom,
            0,
            stop_reason_missing,
        )
        try:
            missing.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        missing_stopped = not proc_alive(missing)
        control_alive = proc_alive(control)
        final_sample = core.read_host_sample(Path("/proc"))
        checks = {
            "baseSampleValidAndNoStop": baseline_reason is None,
            "threeLiveReadsContinue": len(normal_samples) == 3 and all(
                item["reason"] is None and item["candidateAlive"] for item in normal_samples
            ),
            "missingTelemetryFailsClosed": bool(reason and reason.startswith("memory telemetry unavailable:")),
            "missingTelemetryWritesReason": stop_reason_missing.exists() and stop_reason_missing.read_text().strip() == reason,
            "onlyDesignatedCandidateStopped": missing_stopped and control_alive,
            "normalCandidateHasNoStopFile": not stop_reason_normal.exists(),
            "noGlobalOomIncrement": final_sample["oomKill"] == baseline_oom,
            "completeFinalProcSample": set(final_sample["memoryPsiAvg10Pct"]) == {"some", "full"},
        }
        result = {
            "taskId": TASK_ID,
            "recordedAtUtc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "status": "pass" if all(checks.values()) else "fail",
            "baseline": baseline,
            "baselineWarningOnly": baseline_warning,
            "normalSamples": normal_samples,
            "missingTelemetry": {"reason": reason, "severeStreak": streak, "warning": warning},
            "missingCandidateExitCode": missing.returncode,
            "unrelatedControlAliveBeforeCleanup": control_alive,
            "finalSample": final_sample,
            "checks": checks,
            "modelOrServerStarted": False,
            "gpuUsed": False,
            "memoryAllocationGiB": 0,
            "foreignProcessSignaled": False,
        }
        (RUN_DIR / "q109-live-integration-result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if all(checks.values()) else 1
    finally:
        for proc in (missing, control, normal):
            if proc is not None:
                stop_owned(proc)


if __name__ == "__main__":
    raise SystemExit(main())
