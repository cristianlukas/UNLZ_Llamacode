#!/usr/bin/env python3
"""Launch one S23 arm in its own bounded user-systemd scope and monitor guards."""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

TASK = pathlib.Path(__file__).resolve().parents[1]
REPO = pathlib.Path(__file__).resolve().parents[4]
LOCK_ID = "Q-20261021-VF-ITERATION-20"
TOKEN = "50d8dfb3-511a-48b2-a253-2cd6197cee17"
ADAPTER = TASK / "work/run_source23_mmap_arm.py"
PYTHON = pathlib.Path("/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source/.venv/bin/python")
PORT = 8355
MEM_HIGH = 64 * 1024**3
MEM_MAX = 72 * 1024**3
SCOPE_ABORT_BYTES = 68 * 1024**3
MIN_MEM_AVAILABLE = 48 * 1024**3
MAX_SWAP_DROP = 1 * 1024**3
SOME_PSI_LIMIT = 40.0
FULL_PSI_LIMIT = 25.0
PSI_PERSIST_SAMPLES = 4
INTERVAL = 5
MAX_WALL = 2700
MARKERS = ("llama-server", "vllm", "sglang", "ollama serve", "lmstudio", "tritonserver",
           "text-generation-launcher", "aphrodite", "mlx_lm", "--engine strata")


def owned_lock() -> bool:
    try:
        d = json.loads((REPO / "WORK_QUEUE.lock").read_text())
        return d.get("task_id") == LOCK_ID and d.get("token") == TOKEN
    except Exception:
        return False


def proc_value(name: str) -> int:
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        if line.startswith(name + ":"):
            return int(line.split()[1]) * 1024
    raise RuntimeError(f"{name} missing from /proc/meminfo")


def oom_kills() -> int:
    for line in pathlib.Path("/proc/vmstat").read_text().splitlines():
        if line.startswith("oom_kill "):
            return int(line.split()[1])
    raise RuntimeError("oom_kill missing from /proc/vmstat")


def psi_avg10() -> dict[str, float]:
    result = {}
    for line in pathlib.Path("/proc/pressure/memory").read_text().splitlines():
        fields = dict(x.split("=", 1) for x in line.split()[1:])
        result[line.split()[0]] = float(fields["avg10"])
    return result


def gpu_temperatures() -> list[int]:
    r = subprocess.run(
        ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, timeout=5, check=True,
    )
    return [int(x.strip()) for x in r.stdout.splitlines() if x.strip()]


def inference_processes() -> list[dict]:
    found = []
    for entry in os.scandir("/proc"):
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            cmd = pathlib.Path(entry.path, "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
            comm = pathlib.Path(entry.path, "comm").read_text().strip()
        except (OSError, ProcessLookupError):
            continue
        text = (comm + " " + cmd).lower()
        if comm.lower() == "strata" or any(m in text for m in MARKERS):
            found.append({"pid": int(entry.name), "comm": comm, "cmdline": cmd[:350]})
    return found


def port_free(port: int) -> bool:
    r = subprocess.run(["ss", "-ltnH"], capture_output=True, text=True, timeout=5, check=False)
    if r.returncode:
        raise RuntimeError("cannot enumerate local TCP listeners")
    return not any(re.search(rf":{port}\s", line) for line in r.stdout.splitlines())


def control_group(unit: str) -> str | None:
    r = subprocess.run(
        ["systemctl", "--user", "show", f"{unit}.scope", "-p", "ControlGroup", "--value"],
        capture_output=True, text=True, timeout=5, check=False,
    )
    value = r.stdout.strip()
    return value if r.returncode == 0 and value.startswith("/") else None


def cgroup_values(relative: str | None) -> dict | None:
    if not relative:
        return None
    base = pathlib.Path("/sys/fs/cgroup") / relative.lstrip("/")
    try:
        return {
            "path": relative,
            "memoryHigh": int((base / "memory.high").read_text()),
            "memoryMax": int((base / "memory.max").read_text()),
            "memoryCurrent": int((base / "memory.current").read_text()),
            "pids": len((base / "cgroup.procs").read_text().splitlines()),
        }
    except Exception:
        return None


def output_paths(arm: str, seed: int) -> dict[str, pathlib.Path]:
    return {
        "preflight": TASK / f"receipts/preflight-{arm}-seed-{seed}.json",
        "execution": TASK / f"receipts/execution-{arm}-seed-{seed}.json",
        "guardlog": TASK / f"work/source23/guard-{arm}-seed-{seed}.jsonl",
        "runnerlog": TASK / f"work/source23/runner-{arm}-seed-{seed}.log",
        "result": TASK / f"work/source23/results/{arm}-seed-{seed}.json",
        "runnerReceipt": TASK / f"receipts/source-23-{arm}-seed-{seed}-execution.json",
        "serverLog": TASK / f"work/source23/server-{arm}-seed-{seed}.log",
    }


def preflight(arm: str, seed: int, paths: dict[str, pathlib.Path]) -> dict:
    mem = proc_value("MemAvailable")
    swap = proc_value("SwapFree")
    psi = psi_avg10()
    temps = gpu_temperatures()
    processes = inference_processes()
    collisions = [k for k, p in paths.items() if p.exists()]
    problems = []
    if not owned_lock():
        problems.append("Q20 lock ownership mismatch")
    if processes:
        problems.append("inference process detected")
    if not port_free(PORT):
        problems.append(f"port {PORT} is occupied")
    if mem < 90 * 1024**3:
        problems.append("MemAvailable below 90 GiB")
    if psi.get("full", 100.0) >= 0.5:
        problems.append("memory PSI full avg10 is not below 0.5%")
    if oom_kills() != 0:
        problems.append("host OOM kill counter is not zero")
    if not temps or max(temps) >= 85:
        problems.append("GPU temperature is missing or at least 85 C")
    if not PYTHON.is_file() or not ADAPTER.is_file():
        problems.append("pinned Python or adapter is missing")
    if not paths["result"].parent.is_dir():
        problems.append("isolated results directory is missing")
    if collisions:
        problems.append("refusing existing outputs: " + ", ".join(collisions))
    return {
        "atUtc": datetime.now(timezone.utc).isoformat(),
        "arm": arm, "seed": seed, "status": "pass" if not problems else "blocked",
        "problems": problems,
        "lockOwned": owned_lock(),
        "inferenceProcesses": processes,
        "port8355Free": port_free(PORT),
        "memAvailableBytes": mem, "swapFreeBytes": swap, "oomKills": oom_kills(),
        "psiMemory": psi, "gpuTemperaturesC": temps,
        "guiAndOtherAppsAreNotGates": True,
        "outputPathsUnused": not collisions,
    }


def build_command(unit: str, arm: str, seed: int) -> list[str]:
    return [
        "systemd-run", "--user", "--scope", f"--unit={unit}",
        "--property=MemoryHigh=64G", "--property=MemoryMax=72G",
        "--property=TimeoutStopSec=15s", "--property=KillMode=control-group",
        f"--setenv=LCA_WORK_QUEUE_LOCK_TOKEN={TOKEN}",
        "--", "ionice", "-c", "3", str(PYTHON), str(ADAPTER),
        "--arm", arm, "--seed", str(seed),
    ]


def stop_owned_scope(unit: str) -> None:
    subprocess.run(["systemctl", "--user", "stop", f"{unit}.scope"],
                   capture_output=True, text=True, timeout=30, check=False)


def run(arm: str, seed: int, dry_run: bool) -> int:
    paths = output_paths(arm, seed)
    pf = preflight(arm, seed, paths)
    if dry_run:
        unit = f"q20-s23-{arm}-{seed}"
        print(json.dumps({"preflight": pf, "unit": unit, "command": build_command(unit, arm, seed),
                          "gpuStarted": False}, ensure_ascii=False))
        return 0 if pf["status"] == "pass" else 2
    paths["preflight"].write_text(json.dumps(pf, ensure_ascii=False, indent=2) + "\n")
    if pf["status"] != "pass":
        return 2

    unit = f"q20-s23-{arm}-{seed}"
    command = build_command(unit, arm, seed)
    started = time.monotonic()
    psi_some_count = psi_full_count = 0
    stop_reason = None
    samples = 0
    baseline_swap = pf["swapFreeBytes"]
    baseline_oom = pf["oomKills"]
    with paths["runnerlog"].open("xb") as runner_log:
        wrapper = subprocess.Popen(command, cwd=REPO, stdout=runner_log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
    scope = None
    scope_missing_since = None
    with paths["guardlog"].open("x", encoding="utf-8") as log:
        while wrapper.poll() is None:
            if not owned_lock():
                stop_reason = "Q20 lock ownership changed"
            if time.monotonic() - started > MAX_WALL:
                stop_reason = "arm exceeded 2700 seconds"
            current_scope = control_group(unit)
            if current_scope:
                scope = current_scope
                scope_missing_since = None
            elif scope is None:
                scope_missing_since = scope_missing_since or time.monotonic()
            cg = cgroup_values(scope)
            mem = proc_value("MemAvailable")
            swap = proc_value("SwapFree")
            oom = oom_kills()
            psi = psi_avg10()
            temps = gpu_temperatures()
            samples += 1
            psi_some_count = psi_some_count + 1 if psi.get("some", 100.0) > SOME_PSI_LIMIT else 0
            psi_full_count = psi_full_count + 1 if psi.get("full", 100.0) > FULL_PSI_LIMIT else 0
            sample = {
                "elapsedSeconds": round(time.monotonic() - started, 1),
                "memAvailableBytes": mem, "swapFreeBytes": swap, "oomKills": oom,
                "psiMemory": psi, "gpuTemperaturesC": temps, "scope": cg,
                "psiSomeConsecutiveSamples": psi_some_count,
                "psiFullConsecutiveSamples": psi_full_count,
            }
            log.write(json.dumps(sample, ensure_ascii=False) + "\n")
            log.flush()
            if mem < MIN_MEM_AVAILABLE:
                stop_reason = "MemAvailable below 48 GiB"
            elif baseline_swap - swap >= MAX_SWAP_DROP:
                stop_reason = "SwapFree dropped by at least 1 GiB"
            elif oom != baseline_oom:
                stop_reason = "host OOM kill counter changed"
            elif cg is None:
                if scope_missing_since is not None and time.monotonic() - scope_missing_since > 30:
                    stop_reason = "transient scope cgroup was not visible within 30 seconds"
            elif cg["memoryHigh"] != MEM_HIGH or cg["memoryMax"] != MEM_MAX:
                stop_reason = "transient scope memory.high/max mismatch"
            elif cg["memoryCurrent"] > SCOPE_ABORT_BYTES:
                stop_reason = "scope memory.current exceeded 68 GiB"
            elif psi_some_count >= PSI_PERSIST_SAMPLES:
                stop_reason = "some PSI avg10 exceeded 40% for four samples"
            elif psi_full_count >= PSI_PERSIST_SAMPLES:
                stop_reason = "full PSI avg10 exceeded 25% for four samples"
            elif temps and max(temps) >= 85:
                stop_reason = "GPU temperature reached 85 C"
            if stop_reason:
                break
            time.sleep(INTERVAL)

    if stop_reason:
        stop_owned_scope(unit)
        try:
            wrapper.wait(timeout=30)
        except subprocess.TimeoutExpired:
            wrapper.terminate()
            try:
                wrapper.wait(timeout=10)
            except subprocess.TimeoutExpired:
                wrapper.kill()
                wrapper.wait(timeout=10)
    else:
        wrapper.wait()

    external = inference_processes()
    post = {
        "atUtc": datetime.now(timezone.utc).isoformat(),
        "status": "completed" if wrapper.returncode == 0 and not stop_reason and not external and port_free(PORT) else "aborted_or_error",
        "arm": arm, "seed": seed, "attempt": 1, "unit": f"{unit}.scope",
        "command": command, "wrapperReturnCode": wrapper.returncode,
        "stopReason": stop_reason, "monitorSamples": samples,
        "inferenceProcessesAfter": external, "port8355FreeAfter": port_free(PORT),
        "memAvailableBytesAfter": proc_value("MemAvailable"),
        "swapFreeBytesAfter": proc_value("SwapFree"), "oomKillsAfter": oom_kills(),
        "lockOwnedAfter": owned_lock(),
    }
    paths["execution"].write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n")
    return 0 if post["status"] == "completed" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=("stock", "fp8"), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.seed <= 0:
        parser.error("--seed must be positive")
    if not owned_lock():
        raise SystemExit("Q20 lock ownership mismatch")
    return run(args.arm, args.seed, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
