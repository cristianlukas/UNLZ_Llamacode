#!/usr/bin/env python3
"""Run one legacy Muse CU replicate under memory/PSI/OOM guards.

Swap and page-out counters are recorded as telemetry only. On a sustained
resource abort, SIGINT is sent only to the task-owned Python runner so its
finally block can stop its private LlamaCode/Xvfb session.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import signal
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[4]
TASK = pathlib.Path(__file__).resolve().parents[1]
RUNNER = TASK / "scripts/run_muse_cu_session.py"
SOURCE = pathlib.Path("/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source")
PYTHON = SOURCE / ".venv/bin/python"
CONFIGS = {
    "astra": TASK / "receipts/configs/cu-astra.json",
    "q4": TASK / "receipts/configs/cu-q4.json",
}
GIB = 1024 ** 3
MIN_START = 32 * GIB
MIN_RUNTIME = 20 * GIB
PSI_SOME_ABORT = 80.0
PSI_FULL_ABORT = 60.0
STREAK_LIMIT = 15
PORTS = (8350, 8898)
DISPLAY = ":97"


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def snapshot() -> dict:
    mem = {}
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        key, value = line.split(":", 1)
        if key in {"MemAvailable", "SwapTotal", "SwapFree"}:
            mem[key] = int(value.strip().split()[0]) * 1024
    vm = {}
    for line in pathlib.Path("/proc/vmstat").read_text().splitlines():
        fields = line.split()
        if fields[0] in {"pswpin", "pswpout", "oom_kill"}:
            vm[fields[0]] = int(fields[1])
    psi = {}
    for line in pathlib.Path("/proc/pressure/memory").read_text().splitlines():
        fields = dict(item.split("=", 1) for item in line.split()[1:])
        psi[line.split()[0]] = {key: float(fields[key]) for key in ("avg10", "avg60", "avg300")}
    gpu = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid,name,used_memory", "--format=csv,noheader"],
        capture_output=True, text=True, timeout=10,
    )
    return {
        "atUtc": now(), "mem": mem, "vmstat": vm, "psi": psi,
        "computeApps": [line.strip() for line in gpu.stdout.splitlines() if line.strip()],
        "gpuQueryError": None if gpu.returncode == 0 else gpu.stderr.strip(),
    }


def port_free(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(1)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def display_free() -> bool:
    env = os.environ.copy()
    env["DISPLAY"] = DISPLAY
    proc = subprocess.run(["xprop", "-root"], env=env, capture_output=True, text=True, timeout=3)
    return proc.returncode != 0


def write_json(path: pathlib.Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def stop_group(proc: subprocess.Popen | None, label: str) -> None:
    if proc is None or proc.poll() is not None:
        return
    for sig, timeout in ((signal.SIGINT, 30), (signal.SIGTERM, 15), (signal.SIGKILL, 5)):
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            break
        try:
            proc.wait(timeout=timeout)
            return
        except subprocess.TimeoutExpired:
            continue
    if proc.poll() is None:
        raise RuntimeError(f"could not stop task-owned {label} process group")


def model_health() -> dict | None:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8350/health", timeout=1) as response:
            return json.loads(response.read())
    except Exception:
        return None


def preflight_errors(s: dict) -> list[str]:
    errors = []
    if s["mem"].get("MemAvailable", 0) < MIN_START:
        errors.append("MemAvailable below 32 GiB")
    if s["gpuQueryError"]:
        errors.append("nvidia-smi compute-process query failed")
    if s["computeApps"]:
        errors.append("CUDA compute process already active")
    if any(not port_free(port) for port in PORTS):
        errors.append("port 8350 or 8898 is busy")
    if not display_free():
        errors.append("private display :97 is already active")
    some = s["psi"].get("some", {}).get("avg10", 0.0)
    full = s["psi"].get("full", {}).get("avg10", 0.0)
    if some >= PSI_SOME_ABORT or full >= PSI_FULL_ABORT:
        errors.append("memory PSI is already at runtime abort threshold")
    return errors


def run(profile: str, attempt: int) -> int:
    if profile not in {"astra", "q4"}:
        raise SystemExit("usage: run_muse_cu_guarded.py {astra|q4} [attempt]")
    name = f"cu-{profile}-base-r2-attempt-{attempt:02d}"
    receipt = TASK / "receipts" / f"{name}-controller.json"
    monitor_path = TASK / "receipts" / "logs" / f"{name}-resource-monitor.jsonl"
    child_log_path = TASK / "receipts" / "logs" / f"{name}.log"
    engine_log_path = TASK / "receipts" / "logs" / f"cu-{profile}-engine-attempt-{attempt:02d}.log"
    config = CONFIGS[profile]
    config_data = json.loads(config.read_text(encoding="utf-8"))
    initial = snapshot()
    errors = preflight_errors(initial)
    baseline_oom = initial["vmstat"].get("oom_kill", 0)
    record = {
        "taskId": TASK.name, "profile": profile, "arm": "base", "replicate": 2,
        "attempt": attempt, "runner": str(RUNNER), "startedAtUtc": now(),
        "configPath": str(config.resolve()),
        "configSha256": __import__("hashlib").sha256(config.read_bytes()).hexdigest(),
        "engineCommand": [str(PYTHON), str(SOURCE / "serve/server.py"), "--engine", "strata",
                          "--config", str(config.resolve()), "--host", "127.0.0.1", "--port", "8350", "--gpu", "0,1"],
        "engineLog": str(engine_log_path.resolve()),
        "preflight": initial, "preflightErrors": errors,
        "oomKillBaseline": baseline_oom,
        "thresholds": {
            "MemAvailableStartGiB": 32, "MemAvailableAbortGiB": 20,
            "PSISomeAvg10Abort": PSI_SOME_ABORT, "PSIFullAvg10Abort": PSI_FULL_ABORT,
            "abortStreakSamples": STREAK_LIMIT, "swapFreeIsTelemetryOnly": True,
        },
    }
    if errors:
        record.update({"status": "blocked_preflight", "postflight": snapshot()})
        write_json(receipt, record)
        print(json.dumps({"profile": profile, "status": record["status"], "errors": errors}), flush=True)
        return 2

    env = os.environ.copy()
    env.update(config_data.get("env", {}))
    child_log_path.parent.mkdir(parents=True, exist_ok=True)
    monitor_path.parent.mkdir(parents=True, exist_ok=True)
    engine_log_path.parent.mkdir(parents=True, exist_ok=True)
    reason = None
    low_mem_streak = high_psi_streak = 0
    samples = []
    started = time.monotonic()
    cmd = [sys.executable, str(RUNNER), "--profile", profile, "--arm", "base",
           "--rep", "2", "--attempt", str(attempt), "--port", "8898", "--display", DISPLAY]
    record["command"] = cmd
    server = child = None
    status = "starting"
    def sample(monitor):
        nonlocal reason, low_mem_streak, high_psi_streak
        snap = snapshot()
        monitor.write(json.dumps(snap) + "\n")
        monitor.flush()
        samples.append(snap)
        available = snap["mem"].get("MemAvailable", 0)
        low_mem_streak = low_mem_streak + 1 if available < MIN_RUNTIME else 0
        some = snap["psi"].get("some", {}).get("avg10", 0.0)
        full = snap["psi"].get("full", {}).get("avg10", 0.0)
        high_psi_streak = high_psi_streak + 1 if some >= PSI_SOME_ABORT or full >= PSI_FULL_ABORT else 0
        if snap["vmstat"].get("oom_kill", 0) > baseline_oom:
            reason = "system oom_kill counter increased"
        elif low_mem_streak >= STREAK_LIMIT:
            reason = f"MemAvailable below 20 GiB for {low_mem_streak} samples"
        elif high_psi_streak >= STREAK_LIMIT:
            reason = f"memory PSI remained high: some={some}, full={full}"
        return snap

    with child_log_path.open("w", encoding="utf-8") as child_log, \
            engine_log_path.open("w", encoding="utf-8") as engine_log, \
            monitor_path.open("w", encoding="utf-8") as monitor:
        try:
            server = subprocess.Popen(record["engineCommand"], cwd=SOURCE, env=env,
                                      stdout=engine_log, stderr=subprocess.STDOUT, start_new_session=True)
            record["serverPid"] = server.pid
            record["status"] = "loading_model"
            write_json(receipt, record)
            load_deadline = time.monotonic() + 900
            health = None
            while time.monotonic() < load_deadline:
                snap = sample(monitor)
                if reason:
                    raise RuntimeError("resource guard: " + reason)
                if server.poll() is not None:
                    raise RuntimeError(f"Strata exited during load with {server.returncode}")
                health = model_health()
                if health and health.get("status") == "ok":
                    expected_context = 131072
                    expected_images = bool(config_data.get("vision"))
                    if health.get("max_context") != expected_context or bool(health.get("images")) != expected_images:
                        raise RuntimeError(f"Strata health does not match frozen config: {health}")
                    models_url = urllib.request.urlopen("http://127.0.0.1:8350/v1/models", timeout=10)
                    models = json.loads(models_url.read())
                    models_url.close()
                    advertised = json.dumps(models, ensure_ascii=False).casefold()
                    markers = {"astra": ("astra", "iq3_s"), "q4": ("unsloth", "q4_k_xl")}[profile]
                    if not all(marker in advertised for marker in markers):
                        raise RuntimeError(f"Loaded endpoint model does not match {profile}: {models}")
                    record["health"] = health
                    record["endpointModels"] = models
                    record["apiReadyAtUtc"] = now()
                    break
                time.sleep(1)
            else:
                raise TimeoutError("Strata API did not become ready in 900 seconds")
            child = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=child_log,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            record["runnerPid"] = child.pid
            record["status"] = "running"
            write_json(receipt, record)
            while child.poll() is None:
                sample(monitor)
                if reason:
                    record["abortReason"] = reason
                    record["status"] = "aborting_guard"
                    write_json(receipt, record)
                    child.send_signal(signal.SIGINT)
                    try:
                        child.wait(timeout=45)
                    except subprocess.TimeoutExpired:
                        child.terminate()
                        try:
                            child.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            child.kill()
                            child.wait(timeout=5)
                    break
                if server.poll() is not None:
                    raise RuntimeError(f"Strata exited during CU with {server.returncode}")
                time.sleep(1)
            if reason:
                status = "aborted_guard"
            else:
                status = "completed" if child.returncode == 0 else "runner_failed"
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
            status = "aborted_guard" if reason else "failed"
            if child is not None and child.poll() is None:
                child.send_signal(signal.SIGINT)
                try:
                    child.wait(timeout=45)
                except subprocess.TimeoutExpired:
                    child.terminate()
                    child.wait(timeout=10)
        finally:
            stop_group(server, "Strata server")
    post = snapshot()
    record.update({
        "runnerExitCode": None if child is None else child.returncode,
        "serverStopped": server is None or server.poll() is not None,
        "status": status,
        "abortReason": reason,
        "postflight": post,
        "port8350Free": port_free(8350), "port8898Free": port_free(8898),
        "display97Free": display_free(),
        "minMemAvailableBytes": min((s["mem"].get("MemAvailable", 0) for s in samples), default=initial["mem"].get("MemAvailable")),
        "minSwapFreeBytes": min((s["mem"].get("SwapFree", 0) for s in samples), default=initial["mem"].get("SwapFree")),
        "maxPsiSomeAvg10": max((s["psi"].get("some", {}).get("avg10", 0.0) for s in samples), default=0),
        "oomKillDelta": post["vmstat"].get("oom_kill", 0) - baseline_oom,
        "swapOutPagesDelta": post["vmstat"].get("pswpout", 0) - initial["vmstat"].get("pswpout", 0),
        "elapsedSeconds": round(time.monotonic() - started, 3),
        "finishedAtUtc": now(),
    })
    write_json(receipt, record)
    print(json.dumps({"profile": profile, "status": record["status"], "exitCode": record["runnerExitCode"],
                      "elapsedSeconds": record["elapsedSeconds"], "minMemAvailableBytes": record["minMemAvailableBytes"],
                      "minSwapFreeBytes": record["minSwapFreeBytes"], "maxPsiSomeAvg10": record["maxPsiSomeAvg10"],
                      "portsFree": record["port8350Free"] and record["port8898Free"],
                      "displayFree": record["display97Free"], "abortReason": reason}, ensure_ascii=False), flush=True)
    return 0 if record["status"] == "completed" and record["port8350Free"] and record["port8898Free"] and record["display97Free"] else 1


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        raise SystemExit("usage: run_muse_cu_guarded.py {astra|q4} [attempt]")
    raise SystemExit(run(sys.argv[1], int(sys.argv[2]) if len(sys.argv) == 3 else 3))
