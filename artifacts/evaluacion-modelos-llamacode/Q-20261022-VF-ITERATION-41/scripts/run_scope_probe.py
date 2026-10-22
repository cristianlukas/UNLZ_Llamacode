#!/usr/bin/env python3
"""Check system-manager scope semantics for a future Popen wrapper."""
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
WORKER = TASK / "scripts/scope_probe.py"
REPORT = TASK / "receipts/c41-03-scope-worker.json"
OUT = TASK / "receipts/c41-03-scope-semantics.json"


def show(unit):
    r = subprocess.run(["sudo", "-n", "systemctl", "show", unit, "--no-pager",
                        "-p", "ActiveState", "-p", "SubState", "-p", "ControlGroup",
                        "-p", "MemoryHigh", "-p", "MemoryMax", "-p", "MemorySwapMax",
                        "-p", "OOMPolicy", "-p", "KillMode", "-p", "TasksMax",
                        "-p", "CPUQuotaPerSecUSec"], text=True, capture_output=True, timeout=15)
    if r.returncode:
        return {"error": r.stderr[-1000:]}
    return dict(line.split("=", 1) for line in r.stdout.splitlines() if "=" in line)


def main():
    lock = json.loads(LOCK.read_text())
    if lock.get("task") != "Q-20261022-VF-ITERATION-41" or lock.get("token") != "a5758823-c599-48e3-afe5-d34381057eed":
        raise SystemExit("Q41 lock ownership changed; refusing probe")
    REPORT.unlink(missing_ok=True)
    unit = f"llamacode-q41-scope-{os.getpid()}-{uuid.uuid4().hex[:5]}.scope"
    marker = "inherited-without-setenv"
    env = os.environ.copy()
    env["Q41_SCOPE_MARK"] = marker
    command = [
        "sudo", "-n", "-E", "systemd-run", "--system", "--scope", "--quiet",
        f"--unit={unit.removesuffix('.scope')}", "--slice=background.slice",
        f"--uid={os.getuid()}", f"--gid={os.getgid()}",
        "--property=KillMode=control-group", "--property=MemoryHigh=120M",
        "--property=MemoryMax=128M", "--property=MemorySwapMax=0",
        "--property=OOMPolicy=kill", "--property=TasksMax=16",
        "--property=CPUQuota=200%", "--",
        sys.executable, str(WORKER), str(REPORT),
    ]
    proc = subprocess.Popen(command, cwd=ROOT, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    deadline = time.monotonic() + 8
    while not REPORT.exists() and proc.poll() is None and time.monotonic() < deadline:
        time.sleep(0.1)
    properties = show(unit) if REPORT.exists() else {}
    stdout, stderr = proc.communicate(timeout=15)
    worker = json.loads(REPORT.read_text()) if REPORT.exists() else None
    cleaned = subprocess.run(["sudo", "-n", "systemctl", "is-active", unit],
                             text=True, capture_output=True, timeout=10)
    is_active_after = cleaned.stdout.strip() if cleaned.returncode == 0 else "inactive-or-removed"
    result = {
        "taskId": "Q-20261022-VF-ITERATION-41",
        "checkedAtUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "unit": unit,
        "sudoPreserveEnvUsed": True,
        "expectedEnvMarker": marker,
        "expectedCwd": str(ROOT),
        "systemdRunReturnCode": proc.returncode,
        "stdout": stdout,
        "stderr": stderr[-2000:],
        "unitPropertiesWhileRunning": properties,
        "worker": worker,
        "scopeStateAfterExit": is_active_after,
        "acceptance": {
            "stdout_inherited": "Q41-SCOPE-START" in stdout and "Q41-SCOPE-END 23" in stdout,
            "exit_code_preserved": proc.returncode == 23,
            "environment_inherited": bool(worker and worker.get("envMarker") == marker),
            "cwd_preserved": bool(worker and worker.get("cwd") == str(ROOT)),
            "uid_gid_preserved": bool(worker and worker.get("uid") == os.getuid() and worker.get("gid") == os.getgid()),
            "scope_cgroup_system_background": bool(worker and "/background.slice/" in worker.get("cgroup", "") and "user@" not in worker.get("cgroup", "")),
            "limits_effective": bool(worker and worker.get("memoryHigh") == str(120*1024*1024) and worker.get("memoryMax") == str(128*1024*1024) and worker.get("memorySwapMax") == "0" and worker.get("oomGroup") == "1"),
            "oom_policy_and_kill_mode_effective": properties.get("OOMPolicy") == "kill" and properties.get("KillMode") == "control-group",
            "scope_cleaned_after_exit": is_active_after != "active",
        },
    }
    result["passed"] = all(result["acceptance"].values())
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
