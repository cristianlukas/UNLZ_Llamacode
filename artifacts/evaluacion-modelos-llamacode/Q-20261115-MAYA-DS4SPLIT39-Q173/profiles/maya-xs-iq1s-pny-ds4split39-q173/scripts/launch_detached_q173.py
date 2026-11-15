#!/usr/bin/env python3
"""Launch one preregistered Q209 Q173 context run in a bounded user-systemd worker."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROFILE = HERE.parents[0]
REPO = HERE.parents[5]
RECEIPTS = PROFILE / "receipts"
RUNNER = HERE / "run_q173.py"
CLEANUP = HERE / "cleanup_detached_worker.py"
TOKEN = "d9029f6b-c649-4291-b0be-f14d77dc737e"
TASK = "Q-20261103-VF-RESUME-202"
LADDER = {8192: 3, 32768: 1, 65536: 1, 131072: 1, 261888: 1}


def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def sha(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run(argv: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, text=True, capture_output=True, timeout=timeout)


def write_json(path: pathlib.Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def active_state(unit: str) -> str:
    q = run(["systemctl", "--user", "show", unit, "-p", "ActiveState", "--value"])
    return q.stdout.strip() if q.returncode == 0 else "not-found"


def check_lock() -> None:
    lock = json.loads((REPO / "WORK_QUEUE.lock").read_text(encoding="utf-8"))
    queue = (REPO / "WORK_QUEUE.md").read_text(encoding="utf-8")
    if lock.get("token") != TOKEN or lock.get("task") != TASK or TOKEN not in queue:
        raise RuntimeError("WORK_QUEUE.lock is no longer owned by Q202; refusing launch")


def launch(pp: int, runs: int, attempt: str) -> dict:
    check_lock()
    if LADDER.get(pp) != runs:
        raise ValueError(f"not a preregistered Q173 context/runs pair: {pp}/{runs}")
    if not re.fullmatch(r"a[0-9]{2}", attempt):
        raise ValueError("attempt must be aNN, e.g. a02")
    prereg = json.loads((RECEIPTS / "preregistration.json").read_text(encoding="utf-8"))
    if prereg.get("lock_token") != TOKEN or prereg.get("task") != "Q209-MAYA-DS4SPLIT39-Q173":
        raise RuntimeError("Q209 preregistration/lock identity mismatch")
    if prereg.get("runner_sha256") != sha(RUNNER):
        raise RuntimeError("Q209 runner changed since its amended preregistration")

    worker = f"q209-maya-q173-pp{pp}-worker-{attempt}"
    engine = f"q209-maya-q173-pp{pp}-{attempt}"
    worker_description = f"Q209-WORKER|{TOKEN}|{worker}"
    engine_description = f"Q209-MAYA-Q173|{TOKEN}|{engine}"
    for unit in (worker, engine):
        state = active_state(unit)
        if state in ("active", "activating", "reloading"):
            raise RuntimeError(f"unit already active; refusing to touch it: {unit} ({state})")

    receipt = RECEIPTS / f"worker-launch-pp{pp}-{attempt}.json"
    cleanup_receipt = RECEIPTS / f"worker-cleanup-pp{pp}-{attempt}.json"
    argv = [
        "systemd-run", "--user", "--no-block", f"--unit={worker}",
        f"--description={worker_description}",
        "--property=RuntimeMaxSec=3900s", "--property=MemoryMax=8G",
        "--property=MemorySwapMax=0", "--property=OOMPolicy=kill",
        "--property=KillMode=control-group", f"--property=ExecStopPost={CLEANUP}",
        f"--setenv=Q209_WORKER_UNIT={worker}", f"--setenv=Q209_ATTEMPT={attempt}",
        f"--setenv=Q209_ENGINE_UNIT={engine}",
        f"--setenv=Q209_EXPECTED_ENGINE_DESCRIPTION={engine_description}",
        f"--setenv=Q209_CLEANUP_RECEIPT={cleanup_receipt}",
        f"--setenv=Q209_LOCK_TOKEN={TOKEN}", "--setenv=PYTHONUNBUFFERED=1",
        "/usr/bin/python3", str(RUNNER), "run", "--pp", str(pp), "--runs", str(runs),
    ]
    record = {
        "schema": "llamacode.q209-detached-worker-launch.v1",
        "status": "LAUNCHING",
        "timestamp_utc": utc(),
        "task": "Q209-MAYA-DS4SPLIT39-Q173",
        "lock_token": TOKEN,
        "context_tokens": pp,
        "runs": runs,
        "attempt": attempt,
        "worker_unit": worker,
        "worker_description": worker_description,
        "engine_unit": engine,
        "engine_description": engine_description,
        "cleanup_receipt": str(cleanup_receipt),
        "runner_sha256": sha(RUNNER),
        "launcher_sha256": sha(pathlib.Path(__file__)),
        "systemd_run_argv": argv,
    }
    write_json(receipt, record)
    result = run(argv, timeout=60)
    record.update(systemd_run_returncode=result.returncode, stdout=result.stdout, stderr=result.stderr, completed_utc=utc())
    if result.returncode:
        record["status"] = "LAUNCH_REJECTED"
        write_json(receipt, record)
        raise RuntimeError(f"systemd rejected detached worker: {result.stderr}")
    state = active_state(worker)
    record["observed_active_state"] = state
    record["status"] = "START_REQUEST_ACCEPTED" if state in ("active", "activating") else "START_ACCEPTED_STATE_PENDING"
    write_json(receipt, record)
    return record


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--pp", type=int, required=True)
    ap.add_argument("--runs", type=int, required=True)
    ap.add_argument("--attempt", required=True)
    args = ap.parse_args()
    try:
        print(json.dumps(launch(args.pp, args.runs, args.attempt), ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
