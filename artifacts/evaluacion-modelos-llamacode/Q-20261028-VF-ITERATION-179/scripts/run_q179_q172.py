#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import shutil
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ART = pathlib.Path(__file__).resolve().parents[1]
REPO = pathlib.Path(__file__).resolve().parents[4]
TOKEN = "2242863e-c78e-4fa9-9649-c1d1541f3919"
BIN = pathlib.Path("/tmp/q174-d/ninfer-build-short/apps/ninfer-serve")
MODEL = pathlib.Path("/media/cristian/HDD extra/Modelos-eval/Q-20261028-VF-ITERATION-178/reconverted-v3/text/qwen4exp.ninfer")
PART = pathlib.Path(str(MODEL) + ".part-0001")
NGRAM = pathlib.Path("/media/cristian/Disco local/Modelos-eval/Q-20261028-VF-ITERATION-178/reconverted-v3/ngram/qwen4exp-ngram.ninfer")
TOOL = pathlib.Path("/home/cristian/.cache/codex-tool-eval-bench-v2.8.0/.venv/bin/tool-eval-bench")
HOST, PORT = "127.0.0.1", 18480
MODEL_ID = "q179-flashnext-ninfer-all-dual"
MAX_CONTEXT = 262144
MIN_AVAILABLE_KIB = 32 * 1024 * 1024
STARTUP_TIMEOUT_S = 1200
RUNTIME_SHA = "09145c529015ac7d27ce63214138625927c70c1e89e4291594d74be59bd5f895"
TOOL_SHA = "31e3c8f5fa9140738cde4e1cecc909f5335cf928a90fbdd062ec7935e0526472"
EXPECTED = [
    (MODEL, "c599a10d696118a8235c953dda3fb45ef55b8c40356f4c688787cef116b8053d"),
    (PART, "fa72b1f0f2d57615500a6c3568a8e8583cf1b403b2be617fa67e864c890314a2"),
    (NGRAM, "2a3c7868c550171376785ff393ceff26d5b43ed7c9d2c341838582ff1f625656"),
]
RUNS, LOGS, RECEIPTS = ART / "runs", ART / "logs", ART / "receipts"
RESULT = RUNS / "q172-seed42.json"
REPORTS = RUNS / "q172-reports"
SERVER_LOG = LOGS / "ninfer-all-q172-server.log"
TOOL_LOG = LOGS / "q172-tool-eval.log"
PRE = RECEIPTS / "q179-preflight.json"
LAUNCH = RECEIPTS / "q179-launch.json"
POST = RECEIPTS / "q179-postflight.json"
SERVER_NAMES = {"llama-server", "ninfer-serve", "dsx-server", "vllm",
                "aphrodite-engine", "strata", "ollama"}
SERVER_MARKERS = re.compile(r"llama-server|ninfer-serve|dsx-server|vllm|aphrodite-engine|strata|ollama", re.I)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def atomic_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def check_lock() -> None:
    lock = json.loads((REPO / "WORK_QUEUE.lock").read_text(encoding="utf-8"))
    if lock.get("token") != TOKEN or lock.get("task") != "Q146 resume justified VF-20261019-01 tests":
        raise RuntimeError("WORK_QUEUE.lock no pertenece a la cola propietaria; detener")


def mem_available_kib() -> int:
    return next(int(line.split()[1]) for line in pathlib.Path("/proc/meminfo").read_text().splitlines()
                if line.startswith("MemAvailable:"))


def read_resources() -> dict:
    gpu_run = subprocess.run(
        ["nvidia-smi", "--query-gpu=index,uuid,name,memory.used,memory.total,utilization.gpu",
         "--format=csv,noheader,nounits"], text=True, capture_output=True, timeout=15)
    if gpu_run.returncode:
        raise RuntimeError("nvidia-smi GPU query falló: " + gpu_run.stderr.strip())
    gpus, uuid_index = {}, {}
    for line in gpu_run.stdout.splitlines():
        idx, uuid, name, used, total, util = [part.strip() for part in line.split(",")]
        idx = int(idx)
        gpus[idx] = {"uuid": uuid, "name": name, "used_mib": int(used),
                     "total_mib": int(total), "util_percent": int(util)}
        uuid_index[uuid] = idx
    apps = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid,gpu_uuid,used_gpu_memory",
         "--format=csv,noheader,nounits"], text=True, capture_output=True, timeout=15)
    compute = {0: [], 1: []}
    if apps.returncode == 0:
        for line in apps.stdout.splitlines():
            cols = [part.strip() for part in line.split(",")]
            if len(cols) >= 2 and uuid_index.get(cols[1]) in compute:
                compute[uuid_index[cols[1]]].append(int(cols[0]))
    return {"timestamp_utc": now(), "mem_available_kib": mem_available_kib(),
            "memory_psi": pathlib.Path("/proc/pressure/memory").read_text().strip(),
            "gpus": gpus, "compute_pids_by_gpu": compute}


def process_servers(owned_pid: int | None = None) -> list[dict]:
    found = []
    for ent in pathlib.Path("/proc").iterdir():
        if not ent.name.isdigit() or int(ent.name) in {os.getpid(), owned_pid}:
            continue
        try:
            comm = (ent / "comm").read_text().strip().lower()
            args = ent.joinpath("cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            continue
        if comm in SERVER_NAMES or SERVER_MARKERS.search(args):
            found.append({"pid": int(ent.name), "comm": comm, "cmdline": args[:1200]})
    return found


def inference_containers() -> list[str]:
    if not shutil.which("docker"):
        return []
    run = subprocess.run(["docker", "ps", "--format", "{{.ID}} {{.Names}} {{.Image}} {{.Ports}}"],
                         text=True, capture_output=True, timeout=15)
    if run.returncode:
        raise RuntimeError("docker ps falló en el preflight: " + run.stderr.strip())
    return [line for line in run.stdout.splitlines() if SERVER_MARKERS.search(line)]


def port_free() -> bool:
    with socket.socket() as sock:
        return sock.connect_ex((HOST, PORT)) != 0


def listening_server_lines(owned_pid: int | None = None) -> list[str]:
    run = subprocess.run(["ss", "-ltnp"], text=True, capture_output=True, timeout=10)
    if run.returncode:
        raise RuntimeError("ss listener preflight falló: " + run.stderr.strip())
    result = []
    for line in run.stdout.splitlines()[1:]:
        if not SERVER_MARKERS.search(line):
            continue
        if owned_pid is not None and f"pid={owned_pid}," in line:
            continue
        result.append(line)
    return result


def ensure_no_foreign_server(owned_pid: int | None = None) -> None:
    check_lock()
    pids = process_servers(owned_pid)
    containers = inference_containers()
    listeners = listening_server_lines(owned_pid)
    if pids or containers or listeners:
        raise RuntimeError("se detectó un inference server ajeno; no se lo toca: " +
                           json.dumps({"processes": pids, "containers": containers,
                                       "listeners": listeners}, ensure_ascii=False))


def sha(path: pathlib.Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_pins() -> dict:
    actual_runtime, actual_tool = sha(BIN), sha(TOOL)
    if actual_runtime != RUNTIME_SHA or actual_tool != TOOL_SHA:
        raise RuntimeError("runtime o Tool-Eval SHA-256 cambió")
    files = []
    for path, expected in EXPECTED:
        actual = sha(path)
        if actual != expected:
            raise RuntimeError(f"SHA-256 inesperado para {path}: {actual}")
        st = path.stat()
        files.append({"path": str(path), "bytes": st.st_size, "inode": st.st_ino,
                      "mtime_epoch_s": int(st.st_mtime), "sha256": actual})
    return {"runtime": {"path": str(BIN), "sha256": actual_runtime,
                        "commit": "3d882fc116941d9233c40bf30f4d66dbaa3d24bd"},
            "tool_eval": {"path": str(TOOL), "sha256": actual_tool, "version": "2.8.0"},
            "model_artifacts": files}


def server_argv() -> list[str]:
    return [str(BIN), str(MODEL), "--model-id", MODEL_ID, "--host", HOST, "--port", str(PORT),
            "--no-webui", "--max-context", str(MAX_CONTEXT), "--max-concurrency", "1",
            "--devices", "0,1", "--kv-capacity", str(MAX_CONTEXT), "--kv-dtype", "int8",
            "--kv-resident", "32768", "--expert-residency", "device",
            "--ngram-table", str(NGRAM), "--ngram-residency", "disk", "--ngram-io", "buffered",
            "--no-prefix-reuse", "--spec", "none", "--ngram-draft-tokens", "0",
            "--default-max-tokens", "16384", "--temperature", "0.6", "--top-p", "0.95",
            "--top-k", "20", "--min-p", "0.0", "--presence-penalty", "0.0", "--seed", "42"]


def get_json(path: str) -> tuple[int, dict]:
    with urllib.request.urlopen(f"http://{HOST}:{PORT}{path}", timeout=20) as response:
        return response.status, json.loads(response.read())


def stop_owned(proc: subprocess.Popen | None) -> dict:
    if proc is None:
        return {"stopped": True, "pid": None}
    if proc.poll() is not None:
        return {"stopped": True, "pid": proc.pid, "returncode": proc.returncode}
    try:
        comm = pathlib.Path(f"/proc/{proc.pid}/comm").read_text().strip().lower()
        cmdline = pathlib.Path(f"/proc/{proc.pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
    except OSError:
        return {"stopped": proc.poll() is not None, "pid": proc.pid, "reason": "PID terminó"}
    if comm != "ninfer-serve" or str(MODEL) not in cmdline or f"--port {PORT}" not in cmdline:
        return {"stopped": False, "pid": proc.pid, "reason": "PID/cmdline no coincide; no se envió señal"}
    try:
        os.killpg(proc.pid, signal.SIGINT)
    except ProcessLookupError:
        pass
    try:
        code = proc.wait(timeout=35)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            code = proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            code = proc.wait(timeout=5)
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and not port_free():
        time.sleep(0.25)
    return {"stopped": proc.poll() is not None, "pid": proc.pid, "returncode": code,
            "port_free": port_free()}


def readiness(proc: subprocess.Popen, log: pathlib.Path) -> dict:
    started = time.monotonic()
    deadline = started + STARTUP_TIMEOUT_S
    last = None
    while time.monotonic() < deadline:
        check_lock()
        ensure_no_foreign_server(proc.pid)
        if proc.poll() is not None:
            raise RuntimeError(f"NInfer terminó antes de readiness, rc={proc.returncode}")
        state = read_resources()
        if state["mem_available_kib"] < MIN_AVAILABLE_KIB:
            raise RuntimeError("MemAvailable <32 GiB durante inicialización")
        for idx in (0, 1):
            if idx not in state["gpus"] or "3090" not in state["gpus"][idx]["name"]:
                raise RuntimeError(f"RTX 3090 GPU{idx} desapareció")
        try:
            health_code, health = get_json("/health")
            models_code, models = get_json("/v1/models")
            ids = [item.get("id") for item in models.get("data", [])]
            if health_code == 200 and health.get("status") == "ok" and models_code == 200 and MODEL_ID in ids:
                for idx in (0, 1):
                    if proc.pid not in state["compute_pids_by_gpu"].get(idx, []):
                        raise RuntimeError(f"server PID no aparece como compute en GPU{idx}")
                return {"status": "ready", "pid": proc.pid,
                        "ready_seconds": round(time.monotonic() - started, 3),
                        "health": health, "models_http": models_code, "model_ids": ids,
                        "resources_at_ready": state, "server_log": str(log.relative_to(ART))}
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as exc:
            last = str(exc)
        time.sleep(3)
    raise TimeoutError(f"NInfer no llegó a readiness en {STARTUP_TIMEOUT_S}s; último error={last}")


def kill_group(proc: subprocess.Popen | None, sig: int, timeout: int = 20) -> None:
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, sig)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        pass


def main() -> None:
    RUNS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    RECEIPTS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    try:
        check_lock()
        ensure_no_foreign_server()
        if not port_free():
            raise RuntimeError(f"puerto {PORT} ocupado")
        if mem_available_kib() < MIN_AVAILABLE_KIB:
            raise RuntimeError("MemAvailable <32 GiB antes de iniciar")
        pins = verify_pins()
        baseline = read_resources()
        for idx in (0, 1):
            if idx not in baseline["gpus"] or "3090" not in baseline["gpus"][idx]["name"]:
                raise RuntimeError(f"RTX 3090 GPU{idx} no visible")
    except Exception as exc:
        atomic_json(PRE, {"task": "Q179-A01 Flash-Next NInfer-all dual Q172",
                          "timestamp_utc": now(), "lock_token": TOKEN,
                          "decision": "BLOCKED", "error": f"{type(exc).__name__}: {exc}"})
        raise
    preflight = {"task": "Q179-A01 Flash-Next NInfer-all dual Q172",
                 "timestamp_utc": now(), "lock_token": TOKEN, "decision": "PASS",
                 "inference_servers": [], "port_free": True, "pins": pins,
                 "baseline_resources": baseline,
                 "profile": {"gpus": [0, 1], "max_context": MAX_CONTEXT,
                             "kv_resident_positions": 32768, "expert_residency": "device"}}
    atomic_json(PRE, preflight)

    server = None
    tool = None
    tool_log_stream = None
    server_log_stream = None
    status = "failed"
    error = None
    result = None
    low_mem_samples = 0
    samples = []
    launch = {"task": "Q179-A01 Flash-Next NInfer-all dual Q172",
              "timestamp_utc": now(), "lock_token": TOKEN, "status": "starting",
              "server_argv": server_argv(), "harness_argv": None}
    try:
        check_lock()
        ensure_no_foreign_server()
        if not port_free():
            raise RuntimeError(f"puerto {PORT} ocupado al lanzar")
        server_log_stream = SERVER_LOG.open("w", encoding="utf-8")
        server = subprocess.Popen(server_argv(), stdout=server_log_stream,
                                  stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
        launch["server_pid"] = server.pid
        atomic_json(LAUNCH, launch)
        ready = readiness(server, SERVER_LOG)
        launch.update(ready)
        launch["status"] = "ready"

        harness_argv = [
            str(TOOL), "run", "--model", MODEL_ID, "--backend", "ninfer",
            "--base-url", f"http://{HOST}:{PORT}/v1", "--format", "openai",
            "--temperature", "0.6", "--top-p", "0.95", "--top-k", "20", "--min-p", "0.0",
            "--repeat-penalty", "1.0", "--seed", "42",
            "--backend-kwargs", json.dumps({"reasoning_effort": "medium", "presence_penalty": 0.0}),
            "--variant-seed", "20261010", "--hardmode", "--scenarios",
            *[f"TC-{n}" for n in range(70, 98)], "--timeout", "120", "--max-turns", "8",
            "--trials", "1", "--parallel", "1", "--no-warmup", "--fail-on-safety",
            "--label", "Q179-FlashNext-NInferAll-Dual-Q172-seed42", "--redact-url",
            "--output-dir", str(REPORTS), "--json-file", str(RESULT)]
        launch["harness_argv"] = harness_argv
        launch["timestamp_harness_start_utc"] = now()
        launch["status"] = "harness_running"
        atomic_json(LAUNCH, launch)
        tool_log_stream = TOOL_LOG.open("w", encoding="utf-8")
        tool_env = {**os.environ, "CUDA_VISIBLE_DEVICES": ""}
        tool = subprocess.Popen(harness_argv, stdout=tool_log_stream, stderr=subprocess.STDOUT,
                                start_new_session=True, close_fds=True, env=tool_env)
        launch["tool_eval_pid"] = tool.pid
        while tool.poll() is None:
            time.sleep(15)
            check_lock()
            ensure_no_foreign_server(server.pid)
            state = read_resources()
            samples.append(state)
            low_mem_samples = low_mem_samples + 1 if state["mem_available_kib"] < MIN_AVAILABLE_KIB else 0
            if low_mem_samples >= 4:
                raise RuntimeError("MemAvailable <32 GiB en cuatro muestras consecutivas")
            if any(idx not in state["gpus"] or "3090" not in state["gpus"][idx]["name"] for idx in (0, 1)):
                raise RuntimeError("una de las RTX 3090 dejó de estar visible")
            if tool.poll() is None and server.poll() is not None:
                raise RuntimeError(f"NInfer terminó durante Tool-Eval, rc={server.returncode}")
        launch["tool_eval_exit_code"] = tool.returncode
        launch["timestamp_harness_end_utc"] = now()
        if RESULT.is_file():
            result = json.loads(RESULT.read_text(encoding="utf-8"))
        if (not result or result.get("status") != "completed" or
                int(result.get("total_scenarios", 0)) != 28):
            raise RuntimeError("Tool-Eval no completó exactamente los 28 escenarios: " +
                               json.dumps({"exit": tool.returncode,
                                           "result_status": (result or {}).get("status"),
                                           "total_scenarios": (result or {}).get("total_scenarios")}))
        status = "complete"
        launch["status"] = status
        launch["quality_summary"] = {
            "final_score": result.get("final_score"),
            "total_points": result.get("scores", {}).get("total_points"),
            "max_points": result.get("scores", {}).get("max_points"),
            "safety_warnings": result.get("safety_warnings", []),
            "safety_gate": result.get("safety_gate")}
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        launch["status"] = status
        launch["error"] = error
    finally:
        if tool and tool.poll() is None:
            kill_group(tool, signal.SIGINT, 20)
            if tool.poll() is None:
                kill_group(tool, signal.SIGTERM, 10)
            if tool.poll() is None:
                kill_group(tool, signal.SIGKILL, 5)
        server_cleanup = stop_owned(server)
        if tool_log_stream:
            tool_log_stream.flush()
            tool_log_stream.close()
        if server_log_stream:
            server_log_stream.flush()
            server_log_stream.close()
        launch["server_cleanup"] = server_cleanup
        launch["status"] = status
        if error:
            launch["error"] = error
        atomic_json(LAUNCH, launch)
        try:
            ensure_no_foreign_server()
            remaining = []
        except Exception as exc:
            remaining = [{"error": str(exc)}]
        try:
            post_resources = read_resources()
        except Exception as exc:
            post_resources = {"error": str(exc)}
        postflight = {"task": "Q179-A01 Flash-Next NInfer-all dual Q172",
                      "timestamp_utc": now(), "lock_token": TOKEN, "status": status,
                      "error": error, "tool_eval_exit_code": tool.returncode if tool else None,
                      "result_exists": RESULT.is_file(),
                      "result_status": result.get("status") if result else None,
                      "quality_summary": launch.get("quality_summary"),
                      "samples": samples, "remaining_inference_servers": remaining,
                      "port_free": port_free(), "post_resources": post_resources,
                      "server_cleanup": server_cleanup, "gui_preserved": True}
        postflight["decision"] = "PASS" if postflight["port_free"] and not remaining and server_cleanup.get("stopped") else "CHECK"
        atomic_json(POST, postflight)
    print(json.dumps({"status": status, "error": error,
                      "result": str(RESULT), "postflight": str(POST)}, ensure_ascii=False))
    if status != "complete" or error:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
