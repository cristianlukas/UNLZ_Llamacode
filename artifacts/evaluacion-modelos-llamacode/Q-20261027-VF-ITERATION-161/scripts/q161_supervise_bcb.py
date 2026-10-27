#!/usr/bin/env python3
"""Run Q161 BCB-Hard-8 with explicit reasoning budget and owned-process cleanup."""
from __future__ import annotations

import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[4]
QDIR = Path(__file__).resolve().parents[1]
MODEL = Path("/media/cristian/Disco local/Models-eval/Q152-GyroCoderL/Qwen3.8-Flash-Next-Gyro-Coder-L-TQ3_0-v1.1.gguf")
SERVER = Path("/media/cristian/Disco local/Models-eval/Q160-agention-llama-build/bin/llama-server")
RUNNER = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261027-VF-ITERATION-161/scripts/q161_run_bcb_budgeted.py"
FIXTURE = ROOT / "artifacts/bigcodebench-hard-ubuntu-8.json"
MODEL_BYTES = 83_975_624_672
MODEL_SHA256 = "377d5aa5b473a89b4d0d0c9fbd54fd8fcc46da19c16fc881860577189c1403df"
RUNNER_SHA256 = "b4eea9c2f9285c640a5ed1aab58ce5982cb968c3b24c90b4231980a95b33f150"
FIXTURE_SHA256 = "11279cde14113fc8527f141c53e14cb5ccf0dba65749081a4f914408e391c268"
HOST, PORT = "127.0.0.1", 18383
ALIAS = "Gyro-Coder-L-Q161"
STOP = threading.Event()
STOP_REASON: list[str] = []
STOP_LOCK = threading.Lock()


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def set_stop(reason: str) -> None:
    with STOP_LOCK:
        if not STOP_REASON:
            STOP_REASON.append(reason)
    STOP.set()


def proc_table() -> list[tuple[int, int, str, str]]:
    result = subprocess.run(["ps", "-eo", "pid=,pgid=,comm=,args="], capture_output=True, text=True, check=True)
    rows = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(None, 3)
        if len(parts) == 4:
            try:
                rows.append((int(parts[0]), int(parts[1]), parts[2], parts[3]))
            except ValueError:
                continue
    return rows


def other_inference_processes() -> list[str]:
    matches = []
    for pid, _pgid, comm, args in proc_table():
        if pid == os.getpid():
            continue
        if comm in {"llama-server", "llama_server", "llama.cpp"} or "llama-server" in args or "llama_server" in args:
            matches.append(f"pid={pid} comm={comm} args={args[:240]}")
    return matches


def ensure_port_free() -> None:
    with socket.socket() as sock:
        try:
            sock.bind((HOST, PORT))
        except OSError as e:
            raise RuntimeError(f"loopback port {PORT} is not free: {e}") from e


def oom_kills() -> int:
    try:
        for line in Path("/proc/vmstat").read_text().splitlines():
            if line.startswith("oom_kill "):
                return int(line.split()[1])
    except OSError:
        pass
    return 0


def cgroup_oom_kills(pid: int | None) -> int | None:
    if not pid:
        return None
    try:
        lines = Path(f"/proc/{pid}/cgroup").read_text().splitlines()
        path = next(x.split("::", 1)[1] for x in lines if "::" in x)
        events = Path("/sys/fs/cgroup") / path.lstrip("/") / "memory.events"
        for line in events.read_text().splitlines():
            if line.startswith("oom_kill "):
                return int(line.split()[1])
    except (OSError, StopIteration, IndexError, ValueError):
        return None
    return None


def psi() -> tuple[float, float]:
    some = full = 0.0
    for line in Path("/proc/pressure/memory").read_text().splitlines():
        fields = dict(part.split("=", 1) for part in line.split()[1:] if "=" in part)
        if line.startswith("some "):
            some = float(fields.get("avg10", 0.0))
        elif line.startswith("full "):
            full = float(fields.get("avg10", 0.0))
    return some, full


def gpu_snapshot() -> tuple[list[str], list[dict[str, str]]]:
    cards = subprocess.run(
        ["nvidia-smi", "--query-gpu=uuid,name,utilization.gpu,memory.used,memory.free", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, check=True,
    ).stdout.strip().splitlines()
    parsed_cards = []
    for row in cards:
        cols = [x.strip() for x in row.split(",", 4)]
        if len(cols) == 5:
            parsed_cards.append(dict(zip(("uuid", "name", "utilizationGpuPct", "memoryUsedMiB", "memoryFreeMiB"), cols)))
    apps_out = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid,gpu_uuid,used_memory", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, check=True,
    ).stdout.strip().splitlines()
    apps = []
    for row in apps_out:
        cols = [x.strip() for x in row.split(",", 2)]
        if len(cols) == 3 and cols[0].isdigit():
            apps.append(dict(zip(("pid", "gpuUuid", "usedMemoryMiB"), cols)))
    return [x["uuid"] for x in parsed_cards], apps


def owned_group_pids(pgid: int) -> set[int]:
    return {pid for pid, group, _comm, _args in proc_table() if group == pgid}


def mem_snapshot() -> dict[str, int | None]:
    mem = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith(("MemAvailable:", "SwapFree:", "SwapTotal:")):
                key, rest = line.split(":", 1)
                mem[key] = int(rest.strip().split()[0]) * 1024
    except OSError:
        pass
    return {"memAvailableBytes": mem.get("MemAvailable"), "swapFreeBytes": mem.get("SwapFree"), "swapTotalBytes": mem.get("SwapTotal")}


def write_sample(path: Path, server_pid: int | None, baseline_oom: int, baseline_cgroup_oom: int | None, streak: dict[str, int]) -> dict:
    record: dict = {"timestampUtc": now(), **mem_snapshot()}
    try:
        record["psiSomeAvg10Pct"], record["psiFullAvg10Pct"] = psi()
    except Exception as e:
        record["psiError"] = f"{type(e).__name__}: {e}"
        record["psiSomeAvg10Pct"] = record["psiFullAvg10Pct"] = 0.0
    try:
        record["gpuUuids"], record["computeApps"] = gpu_snapshot()
    except Exception as e:
        record["gpuError"] = f"{type(e).__name__}: {e}"
        record["gpuUuids"], record["computeApps"] = [], []
    global_now = oom_kills()
    cgroup_now = cgroup_oom_kills(server_pid)
    record["oomKillCountGlobal"] = global_now
    record["oomKillCountCgroup"] = cgroup_now
    record["oomKillDeltaGlobal"] = global_now - baseline_oom
    record["oomKillDeltaCgroup"] = None if baseline_cgroup_oom is None or cgroup_now is None else cgroup_now - baseline_cgroup_oom
    some, full = record["psiSomeAvg10Pct"], record["psiFullAvg10Pct"]
    streak["some"] = streak["some"] + 1 if some >= 80.0 else 0
    streak["full"] = streak["full"] + 1 if full >= 60.0 else 0
    record["psiSomeSevereConsecutiveSamples"] = streak["some"]
    record["psiFullSevereConsecutiveSamples"] = streak["full"]
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    if global_now > baseline_oom:
        set_stop(f"global oom_kill counter increased from {baseline_oom} to {global_now}")
    if baseline_cgroup_oom is not None and cgroup_now is not None and cgroup_now > baseline_cgroup_oom:
        set_stop(f"test cgroup oom_kill counter increased from {baseline_cgroup_oom} to {cgroup_now}")
    if streak["some"] >= 15:
        set_stop("global memory PSI some avg10 >=80% for 15 consecutive one-second samples")
    if streak["full"] >= 15:
        set_stop("global memory PSI full avg10 >=60% for 15 consecutive one-second samples")
    return record


def monitor_loop(path: Path, server_pid: int, baseline_oom: int, baseline_cgroup_oom: int | None) -> None:
    streak = {"some": 0, "full": 0}
    while not STOP.is_set():
        try:
            write_sample(path, server_pid, baseline_oom, baseline_cgroup_oom, streak)
        except Exception as e:
            set_stop(f"resource monitor failed: {type(e).__name__}: {e}")
        STOP.wait(1)


def terminate_owned(proc: subprocess.Popen | None, label: str) -> dict:
    if proc is None:
        return {"label": label, "started": False, "clean": True}
    result = {"label": label, "started": True, "pid": proc.pid, "pgid": proc.pid, "signals": []}
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        result["signals"].append("SIGTERM")
    except ProcessLookupError:
        pass
    if proc.poll() is None:
        try:
            proc.wait(timeout=25)
        except subprocess.TimeoutExpired:
            pass
    time.sleep(0.25)
    try:
        os.killpg(proc.pid, 0)
        group_exists = True
    except ProcessLookupError:
        group_exists = False
    if group_exists:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
            result["signals"].append("SIGKILL")
        except ProcessLookupError:
            pass
        if proc.poll() is None:
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                result["clean"] = False
    result["exitCode"] = proc.poll()
    try:
        os.killpg(proc.pid, 0)
        result["processGroupGone"] = False
    except ProcessLookupError:
        result["processGroupGone"] = True
    result["clean"] = result.get("clean", True) and result["processGroupGone"]
    return result


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = QDIR / "runs" / f"gyro-coder-l-budget2048-screen-seed-4242-{stamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    monitor_path = run_dir / "resource-samples.jsonl"
    server_log_path = run_dir / "server.log"
    runner_log_path = run_dir / "runner.log"
    runner_output = run_dir / "result.json"
    receipt_path = QDIR / "receipts" / f"screen-run-{stamp}.json"
    started = now()
    server: subprocess.Popen | None = None
    runner: subprocess.Popen | None = None
    monitor: threading.Thread | None = None
    server_log = None
    runner_log = None
    cleanup: list[dict] = []
    baseline_oom = oom_kills()
    preflight: dict = {"timestampUtc": started, "modelPath": str(MODEL), "serverBinary": str(SERVER), "port": PORT}
    status = "preflight_failed"
    error = None
    runner_exit = None
    try:
        if not MODEL.is_file() or MODEL.stat().st_size != MODEL_BYTES:
            raise RuntimeError(f"model byte-size gate failed: {MODEL.stat().st_size if MODEL.exists() else 'missing'} / {MODEL_BYTES}")
        model_hash = sha256(MODEL)
        if model_hash != MODEL_SHA256:
            raise RuntimeError(f"model SHA-256 mismatch: {model_hash}")
        if sha256(RUNNER) != RUNNER_SHA256:
            raise RuntimeError("Q161 runner SHA-256 mismatch")
        if sha256(FIXTURE) != FIXTURE_SHA256:
            raise RuntimeError("BCB fixture SHA-256 mismatch")
        if not SERVER.is_file() or not os.access(SERVER, os.X_OK):
            raise RuntimeError("pinned llama-server binary is missing or not executable")
        others = other_inference_processes()
        if others:
            raise RuntimeError("another inference server is active; no process was stopped: " + "; ".join(others))
        ensure_port_free()
        gpu_uuids, app_rows = gpu_snapshot()
        gpu_names = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True, check=True).stdout.splitlines()
        if len(gpu_uuids) < 2 or sum("RTX 3090" in name for name in gpu_names) < 2:
            raise RuntimeError(f"two RTX 3090s are not visible: {gpu_names}")
        preflight.update({"status": "pass", "modelBytes": MODEL.stat().st_size, "modelSha256": model_hash,
                          "runnerSha256": RUNNER_SHA256, "fixtureSha256": FIXTURE_SHA256,
                          "gpuUuids": gpu_uuids, "gpuNames": gpu_names, "computeAppsBefore": app_rows,
                          "oomKillGlobalBefore": baseline_oom, **mem_snapshot()})
        (run_dir / "preflight.json").write_text(json.dumps(preflight, ensure_ascii=False, indent=2) + "\n")
        launch = [str(SERVER), "--model", str(MODEL), "--alias", ALIAS,
                  "--host", HOST, "--port", str(PORT), "--ctx-size", "8192",
                  "--n-gpu-layers", "999", "--split-mode", "layer", "--tensor-split", "1,1",
                  "--fit", "on", "--flash-attn", "on", "--jinja", "--ngram-on-disk", "--reasoning", "on"]
        env = os.environ.copy(); env["CUDA_VISIBLE_DEVICES"] = "0,1"
        server_log = server_log_path.open("w", encoding="utf-8")
        server = subprocess.Popen(launch, cwd=SERVER.parent, stdout=server_log, stderr=subprocess.STDOUT,
                                  env=env, start_new_session=True, text=True)
        baseline_cg = cgroup_oom_kills(server.pid)
        monitor = threading.Thread(target=monitor_loop, args=(monitor_path, server.pid, baseline_oom, baseline_cg), daemon=True)
        monitor.start()
        status = "server_starting"
        deadline = time.monotonic() + 2700
        ready = False
        last_note = 0.0
        while time.monotonic() < deadline and not STOP.is_set():
            if server.poll() is not None:
                raise RuntimeError(f"llama-server exited during startup with code {server.returncode}")
            try:
                with urlopen(f"http://{HOST}:{PORT}/health", timeout=3) as response:
                    health = response.status == 200
            except Exception:
                health = False
            _, apps = gpu_snapshot()
            owned_pids = owned_group_pids(server.pid)
            owned_uuids = {a["gpuUuid"] for a in apps if int(a["pid"]) in owned_pids}
            if health and len(owned_uuids.intersection(set(gpu_uuids))) >= 2:
                ready = True
                break
            if STOP.is_set():
                raise RuntimeError(STOP_REASON[0])
            if time.monotonic() - last_note >= 60:
                print(f"startup pending: health={health}; owned GPUs={len(owned_uuids & set(gpu_uuids))}/2", flush=True)
                last_note = time.monotonic()
            time.sleep(2)
        if not ready:
            raise RuntimeError("server readiness or two-GPU ownership gate timed out after 2700 seconds")
        status = "screen_running"
        preflight.update({"serverPid": server.pid, "serverReady": True, "serverOwnedGpuUuids": sorted(owned_uuids), "serverArguments": launch})
        (run_dir / "preflight.json").write_text(json.dumps(preflight, ensure_ascii=False, indent=2) + "\n")
        runner_cmd = [sys.executable, str(RUNNER), "--url", f"http://{HOST}:{PORT}/v1/chat/completions",
                      "--arm", "swift", "--model", ALIAS, "--seed", "4242", "--out", str(runner_output), "--max-tokens", "6144", "--budget", "2048"]
        runner_log = runner_log_path.open("w", encoding="utf-8")
        runner = subprocess.Popen(runner_cmd, cwd=ROOT, stdout=runner_log, stderr=subprocess.STDOUT,
                                  start_new_session=True, text=True)
        log_pos = 0
        while runner.poll() is None:
            if STOP.is_set():
                raise RuntimeError(STOP_REASON[0])
            if server.poll() is not None:
                raise RuntimeError(f"llama-server exited while the benchmark runner was active with code {server.returncode}")
            try:
                with runner_log_path.open("r", encoding="utf-8", errors="replace") as f:
                    f.seek(log_pos)
                    chunk = f.read()
                    log_pos = f.tell()
                    if chunk:
                        print(chunk, end="", flush=True)
            except OSError:
                pass
            time.sleep(0.5)
        runner_exit = runner.returncode
        try:
            with runner_log_path.open("r", encoding="utf-8", errors="replace") as f:
                f.seek(log_pos); print(f.read(), end="", flush=True)
        except OSError:
            pass
        if runner_exit != 0:
            status = "screen_incomplete_or_gate_failed"
        else:
            status = "screen_completed"
    except KeyboardInterrupt:
        status = "interrupted"
        error = "KeyboardInterrupt"
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        if STOP.is_set() and STOP_REASON:
            status = "stopped_by_safety_gate"
            error = STOP_REASON[0]
    finally:
        if runner_log:
            runner_log.close()
        if server_log:
            server_log.close()
        if runner is not None and runner.poll() is None:
            cleanup.append(terminate_owned(runner, "Q161 BCB runner process group"))
        if server is not None:
            cleanup.append(terminate_owned(server, "Q161 candidate llama-server process group"))
        STOP.set()
        if monitor:
            monitor.join(timeout=5)
        try:
            ensure_port_free()
            port_free = True
        except Exception:
            port_free = False
        results = None
        if runner_output.is_file():
            try:
                results = json.loads(runner_output.read_text())
            except Exception as e:
                error = (error + "; " if error else "") + f"could not parse runner result: {e}"
        receipt = {"taskId": "Q161", "startedAtUtc": started, "finishedAtUtc": now(), "status": status,
                   "error": error, "stopReason": STOP_REASON[0] if STOP_REASON else None,
                   "preflight": preflight, "runnerExitCode": runner_exit, "resultFile": str(runner_output) if runner_output.exists() else None,
                   "result": None if results is None else {k: results.get(k) for k in ("benchmark", "seed", "model", "runs", "transportOk", "passed", "sandboxErrors", "noFinalContent")},
                   "screenGatePass": bool(results and results.get("runs") == 8 and results.get("transportOk") == 8 and results.get("sandboxErrors") == 0 and results.get("noFinalContent") == 0 and results.get("passed", 0) >= 4),
                   "cleanup": cleanup, "port18383FreeAfterCleanup": port_free,
                   "logs": {"server": str(server_log_path), "runner": str(runner_log_path), "resourceSamples": str(monitor_path)}}
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        print(f"Q161 status={status}; receipt={receipt_path}; portFree={port_free}", flush=True)
    return 0 if status == "screen_completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
