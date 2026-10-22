#!/usr/bin/env python3
"""Run a CPU-only OOM containment regression in one disposable system service."""
import datetime
import json
import os
import pathlib
import subprocess
import sys
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261022-VF-ITERATION-41"
LOCK = ROOT / "WORK_QUEUE.lock"
WORKER = TASK / "scripts/oom_worker.py"
REPORT = TASK / "receipts/c41-02-worker.json"
OUT = TASK / "receipts/c41-02-oom-containment.json"


def show(unit):
    result = subprocess.run(
        ["sudo", "-n", "systemctl", "show", unit, "--no-pager",
         "-p", "Result", "-p", "MemoryHigh", "-p", "MemoryMax",
         "-p", "MemorySwapMax", "-p", "OOMPolicy", "-p", "OOMScoreAdjust",
         "-p", "KillMode", "-p", "TasksMax", "-p", "CPUQuotaPerSecUSec",
         "-p", "ControlGroup", "-p", "ExecMainCode", "-p", "ExecMainStatus"],
        text=True, capture_output=True, timeout=15)
    if result.returncode:
        raise RuntimeError(result.stderr[-2000:])
    return dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)


def alive(pid):
    try:
        pid = int(pid)
        os.kill(pid, 0)
        stat = pathlib.Path(f"/proc/{pid}/stat").read_text().split()
        return len(stat) < 3 or stat[2] not in {"Z", "X"}
    except (ProcessLookupError, ValueError):
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def main():
    lock = json.loads(LOCK.read_text())
    if lock.get("task") != "Q-20261022-VF-ITERATION-41" or lock.get("token") != "a5758823-c599-48e3-afe5-d34381057eed":
        raise SystemExit("Q41 lock ownership changed; refusing test")
    REPORT.unlink(missing_ok=True)
    unit = f"llamacode-q41-oom-{os.getpid()}-{uuid.uuid4().hex[:6]}.service"
    controller_pid = os.getpid()
    command = [
        "sudo", "-n", "systemd-run", "--system", "--wait", "--pipe", "--quiet",
        f"--unit={unit.removesuffix('.service')}", "--slice=background.slice",
        f"--uid={os.getuid()}", f"--gid={os.getgid()}",
        "--property=Type=exec", "--property=KillMode=control-group",
        "--property=MemoryHigh=120M", "--property=MemoryMax=128M",
        "--property=MemorySwapMax=0", "--property=OOMPolicy=kill",
        "--property=OOMScoreAdjust=900", "--property=ManagedOOMMemoryPressure=auto",
        "--property=TasksMax=16", "--property=CPUQuota=200%",
        "--property=RuntimeMaxSec=30s", f"--setenv=Q41_WORKER_REPORT={REPORT}",
        sys.executable, str(WORKER),
    ]
    try:
        run = subprocess.run(command, text=True, capture_output=True, timeout=45)
        returncode, stdout, stderr = run.returncode, run.stdout, run.stderr
    except subprocess.TimeoutExpired as exc:
        subprocess.run(["sudo", "-n", "systemctl", "stop", unit],
                       text=True, capture_output=True, timeout=15)
        returncode = -1
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
    props = show(unit)
    journal = subprocess.run(
        ["sudo", "-n", "journalctl", "--unit", unit, "--no-pager", "-o", "cat"],
        text=True, capture_output=True, timeout=15)
    journal_text = journal.stdout if journal.returncode == 0 else journal.stderr
    worker = json.loads(REPORT.read_text()) if REPORT.exists() else None
    controller_survived = pathlib.Path(f"/proc/{controller_pid}").exists()
    worker_alive = alive(worker.get("worker_pid")) if worker else None
    child_alive = alive(worker.get("child_pid")) if worker else None
    acceptance = {
        "oom_confined_to_test_unit": props.get("Result") == "oom-kill",
        "memory_max_128m": props.get("MemoryMax") == str(128 * 1024 * 1024),
        "memory_high_120m": props.get("MemoryHigh") == str(120 * 1024 * 1024),
        "swap_disabled": props.get("MemorySwapMax") == "0",
        "oom_policy_kill": props.get("OOMPolicy") == "kill",
        "kill_mode_control_group": props.get("KillMode") == "control-group",
        "worker_cgroup_outside_user_manager": bool(worker and "/background.slice/" in worker.get("cgroup", "") and "user@" not in worker.get("cgroup", "")),
        "worker_reports_effective_limits": bool(worker and worker.get("memory_max") == str(128 * 1024 * 1024) and worker.get("memory_swap_max") == "0" and worker.get("oom_group") == "1"),
        "worker_and_child_terminated": bool(worker and worker_alive is False and child_alive is False),
        "controller_survived": controller_survived,
        "oom_logged": "killed by the oom killer" in journal_text.lower() or props.get("Result") == "oom-kill",
        "worker_started": worker is not None,
        "allocation_did_not_complete": "UNEXPECTED-ALLOC-SUCCESS" not in stdout,
    }
    result = {
        "taskId": "Q-20261022-VF-ITERATION-41",
        "checkedAtUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "unit": unit,
        "controllerPid": controller_pid,
        "controllerCgroup": pathlib.Path("/proc/self/cgroup").read_text().strip(),
        "controllerSurvived": controller_survived,
        "systemdRunReturnCode": returncode,
        "systemdRunStdoutTail": stdout[-4000:],
        "systemdRunStderrTail": stderr[-2000:],
        "unitProperties": props,
        "journalTail": journal_text[-4000:],
        "worker": worker,
        "workerAliveAfterRun": worker_alive,
        "childAliveAfterRun": child_alive,
        "acceptance": acceptance,
        "passed": all(acceptance.values()),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    if worker_alive or child_alive:
        subprocess.run(["sudo", "-n", "systemctl", "stop", unit],
                       text=True, capture_output=True, timeout=15)
    subprocess.run(["sudo", "-n", "systemctl", "reset-failed", unit],
                   text=True, capture_output=True, timeout=15)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
