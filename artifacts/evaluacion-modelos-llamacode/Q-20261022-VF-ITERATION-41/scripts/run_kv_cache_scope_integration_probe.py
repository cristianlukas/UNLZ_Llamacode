#!/usr/bin/env python3
"""Exercise tools.kv_cache_ab.start_server without launching a model."""
import datetime
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261022-VF-ITERATION-41"
LOCK = ROOT / "WORK_QUEUE.lock"
PROBE = TASK / "scripts/scope_lifecycle_probe.py"
REPORT = TASK / "receipts/c41-05-kv-cache-worker.json"
LOG = TASK / "receipts/c41-05-kv-cache-server.log"
OUT = TASK / "receipts/c41-05-kv-cache-integration.json"
TOKEN = "a5758823-c599-48e3-afe5-d34381057eed"


def alive(pid):
    try:
        os.kill(int(pid), 0)
        state = Path(f"/proc/{pid}/stat").read_text().split()[2]
        return state not in {"Z", "X"}
    except PermissionError:
        return True
    except (OSError, ValueError, TypeError, IndexError):
        return False


def show(unit):
    import subprocess
    r = subprocess.run(["sudo", "-n", "systemctl", "show", unit, "--no-pager",
                        "-p", "ActiveState", "-p", "SubState", "-p", "Result",
                        "-p", "OOMPolicy", "-p", "KillMode", "-p", "ManagedOOMMemoryPressure",
                        "-p", "ManagedOOMSwap", "-p", "MemoryHigh", "-p", "MemoryMax",
                        "-p", "MemorySwapMax"],
                       text=True, capture_output=True, timeout=15)
    return dict(line.split("=", 1) for line in r.stdout.splitlines() if "=" in line)


def main():
    lock = json.loads(LOCK.read_text())
    if lock.get("task") != "Q-20261022-VF-ITERATION-41" or lock.get("token") != TOKEN:
        raise SystemExit("Q41 lock ownership changed; refusing kv-cache integration canary")
    sys.path.insert(0, str(ROOT))
    from tools.kv_cache_ab import start_server

    REPORT.unlink(missing_ok=True)
    LOG.unlink(missing_ok=True)
    server = None
    worker = None
    stop_error = None
    stop_code = None
    try:
        server = start_server(
            Path(sys.executable), [str(PROBE), str(REPORT), "long"],
            {"Q41_SCOPE_MARK": "q41-kv-cache-integration"}, LOG,
            {"kind": "native"},
        )
        import time
        deadline = time.monotonic() + 10
        while not REPORT.exists() and server.process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        worker = json.loads(REPORT.read_text()) if REPORT.exists() else None
        scope = getattr(server.stop_callback, "__self__", None)
        unit = getattr(scope, "unit", None)
        properties = show(unit) if unit and worker else {}
        stop_code = server.stop()
    except Exception as exc:
        stop_error = f"{type(exc).__name__}: {exc}"
    finally:
        if server is not None and server.process.poll() is None:
            try:
                server.stop()
            except Exception as exc:
                stop_error = stop_error or f"cleanup: {type(exc).__name__}: {exc}"

    log_text = LOG.read_text(errors="replace") if LOG.exists() else ""
    unit_after = show(unit) if "unit" in locals() and unit else {}
    parent_alive = alive(worker.get("pid")) if worker else None
    child_alive = alive(worker.get("childPid")) if worker else None
    acceptance = {
        "worker_report_written": worker is not None,
        "linux_native_launch_used_scope": bool(worker and "/background.slice/" in worker.get("cgroup", "")),
        "scope_metadata_available": bool(properties.get("Result") == "success"),
        "systemd_oomd_candidate_confirmed": (
            properties.get("ManagedOOMMemoryPressure") == "kill"
            and properties.get("ManagedOOMSwap") == "kill"),
        "no_memory_or_swap_caps": (
            properties.get("MemoryHigh") == "infinity"
            and properties.get("MemoryMax") == "infinity"
            and properties.get("MemorySwapMax") == "infinity"),
        "oom_score_adjust_applied": bool(worker and worker.get("oomScoreAdj") == "900" and worker.get("childOomScoreAdj") == "900"),
        "log_path_received_output": "Q41-LIFECYCLE-START" in log_text,
        "explicit_stop_killed_tree": worker is not None and parent_alive is False and child_alive is False,
        "scope_inactive_after_stop": unit_after.get("ActiveState") in {"inactive", "failed"},
        "controller_had_no_error": stop_error is None,
    }
    result = {
        "taskId": "Q-20261022-VF-ITERATION-41",
        "checkedAtUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "unit": unit if "unit" in locals() else None,
        "worker": worker,
        "scopePropertiesWhileRunning": properties if "properties" in locals() else {},
        "scopePropertiesAfterStop": unit_after,
        "serverStopCode": stop_code,
        "parentAliveAfterStop": parent_alive,
        "childAliveAfterStop": child_alive,
        "logPath": str(LOG),
        "logTail": log_text[-3000:],
        "stopError": stop_error,
        "acceptance": acceptance,
        "passed": all(acceptance.values()),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
