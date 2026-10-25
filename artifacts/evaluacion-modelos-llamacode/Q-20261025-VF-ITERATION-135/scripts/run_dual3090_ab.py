#!/usr/bin/env python3
"""Run the preregistered Q135 paired Qwen3.8 blend A/B on both RTX 3090s."""
from __future__ import annotations

import datetime as dt
import argparse
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

REPO = pathlib.Path(__file__).resolve().parents[4]
ROOT = pathlib.Path(__file__).resolve().parents[1]
ATTEMPT_ROOT = ROOT / "attempts" / "unset"
LOCK = REPO / "WORK_QUEUE.lock"
TOKEN = "q135-sheet-items-59-64-473b366bf0734c94adc5ec2a39e6eb68"
SERVER = pathlib.Path("/home/cristian/.cache/llamacode/embeddinggemma2-eval/runtime/llama-b11554/llama-server")
SERVER_SHA = "fe8a7d6073d3e3a276193fcaec162cbf280d2572ad2016c9100fd924be19c6ed"
EVAL = pathlib.Path("/home/cristian/.cache/codex-tool-eval-bench-v2.8.0/.venv/bin/tool-eval-bench")
EVAL_ROOT = pathlib.Path("/home/cristian/.cache/codex-tool-eval-bench-v2.8.0")
TEMPLATE = REPO / "assets/chat-templates/qwen38-tools-fixed.jinja"
TEMPLATE_SHA = "03c3e852d2c349ce306ed9ecd870c83487bf123918843387b179ead1fcce93af"
MODEL = {
    "control": {
        "path": pathlib.Path("/media/cristian/Disco local/Models/llamacpp/Qwen3.8-27B-GGUF-Q4_K_M/Qwen3.8-27B-Q4_K_M.gguf"),
        "size": 18_973_870_528,
        "sha": "c600de0300ae8a0eb3a6c0b8b5561b8b96f16bd2c863c2a66c42de29d391a747",
        "alias": "qwen38-control-q4km",
    },
    "blend": {
        "path": pathlib.Path("/media/cristian/Disco local/Modelos-eval/Q135-jetbrains-blend/Qwen3.8-3.6-27B-blend-Q4_K_M.gguf"),
        "size": 16_810_715_104,
        "sha": "5f54ded85a78f11ad7a1c02d17564a268238ac8afe9b3d94fb0b614e473006a1",
        "alias": "jetbrains-qwen38-36-blend-q4km",
    },
}
PORT = 18104
BASE_URL = f"http://127.0.0.1:{PORT}/v1"
HEALTH_URL = f"http://127.0.0.1:{PORT}/health"
SEQUENCE = ((42, "control"), (42, "blend"), (43, "blend"), (43, "control"), (44, "control"), (44, "blend"))
KNOWN_SERVER = re.compile(r"(?:llama-server|vllm|sglang|aphrodite|strata[-_ ]?engine|openjet|mk_server|ollama|mlx_lm\.server|tabbyapi)", re.I)
MIN_FREE_DISK = 25 * 1024**3
MIN_MEM = 2 * 1024**3
MAX_TEMP = 85
SAMPLE_SECONDS = 10


def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path: pathlib.Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def lock_ok() -> None:
    if not LOCK.is_file() or json.loads(LOCK.read_text()).get("token") != TOKEN:
        raise RuntimeError("WORK_QUEUE.lock dejó de pertenecer a Q135")


def server_processes() -> list[dict[str, object]]:
    out = []
    for p in pathlib.Path("/proc").iterdir():
        if not p.name.isdigit() or int(p.name) == os.getpid():
            continue
        try:
            comm = (p / "comm").read_text().strip()
            cmd = (p / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
        except (OSError, ProcessLookupError):
            continue
        if KNOWN_SERVER.search(comm) or KNOWN_SERVER.search(cmd):
            out.append({"pid": int(p.name), "comm": comm, "cmdline": cmd[:500]})
    return out


def gpu_rows() -> list[dict[str, int | str]]:
    q = "index,name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu"
    p = subprocess.run(["nvidia-smi", "--query-gpu=" + q, "--format=csv,noheader,nounits"],
                       capture_output=True, text=True, timeout=15, check=True)
    rows = []
    for line in p.stdout.splitlines():
        fields = [x.strip() for x in line.split(",")]
        if len(fields) != 7:
            raise RuntimeError("no se pudo interpretar nvidia-smi: " + line)
        rows.append({"index": int(fields[0]), "name": fields[1], "total_mib": int(fields[2]),
                     "used_mib": int(fields[3]), "free_mib": int(fields[4]),
                     "temperature_c": int(fields[5]), "utilization_percent": int(fields[6])})
    if len(rows) < 2 or any("3090" not in str(x["name"]) for x in rows[:2]):
        raise RuntimeError("no se detectan las dos RTX 3090 esperadas")
    return rows[:2]


def gpu_process_rows() -> list[dict[str, int | str]]:
    devices = subprocess.run(["nvidia-smi", "--query-gpu=index,uuid", "--format=csv,noheader"],
                             capture_output=True, text=True, timeout=15, check=True)
    uuid_to_index = {}
    for line in devices.stdout.splitlines():
        index, uuid = [x.strip() for x in line.split(",", 1)]
        uuid_to_index[uuid] = int(index)
    p = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,gpu_uuid,used_memory", "--format=csv,noheader"],
                       capture_output=True, text=True, timeout=15, check=True)
    rows = []
    for line in p.stdout.splitlines():
        fields = [x.strip() for x in line.split(",")]
        if len(fields) != 3:
            continue
        try:
            rows.append({"pid": int(fields[0]), "gpu_index": uuid_to_index[fields[1]],
                         "gpu_uuid": fields[1], "used_mib": int(fields[2].split()[0])})
        except (ValueError, KeyError):
            continue
    return rows


def mem_info() -> dict[str, int]:
    out = {}
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        key, _, value = line.partition(":")
        if key in {"MemAvailable", "SwapFree"}:
            out[key] = int(value.split()[0]) * 1024
    return out


def psi_memory() -> dict[str, float]:
    out = {}
    for line in pathlib.Path("/proc/pressure/memory").read_text().splitlines():
        parts = line.split()
        vals = dict(x.split("=") for x in parts[1:])
        out[parts[0]] = float(vals["avg10"])
    return out


def oom_kills() -> int:
    for line in pathlib.Path("/proc/vmstat").read_text().splitlines():
        if line.startswith("oom_kill "):
            return int(line.split()[1])
    return 0


def listener_free() -> None:
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", PORT))
        except OSError as exc:
            raise RuntimeError(f"puerto {PORT} ocupado: {exc}") from exc


def host_sample(server_pid: int | None) -> dict[str, object]:
    mem = mem_info()
    gpus = gpu_rows()
    return {"at_utc": utc(), "server_pid": server_pid, "mem_available_bytes": mem["MemAvailable"],
            "swap_free_bytes": mem["SwapFree"], "memory_psi_avg10": psi_memory(),
            "host_oom_kill_count": oom_kills(), "gpus": gpus}


def guard(sample: dict[str, object], server_pid: int) -> None:
    if any(int(g["temperature_c"]) >= MAX_TEMP for g in sample["gpus"]):
        raise RuntimeError("alguna RTX 3090 alcanzó 85 C; abort gate")
    if int(sample["host_oom_kill_count"]) > INITIAL_OOM_KILLS:
        raise RuntimeError("el contador global de OOM kill aumentó")
    if server_pid and not pathlib.Path(f"/proc/{server_pid}").exists():
        raise RuntimeError("el llama-server de esta celda terminó inesperadamente")


def check_artifacts() -> dict[str, object]:
    lock_ok()
    if sha256(SERVER) != SERVER_SHA or sha256(TEMPLATE) != TEMPLATE_SHA:
        raise RuntimeError("hash de runtime o plantilla distinto al preregistro")
    device_env = dict(os.environ)
    device_env["CUDA_VISIBLE_DEVICES"] = "0,1"
    devices = subprocess.run([str(SERVER), "--list-devices"], env=device_env, capture_output=True,
                             text=True, timeout=30, check=True).stdout.strip()
    if "CUDA0: NVIDIA GeForce RTX 3090" not in devices or "CUDA1: NVIDIA GeForce RTX 3090" not in devices:
        raise RuntimeError("runtime no enumera ambas RTX 3090: " + devices)
    if not EVAL.is_file():
        raise RuntimeError("falta Tool-Eval Bench")
    p = subprocess.run([str(EVAL), "--version"], capture_output=True, text=True, check=True)
    if "2.8.0" not in p.stdout + p.stderr:
        raise RuntimeError("versión Tool-Eval Bench no es 2.8.0")
    if subprocess.run(["git", "-C", str(EVAL_ROOT), "rev-parse", "HEAD"], capture_output=True,
                      text=True, check=True).stdout.strip() != "0a1ba68c7709f429298bc92417a9e003f61de4e3":
        raise RuntimeError("commit Tool-Eval Bench cambió")
    artifact_rows = {}
    for key, spec in MODEL.items():
        path = spec["path"]
        if not path.is_file() or path.stat().st_size != spec["size"]:
            raise RuntimeError(f"{key}: archivo ausente o tamaño distinto al preregistro")
        actual = sha256(path)
        if actual != spec["sha"]:
            raise RuntimeError(f"{key}: SHA-256 no coincide con el pin")
        artifact_rows[key] = {"path": str(path), "size_bytes": path.stat().st_size,
                              "sha256": actual, "mtime_ns": path.stat().st_mtime_ns}
    free_disk = shutil.disk_usage(MODEL["blend"]["path"].parent).free
    if free_disk < MIN_FREE_DISK:
        raise RuntimeError(f"espacio destino bajo 25 GiB: {free_disk} bytes")
    return {"at_utc": utc(), "lock_token": TOKEN, "runtime_sha256": SERVER_SHA,
            "runtime_devices": devices, "template_sha256": TEMPLATE_SHA, "tool_eval_version": p.stdout.strip(),
            "tool_eval_commit": "0a1ba68c7709f429298bc92417a9e003f61de4e3",
            "artifacts": artifact_rows, "destination_free_bytes": free_disk}


def start_server(model_key: str, run_id: str) -> tuple[subprocess.Popen[bytes], pathlib.Path, list[dict[str, int | str]]]:
    lock_ok()
    others = server_processes()
    if others:
        raise RuntimeError("servidor de inferencia externo activo: " + json.dumps(others, ensure_ascii=False))
    listener_free()
    pre_gpus = gpu_rows()
    if any(int(g["temperature_c"]) >= MAX_TEMP for g in pre_gpus):
        raise RuntimeError("temperatura previa >=85 C")
    before_mem = mem_info()
    spec = MODEL[model_key]
    cell_dir = ATTEMPT_ROOT / "runs" / run_id
    log_path = ATTEMPT_ROOT / "logs" / f"{run_id}-llama-server.log"
    cell_dir.mkdir(parents=True, exist_ok=False)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    args = [str(SERVER), "--model", str(spec["path"]), "--alias", str(spec["alias"]),
            "--host", "127.0.0.1", "--port", str(PORT), "--n-gpu-layers", "999",
            "--split-mode", "layer", "--tensor-split", "1,1", "--ctx-size", "32768",
            "--batch-size", "512", "--ubatch-size", "512", "--threads", "8",
            "--cache-type-k", "q4_0", "--cache-type-v", "q4_0", "--flash-attn", "on",
            "--jinja", "--chat-template-file", str(TEMPLATE), "--reasoning-effort", "medium",
            "--reasoning-budget", "4096", "--n-predict", "4096", "--spec-type", "none"]
    env = dict(os.environ)
    env["CUDA_VISIBLE_DEVICES"] = "0,1"
    proc: subprocess.Popen[bytes] | None = None
    try:
        with log_path.open("wb") as log:
            proc = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, env=env,
                                    start_new_session=True, cwd=str(cell_dir))
        write_json(cell_dir / "server-invocation.json", {"at_utc": utc(), "pid": proc.pid,
                    "args": args, "cuda_visible_devices": "0,1", "mem_available_before_bytes": before_mem["MemAvailable"],
                    "gpu_before": pre_gpus, "artifact": spec, "server_log": str(log_path)})
        started = time.monotonic()
        stable_low_samples = 0
        last_sample = 0.0
        while time.monotonic() - started < 1800:
            if proc.poll() is not None:
                raise RuntimeError(f"server exited before READY rc={proc.returncode}; log={log_path}")
            now = time.monotonic()
            if now - last_sample >= SAMPLE_SECONDS:
                sample = host_sample(proc.pid)
                write_jsonl(cell_dir / "telemetry.jsonl", sample)
                guard(sample, proc.pid)
                stable_low_samples = stable_low_samples + 1 if int(sample["mem_available_bytes"]) < MIN_MEM else 0
                if stable_low_samples >= 2:
                    raise RuntimeError("MemAvailable <2 GiB for two consecutive samples")
                last_sample = now
            try:
                with urllib.request.urlopen(HEALTH_URL, timeout=3) as response:
                    if response.status == 200:
                        post_gpus = gpu_rows()
                        deltas = [int(post_gpus[i]["used_mib"]) - int(pre_gpus[i]["used_mib"]) for i in range(2)]
                        if any(delta < 1024 for delta in deltas):
                            raise RuntimeError(f"el modelo no asignó >=1 GiB a ambas GPU; delta MiB={deltas}")
                        compute_rows = [x for x in gpu_process_rows() if int(x["pid"]) == proc.pid]
                        devices_used = sorted({int(x["gpu_index"]) for x in compute_rows})
                        if devices_used != [0, 1] or any(int(x["used_mib"]) < 1024 for x in compute_rows):
                            raise RuntimeError(f"nvidia-smi no confirma asignaciones del server en GPU0 y GPU1: {compute_rows}")
                        with urllib.request.urlopen(BASE_URL + "/models", timeout=5) as model_resp:
                            model_info = json.loads(model_resp.read())
                        write_json(cell_dir / "server-ready.json", {"at_utc": utc(), "pid": proc.pid,
                                    "health_status": response.status, "gpu_after_load": post_gpus,
                                    "gpu_used_delta_mib": deltas, "server_gpu_compute_rows": compute_rows,
                                    "models_endpoint": model_info})
                        return proc, log_path, post_gpus
            except (urllib.error.URLError, TimeoutError, OSError):
                pass
            time.sleep(2)
        raise RuntimeError("server did not become healthy within 30 minutes")
    except BaseException as exc:
        if proc is not None:
            pid = proc.pid
            stop_owned(proc)
            write_json(cell_dir / "server-cleanup.json", {"at_utc": utc(), "pid": pid,
                        "return_code": proc.poll(), "stopped": proc.poll() is not None,
                        "failure": f"{type(exc).__name__}: {exc}"})
        raise


def write_jsonl(path: pathlib.Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def run_cell(model_key: str, seed: int) -> None:
    run_id = f"seed-{seed}-{model_key}"
    cell_dir = ATTEMPT_ROOT / "runs" / run_id
    proc: subprocess.Popen[bytes] | None = None
    eval_proc: subprocess.Popen[bytes] | None = None
    failure: str | None = None
    started = utc()
    try:
        proc, server_log, _ = start_server(model_key, run_id)
        env = dict(os.environ)
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            env.pop(key, None)
        env["NO_PROXY"] = "127.0.0.1,localhost"
        out_json = cell_dir / "result.json"
        report_dir = cell_dir / "reports"
        cmd = [str(EVAL), "run", "--hardmode-only", "--base-url", BASE_URL,
               "--model", str(MODEL[model_key]["alias"]), "--backend", "llamacpp",
               "--temperature", "0.6", "--top-p", "0.95", "--top-k", "20", "--min-p", "0",
               "--repeat-penalty", "1", "--seed", str(seed), "--variant-seed", "20261010",
               "--timeout", "120", "--max-turns", "8", "--parallel", "1", "--context-size", "32768",
               "--backend-kwargs", '{"reasoning_effort":"medium"}', "--label", f"Q135-{model_key}-seed-{seed}",
               "--json-file", str(out_json), "--output-dir", str(report_dir), "--no-live"]
        log_path = ATTEMPT_ROOT / "logs" / f"{run_id}-tool-eval.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("wb") as log:
            eval_proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env,
                                         start_new_session=True, cwd=str(cell_dir))
            started_monotonic = time.monotonic()
            next_sample = 0.0
            low_samples = 0
            while eval_proc.poll() is None:
                lock_ok()
                now = time.monotonic()
                if now >= next_sample:
                    others = [p for p in server_processes() if int(p["pid"]) != proc.pid]
                    if others:
                        raise RuntimeError("apareció otro inference server durante la corrida: " + json.dumps(others, ensure_ascii=False))
                    sample = host_sample(proc.pid)
                    write_jsonl(cell_dir / "telemetry.jsonl", sample)
                    guard(sample, proc.pid)
                    low_samples = low_samples + 1 if int(sample["mem_available_bytes"]) < MIN_MEM else 0
                    if low_samples >= 2:
                        raise RuntimeError("MemAvailable <2 GiB for two consecutive samples")
                    next_sample = now + SAMPLE_SECONDS
                time.sleep(2)
            rc = int(eval_proc.returncode or 0)
        result = None
        if out_json.is_file():
            result = json.loads(out_json.read_text(encoding="utf-8"))
        cell = {"id": run_id, "seed": seed, "model": model_key, "started_at_utc": started,
                "finished_at_utc": utc(), "duration_seconds": round(time.monotonic() - started_monotonic, 3),
                "exit_code": rc, "result_exists": out_json.is_file(),
                "result_sha256": sha256(out_json) if out_json.is_file() else None,
                "result": result, "log": str(log_path), "server_log": str(server_log)}
        write_json(cell_dir / "cell-result.json", cell)
        write_json(ROOT / "receipts" / "cell-progress.json", {"updated_at_utc": utc(), "last_cell": cell})
        if rc != 0 or result is None:
            raise RuntimeError(f"Tool-Eval cell {run_id} incomplete (rc={rc}); no retry")
    except BaseException as exc:
        failure = f"{type(exc).__name__}: {exc}"
        write_json(ATTEMPT_ROOT / "run-failure.json", {"status": "aborted_no_retry", "at_utc": utc(),
                    "cell": run_id, "reason": failure})
        raise
    finally:
        if eval_proc is not None and eval_proc.poll() is None:
            stop_owned(eval_proc)
        if proc is not None:
            pid = proc.pid
            stop_owned(proc)
            write_json(cell_dir / "server-cleanup.json", {"at_utc": utc(), "pid": pid,
                        "return_code": proc.poll(), "stopped": proc.poll() is not None,
                        "failure": failure})
        if cell_dir.exists():
            for _ in range(10):
                try:
                    listener_free()
                    break
                except RuntimeError:
                    time.sleep(1)


def stop_owned(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=20)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass


def main() -> int:
    global ATTEMPT_ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", required=True, help="new isolated campaign directory, e.g. attempt-02")
    args = parser.parse_args()
    if not re.fullmatch(r"attempt-[0-9]{2}", args.attempt):
        raise RuntimeError("attempt must match attempt-NN")
    ATTEMPT_ROOT = ROOT / "attempts" / args.attempt
    if ATTEMPT_ROOT.exists():
        raise RuntimeError(f"{ATTEMPT_ROOT} already exists; refusing to overwrite")
    ATTEMPT_ROOT.mkdir(parents=True, exist_ok=False)
    (ATTEMPT_ROOT / "runs").mkdir()
    (ATTEMPT_ROOT / "logs").mkdir()
    (ROOT / "receipts").mkdir(exist_ok=True)
    global INITIAL_OOM_KILLS
    INITIAL_OOM_KILLS = oom_kills()
    preflight = check_artifacts()
    preflight["gpu_before_campaign"] = gpu_rows()
    preflight["host_memory_before_campaign"] = mem_info()
    preflight["inference_servers_before_campaign"] = server_processes()
    preflight["port"] = PORT
    preflight["stop_policy"] = {"no_memory_caps": True, "memavailable_abort_bytes": MIN_MEM,
                                "consecutive_samples": 2, "max_gpu_temp_c": MAX_TEMP,
                                "oom_counter_increase": "abort", "no_automatic_retry": True}
    preflight["attempt"] = args.attempt
    write_json(ROOT / "receipts" / f"{args.attempt}-campaign-preflight.json", preflight)
    schedule = [{"seed": s, "model": m, "sequence_index": i + 1} for i, (s, m) in enumerate(SEQUENCE)]
    write_json(ROOT / "receipts" / f"{args.attempt}-campaign-schedule.json", {"created_at_utc": utc(), "attempt": args.attempt, "cells": schedule})
    completed = []
    for index, cell in enumerate(SEQUENCE, 1):
        print(f"CELL {index}/6 START seed={cell[0]} model={cell[1]} at={utc()}", flush=True)
        run_cell(cell[1], cell[0])
        completed.append({"sequence_index": index, "seed": cell[0], "model": cell[1], "status": "complete"})
        write_json(ROOT / "receipts" / f"{args.attempt}-campaign-progress.json", {"updated_at_utc": utc(), "completed": completed})
        print(f"CELL {index}/6 COMPLETE at={utc()}", flush=True)
    write_json(ROOT / "receipts" / f"{args.attempt}-benchmark-final.json", {"status": "six_cells_completed_pending_audit",
                "attempt": args.attempt,
                "closed_at_utc": utc(), "cells": completed,
                "decision": "await paired score, critical-safety, token and E2E gates; no production adoption"})
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BaseException as exc:
        if isinstance(exc, SystemExit):
            raise
        print(f"Q135 ABORT {utc()} {type(exc).__name__}: {exc}", flush=True)
        raise SystemExit(2)
