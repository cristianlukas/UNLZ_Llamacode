#!/usr/bin/env python3
"""Two-stage CPU-only test of detached lifetime and ExecStopPost child cleanup."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import time
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[4]
PROFILE = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261115-MAYA-DS4SPLIT39-Q173/profiles/maya-xs-iq1s-pny-ds4split39-q173"
RECEIPTS = PROFILE / "receipts"
CLEANUP = PROFILE / "scripts/cleanup_detached_worker.py"
TOKEN = "d9029f6b-c649-4291-b0be-f14d77dc737e"


def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def cmd(argv: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, text=True, capture_output=True, timeout=timeout)


def check_lock() -> None:
    lock = json.loads((ROOT / "WORK_QUEUE.lock").read_text(encoding="utf-8"))
    queue = (ROOT / "WORK_QUEUE.md").read_text(encoding="utf-8")
    if lock.get("token") != TOKEN or lock.get("task") != "Q-20261103-VF-RESUME-202" or TOKEN not in queue:
        raise RuntimeError("WORK_QUEUE.lock is no longer owned by Q202; refusing lifecycle smoke")


def show(unit: str, prop: str) -> str:
    p = cmd(["systemctl", "--user", "show", unit, f"-p{prop}", "--value"])
    return p.stdout.strip() if p.returncode == 0 else "not-found"


def write(path: pathlib.Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def launch(nonce: str) -> dict:
    check_lock()
    if not nonce.replace("-", "").isalnum() or len(nonce) > 24:
        raise ValueError("unsafe smoke nonce")
    worker = f"q209-lifecycle-smoke-{nonce}-worker"
    child = f"q209-lifecycle-smoke-{nonce}-child"
    worker_desc = f"Q209-CPU-SMOKE-WORKER|{nonce}"
    child_desc = f"Q209-CPU-SMOKE-CHILD|{nonce}"
    receipt = RECEIPTS / f"detached-worker-smoke-{nonce}.json"
    cleanup_receipt = RECEIPTS / f"detached-worker-smoke-{nonce}-cleanup.json"
    marker = RECEIPTS / f"detached-worker-smoke-{nonce}-started.txt"
    if show(worker, "LoadState") != "not-found" or show(child, "LoadState") != "not-found":
        raise RuntimeError("smoke unit names already exist; refusing reuse")

    child_start = cmd([
        "systemd-run", "--user", "--no-block", f"--unit={child}",
        f"--description={child_desc}", "--property=RuntimeMaxSec=300s",
        "--property=MemoryMax=128M", "--property=MemorySwapMax=0",
        "--property=KillMode=control-group", "/usr/bin/sleep", "infinity",
    ])
    if child_start.returncode:
        raise RuntimeError(f"could not start harmless CPU child: {child_start.stderr}")
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and show(child, "ActiveState") != "active":
        time.sleep(0.2)
    if show(child, "ActiveState") != "active":
        raise RuntimeError("harmless child did not become active")

    worker_code = "import pathlib,sys,time; pathlib.Path(sys.argv[1]).write_text('started\\n'); time.sleep(30)"
    worker_start = cmd([
        "systemd-run", "--user", "--no-block", f"--unit={worker}",
        f"--description={worker_desc}", "--property=RuntimeMaxSec=8s",
        "--property=MemoryMax=128M", "--property=MemorySwapMax=0",
        "--property=OOMPolicy=kill", "--property=KillMode=control-group",
        f"--property=ExecStopPost={CLEANUP}",
        f"--setenv=Q209_ENGINE_UNIT={child}",
        f"--setenv=Q209_EXPECTED_ENGINE_DESCRIPTION={child_desc}",
        f"--setenv=Q209_CLEANUP_RECEIPT={cleanup_receipt}",
        f"--setenv=Q209_LOCK_TOKEN={TOKEN}",
        "/usr/bin/python3", "-c", worker_code, str(marker),
    ])
    if worker_start.returncode:
        cmd(["systemctl", "--user", "stop", child], timeout=30)
        raise RuntimeError(f"systemd rejected harmless lifecycle worker: {worker_start.stderr}")
    record = {
        "schema": "llamacode.q209-detached-worker-cpu-smoke.v1",
        "status": "LAUNCHED",
        "timestamp_utc": utc(),
        "lock_token": TOKEN,
        "gpu_used": False,
        "model_used": False,
        "worker_unit": worker,
        "worker_description": worker_desc,
        "child_unit": child,
        "child_description": child_desc,
        "marker": str(marker),
        "cleanup_receipt": str(cleanup_receipt),
        "controller_launcher_returncode": worker_start.returncode,
        "controller_launcher_stdout": worker_start.stdout,
        "controller_launcher_stderr": worker_start.stderr,
        "worker_runtime_limit_seconds": 8,
    }
    write(receipt, record)
    return record


def verify(nonce: str) -> dict:
    check_lock()
    receipt = RECEIPTS / f"detached-worker-smoke-{nonce}.json"
    cleanup_receipt = RECEIPTS / f"detached-worker-smoke-{nonce}-cleanup.json"
    idempotent_receipt = RECEIPTS / f"detached-worker-smoke-{nonce}-already-stopped.json"
    record = json.loads(receipt.read_text(encoding="utf-8"))
    marker = pathlib.Path(record["marker"])
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not marker.exists():
            time.sleep(0.2)
        if not marker.exists():
            raise RuntimeError("detached worker did not survive its launching process")
        record["marker_after_launcher_exit"] = marker.read_text(encoding="utf-8").strip()
        if record["marker_after_launcher_exit"] != "started":
            raise RuntimeError("worker start marker invalid")

        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not cleanup_receipt.exists():
            time.sleep(0.25)
        if not cleanup_receipt.exists():
            raise RuntimeError("ExecStopPost did not leave a cleanup receipt")
        cleanup = json.loads(cleanup_receipt.read_text(encoding="utf-8"))
        worker_state = show(record["worker_unit"], "ActiveState")
        worker_result = show(record["worker_unit"], "Result")
        child_state = show(record["child_unit"], "ActiveState")
        if cleanup.get("status") not in ("PASS_STOPPED", "PASS_ALREADY_STOPPED"):
            raise RuntimeError(f"cleanup hook failed: {cleanup}")
        if worker_state not in ("failed", "inactive") or worker_result != "timeout":
            raise RuntimeError(f"worker did not terminate at its bounded timeout: {worker_state}/{worker_result}")
        if child_state not in ("failed", "inactive", "not-found"):
            raise RuntimeError(f"fake child survived worker exit: {child_state}")

        # Re-enter cleanup against the same completed fake child while
        # deliberately supplying a different expected description. It must
        # recognize the unit is already stopped and avoid sending a signal.
        idempotent_expected = f"Q209-MAYA-Q173|{TOKEN}|{record['child_unit']}"
        env = os.environ.copy()
        env.update({
            "Q209_ENGINE_UNIT": record["child_unit"],
            "Q209_EXPECTED_ENGINE_DESCRIPTION": idempotent_expected,
            "Q209_CLEANUP_RECEIPT": str(idempotent_receipt),
            "Q209_LOCK_TOKEN": TOKEN,
        })
        idempotent_run = subprocess.run(
            [sys.executable, str(CLEANUP)], text=True, capture_output=True,
            timeout=30, env=env,
        )
        idempotent = json.loads(idempotent_receipt.read_text(encoding="utf-8")) if idempotent_receipt.exists() else {}
        if idempotent_run.returncode != 0 or idempotent.get("status") != "PASS_ALREADY_STOPPED" or idempotent.get("stop_attempted") is not False:
            raise RuntimeError(f"already-stopped cleanup was not a safe no-op: rc={idempotent_run.returncode} receipt={idempotent}")
        if idempotent.get("actual_description") == idempotent_expected:
            raise RuntimeError("idempotency case failed to exercise an identity-description mismatch")

        record.update({
            "status": "PASS",
            "verified_utc": utc(),
            "worker_final_state": worker_state,
            "worker_result": worker_result,
            "child_final_state": child_state,
            "cleanup": cleanup,
            "already_stopped_cleanup": idempotent,
            "assertions": {
                "launcher_returned_without_waiting_for_worker": True,
                "worker_continued_after_launcher_process_exit": True,
                "worker_timeout_was_bounded": True,
                "worker_exit_hook_stopped_exact_child_unit": True,
                "repeat_cleanup_after_normal_child_exit_is_safe_noop": True,
                "gpu_used": False,
                "model_used": False,
            },
        })
        write(receipt, record)
        return record
    except Exception as e:
        record.update({"status": "FAIL", "verified_utc": utc(), "error": f"{type(e).__name__}: {e}"})
        emergency = []
        for unit, expected in ((record["worker_unit"], record["worker_description"]), (record["child_unit"], record["child_description"])):
            actual = show(unit, "Description")
            if actual == expected:
                stopped = cmd(["systemctl", "--user", "stop", unit], timeout=30)
                emergency.append({"unit": unit, "stop_returncode": stopped.returncode, "description_matched": True})
            else:
                emergency.append({"unit": unit, "description_matched": False, "stop_attempted": False})
        record["emergency_cleanup"] = emergency
        write(receipt, record)
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    p_launch = sub.add_parser("launch")
    p_launch.add_argument("--nonce", default=uuid.uuid4().hex[:12])
    p_verify = sub.add_parser("verify")
    p_verify.add_argument("--nonce", required=True)
    args = ap.parse_args()
    try:
        result = launch(args.nonce) if args.command == "launch" else verify(args.nonce)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
