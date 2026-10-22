#!/usr/bin/env python3
"""Run Q35 fixtures serially, preserving a resume receipt after every request."""
import datetime
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261022-VF-ITERATION-35"
LOCK = ROOT / "WORK_QUEUE.lock"
TOKEN = "20f0de1a-7953-4c05-95f8-f6a5b73fac26"
TASK_ID = "Q-20261022-VF-ITERATION-35"
PYTHON = Path("/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source/.venv/bin/python")
PYTHONPATH = "/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source/tools"
SERVER_ROOT = Path("/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source")
RUNNER = TASK / "scripts/run_context_holdout.py"
CONTEXTS = [131072, 262144, 524288, 1048576]
SEEDS = [2026101, 2026102, 2026103]
RUN_SLICE = "background.slice"
SERVICE_ENV_KEYS = (
    "HOME", "USER", "PATH", "LANG", "LC_ALL", "LD_LIBRARY_PATH",
    "CUDA_VISIBLE_DEVICES", "XDG_CACHE_HOME",
)


def atomic_json(path, value):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)


def verify_lock():
    lock = json.loads(LOCK.read_text())
    if lock.get("token") != TOKEN or lock.get("task_id") != TASK_ID:
        raise RuntimeError(f"work queue lock ownership changed: {lock}")


def run_service(spec, context, seed, attempt_no):
    """Run one inference in a cgroup separate from the Codex desktop scope."""
    unit = f"llamacode-q35-context-{context}-seed-{seed}-a{attempt_no:02d}"
    command = [
        "systemd-run", "--user", "--quiet", "--wait", "--collect",
        f"--unit={unit}", f"--slice={RUN_SLICE}",
        "--property=Type=exec", "--property=KillMode=control-group",
        "--property=OOMPolicy=stop", "--property=ManagedOOMMemoryPressure=auto",
        f"--working-directory={SERVER_ROOT}",
    ]
    service_env = os.environ.copy()
    service_env["PYTHONPATH"] = PYTHONPATH
    service_env["STRATA_ROOT"] = str(SERVER_ROOT)
    for key in SERVICE_ENV_KEYS:
        if key in service_env:
            command.append(f"--setenv={key}={service_env[key]}")
    command.append(f"--setenv=PYTHONPATH={service_env['PYTHONPATH']}")
    command.append(f"--setenv=STRATA_ROOT={service_env['STRATA_ROOT']}")
    command.extend([
        str(PYTHON), str(RUNNER), "--context", str(context),
        "--config", spec["config_path"], "--fixture-dir", spec["fixture_dir"],
        "--out-dir", spec["run_dir"], "--server-root", str(SERVER_ROOT),
        "--python", str(PYTHON), "--timeout", "1200", "--max-tokens", "768",
        "--port", "8350", "--seed", str(seed),
    ])
    result = subprocess.run(command, text=True, capture_output=True)
    journal = subprocess.run(
        ["journalctl", "--user-unit", f"{unit}.service", "--no-pager", "-o", "cat"],
        text=True, capture_output=True,
    )
    journal_text = journal.stdout if journal.returncode == 0 else journal.stderr
    return unit, result, journal_text


def has_valid_result(row, expected_run_directory):
    return (
        row.get("run_directory") == str(expected_run_directory)
        and row.get("receipt")
        and row.get("request_sent") is True
        and row.get("classification") == "valid quality"
        and row.get("return_code") == 0
    )


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    manifest_path = TASK / "receipts/fixtures-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    by_key = {(row["context"], row["seed"]): row for row in manifest["runs"]}
    progress_path = TASK / "receipts/progress.json"
    progress = json.loads(progress_path.read_text()) if progress_path.exists() else {
        "task": TASK_ID, "started_at_utc": utc_now(), "completed": [], "state": "running"
    }
    for context in CONTEXTS:
        for seed in SEEDS:
            key = f"{context}:{seed}"
            expected_run_directory = str((TASK / f"runs/{context}/{seed}").resolve())
            if any(row.get("key") == key and has_valid_result(row, expected_run_directory)
                   for row in progress["completed"]):
                continue
            verify_lock()
            spec = by_key[(context, seed)]
            fixture_dir = Path(spec["fixture_dir"])
            run_dir = Path(spec["run_dir"])
            config_path = Path(spec["config_path"])
            for path in (fixture_dir / "probe-prompt.txt", fixture_dir / "probe-expected.json", config_path):
                if not path.is_file():
                    raise RuntimeError(f"required file missing: {path}")
            config_sha = hashlib.sha256(config_path.read_bytes()).hexdigest()
            if config_sha != spec["config_sha256"]:
                raise RuntimeError(f"config hash mismatch before run {key}")
            attempts = progress.setdefault("attempts", [])
            attempt_no = 1 + sum(row.get("key") == key for row in attempts)
            unit = f"llamacode-q35-context-{context}-seed-{seed}-a{attempt_no:02d}"
            started = utc_now()
            active = {
                "key": key, "context": context, "seed": seed,
                "attempt_no": attempt_no, "service_unit": f"{unit}.service",
                "run_directory": str(run_dir.resolve()), "state": "starting",
                "started_at_utc": started,
            }
            progress["state"] = "run-in-progress"
            progress["active_run"] = active
            progress["updated_at_utc"] = utc_now()
            attempt = dict(active)
            attempts.append(attempt)
            atomic_json(progress_path, progress)
            print(json.dumps({"event": "run-start", **active}), flush=True)
            verify_lock()
            unit, result, journal_text = run_service(spec, context, seed, attempt_no)
            (run_dir / "systemd-unit.log").write_text(journal_text, encoding="utf-8")
            receipt_path = run_dir / "receipt.json"
            receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else None
            row = {
                "key": key, "context": context, "seed": seed,
                "attempt_no": attempt_no, "service_unit": f"{unit}.service",
                "started_at_utc": started, "finished_at_utc": utc_now(),
                "return_code": result.returncode,
                "stdout_tail": result.stdout[-3000:], "stderr_tail": result.stderr[-3000:],
                "systemd_log": str((run_dir / "systemd-unit.log").resolve()),
                "run_directory": str(run_dir.resolve()),
                "receipt": str(receipt_path.resolve()) if receipt else None,
                "classification": (receipt.get("classification") if receipt else
                                   "invalid infrastructure / systemd-oom-kill" if "oom-kill" in journal_text.lower()
                                   else "invalid infrastructure / missing result receipt"),
                "request_sent": receipt.get("request_sent") if receipt else False,
                "correct": (receipt.get("quality_score") or {}).get("correct") if receipt else None,
                "total": (receipt.get("quality_score") or {}).get("total") if receipt else None,
                "strict_output_valid": receipt.get("strict_output_valid") if receipt else None,
                "transport_error": receipt.get("transport_error") if receipt else result.stderr[-1000:],
                "monitor_abort_reason": receipt.get("monitor_abort_reason") if receipt else None,
            }
            progress["completed"].append(row)
            progress["last_completed_key"] = key
            attempt.update(row)
            attempt["state"] = "finished"
            progress["active_run"] = None
            progress["updated_at_utc"] = utc_now()
            atomic_json(progress_path, progress)
            print(json.dumps({"event": "run-finish", **{k: row[k] for k in (
                "key", "return_code", "classification", "request_sent", "correct", "total",
                "strict_output_valid", "transport_error", "monitor_abort_reason")}}, ensure_ascii=False), flush=True)
            # Any infrastructure/resource failure stops the batch; a later recovery
            # must be separately recorded and run in its own systemd cgroup.
            if not receipt or result.returncode != 0 or receipt.get("monitor_abort_reason"):
                progress["state"] = "paused-after-failure"
                progress["resume_at"] = key
                progress["updated_at_utc"] = utc_now()
                atomic_json(progress_path, progress)
                return 2
    progress["state"] = "all-runs-finished"
    progress["finished_at_utc"] = utc_now()
    atomic_json(progress_path, progress)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
