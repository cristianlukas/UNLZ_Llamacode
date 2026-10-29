#!/usr/bin/env python3
"""Q178: measured dual-GPU NInfer-all startup and Flash-Next context ladder."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import signal
import socket
import statistics
import subprocess
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ART = pathlib.Path(__file__).resolve().parents[1]
REPO = pathlib.Path(__file__).resolve().parents[4]
TOKEN = "2242863e-c78e-4fa9-9649-c1d1541f3919"
BIN = pathlib.Path("/tmp/q174-d/ninfer-build-short/apps/ninfer-serve")
MODEL = pathlib.Path("/media/cristian/HDD extra/Modelos-eval/Q-20261027-VF-ITERATION-171/artifact/qwen4exp.ninfer")
PART = pathlib.Path(str(MODEL) + ".part-0001")
NGRAM = pathlib.Path("/media/cristian/Disco local/Modelos-eval/Q39-NInfer-v0.16.1-FlashNext-IQ2XS/qwen4exp.ninfer.ngram")
PORT = 18478
HOST = "127.0.0.1"
MODEL_ID = "q178-qwen-flashnext-ninfer"
LEVELS = [(8192, 3), (32768, 1), (65536, 1), (131072, 1), (261888, 1)]
OUTPUT_TOKENS = 128
MIN_AVAILABLE_KIB = 32 * 1024 * 1024
RUNTIME_SHA = "09145c529015ac7d27ce63214138625927c70c1e89e4291594d74be59bd5f895"
MODEL_SHA = "6c3dd0a8a730566b3cda9b6c563a8a345d1986f930be409a0dca8bd2a9887584"
PART_SHA = "a089cb07a49c18b8eb942e89c4e3676f0b03adf0fdbd141dc8f5d4cf5418de1f"
NGRAM_SHA = "0478dd2f62a4d02b5cf3ab64d69229bd88dd95366498ad7c72828f95b99135b6"
RUNS = ART / "runs"
LOGS = ART / "logs"
OUT = RUNS / "context-ladder.json"
EVENTS = RUNS / "context-ladder-events.jsonl"
RESOURCES = LOGS / "resources.jsonl"
SAMPLING = {"temperature": 0.6, "top_p": 0.95, "top_k": 20,
            "min_p": 0.0, "repeat_penalty": 1.0,
            "presence_penalty": 0.0, "seed": 42}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def atomic_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def append_jsonl(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def check_lock() -> None:
    lock = json.loads((REPO / "WORK_QUEUE.lock").read_text(encoding="utf-8"))
    if lock.get("token") != TOKEN:
        raise RuntimeError("WORK_QUEUE.lock no pertenece al lote Q146; detenerse")


def read_resources() -> dict:
    mem_available = next(int(line.split()[1]) for line in pathlib.Path("/proc/meminfo").read_text().splitlines()
                         if line.startswith("MemAvailable:"))
    proc = subprocess.run(["nvidia-smi", "--query-gpu=index,uuid,memory.used,memory.total,utilization.gpu",
                           "--format=csv,noheader,nounits"], text=True, capture_output=True, timeout=10)
    if proc.returncode:
        raise RuntimeError("nvidia-smi query falló: " + proc.stderr.strip())
    gpus = {}
    uuid_to_index = {}
    for line in proc.stdout.splitlines():
        idx, uuid, used, total, util = [item.strip() for item in line.split(",")]
        gpus[int(idx)] = {"uuid": uuid, "used_mib": int(used), "total_mib": int(total),
                          "util_percent": int(util)}
        uuid_to_index[uuid] = int(idx)
    apps = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,gpu_uuid,used_gpu_memory",
                           "--format=csv,noheader,nounits"], text=True, capture_output=True, timeout=10)
    compute = {0: [], 1: []}
    if apps.returncode == 0:
        for line in apps.stdout.splitlines():
            bits = [part.strip() for part in line.split(",")]
            if len(bits) >= 2:
                idx = uuid_to_index.get(bits[1])
                if idx in compute:
                    compute[idx].append(int(bits[0]))
    return {"timestamp_utc": now(), "mem_available_kib": mem_available,
            "memory_psi": pathlib.Path("/proc/pressure/memory").read_text().strip(),
            "gpus": gpus, "compute_pids_by_gpu": compute}


def inference_processes() -> list[dict]:
    result = []
    for ent in pathlib.Path("/proc").iterdir():
        if not ent.name.isdigit() or int(ent.name) == os.getpid():
            continue
        try:
            comm = (ent / "comm").read_text().strip().lower()
            cmdline = (ent / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            continue
        if comm in {"llama-server", "ninfer-serve", "dsx-server", "vllm", "aphrodite-engine", "strata"}:
            result.append({"pid": int(ent.name), "comm": comm, "cmdline": cmdline[:900]})
    return result


def check_no_foreign_server(owned_pid: int | None = None) -> None:
    check_lock()
    found = inference_processes()
    foreign = [p for p in found if p["pid"] != owned_pid]
    if foreign:
        raise RuntimeError("Se detectó otra inferencia activa; detenerse: " + json.dumps(foreign))


def port_is_free() -> bool:
    with socket.socket() as sock:
        return sock.connect_ex((HOST, PORT)) != 0


def verify_pins() -> dict:
    expected = [(MODEL, MODEL_SHA, 32000000000), (PART, PART_SHA, 7225180928),
                (NGRAM, NGRAM_SHA, 29127258112)]
    runtime_hash = hashlib.file_digest(BIN.open("rb"), "sha256").hexdigest()
    if runtime_hash != RUNTIME_SHA:
        raise RuntimeError(f"NInfer-all binary SHA mismatch: {runtime_hash}")
    verified = [{"path": str(BIN), "bytes": BIN.stat().st_size, "mtime_ns": BIN.stat().st_mtime_ns,
                 "sha256": runtime_hash, "validation": "SHA-256 recomputed"}]
    prior = json.loads((REPO / "artifacts/evaluacion-modelos-llamacode/Q-20261027-VF-ITERATION-171/receipts/ninfer-artifact-validation.json").read_text(encoding="utf-8"))
    for path, sha, expected_size in expected:
        if not path.is_file():
            raise RuntimeError(f"falta artefacto fijado: {path}")
        stat = path.stat()
        if expected_size is not None and stat.st_size != expected_size:
            raise RuntimeError(f"tamaño distinto para {path}: {stat.st_size}")
        old = prior["sha256"].get(str(path))
        if not old or old.get("sha256") != sha or old.get("bytes") != stat.st_size:
            raise RuntimeError(f"receipt SHA/size mismatch para {path}")
        verified.append({"path": str(path), "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns,
                         "sha256": sha, "validation": "size+mtime read-only; exact SHA inherited from Q171 receipt"})
    if not port_is_free():
        raise RuntimeError(f"puerto {PORT} ocupado antes del test")
    check_no_foreign_server()
    return {"timestamp_utc": now(), "files": verified,
            "runtime_version": "untagged+3d882fc", "runtime_commit": "3d882fc116941d9233c40bf30f4d66dbaa3d24bd",
            "port_free": True, "inference_servers": inference_processes(), "resources": read_resources()}


def server_command() -> list[str]:
    return [str(BIN), str(MODEL), "--model-id", MODEL_ID,
            "--host", HOST, "--port", str(PORT), "--no-webui",
            "--max-context", "262144", "--max-concurrency", "1",
            "--devices", "0,1", "--kv-capacity", "262144", "--kv-dtype", "int8",
            "--expert-residency", "disk", "--expert-cache-mib", "auto",
            "--ngram-table", str(NGRAM), "--ngram-residency", "disk", "--ngram-io", "buffered",
            "--no-prefix-reuse", "--spec", "none", "--ngram-draft-tokens", "0",
            "--default-max-tokens", str(OUTPUT_TOKENS), "--temperature", "0.6",
            "--top-p", "0.95", "--top-k", "20", "--min-p", "0.0",
            "--presence-penalty", "0.0", "--seed", "42"]


def get_health() -> tuple[int, dict]:
    with urllib.request.urlopen(f"http://{HOST}:{PORT}/health", timeout=10) as response:
        return response.status, json.loads(response.read())


def post(path: str, body: dict, timeout: int = 180) -> tuple[int, dict]:
    data = json.dumps(body, separators=(",", ":")).encode()
    request = urllib.request.Request(f"http://{HOST}:{PORT}{path}", data=data,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, json.loads(response.read())


def check_dual(proc: subprocess.Popen, baseline: dict) -> dict:
    check_no_foreign_server(proc.pid)
    state = read_resources()
    if state["mem_available_kib"] < MIN_AVAILABLE_KIB:
        raise RuntimeError("MemAvailable ya está por debajo del piso de 32 GiB")
    if proc.pid not in state["compute_pids_by_gpu"].get(0, []) or proc.pid not in state["compute_pids_by_gpu"].get(1, []):
        raise RuntimeError("el mismo proceso no figura como compute en las dos GPU: " + json.dumps(state["compute_pids_by_gpu"]))
    for index in (0, 1):
        if state["gpus"][index]["used_mib"] <= baseline["gpus"][index]["used_mib"] + 1024:
            raise RuntimeError(f"la GPU{index} no muestra al menos 1 GiB adicional sobre baseline")
    return state


def sample_text(start: int, count: int = 1024) -> str:
    regions = ["north ridge", "river basin", "coastal plain", "western plateau", "central valley"]
    materials = ["copper", "basalt", "silica", "timber", "granite", "aluminum", "clay"]
    actions = ["measured", "compared", "recorded", "reviewed", "estimated", "classified", "verified"]
    return "".join(
        f"Record {i:07d}: the {regions[i % 5]} team {actions[(i // 3) % 7]} "
        f"{materials[(i // 7) % 7]} sample {i % 997} at {12 + i % 89} units. "
        f"The note cites station {i % 113}, batch {i % 431}, and observation {i % 2027}.\n"
        for i in range(start, start + count)
    )


def tokenize_fixture(target: int) -> list[int]:
    ids: list[int] = []
    start = 0
    while len(ids) < target:
        _, response = post("/tokenize", {"content": sample_text(start), "add_special": False,
                                            "parse_special": False, "with_pieces": False}, timeout=240)
        chunk = response.get("tokens")
        if not isinstance(chunk, list) or not chunk:
            raise RuntimeError("/tokenize devolvió una lista vacía/no válida")
        ids.extend(int(item) for item in chunk)
        start += 1024
    return ids[:target]


def stop_server(proc: subprocess.Popen) -> dict:
    if proc.poll() is not None:
        return {"pid": proc.pid, "already_exited": True, "returncode": proc.returncode}
    found = {p["pid"]: p for p in inference_processes()}
    exact = found.get(proc.pid)
    if not exact or str(MODEL) not in exact["cmdline"] or f"--port {PORT}" not in exact["cmdline"]:
        return {"pid": proc.pid, "stopped": False, "reason": "PID/cmdline mismatch; process left untouched"}
    proc.send_signal(signal.SIGINT)
    try:
        code = proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.send_signal(signal.SIGTERM)
        try:
            code = proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            return {"pid": proc.pid, "stopped": False, "reason": "owned server ignored SIGINT and SIGTERM"}
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and not port_is_free():
        time.sleep(0.25)
    return {"pid": proc.pid, "stopped": proc.poll() is not None, "returncode": code,
            "port_free": port_is_free()}


def start_server(label: str, baseline: dict, result: dict,
                 active_ref: list[subprocess.Popen | None], monitor_abort: threading.Event) -> tuple[subprocess.Popen, dict]:
    check_no_foreign_server()
    if not port_is_free():
        raise RuntimeError("puerto ocupado antes de iniciar el proceso propio")
    log_path = LOGS / f"server-{label}.log"
    log_stream = log_path.open("w", encoding="utf-8")
    started = time.monotonic()
    proc = subprocess.Popen(server_command(), stdout=log_stream, stderr=subprocess.STDOUT,
                            start_new_session=True, close_fds=True)
    active_ref[0] = proc
    entry = {"label": label, "pid": proc.pid, "started_utc": now(), "argv": server_command(),
             "log": str(log_path.relative_to(ART)), "ready_seconds": None}
    result["initialization_runs"].append(entry)
    atomic_json(OUT, result)
    deadline = time.monotonic() + 1200
    last_error = None
    try:
        while time.monotonic() < deadline:
            check_lock()
            if monitor_abort.is_set():
                raise RuntimeError("resource monitor aborted server startup")
            if proc.poll() is not None:
                raise RuntimeError(f"server {label} terminó antes de readiness, exit={proc.returncode}")
            state = read_resources()
            append_jsonl(RESOURCES, {"phase": label, **state})
            if state["mem_available_kib"] < MIN_AVAILABLE_KIB:
                raise RuntimeError(f"MemAvailable debajo de 32 GiB al iniciar {label}")
            try:
                status, health = get_health()
                if status == 200 and health.get("status") == "ok":
                    dual = check_dual(proc, baseline)
                    entry.update({"ready_utc": now(), "ready_seconds": round(time.monotonic() - started, 3),
                                  "health": health, "resources_at_ready": dual, "status": "ready"})
                    atomic_json(OUT, result)
                    return proc, entry
            except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as exc:
                last_error = str(exc)
            time.sleep(1)
        raise TimeoutError(f"server {label} no llegó a /health en 1200 s; último error={last_error}")
    except Exception as exc:
        entry.update({"status": "failed_before_ready", "error": f"{type(exc).__name__}: {exc}",
                      "cleanup": stop_server(proc)})
        active_ref[0] = None
        atomic_json(OUT, result)
        raise
    finally:
        log_stream.flush()
        log_stream.close()


def monitor_resources(stop: threading.Event, abort: threading.Event,
                      active: list[subprocess.Popen | None]) -> None:
    consecutive_low = 0
    while not stop.wait(15):
        try:
            state = read_resources()
            append_jsonl(RESOURCES, {"phase": "monitor", **state})
            consecutive_low = consecutive_low + 1 if state["mem_available_kib"] < MIN_AVAILABLE_KIB else 0
            if consecutive_low >= 4:
                abort.set()
                server = active[0]
                if server is not None and server.poll() is None:
                    server.send_signal(signal.SIGINT)
                append_jsonl(RESOURCES, {"timestamp_utc": now(),
                    "stop_guard": "MemAvailable <32 GiB for four consecutive 15-second samples"})
                return
        except Exception as exc:
            append_jsonl(RESOURCES, {"timestamp_utc": now(), "monitor_error": f"{type(exc).__name__}: {exc}"})


def main() -> None:
    RUNS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    check_lock()
    baseline = verify_pins()
    atomic_json(ART / "receipts/preflight.json", baseline)
    initial_gpu = baseline["resources"]["gpus"]
    result = {"task_id": "Q178-Qwen-FlashNext-NInfer-all-dual3090-context", "started_utc": now(),
              "runtime_commit": "3d882fc116941d9233c40bf30f4d66dbaa3d24bd",
              "runtime_sha256": RUNTIME_SHA, "model_sha256": MODEL_SHA, "part_sha256": PART_SHA,
              "ngram_sha256": NGRAM_SHA, "model": "Qwen3.8 Flash-Next RCO IQ2_XS NInfer artifact qwen4exp",
              "gpu_topology": "GPU0+GPU1 pipeline; one stage per RTX 3090; not tensor-parallel",
              "baseline": baseline, "max_context": 262144, "context_levels": LEVELS,
              "output_tokens": OUTPUT_TOKENS, "sampling": SAMPLING,
              "initialization_runs": [], "smoke": None, "samples": [], "status": "running"}
    atomic_json(OUT, result)
    active: subprocess.Popen | None = None
    active_ref: list[subprocess.Popen | None] = [None]
    monitor_stop = threading.Event()
    monitor_abort = threading.Event()
    monitor = threading.Thread(target=monitor_resources, args=(monitor_stop, monitor_abort, active_ref), daemon=True)
    monitor.start()
    try:
        active, _ = start_server("cold-process", baseline["resources"], result, active_ref, monitor_abort)
        active_ref[0] = active
        if monitor_abort.is_set():
            raise RuntimeError("resource monitor aborted before cold cleanup")
        cleanup = stop_server(active)
        active_ref[0] = None
        result["initialization_runs"][-1]["cleanup"] = cleanup
        active = None
        if not cleanup.get("stopped") or not cleanup.get("port_free"):
            raise RuntimeError("el primer proceso no se limpió/port quedó ocupado")

        active, _ = start_server("hot-likely-clean-relaunch", baseline["resources"], result, active_ref, monitor_abort)
        active_ref[0] = active
        if monitor_abort.is_set():
            raise RuntimeError("resource monitor aborted before smoke")
        status, smoke = post("/completion", {"prompt": "Q178 smoke. Respondé con una frase breve.",
            "n_predict": 16, "cache_prompt": False, "stream": False, "ignore_eos": True,
            "return_tokens": True, **SAMPLING}, timeout=300)
        generated = int((smoke.get("timings") or {}).get("predicted_n", 0))
        result["smoke"] = {"http_status": status, "prompt": smoke.get("content"),
                           "predicted_n": generated,
                           "timings": smoke.get("timings"),
                           "valid": status == 200 and generated == 16,
                           "dual_gpu_resources": check_dual(active, baseline["resources"])}
        atomic_json(OUT, result)
        if not result["smoke"]["valid"]:
            raise RuntimeError("smoke no produjo exactamente 16 tokens")

        for target, reps in LEVELS:
            check_lock()
            if monitor_abort.is_set():
                raise RuntimeError("resource monitor aborted due low MemAvailable")
            dual_before = check_dual(active, baseline["resources"])
            tokens = tokenize_fixture(target)
            token_hash = hashlib.sha256(json.dumps(tokens, separators=(",", ":")).encode()).hexdigest()
            level = {"target_prompt_tokens": target, "bucket": "256K" if target == 261888 else f"{target//1024}K",
                     "repetitions_preregistered": reps, "token_count": len(tokens),
                     "token_ids_sha256": token_hash, "samples": []}
            result["samples"].append(level)
            atomic_json(OUT, result)
            for repetition in range(1, reps + 1):
                if monitor_abort.is_set():
                    raise RuntimeError("resource monitor aborted due low MemAvailable")
                if active.poll() is not None:
                    raise RuntimeError(f"inference server terminó, exit={active.returncode}")
                before = check_dual(active, baseline["resources"])
                started = time.monotonic()
                status, response = post("/completion", {"prompt": tokens, "n_predict": OUTPUT_TOKENS,
                    "cache_prompt": False, "stream": False, "ignore_eos": True,
                    "return_tokens": True, **SAMPLING}, timeout=2400)
                wall = time.monotonic() - started
                timings = response.get("timings") or {}
                prompt_n = int(timings.get("prompt_n", -1))
                cache_n = int(timings.get("cache_n", -1))
                generated_n = int(timings.get("predicted_n", 0))
                prompt_ms = float(timings.get("prompt_ms", 0))
                generated_ms = float(timings.get("predicted_ms", 0))
                valid = status == 200 and prompt_n == target and cache_n == 0 and generated_n == OUTPUT_TOKENS and prompt_ms > 0 and generated_ms > 0
                sample = {"timestamp_utc": now(), "repetition": repetition, "http_status": status,
                    "prompt_n": prompt_n, "cache_n": cache_n, "prompt_ms": prompt_ms,
                    "predicted_n": generated_n, "predicted_ms": generated_ms,
                    "prefill_tok_s": prompt_n / (prompt_ms / 1000) if prompt_ms > 0 else None,
                    "decode_tok_s_n_over_ms": generated_n / (generated_ms / 1000) if generated_ms > 0 else None,
                    "decode_tok_s_nminus1_over_ms": max(generated_n - 1, 0) / (generated_ms / 1000) if generated_ms > 0 else None,
                    "client_wall_s": wall, "response_token_ids": len(response.get("tokens", [])),
                    "text_sha256": hashlib.sha256(str(response.get("content", "")).encode()).hexdigest(),
                    "valid": valid, "gpu_before": before["gpus"], "compute_pids_by_gpu": before["compute_pids_by_gpu"],
                    "mem_available_before_kib": before["mem_available_kib"]}
                level["samples"].append(sample)
                append_jsonl(EVENTS, {"context_tokens": target, **sample})
                atomic_json(OUT, result)
                print(json.dumps({"context": target, "rep": repetition, "valid": valid,
                    "prefill": sample["prefill_tok_s"], "decode": sample["decode_tok_s_n_over_ms"],
                    "ttft_s": prompt_ms / 1000, "wall_s": round(wall, 2)}, ensure_ascii=False), flush=True)
                if not valid:
                    raise RuntimeError(f"muestra inválida a {target} tokens")
            level["status"] = "complete"
            level["prefill_median_tok_s"] = statistics.median(s["prefill_tok_s"] for s in level["samples"])
            level["decode_median_tok_s_n_over_ms"] = statistics.median(s["decode_tok_s_n_over_ms"] for s in level["samples"])
            level["ttft_median_s"] = statistics.median(s["prompt_ms"] / 1000 for s in level["samples"])
            atomic_json(OUT, result)
        result["status"] = "complete"
    except Exception as exc:
        result["status"] = "failed_or_interrupted"
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        if active is not None:
            result["final_cleanup"] = stop_server(active)
            active_ref[0] = None
        monitor_stop.set()
        monitor.join(timeout=3)
        result["finished_utc"] = now()
        try:
            result["postflight"] = read_resources()
        except Exception as exc:
            result["postflight_error"] = f"{type(exc).__name__}: {exc}"
        result["port_free_after_cleanup"] = port_is_free()
        result["remaining_inference_processes"] = inference_processes()
        atomic_json(OUT, result)


if __name__ == "__main__":
    main()
