#!/usr/bin/env python3
"""Run one isolated Strata screen with a host-pressure monitor and cleanup."""

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
import urllib.error
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[4]
TASK = pathlib.Path(__file__).resolve().parents[1]
SOURCE = pathlib.Path("/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source")
PYTHON = SOURCE / ".venv/bin/python"
ENGINE_CONFIGS = {
    "context262k": ("iq3xxs-context262k-attempt03.json", 8351, 262144, False),
    "astraVision": ("astra-vision-attempt03.json", 8350, 131072, True),
    "cuRetry": ("iq3xxs-context131k-attempt02.json", 8350, 131072, False),
}
GIB = 1024**3
MIN_BEFORE_LOAD = 32 * GIB
MIN_DURING_RUN = 20 * GIB
MIN_SWAP_FREE = 1 * GIB
MAX_SOME_AVG10 = 80.0
MAX_FULL_AVG10 = 60.0
PSI_HIGH_SAMPLES = 15


def mem_and_pressure() -> dict:
    mem = {}
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        key, value = line.split(":", 1)
        if key in {"MemAvailable", "SwapTotal", "SwapFree"}:
            mem[key] = int(value.strip().split()[0]) * 1024
    vmstat = {}
    for line in pathlib.Path("/proc/vmstat").read_text().splitlines():
        fields = line.split()
        if fields[0] in {"pswpin", "pswpout"}:
            vmstat[fields[0]] = int(fields[1])
    psi = {}
    for line in pathlib.Path("/proc/pressure/memory").read_text().splitlines():
        parts = line.split()
        fields = dict(x.split("=", 1) for x in parts[1:])
        psi[parts[0]] = {k: float(fields[k]) for k in ("avg10", "avg60", "avg300")}
    return {
        "atUtc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "memAvailableBytes": mem.get("MemAvailable"),
        "swapFreeBytes": mem.get("SwapFree"),
        "swapTotalBytes": mem.get("SwapTotal"),
        "swapUsedBytes": mem.get("SwapTotal", 0) - mem.get("SwapFree", 0),
        "swapVmstatPages": vmstat,
        "psiMemory": psi,
    }


def compute_processes() -> list[str]:
    result = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid,name,used_memory", "--format=csv,noheader"],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError("nvidia-smi compute-process preflight failed: " + result.stderr.strip())
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def check_guard(snapshot: dict, baseline_pswpout: int, high_streak: int, before_load: bool = False):
    available = snapshot["memAvailableBytes"]
    floor = MIN_BEFORE_LOAD if before_load else MIN_DURING_RUN
    if available is None or available < floor:
        raise RuntimeError(f"resource guard: MemAvailable {available} below {floor}")
    swap_free = snapshot.get("swapFreeBytes")
    if swap_free is None or swap_free < MIN_SWAP_FREE:
        raise RuntimeError(f"resource guard: SwapFree below 1 GiB: {swap_free}")
    some = snapshot["psiMemory"].get("some", {}).get("avg10", 0.0)
    full = snapshot["psiMemory"].get("full", {}).get("avg10", 0.0)
    if some >= MAX_SOME_AVG10 or full >= MAX_FULL_AVG10:
        high_streak += 1
    else:
        high_streak = 0
    if high_streak >= PSI_HIGH_SAMPLES:
        raise RuntimeError(
            f"resource guard: PSI stayed high for {high_streak} samples "
            f"(some={some}, full={full})"
        )
    return high_streak


def port_open(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(1)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def health(port: int):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as response:
            return json.loads(response.read())
    except Exception:
        return None


def stop_group(proc: subprocess.Popen | None, label: str):
    if proc is None or proc.poll() is not None:
        return
    for sig, timeout in ((signal.SIGINT, 25), (signal.SIGTERM, 10), (signal.SIGKILL, 5)):
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


def child_command(mode: str, port: int, baseline_pswpout: int, env: dict[str, str], attempt: int, config: pathlib.Path) -> tuple[list[str], pathlib.Path | None]:
    base = f"http://127.0.0.1:{port}"
    if mode == "context262k":
        tokenizer = pathlib.Path("/media/cristian/Disco local/Models/FlashNext-IQ3XXS-ISTA-Strata-eval-20261009/strata-data/packs/iq3_xxs/tokenizer")
        module = SOURCE / "tools/strata_tokenizer.py"
        out = TASK / f"receipts/context/iq3xxs-262k-attempt-{attempt:02d}.json"
        command = [
            str(PYTHON), str(TASK / "scripts/probe_262k_revised_guard.py"),
            "--tokenizer-dir", str(tokenizer), "--tokenizer-module", str(module),
            "--config", str(config),
            "--endpoint", base + "/v1/chat/completions", "--out", str(out),
        ]
        env["LC_EVAL_PSWPOUT_BASELINE"] = str(baseline_pswpout)
        return command, out
    if mode == "astraVision":
        fixtures = TASK / "fixtures/vision-holdout-v1"
        out = TASK / f"receipts/vision/astra-control-attempt-{attempt:02d}.json"
        return [
            sys.executable, str(TASK / "scripts/run_vision_smoke.py"),
            "--endpoint", base + "/v1/chat/completions", "--profile", "ASTRA IQ3_S / Strata v0.1.41",
            "--image", str(fixtures / "vision-holdout.png"),
            "--prompt", str(fixtures / "prompt.txt"),
            "--expected", str(fixtures / "expected.json"), "--out", str(out),
        ], out
    out = TASK / "receipts/sessions/iq3xxs-cu-r2-try3/controller-child.log"
    out.parent.mkdir(parents=True, exist_ok=True)
    return [
        sys.executable, str(TASK / "scripts/run_cu_retry.py"),
        "--profile", "iq3xxs", "--arm", "base", "--rep", "2", "--attempt", "3",
        "--port", "8898", "--display", ":98",
    ], None


def main() -> int:
    if len(sys.argv) not in (2, 3) or sys.argv[1] not in ENGINE_CONFIGS:
        raise SystemExit("usage: run_resource_guarded_screen.py {context262k|astraVision|cuRetry} [attempt]")
    mode = sys.argv[1]
    attempt = int(sys.argv[2]) if len(sys.argv) == 3 else 1
    if attempt < 1:
        raise SystemExit("attempt must be positive")
    config_name, port, expected_context, expected_images = ENGINE_CONFIGS[mode]
    config = TASK / "receipts/configs" / config_name
    engine_log = TASK / "receipts/logs" / (config.stem + ".server-console.log")
    monitor_log = TASK / "receipts/logs" / f"{mode}-attempt-{attempt:02d}.resource-monitor.jsonl"
    summary_path = TASK / "receipts" / f"{mode}-attempt-{attempt:02d}-controller.json"
    config_data = json.loads(config.read_text(encoding="utf-8"))
    initial = mem_and_pressure()
    baseline_pswpout = initial["swapVmstatPages"].get("pswpout", 0)
    compute = compute_processes()
    receipt = {
        "taskId": "Q-20261015-IQ3XXS-REMAINING-SCREENS",
        "mode": mode,
        "attempt": attempt,
        "startedAtUtc": initial["atUtc"],
        "configPath": str(config.resolve()),
        "configSha256": __import__("hashlib").sha256(config.read_bytes()).hexdigest(),
        "engineCommand": [str(PYTHON), "-m", "serve.server", "--engine", "strata",
                          "--config", str(config.resolve()), "--host", "127.0.0.1", "--port", str(port)],
        "port": port,
        "expectedHealth": {"max_context": expected_context, "images": expected_images},
        "preflight": initial,
        "computeProcesses": compute,
        "samples": [],
        "status": "starting",
        "engineLog": str(engine_log.resolve()),
        "monitorLog": str(monitor_log.resolve()),
    }
    if initial["memAvailableBytes"] is None or initial["memAvailableBytes"] < MIN_BEFORE_LOAD:
        receipt.update({"status": "blocked_preflight_guard", "error": "MemAvailable below 32 GiB"})
        summary_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        return 2
    if initial.get("swapFreeBytes") is None or initial["swapFreeBytes"] < MIN_SWAP_FREE:
        receipt.update({"status": "blocked_preflight_guard", "error": "SwapFree below 1 GiB"})
        summary_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        return 2
    if compute:
        receipt.update({"status": "blocked_preflight_gpu_busy", "error": "unrelated CUDA compute process present"})
        summary_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        return 2
    if port_open(port):
        receipt.update({"status": "blocked_preflight_port_busy", "error": f"port {port} already in use"})
        summary_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        return 2

    engine_log.parent.mkdir(parents=True, exist_ok=True)
    monitor_log.parent.mkdir(parents=True, exist_ok=True)
    server_proc = None
    child_proc = None
    server_f = engine_log.open("w", encoding="utf-8")
    child_log_path = TASK / "receipts/sessions" / f"{mode}-attempt-{attempt:02d}" / "child.log"
    child_log_path.parent.mkdir(parents=True, exist_ok=True)
    child_f = child_log_path.open("w", encoding="utf-8")
    env = os.environ.copy()
    high_streak = 0
    last_sample = 0.0
    try:
        server_proc = subprocess.Popen(
            receipt["engineCommand"], cwd=SOURCE, env=env,
            stdout=server_f, stderr=subprocess.STDOUT, start_new_session=True,
        )
        receipt["serverPid"] = server_proc.pid
        load_deadline = time.monotonic() + 900
        monitor = monitor_log.open("w", encoding="utf-8")
        try:
            while time.monotonic() < load_deadline:
                snap = mem_and_pressure()
                high_streak = check_guard(snap, baseline_pswpout, high_streak)
                monitor.write(json.dumps(snap) + "\n")
                monitor.flush()
                receipt["samples"].append(snap)
                if server_proc.poll() is not None:
                    raise RuntimeError(f"server exited during startup with {server_proc.returncode}")
                h = health(port)
                if h and h.get("status") == "ok":
                    receipt["health"] = h
                    if h.get("max_context") != expected_context or bool(h.get("images")) != expected_images:
                        raise RuntimeError(f"server health does not match frozen config: {h}")
                    break
                time.sleep(1)
            else:
                receipt.update({"status": "aborted_api_not_ready", "error": "API did not become ready in 900s"})
                raise TimeoutError("API did not become ready in 900s")
            receipt["apiReadyAtUtc"] = dt.datetime.now(dt.timezone.utc).isoformat()
            command, expected_out = child_command(mode, port, baseline_pswpout, env, attempt, config)
            receipt["childCommand"] = command
            receipt["childReceipt"] = str(expected_out.resolve()) if expected_out else None
            child_proc = subprocess.Popen(
                command, cwd=ROOT, env=env, stdout=child_f, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            receipt["childPid"] = child_proc.pid
            run_deadline = time.monotonic() + 900
            while time.monotonic() < run_deadline:
                snap = mem_and_pressure()
                high_streak = check_guard(snap, baseline_pswpout, high_streak)
                if time.monotonic() - last_sample >= 1:
                    monitor.write(json.dumps(snap) + "\n")
                    monitor.flush()
                    receipt["samples"].append(snap)
                    last_sample = time.monotonic()
                if child_proc.poll() is not None:
                    receipt["childExitCode"] = child_proc.returncode
                    receipt["status"] = "completed" if child_proc.returncode == 0 else "child_nonzero"
                    break
                if server_proc.poll() is not None:
                    raise RuntimeError(f"server exited during screen with {server_proc.returncode}")
                time.sleep(1)
            else:
                receipt.update({"status": "aborted_child_timeout", "error": "screen exceeded 900s"})
                stop_group(child_proc, "screen runner")
                receipt["childExitCode"] = child_proc.returncode
        finally:
            monitor.close()
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        receipt["error"] = message
        if "resource guard" in message:
            receipt["status"] = "aborted_resource_guard"
        elif receipt.get("status") == "starting":
            receipt["status"] = "aborted_infrastructure"
    finally:
        try:
            stop_group(child_proc, "screen runner")
        finally:
            stop_group(server_proc, "Strata server")
            child_f.close()
            server_f.close()
    receipt["postflight"] = mem_and_pressure()
    receipt["serverStopped"] = server_proc is None or server_proc.poll() is not None
    receipt["portOpenAfterCleanup"] = port_open(port)
    if receipt.get("status") == "completed" and mode != "cuRetry" and expected_out and expected_out.exists():
        result = json.loads(expected_out.read_text(encoding="utf-8"))
        receipt["quality"] = {
            "status": result.get("status"),
            "exactMatch": result.get("retrievalExact") if mode == "context262k" else result.get("exactMatch"),
            "exactMatchCount": result.get("exactMatchCount"),
            "exactMatchTotal": result.get("exactMatchTotal"),
            "transportError": result.get("transportError"),
        }
    receipt["finishedAtUtc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    summary_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt.get(k) for k in ("mode", "status", "childExitCode", "error", "quality", "serverStopped", "portOpenAfterCleanup")}, ensure_ascii=False))
    return 0 if receipt.get("status") == "completed" and not receipt.get("portOpenAfterCleanup") else 1


if __name__ == "__main__":
    raise SystemExit(main())
