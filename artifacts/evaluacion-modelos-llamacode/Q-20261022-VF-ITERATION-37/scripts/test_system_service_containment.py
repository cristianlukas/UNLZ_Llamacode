#!/usr/bin/env python3
"""Show a test worker OOM stays in its systemd system-service cgroup."""
import datetime
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261022-VF-ITERATION-37"
LOCK = ROOT / "WORK_QUEUE.lock"
TASK_ID = "Q-20261022-VF-ITERATION-37"
WORKER = TASK / "scripts/oom_worker.py"


def desktop_pids():
    found = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            argv = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
            if argv == "/usr/lib/chatgpt/ChatGPT":
                found["chatgpt"] = int(entry.name)
            elif "/usr/lib/chatgpt/resources/codex " in argv and "app-server" in argv:
                found["codex_app_server"] = int(entry.name)
        except OSError:
            continue
    return found


def systemctl_show(unit):
    result = subprocess.run(
        ["sudo", "-n", "systemctl", "show", unit, "--no-pager", "-p", "Result",
         "-p", "MemoryHigh", "-p", "MemoryMax", "-p", "MemorySwapMax", "-p",
         "OOMPolicy", "-p", "OOMScoreAdjust", "-p", "ControlGroup"],
        text=True, capture_output=True, timeout=15,
    )
    if result.returncode:
        raise RuntimeError(f"systemctl show failed: {result.stderr[-2000:]}")
    return dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)


def main():
    lock = json.loads(LOCK.read_text())
    if lock.get("task_id") != TASK_ID or not lock.get("token"):
        raise SystemExit(f"work queue lock ownership changed; refusing test: {lock}")

    unit = f"llamacode-q37-system-oom-{os.getpid()}-{uuid.uuid4().hex[:6]}.service"
    report_path = TASK / "receipts/system-service-oom-worker.json"
    report_path.unlink(missing_ok=True)
    desktop_before = desktop_pids()
    controller_pid = os.getpid()
    command = [
        "sudo", "-n", "systemd-run", "--system", "--quiet", "--pipe", "--wait",
        f"--unit={unit.removesuffix('.service')}", "--slice=background.slice",
        f"--uid={os.getuid()}", f"--gid={os.getgid()}",
        "--property=Type=exec", "--property=KillMode=control-group",
        "--property=MemoryHigh=120M", "--property=MemoryMax=128M",
        "--property=MemorySwapMax=0", "--property=OOMScoreAdjust=900",
        "--property=OOMPolicy=kill", "--property=ManagedOOMMemoryPressure=auto",
        f"--setenv=Q37_WORKER_REPORT={report_path}", sys.executable, str(WORKER),
    ]
    try:
        run = subprocess.run(command, text=True, capture_output=True, timeout=90)
        returncode, stdout, stderr = run.returncode, run.stdout, run.stderr
    except subprocess.TimeoutExpired as exc:
        subprocess.run(["sudo", "-n", "systemctl", "stop", unit],
                       text=True, capture_output=True, timeout=15)
        returncode, stdout = -1, exc.stdout or ""
        stderr = (exc.stderr or b"").decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")

    props = systemctl_show(unit)
    journal = subprocess.run(["sudo", "-n", "journalctl", "--unit", unit, "--no-pager", "-o", "cat"],
                             text=True, capture_output=True, timeout=15)
    journal_text = journal.stdout if journal.returncode == 0 else journal.stderr
    worker_report = json.loads(report_path.read_text()) if report_path.exists() else None
    desktop_after = desktop_pids()
    controller_alive = Path(f"/proc/{controller_pid}").exists()
    receipt = {
        "task": TASK_ID,
        "checked_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "unit": unit,
        "controller_cgroup": Path("/proc/self/cgroup").read_text().strip(),
        "controller_survived": controller_alive,
        "desktop_pids_before": desktop_before,
        "desktop_pids_after": desktop_after,
        "worker_report": worker_report,
        "systemd_run_returncode": returncode,
        "systemd_run_stderr": stderr[-2000:],
        "unit_properties": props,
        "unit_journal_tail": journal_text[-4000:],
        "acceptance": {
            "oom_killed_only_in_service": props.get("Result") == "oom-kill",
            "memory_max_128m": props.get("MemoryMax") == str(128 * 1024 * 1024),
            "memory_high_120m": props.get("MemoryHigh") == str(120 * 1024 * 1024),
            "oom_policy_kill": props.get("OOMPolicy") == "kill",
            "oom_score_adjust_900": props.get("OOMScoreAdjust") == "900",
            "worker_cgroup_outside_user_manager": bool(worker_report and
                "/background.slice/" in worker_report.get("cgroup", "") and
                "user@" not in worker_report.get("cgroup", "")),
            "q35_monitor_reads_system_worker_and_user_pressure": bool(worker_report and
                "/background.slice/" in worker_report.get("q35_cgroup_memory_state", {}).get("process_cgroup", "") and
                (worker_report.get("q35_cgroup_memory_state", {}).get("user_manager") or {}).get("path", "").endswith("user@1000.service")),
            "worker_group_oom_enabled": bool(worker_report and worker_report.get("oom_group") == "1"),
            "caller_survived": controller_alive,
            "desktop_survived": all(pid in desktop_after.values() for pid in desktop_before.values()),
            "local_oom_logged": props.get("Result") == "oom-kill" and "killed by the OOM killer" in journal_text,
        },
    }
    receipt["passed"] = all(receipt["acceptance"].values())
    out = TASK / "receipts/system-service-oom-containment.json"
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    subprocess.run(["sudo", "-n", "systemctl", "reset-failed", unit],
                   text=True, capture_output=True, timeout=15)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
