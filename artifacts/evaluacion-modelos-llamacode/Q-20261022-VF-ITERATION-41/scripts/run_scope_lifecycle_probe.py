#!/usr/bin/env python3
"""CPU-only lifecycle canaries for tools.linux_eval_scope."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261022-VF-ITERATION-41"
LOCK = ROOT / "WORK_QUEUE.lock"
PROBE = TASK / "scripts/scope_lifecycle_probe.py"
OUT = TASK / "receipts/c41-05-scope-lifecycle.json"
TOKEN = "a5758823-c599-48e3-afe5-d34381057eed"


def show(unit):
    r = subprocess.run(
        ["sudo", "-n", "systemctl", "show", unit, "--no-pager", "-p",
         "Result", "-p", "ActiveState", "-p", "SubState", "-p", "ControlGroup",
         "-p", "MemoryHigh", "-p", "MemoryMax", "-p", "MemorySwapMax",
         "-p", "OOMPolicy", "-p", "KillMode", "-p", "ManagedOOMMemoryPressure",
         "-p", "ManagedOOMSwap"],
        text=True, capture_output=True, timeout=15)
    if r.returncode:
        return {"error": r.stderr[-1000:]}
    return dict(line.split("=", 1) for line in r.stdout.splitlines() if "=" in line)


def alive(pid):
    try:
        os.kill(int(pid), 0)
        state = Path(f"/proc/{pid}/stat").read_text().split()[2]
        return state not in {"Z", "X"}
    except PermissionError:
        return True
    except (OSError, TypeError, ValueError, IndexError):
        return False


def wait_report(path, process, timeout=10):
    deadline = time.monotonic() + timeout
    while not path.exists() and process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.01)
    return json.loads(path.read_text()) if path.exists() else None


def main():
    lock = json.loads(LOCK.read_text())
    if lock.get("task") != "Q-20261022-VF-ITERATION-41" or lock.get("token") != TOKEN:
        raise SystemExit("Q41 lock ownership changed; refusing lifecycle canary")
    sys.path.insert(0, str(ROOT))
    from tools.linux_eval_scope import popen_in_background_scope

    short_report = TASK / "receipts/c41-05-short-worker.json"
    long_report = TASK / "receipts/c41-05-long-worker.json"
    short_report.unlink(missing_ok=True)
    long_report.unlink(missing_ok=True)
    marker = "q41-scope-lifecycle"
    short = long = None
    short_worker = long_worker = None
    short_out = short_err = long_out = long_err = ""
    short_props = long_props = {}
    long_stop_error = None
    cleanup_error = None
    try:
        short = popen_in_background_scope(
            [sys.executable, str(PROBE), str(short_report), "short"],
            cwd=str(ROOT), env_overrides={"Q41_SCOPE_MARK": marker},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        short_worker = wait_report(short_report, short.process)
        short_props = show(short.unit) if short_worker else {}
        short_out, short_err = short.process.communicate(timeout=20)

        long = popen_in_background_scope(
            [sys.executable, str(PROBE), str(long_report), "long"],
            cwd=str(ROOT), env_overrides={"Q41_SCOPE_MARK": marker},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        long_worker = wait_report(long_report, long.process)
        long_props = show(long.unit) if long_worker else {}
        if not long_worker:
            raise RuntimeError("long-running worker did not write report")
        long.stop(timeout_seconds=15)
        long_out, long_err = long.process.communicate(timeout=5)
    except Exception as exc:
        cleanup_error = f"{type(exc).__name__}: {exc}"
    finally:
        if long is not None and long.process.poll() is None:
            try:
                long.stop(timeout_seconds=15)
                long_out, long_err = long.process.communicate(timeout=5)
            except Exception as exc:
                cleanup_error = cleanup_error or f"cleanup: {type(exc).__name__}: {exc}"

    short_after = show(short.unit) if short else {}
    long_after = show(long.unit) if long else {}
    short_active = short_after.get("ActiveState", "inactive") == "active"
    long_active = long_after.get("ActiveState", "inactive") == "active"
    short_child_alive = alive(short_worker.get("childPid")) if short_worker else None
    long_parent_alive = alive(long_worker.get("pid")) if long_worker else None
    long_child_alive = alive(long_worker.get("childPid")) if long_worker else None
    same_short_cgroup = bool(short_worker and short_worker.get("cgroup") == short_worker.get("childCgroup"))
    same_long_cgroup = bool(long_worker and long_worker.get("cgroup") == long_worker.get("childCgroup"))
    score_ok = bool(
        short_worker and long_worker
        and short_worker.get("oomScoreAdj") == "900"
        and short_worker.get("childOomScoreAdj") == "900"
        and long_worker.get("oomScoreAdj") == "900"
        and long_worker.get("childOomScoreAdj") == "900")
    acceptance = {
        "short_stdout_preserved": "Q41-LIFECYCLE-START" in short_out and "Q41-LIFECYCLE-END 23" in short_out,
        "short_exit_code_preserved": bool(short and short.process.returncode == 23),
        "environment_and_cwd_preserved": bool(
            short_worker and short_worker.get("marker") == marker and short_worker.get("cwd") == str(ROOT)),
        "oom_score_adjustment_inherited": score_ok,
        "short_scope_under_background_slice": bool(short_worker and "/background.slice/" in short_worker.get("cgroup", "")),
        "short_parent_child_share_scope": same_short_cgroup,
        "short_scope_cleaned": not short_active and short_child_alive is False,
        "long_scope_properties_confirmed": (
            long_props.get("OOMPolicy") == "kill"
            and long_props.get("KillMode") == "control-group"
            and long_props.get("ManagedOOMMemoryPressure") == "kill"
            and long_props.get("ManagedOOMSwap") == "kill"
            and long_props.get("ControlGroup", "").startswith("/background.slice/")),
        "long_has_no_memory_or_swap_cap": (
            long_props.get("MemoryHigh") == "infinity"
            and long_props.get("MemoryMax") == "infinity"
            and long_props.get("MemorySwapMax") == "infinity"),
        "long_parent_child_share_scope": same_long_cgroup,
        "explicit_stop_removed_process_tree": (
            long_parent_alive is False and long_child_alive is False and not long_active),
        "controller_survived": Path(f"/proc/{os.getpid()}").exists(),
        "no_controller_or_cleanup_error": cleanup_error is None,
    }
    result = {
        "taskId": "Q-20261022-VF-ITERATION-41",
        "checkedAtUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "shortUnit": short.unit if short else None,
        "longUnit": long.unit if long else None,
        "shortWorker": short_worker,
        "longWorker": long_worker,
        "shortPropertiesWhileRunning": short_props,
        "shortPropertiesAfterExit": short_after,
        "longPropertiesWhileRunning": long_props,
        "longPropertiesAfterStop": long_after,
        "shortReturnCode": short.process.returncode if short else None,
        "longReturnCode": long.process.returncode if long else None,
        "shortStdout": short_out[-3000:],
        "shortStderr": short_err[-1000:],
        "longStdout": long_out[-3000:],
        "longStderr": long_err[-1000:],
        "longWorkerAliveAfterStop": long_parent_alive,
        "longChildAliveAfterStop": long_child_alive,
        "shortChildAliveAfterExit": short_child_alive,
        "controllerError": cleanup_error,
        "acceptance": acceptance,
        "passed": all(acceptance.values()),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
