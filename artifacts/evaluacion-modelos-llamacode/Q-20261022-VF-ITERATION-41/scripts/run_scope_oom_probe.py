#!/usr/bin/env python3
"""OOM containment regression for a system-manager scope launched via Popen."""
import datetime
import json
import os
import pathlib
import subprocess
import sys
import time
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261022-VF-ITERATION-41"
LOCK = ROOT / "WORK_QUEUE.lock"
WORKER = TASK / "scripts/oom_worker.py"
REPORT = TASK / "receipts/c41-04-attempt-04-worker.json"
OUT = TASK / "receipts/c41-04-attempt-04-scope-oom-containment.json"
TOKEN = "a5758823-c599-48e3-afe5-d34381057eed"


def show(unit):
    r = subprocess.run(
        ["sudo", "-n", "systemctl", "show", unit, "--no-pager", "-p", "Result",
         "-p", "ActiveState", "-p", "SubState", "-p", "ControlGroup",
         "-p", "MemoryHigh", "-p", "MemoryMax", "-p", "MemorySwapMax",
         "-p", "OOMPolicy", "-p", "KillMode", "-p", "TasksMax",
         "-p", "CPUQuotaPerSecUSec"],
        text=True, capture_output=True, timeout=15)
    if r.returncode:
        return {"error": r.stderr[-1000:]}
    return dict(line.split("=", 1) for line in r.stdout.splitlines() if "=" in line)


def normalize_cgroup(raw):
    """Accept either /path from oom_worker or 0::/path from procfs."""
    if not raw:
        return ""
    for line in raw.splitlines():
        if line.startswith("0::"):
            return line.split(":", 2)[2]
    return raw.strip()


def parse_events(text):
    try:
        return {key: int(value) for key, value in (line.split() for line in text.splitlines())}
    except (ValueError, TypeError):
        return {}


def read_events_handle(handle):
    if handle is None:
        return {}
    try:
        handle.seek(0)
        return parse_events(handle.read())
    except OSError:
        return {}


def read_events_path(cgroup):
    if not cgroup:
        return {}
    p = pathlib.Path("/sys/fs/cgroup") / cgroup.lstrip("/") / "memory.events"
    try:
        return parse_events(p.read_text())
    except OSError:
        return {}


def alive(pid):
    try:
        pid = int(pid)
        os.kill(pid, 0)
        state = pathlib.Path(f"/proc/{pid}/stat").read_text().split()[2]
        return state not in {"Z", "X"}
    except PermissionError:
        return True
    except (OSError, ValueError, IndexError, TypeError):
        return False


def stop_owned_scope(unit):
    """Stop only the unique transient scope created by this controller."""
    return subprocess.run(["sudo", "-n", "systemctl", "stop", unit],
                          text=True, capture_output=True, timeout=15)


def main():
    lock = json.loads(LOCK.read_text())
    if lock.get("task") != "Q-20261022-VF-ITERATION-41" or lock.get("token") != TOKEN:
        raise SystemExit("Q41 lock ownership changed; refusing scope OOM test")

    REPORT.unlink(missing_ok=True)
    unit = f"llamacode-q41-scope-oom-{os.getpid()}-{uuid.uuid4().hex[:5]}.scope"
    base = os.environ.copy()
    base["Q41_WORKER_REPORT"] = str(REPORT)
    base["Q41_OOM_DELAY_S"] = "0.6"
    controller_pid = os.getpid()
    command = [
        "sudo", "-n", "-E", "systemd-run", "--system", "--scope", "--quiet",
        f"--unit={unit.removesuffix('.scope')}", "--slice=background.slice",
        f"--uid={os.getuid()}", f"--gid={os.getgid()}",
        "--property=KillMode=control-group", "--property=MemoryHigh=120M",
        "--property=MemoryMax=128M", "--property=MemorySwapMax=0",
        "--property=OOMPolicy=kill", "--property=TasksMax=16",
        "--property=CPUQuota=200%",
        "--setenv=Q41_WORKER_REPORT=" + str(REPORT),
        "--setenv=Q41_OOM_DELAY_S=0.6", "--", sys.executable, str(WORKER),
    ]
    proc = None
    worker = None
    event_handle = None
    cgroup = ""
    child_cgroup = ""
    baseline = {}
    events_during_scope = {}
    events_after_exit_unattributed = {}
    cgroup_path = None
    props_before = {}
    stdout = ""
    stderr = ""
    controller_error = None
    oom_seen = False
    try:
        proc = subprocess.Popen(command, cwd=ROOT, env=base, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        deadline = time.monotonic() + 20
        while not REPORT.exists() and proc.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        if REPORT.exists():
            worker = json.loads(REPORT.read_text())
            cgroup = normalize_cgroup(worker.get("cgroup", ""))
            child_cgroup = normalize_cgroup(worker.get("child_cgroup", ""))
            cgroup_path = pathlib.Path("/sys/fs/cgroup") / cgroup.lstrip("/")
            event_path = cgroup_path / "memory.events"
            event_handle = event_path.open("r")
            baseline = read_events_handle(event_handle)
            events_during_scope = dict(baseline)
            props_before = show(unit)
            deadline = time.monotonic() + 20
            while proc.poll() is None and time.monotonic() < deadline:
                if cgroup_path.exists():
                    events_during_scope = read_events_handle(event_handle)
                if int(events_during_scope.get("oom_kill", 0)) > int(baseline.get("oom_kill", 0)):
                    oom_seen = True
                    break
                time.sleep(0.002)
        else:
            raise RuntimeError("worker did not write its report before timeout")
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            stop_owned_scope(unit)
            stdout, stderr = proc.communicate(timeout=15)
    except Exception as exc:
        controller_error = f"{type(exc).__name__}: {exc}"
    finally:
        # Never leave a child behind if parsing, sampling, or communicate fails.
        if proc is not None and proc.poll() is None:
            try:
                stop_owned_scope(unit)
                stdout, stderr = proc.communicate(timeout=15)
            except Exception as exc:
                controller_error = controller_error or f"cleanup: {type(exc).__name__}: {exc}"

    worker_alive = alive(worker.get("worker_pid")) if worker else None
    child_alive = alive(worker.get("child_pid")) if worker else None
    if worker and (worker_alive or child_alive):
        try:
            stop_owned_scope(unit)
            time.sleep(0.1)
        except Exception as exc:
            controller_error = controller_error or f"descendant cleanup: {type(exc).__name__}: {exc}"
        worker_alive = alive(worker.get("worker_pid"))
        child_alive = alive(worker.get("child_pid"))

    cgroup_exists_after_run = bool(cgroup_path and cgroup_path.exists())
    if cgroup_exists_after_run:
        events_during_scope = read_events_handle(event_handle)
    else:
        # After unit removal, a retained kernfs descriptor may expose ancestor
        # counters; record them for diagnosis but never attribute them to scope.
        events_after_exit_unattributed = read_events_handle(event_handle)
    oom_delta_during_scope = int(events_during_scope.get("oom_kill", 0)) - int(baseline.get("oom_kill", 0))
    props_after = show(unit)
    jr = subprocess.run(["sudo", "-n", "journalctl", "--unit", unit,
                         "--no-pager", "-o", "cat"],
                        text=True, capture_output=True, timeout=15)
    journal = jr.stdout if jr.returncode == 0 else jr.stderr
    if event_handle is not None:
        event_handle.close()

    acceptance = {
        "worker_report_written": worker is not None,
        "scope_and_child_share_background_cgroup": bool(
            worker and cgroup == child_cgroup and cgroup.startswith("/background.slice/")
            and "user@" not in cgroup),
        "limits_and_group_oom_effective": bool(
            worker and worker.get("memory_high") == str(120 * 1024 * 1024)
            and worker.get("memory_max") == str(128 * 1024 * 1024)
            and worker.get("memory_swap_max") == "0"
            and worker.get("oom_group") == "1"),
        "unit_properties_confirmed_before_oom": (
            props_before.get("OOMPolicy") == "kill"
            and props_before.get("KillMode") == "control-group"
            and props_before.get("MemoryMax") == str(128 * 1024 * 1024)),
        "scope_oom_confirmed": (
            oom_delta_during_scope > 0
            or props_after.get("Result") == "oom-kill"
            or "oom killer" in journal.lower()
            or "oom-kill" in journal.lower()),
        "worker_and_child_terminated": bool(worker and worker_alive is False and child_alive is False),
        "controller_survived": pathlib.Path(f"/proc/{controller_pid}").exists(),
        "allocation_did_not_complete": "UNEXPECTED-ALLOC-SUCCESS" not in stdout,
        "scope_client_returned_after_worker_exit": proc is not None and proc.poll() is not None,
        "controller_had_no_internal_error": controller_error is None,
    }
    result = {
        "taskId": "Q-20261022-VF-ITERATION-41",
        "attempt": 4,
        "checkedAtUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "unit": unit,
        "controllerPid": controller_pid,
        "controllerCgroup": pathlib.Path("/proc/self/cgroup").read_text().strip(),
        "controllerSurvived": acceptance["controller_survived"],
        "systemdRunReturnCode": proc.returncode if proc is not None else None,
        "stdout": stdout[-4000:],
        "stderr": stderr[-2000:],
        "controllerError": controller_error,
        "propertiesWhileRunning": props_before,
        "propertiesAfterExit": props_after,
        "cgroup": cgroup,
        "childCgroup": child_cgroup,
        "memoryEventsBaseline": baseline,
        "cgroupStillExistsAfterRun": cgroup_exists_after_run,
        "memoryEventsDuringScope": events_during_scope,
        "oomKillDeltaDuringScope": oom_delta_during_scope,
        "memoryEventsAfterExitUnattributed": events_after_exit_unattributed,
        "journalTail": journal[-3000:],
        "worker": worker,
        "workerAliveAfterRun": worker_alive,
        "childAliveAfterRun": child_alive,
        "acceptance": acceptance,
        "passed": all(acceptance.values()),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
