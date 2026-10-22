#!/usr/bin/env python3
"""Prove a bounded test worker OOM cannot take down its caller or Codex."""
import datetime
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261022-VF-ITERATION-36"
LOCK = ROOT / "WORK_QUEUE.lock"
TOKEN = "b0bf4359-58fd-44b5-8fc1-f7ed67ce0597"
TASK_ID = "Q-20261022-VF-ITERATION-36"
WORKER = TASK / "scripts/oom_stress_worker.py"


def codex_pids():
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


def unit_properties(unit):
    result = subprocess.run(
        ["systemctl", "--user", "show", f"{unit}.service", "--no-pager",
         "-p", "Result", "-p", "MemoryHigh", "-p", "MemoryMax", "-p", "MemorySwapMax",
         "-p", "OOMPolicy", "-p", "OOMScoreAdjust", "-p", "MemoryPeak", "-p", "ControlGroup"],
        text=True, capture_output=True, timeout=10, check=True,
    )
    return dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)


def main():
    lock = json.loads(LOCK.read_text())
    if lock.get("token") != TOKEN or lock.get("task_id") != TASK_ID:
        raise SystemExit(f"lock ownership changed; refusing test: {lock}")
    unit = f"llamacode-q36-cgroup-oom-{os.getpid()}-{uuid.uuid4().hex[:6]}"
    report_path = TASK / f"receipts/worker-report-{os.getpid()}.json"
    codex_before = codex_pids()
    controller_pid = os.getpid()
    command = [
        "systemd-run", "--user", "--quiet", "--pipe", "--wait",
        f"--unit={unit}", "--slice=background.slice",
        "--property=Type=exec", "--property=KillMode=control-group",
        "--property=MemoryHigh=120M", "--property=MemoryMax=128M",
        "--property=MemorySwapMax=0", "--property=OOMScoreAdjust=900",
        "--property=OOMPolicy=kill", "--property=ManagedOOMMemoryPressure=kill",
        "--property=ManagedOOMMemoryPressureLimit=35%",
        f"--setenv=Q36_WORKER_REPORT={report_path}",
        sys.executable, str(WORKER),
    ]
    try:
        run = subprocess.run(command, text=True, capture_output=True, timeout=90)
        returncode, stdout, stderr = run.returncode, run.stdout, run.stderr
    except subprocess.TimeoutExpired as exc:
        subprocess.run(["systemctl", "--user", "stop", f"{unit}.service"],
                       text=True, capture_output=True, timeout=15)
        returncode, stdout = -1, exc.stdout or ""
        stderr = (exc.stderr or b"").decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
    props = unit_properties(unit)
    codex_after = codex_pids()
    controller_alive = True
    try:
        os.kill(controller_pid, 0)
    except OSError:
        controller_alive = False
    control_group = props.get("ControlGroup", "")
    cg_path = Path("/sys/fs/cgroup") / control_group.lstrip("/") if control_group else None
    oom_events = {}
    oom_group = None
    if cg_path and cg_path.exists():
        oom_events = {k: int(v) for k, v in
                      (line.split() for line in (cg_path / "memory.events").read_text().splitlines())}
        oom_group = (cg_path / "memory.oom.group").read_text().strip()
    journal_result = subprocess.run(
        ["journalctl", "--user-unit", f"{unit}.service", "--no-pager", "-o", "cat"],
        text=True, capture_output=True, timeout=10,
    )
    journal_text = journal_result.stdout if journal_result.returncode == 0 else journal_result.stderr
    parsed = json.loads(report_path.read_text()) if report_path.exists() else None
    for line in stdout.splitlines():
        if parsed:
            break
        try:
            parsed = json.loads(line)
            break
        except json.JSONDecodeError:
            continue
    receipt = {
        "task": TASK_ID,
        "checked_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "unit": unit,
        "controller_cgroup": Path("/proc/self/cgroup").read_text().strip(),
        "controller_pid_survived": controller_alive,
        "codex_pids_before": codex_before,
        "codex_pids_after": codex_after,
        "worker_report": parsed,
        "systemd_run_returncode": returncode,
        "systemd_run_stderr": stderr[-2000:],
        "unit_properties": props,
        "unit_journal_tail": journal_text[-4000:],
        "cgroup_oom_events": oom_events,
        "cgroup_oom_group_after": oom_group,
        "acceptance": {
            "result_oom_kill": props.get("Result") == "oom-kill",
            "memory_max_128m": props.get("MemoryMax") == str(128 * 1024 * 1024),
            "memory_high_120m": props.get("MemoryHigh") == str(120 * 1024 * 1024),
            "oom_policy_kill": props.get("OOMPolicy") == "kill",
            "oom_score_adjust_900": props.get("OOMScoreAdjust") == "900",
            "group_oom_enabled": bool(parsed and parsed.get("oom_group") == "1") and "Killing process" in journal_text,
            "local_oom_event": props.get("Result") == "oom-kill" and "killed by the OOM killer" in journal_text,
            "caller_survived": controller_alive,
            "codex_main_survived": bool(codex_before.get("chatgpt")) and codex_before.get("chatgpt") in codex_after.values(),
            "codex_app_server_survived": bool(codex_before.get("codex_app_server")) and codex_before.get("codex_app_server") in codex_after.values(),
            "worker_cgroup": bool(parsed and "background.slice/" in parsed.get("cgroup", "")
                                  and unit in parsed.get("cgroup", "")),
        },
    }
    receipt["passed"] = all(receipt["acceptance"].values())
    out = TASK / "receipts/systemd-oom-containment.json"
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
