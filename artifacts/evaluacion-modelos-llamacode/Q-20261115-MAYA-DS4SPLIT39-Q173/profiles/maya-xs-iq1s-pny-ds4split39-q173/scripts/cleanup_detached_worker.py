#!/usr/bin/env python3
"""Fail-closed ExecStopPost cleanup for an exact, owned Q209 engine unit."""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
PROFILE = HERE.parents[0]
RECEIPTS = PROFILE / "receipts"


def run(argv: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, text=True, capture_output=True, timeout=timeout)


def write_json(path: pathlib.Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def state(unit: str) -> tuple[str, str]:
    load = run(["systemctl", "--user", "show", unit, "-p", "LoadState", "--value"])
    active = run(["systemctl", "--user", "show", unit, "-p", "ActiveState", "--value"])
    return load.stdout.strip(), active.stdout.strip()


def main() -> int:
    unit = os.environ.get("Q209_ENGINE_UNIT", "")
    expected = os.environ.get("Q209_EXPECTED_ENGINE_DESCRIPTION", "")
    receipt_raw = os.environ.get("Q209_CLEANUP_RECEIPT", "")
    if not re.fullmatch(r"q209-maya-q173-pp[0-9]+-a[0-9]{2}|q209-lifecycle-smoke-[a-z0-9-]+-child", unit):
        print(f"Refusing unexpected unit name: {unit!r}", file=sys.stderr)
        return 2
    if not expected.startswith("Q209-") or not receipt_raw:
        print("Refusing cleanup without exact Q209 description and receipt path", file=sys.stderr)
        return 2
    receipt_path = pathlib.Path(receipt_raw).resolve()
    if RECEIPTS.resolve() not in receipt_path.parents:
        print("Refusing receipt path outside the Q209 profile receipts directory", file=sys.stderr)
        return 2

    load, active = state(unit)
    actual = run(["systemctl", "--user", "show", unit, "-p", "Description", "--value"])
    record = {
        "schema": "llamacode.q209-detached-worker-cleanup.v1",
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "unit": unit,
        "expected_description": expected,
        "actual_description": actual.stdout.strip(),
        "service_result": os.environ.get("SERVICE_RESULT"),
        "exit_code": os.environ.get("EXIT_CODE"),
        "exit_status": os.environ.get("EXIT_STATUS"),
        "before": {"load_state": load, "active_state": active},
    }

    # The runner normally stops and unloads its exact Maya unit before exiting.
    # systemd may then report the fallback unit-name description, or no unit at
    # all. An already-stopped unit needs no signal, so make cleanup idempotent
    # before checking the description used to authorize a stop.
    if load == "not-found" or active in ("inactive", "failed"):
        record.update(status="PASS_ALREADY_STOPPED", stop_attempted=False)
        write_json(receipt_path, record)
        print(json.dumps(record, ensure_ascii=False))
        return 0

    if actual.returncode != 0 or actual.stdout.strip() != expected:
        record.update(status="REFUSED_IDENTITY_MISMATCH", stop_attempted=False)
        write_json(receipt_path, record)
        print("Q209 cleanup refused: exact unit description did not match", file=sys.stderr)
        return 3

    stop = run(["systemctl", "--user", "stop", unit], timeout=180)
    record["stop_returncode"] = stop.returncode
    record["stop_stdout"] = stop.stdout[-2000:]
    record["stop_stderr"] = stop.stderr[-2000:]
    deadline = time.monotonic() + 30
    after_load, after_active = state(unit)
    while time.monotonic() < deadline and after_active not in ("inactive", "failed"):
        time.sleep(0.5)
        after_load, after_active = state(unit)
    record["after"] = {"load_state": after_load, "active_state": after_active}
    record["status"] = "PASS_STOPPED" if stop.returncode == 0 and after_active in ("inactive", "failed") else "FAIL_STOP_DID_NOT_COMPLETE"
    record["stop_attempted"] = True

    write_json(receipt_path, record)
    print(json.dumps(record, ensure_ascii=False))
    return 0 if record["status"].startswith("PASS") else 4


if __name__ == "__main__":
    raise SystemExit(main())
