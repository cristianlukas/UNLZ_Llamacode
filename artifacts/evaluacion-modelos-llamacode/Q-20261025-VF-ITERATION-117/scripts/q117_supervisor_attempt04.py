#!/usr/bin/env python3
"""Run exactly one ASTRA 1M request inside isolated systemd transient units."""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-117"
Q35 = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261022-VF-ITERATION-35"
Q97 = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-97"
TASK_ID = "Q-20261025-VF-ITERATION-117"
TOKEN = os.environ.get("LLAMACODE_QUEUE_LOCK_TOKEN", "")
LOCK_TASK_ID = os.environ.get("LLAMACODE_TASK_ID", "")
PYTHON = Path("/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source/.venv/bin/python")
PYTHONPATH_VALUE = "/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source/tools"
SERVER_ROOT = Path("/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source")
RUNNER = TASK / "scripts/run_context_holdout_attempt04.py"
CONFIG = TASK / "configs/astra-default-1m-seed-2026103-attempt04.json"
FIXTURE = Q35 / "fixtures/1048576/2026103"
OUT = TASK / "runs/astra-1m-seed-2026103-attempt04"
PROGRESS = TASK / "receipts/progress-attempt04.json"
PREFLIGHT = TASK / "receipts/q117-preflight-attempt04.json"
SUMMARY = TASK / "receipts/q117-final-summary-attempt04.json"
UNIT = "llamacode-q117-context-1048576-seed-2026103-a04"
SUPERVISOR_UNIT = "llamacode-q117-supervisor-attempt04.service"
GIB = 1024 ** 3

sys.path.insert(0, str(TASK / "scripts"))
from resource_isolation_attempt04 import calculate_worker_limits, systemd_properties
from run_context_holdout import assert_port_bindable, gpu_snapshot, inference_server_processes
from q117_pressure_guard import read_sample


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def lock_value(lock):
    return lock.get("task_id", lock.get("taskId"))


def verify_lock():
    lock = json.loads((ROOT / "WORK_QUEUE.lock").read_text(encoding="utf-8"))
    if not TOKEN or lock.get("token") != TOKEN or lock_value(lock) != LOCK_TASK_ID or LOCK_TASK_ID != TASK_ID:
        raise RuntimeError(f"queue lock ownership changed: {lock}")
    return lock


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def asset_metadata_matches():
    expected = json.loads((Q97 / "receipts/q97-fingerprint-prelaunch.json").read_text())
    rows = []
    for name, asset in expected["assets"].items():
        path = Path(asset["path"])
        stat = path.stat()
        actual = {"bytes": stat.st_size, "device": stat.st_dev, "inode": stat.st_ino,
                  "mtimeNs": stat.st_mtime_ns}
        pinned = {key: asset[key] for key in actual}
        rows.append({"name": name, "path": str(path), "expected": pinned, "actual": actual,
                     "sha256PreviouslyVerified": asset["sha256Expected"], "matches": actual == pinned})
    if not all(row["matches"] for row in rows):
        raise RuntimeError("ASTRA asset identity changed since pinned SHA-256 verification")
    return rows


def preflight():
    verify_lock()
    external = inference_server_processes()
    if external:
        raise RuntimeError(f"external inference server detected: {external}")
    assert_port_bindable(8350)
    host = read_sample()
    if host["memAvailableGiB"] < 80:
        raise RuntimeError(f"preflight requires 80 GiB MemAvailable; got {host['memAvailableGiB']:.2f}")
    meminfo = Path("/proc/meminfo").read_text()
    limits = calculate_worker_limits(meminfo)
    if limits["memory_max_bytes"] < 64 * GIB:
        raise RuntimeError("safe isolated-worker memory budget below 64 GiB")
    values = {}
    for line in meminfo.splitlines():
        key, rest = line.split(":", 1)
        if key in {"SwapFree"}:
            values[key] = int(rest.split()[0]) * 1024
    if values.get("SwapFree", 0) < GIB:
        raise RuntimeError("preflight requires at least 1 GiB SwapFree")
    disk = shutil.disk_usage(TASK)
    if disk.free < 5 * GIB:
        raise RuntimeError(f"preflight requires 5 GiB free in artifacts volume; got {disk.free/GIB:.2f}")
    gpus = gpu_snapshot()
    if isinstance(gpus, dict):
        raise RuntimeError(f"GPU telemetry unavailable: {gpus}")
    for index in (0, 1):
        gpu = next((row for row in gpus if row["index"] == index), None)
        if not gpu or gpu["memory_total_mib"] - gpu["memory_used_mib"] < 23000:
            raise RuntimeError(f"GPU{index} needs 23000 MiB free: {gpus}")
    assets = asset_metadata_matches()
    fixture_hashes = {}
    for name in ("probe-prompt.txt", "probe-expected.json", "probe-metadata.json"):
        fixture_hashes[name] = sha256(FIXTURE / name)
    config_sha = sha256(CONFIG)
    runtime = Path(json.loads(CONFIG.read_text())["exe"])
    if not runtime.is_file() or not os.access(runtime, os.X_OK):
        raise RuntimeError(f"pinned Strata runtime missing/not executable: {runtime}")
    result = {
        "checkedAtUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "lockToken": TOKEN, "taskId": LOCK_TASK_ID, "inferenceServers": external,
        "port8350Bindable": True, "memory": host,
        "swapFreeBytes": values["SwapFree"], "workerLimits": limits,
        "resultsVolumeFreeBytes": disk.free, "gpus": gpus,
        "pinnedAssets": assets, "fixtureSha256": fixture_hashes,
        "configSha256": config_sha, "runtimePath": str(runtime),
        "decision": "pass",
    }
    atomic_json(PREFLIGHT, result)
    return result, limits


def run_once(limits):
    command = [
        "sudo", "-n", "systemd-run", "--system", "--quiet", "--wait", "--collect",
        f"--unit={UNIT.removesuffix('.service')}", "--slice=background.slice",
        f"--uid={os.getuid()}", f"--gid={os.getgid()}", *systemd_properties(limits),
        f"--working-directory={SERVER_ROOT}",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = PYTHONPATH_VALUE
    env["STRATA_ROOT"] = str(SERVER_ROOT)
    for key in ("HOME", "USER", "PATH", "LANG", "LC_ALL", "LD_LIBRARY_PATH", "CUDA_VISIBLE_DEVICES", "XDG_CACHE_HOME"):
        if key in env:
            command.append(f"--setenv={key}={env[key]}")
    command.extend([
        f"--setenv=PYTHONPATH={PYTHONPATH_VALUE}", f"--setenv=STRATA_ROOT={SERVER_ROOT}",
        f"--setenv=LLAMACODE_EXPECTED_MEMORY_HIGH_BYTES={limits['memory_high_bytes']}",
        f"--setenv=LLAMACODE_EXPECTED_MEMORY_MAX_BYTES={limits['memory_max_bytes']}",
        f"--setenv=LLAMACODE_EXPECTED_MEMORY_SWAP_MAX_BYTES={limits['memory_swap_max_bytes']}",
        f"--setenv=LLAMACODE_QUEUE_LOCK_TOKEN={TOKEN}", f"--setenv=LLAMACODE_TASK_ID={LOCK_TASK_ID}",
        str(PYTHON), str(RUNNER), "--context", "1048576", "--config", str(CONFIG),
        "--fixture-dir", str(FIXTURE), "--out-dir", str(OUT), "--server-root", str(SERVER_ROOT),
        "--python", str(PYTHON), "--timeout", "1200", "--max-tokens", "768", "--port", "8350",
        "--seed", "2026103",
    ])
    atomic_json(PROGRESS, {"taskId": TASK_ID, "phase": "worker_start", "unit": UNIT,
                           "startedAtUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                           "command": command, "lockToken": TOKEN})
    result = subprocess.run(command, capture_output=True, text=True)
    journal = subprocess.run(["sudo", "-n", "journalctl", "--unit", f"{UNIT}.service",
                              "--no-pager", "-o", "cat"], capture_output=True, text=True)
    (OUT / "systemd-unit.log").write_text(journal.stdout if journal.returncode == 0 else journal.stderr)
    (OUT / "systemd-run.stdout.txt").write_text(result.stdout)
    (OUT / "systemd-run.stderr.txt").write_text(result.stderr)
    if not (OUT / "receipt.json").exists():
        sample_path = OUT / "memory-monitor.jsonl"
        samples = []
        if sample_path.exists():
            for line in sample_path.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    samples.append(json.loads(line))
                except json.JSONDecodeError:
                    samples.append({"monitor_error": "truncated JSONL sample", "raw": line[:300]})
        summary = {
            "taskId": TASK_ID, "lockToken": TOKEN,
            "completedAtUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "worker_terminated_without_final_receipt",
            "workerReturnCode": result.returncode,
            "monitorSampleCount": len(samples),
            "lastPersistedMonitorSample": samples[-1] if samples else None,
            "monitorSamplePath": str(sample_path),
            "systemdUnitLog": str(OUT / "systemd-unit.log"),
            "modelResponse": "unavailable; no final runner receipt",
            "evidence": str(OUT),
        }
        atomic_json(SUMMARY, summary)
        atomic_json(PROGRESS, {"taskId": TASK_ID, "phase": "worker_terminated_without_receipt",
                               "unit": UNIT, "completedAtUtc": summary["completedAtUtc"],
                               "status": summary["status"], "monitorSampleCount": len(samples)})
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2
    receipt = json.loads((OUT / "receipt.json").read_text())
    samples = receipt.get("monitor_samples", [])
    avail = [row.get("memAvailableGiB") for row in samples if isinstance(row.get("memAvailableGiB"), (int, float))]
    rss = [row.get("process_tree_rss_bytes") for row in samples if isinstance(row.get("process_tree_rss_bytes"), (int, float))]
    gpu_memory = receipt.get("gpu_memory", {})
    both_gpus_used = all(int(gpu_memory.get(str(i), {}).get("peak_delta_mib") or 0) > 0 for i in (0, 1))
    monitor_valid = bool(samples) and not any("monitor_error" in row for row in samples)
    guard_pass = (
        result.returncode == 0 and receipt.get("request_sent") is True and receipt.get("http_status") == 200
        and receipt.get("monitor_abort_reason") is None and monitor_valid and bool(avail)
        and min(avail) >= 32.0 and both_gpus_used
        and (receipt.get("run_cgroup_memory_swap_delta_bytes") or 0) <= 4 * 1024 * 1024
    )
    summary = {
        "taskId": TASK_ID, "lockToken": TOKEN,
        "completedAtUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "memory_guard_pass" if guard_pass else "memory_guard_not_passed",
        "model": "ASTRA DEFAULT Qwen3.8 Flash-Next GSQ-RCO IQ2_XS / Strata 0.1.41",
        "context": 1048576, "both3090Used": both_gpus_used,
        "requestSent": receipt.get("request_sent"), "httpStatus": receipt.get("http_status"),
        "monitorAbortReason": receipt.get("monitor_abort_reason"), "monitorValid": monitor_valid,
        "sampleCount": len(samples), "minMemAvailableGiB": min(avail) if avail else None,
        "peakProcessTreeRssGiB": max(rss) / GIB if rss else None,
        "gpuMemory": gpu_memory,
        "runCgroupSwapDeltaBytes": receipt.get("run_cgroup_memory_swap_delta_bytes"),
        "oomAndPressureEvidence": {
            "globalOomBaseline": samples[0].get("oomKill") if samples else None,
            "globalOomFinal": samples[-1].get("oomKill") if samples else None,
            "peakPsiFullAvg10Pct": max((row.get("memoryPsiAvg10Pct", {}).get("full", 0) for row in samples), default=None),
            "peakPsiSomeAvg10Pct": max((row.get("memoryPsiAvg10Pct", {}).get("some", 0) for row in samples), default=None),
        },
        "qualityResultNotUsedForAdoption": receipt.get("quality_score"),
        "workerReturnCode": result.returncode, "guardPass": guard_pass,
        "evidence": str(OUT / "receipt.json"),
    }
    atomic_json(SUMMARY, summary)
    atomic_json(PROGRESS, {"taskId": TASK_ID, "phase": "complete", "unit": UNIT,
                           "completedAtUtc": summary["completedAtUtc"], "status": summary["status"]})
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if guard_pass else 2


def main():
    verify_lock()
    preflight_result, limits = preflight()
    atomic_json(PROGRESS, {"taskId": TASK_ID, "phase": "preflight_passed", "unit": UNIT,
                           "preflight": preflight_result, "startedAtUtc": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    return run_once(limits)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        atomic_json(SUMMARY, {"taskId": TASK_ID, "lockToken": TOKEN, "status": "preflight_or_supervisor_failure",
                              "error": f"{type(exc).__name__}: {exc}",
                              "completedAtUtc": datetime.datetime.now(datetime.timezone.utc).isoformat()})
        print(f"Q117 supervisor blocked/failed safely: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(3)
