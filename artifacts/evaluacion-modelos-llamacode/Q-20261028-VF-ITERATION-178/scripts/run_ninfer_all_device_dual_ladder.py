#!/usr/bin/env python3
"""Q178 A05: measure Flash-Next NInfer-all with device-resident experts across two RTX 3090s."""
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
MODEL = pathlib.Path("/media/cristian/HDD extra/Modelos-eval/Q-20261028-VF-ITERATION-178/reconverted-v3/text/qwen4exp.ninfer")
PART = pathlib.Path(str(MODEL) + ".part-0001")
NGRAM = pathlib.Path("/media/cristian/Disco local/Modelos-eval/Q-20261028-VF-ITERATION-178/reconverted-v3/ngram/qwen4exp-ngram.ninfer")
BENCHY = pathlib.Path("/home/cristian/.cache/q173-llama-benchy-0.4.0/bin/llama-benchy")
TOKENIZER = pathlib.Path("/home/cristian/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9")
HOST = "127.0.0.1"
PORT = 18478
MODEL_ID = "q178-flashnext-ninfer-all-device-dual"
LEVELS = [(8192, 3), (32768, 1), (65536, 1), (131072, 1), (261888, 1)]
OUTPUT_TOKENS = 128
MIN_AVAILABLE_KIB = 32 * 1024 * 1024
STARTUP_TIMEOUT_S = 1200
RUNTIME_SHA = "09145c529015ac7d27ce63214138625927c70c1e89e4291594d74be59bd5f895"
BENCHY_SHA = "e8a892fe937d5ae1b6a43c31e8cb286ce4774f70396f62ab71008c9ddb0a01a1"
TOKENIZER_JSON_SHA = "5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42"
TOKENIZER_CONFIG_SHA = "5186f0defcd7f232382c7f0aebcd2252d073bb921ab240e407b7ae8745d2b29b"
ARTIFACTS = [
    (MODEL, "c599a10d696118a8235c953dda3fb45ef55b8c40356f4c688787cef116b8053d", 32000000000, 224838, 1793233048),
    (PART, "fa72b1f0f2d57615500a6c3568a8e8583cf1b403b2be617fa67e864c890314a2", 6640145152, 224839, 1793233113),
    (NGRAM, "2a3c7868c550171376785ff393ceff26d5b43ed7c9d2c341838582ff1f625656", 28800142336, 1264332, 1793233170),
]
RUNS = ART / "runs"
LOGS = ART / "logs"
OUT = RUNS / "ninfer-device-dual-context-ladder.json"
EVENTS = RUNS / "ninfer-device-dual-context-ladder-events.jsonl"
RESOURCES = LOGS / "ninfer-device-dual-resources.jsonl"
SAMPLING = {"temperature": 0.6, "top_p": 0.95, "top_k": 20,
            "min_p": 0.0, "repetition_penalty": 1.0,
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


def mem_available_kib() -> int:
    return next(int(line.split()[1]) for line in pathlib.Path("/proc/meminfo").read_text().splitlines()
                if line.startswith("MemAvailable:"))


def read_resources() -> dict:
    proc = subprocess.run(["nvidia-smi", "--query-gpu=index,uuid,name,memory.used,memory.total,utilization.gpu",
                           "--format=csv,noheader,nounits"], text=True, capture_output=True, timeout=10)
    if proc.returncode:
        raise RuntimeError("nvidia-smi query GPUs falló: " + proc.stderr.strip())
    gpus, uuid_index = {}, {}
    for line in proc.stdout.splitlines():
        idx, uuid, name, used, total, util = [part.strip() for part in line.split(",")]
        idx = int(idx)
        gpus[idx] = {"uuid": uuid, "name": name, "used_mib": int(used),
                     "total_mib": int(total), "util_percent": int(util)}
        uuid_index[uuid] = idx
    apps = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,gpu_uuid,used_gpu_memory",
                           "--format=csv,noheader,nounits"], text=True, capture_output=True, timeout=10)
    compute = {0: [], 1: []}
    if apps.returncode == 0:
        for line in apps.stdout.splitlines():
            cols = [part.strip() for part in line.split(",")]
            if len(cols) >= 2 and uuid_index.get(cols[1]) in compute:
                compute[uuid_index[cols[1]]].append(int(cols[0]))
    return {"timestamp_utc": now(), "mem_available_kib": mem_available_kib(),
            "memory_psi": pathlib.Path("/proc/pressure/memory").read_text().strip(),
            "gpus": gpus, "compute_pids_by_gpu": compute}


def inference_processes() -> list[dict]:
    names = {"llama-server", "ninfer-serve", "dsx-server", "vllm", "aphrodite-engine", "strata"}
    found = []
    for ent in pathlib.Path("/proc").iterdir():
        if not ent.name.isdigit() or int(ent.name) == os.getpid():
            continue
        try:
            comm = (ent / "comm").read_text().strip().lower()
            args = (ent / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            continue
        if comm in names:
            found.append({"pid": int(ent.name), "comm": comm, "cmdline": args[:1200]})
    return found


def ensure_no_foreign_server(owned_pid: int | None = None) -> None:
    check_lock()
    foreign = [item for item in inference_processes() if item["pid"] != owned_pid]
    if foreign:
        raise RuntimeError("Se detectó otro inference server; se preserva y se detiene el test: " +
                           json.dumps(foreign, ensure_ascii=False))


def port_is_free() -> bool:
    with socket.socket() as sock:
        return sock.connect_ex((HOST, PORT)) != 0


def sha(path: pathlib.Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_pins() -> dict:
    runtime_sha = sha(BIN)
    benchy_sha = sha(BENCHY)
    if runtime_sha != RUNTIME_SHA or benchy_sha != BENCHY_SHA:
        raise RuntimeError("runtime o llama-benchy SHA-256 distinto")
    verified = []
    for path, expected_sha, expected_size, expected_inode, expected_mtime in ARTIFACTS:
        if not path.is_file():
            raise RuntimeError(f"falta artefacto fijado: {path}")
        st = path.stat()
        if (st.st_size, st.st_ino, int(st.st_mtime)) != (expected_size, expected_inode, expected_mtime):
            raise RuntimeError(f"size/inode/mtime cambió para {path}")
        verified.append({"path": str(path), "bytes": st.st_size, "inode": st.st_ino,
                         "mtime_epoch_s": int(st.st_mtime), "sha256": expected_sha,
                         "sha_validation": "full SHA-256 computed after conversion; stat identity rechecked before load"})
    tok_json = TOKENIZER / "tokenizer.json"
    tok_config = TOKENIZER / "tokenizer_config.json"
    if sha(tok_json) != TOKENIZER_JSON_SHA or sha(tok_config) != TOKENIZER_CONFIG_SHA:
        raise RuntimeError("tokenizer SHA-256 distinto")
    if not port_is_free():
        raise RuntimeError(f"puerto {PORT} ocupado antes del test")
    ensure_no_foreign_server()
    resources = read_resources()
    if resources["mem_available_kib"] < MIN_AVAILABLE_KIB:
        raise RuntimeError("MemAvailable debajo del piso preregistrado de 32 GiB")
    for index in (0, 1):
        gpu = resources["gpus"].get(index)
        if not gpu or "3090" not in gpu["name"]:
            raise RuntimeError(f"GPU{index} no es RTX 3090 o no está visible: {gpu}")
    return {"timestamp_utc": now(), "runtime": {"path": str(BIN), "sha256": runtime_sha,
            "commit": "3d882fc116941d9233c40bf30f4d66dbaa3d24bd"},
            "benchmark_client": {"path": str(BENCHY), "sha256": benchy_sha, "version": "0.4.0"},
            "model_artifacts": verified, "tokenizer": {"path": str(TOKENIZER),
            "tokenizer_json_sha256": TOKENIZER_JSON_SHA, "tokenizer_config_sha256": TOKENIZER_CONFIG_SHA},
            "port_free": True, "inference_servers": inference_processes(), "resources": resources,
            "cache_note": "SHA-256 was computed before this test; process-cold init is not cold-disk init and page cache was not purged."}


def server_command() -> list[str]:
    return [str(BIN), str(MODEL), "--model-id", MODEL_ID, "--host", HOST, "--port", str(PORT),
            "--no-webui", "--max-context", "262144", "--max-concurrency", "1",
            "--devices", "0,1", "--kv-capacity", "262144", "--kv-dtype", "int8", "--kv-resident", "32768",
            "--expert-residency", "device",
            "--ngram-table", str(NGRAM), "--ngram-residency", "disk", "--ngram-io", "buffered",
            "--no-prefix-reuse", "--spec", "none", "--ngram-draft-tokens", "0",
            "--default-max-tokens", str(OUTPUT_TOKENS), "--temperature", "0.6",
            "--top-p", "0.95", "--top-k", "20", "--min-p", "0.0",
            "--presence-penalty", "0.0", "--seed", "42"]


def get_json(path: str, timeout: int = 15) -> tuple[int, dict]:
    with urllib.request.urlopen(f"http://{HOST}:{PORT}{path}", timeout=timeout) as response:
        return response.status, json.loads(response.read())


def check_dual(proc: subprocess.Popen) -> dict:
    ensure_no_foreign_server(proc.pid)
    state = read_resources()
    if state["mem_available_kib"] < MIN_AVAILABLE_KIB:
        raise RuntimeError("MemAvailable debajo de 32 GiB")
    if proc.pid not in state["compute_pids_by_gpu"].get(0, []) or proc.pid not in state["compute_pids_by_gpu"].get(1, []):
        raise RuntimeError("el PID de NInfer-all no figura como compute en ambas GPU: " +
                           json.dumps(state["compute_pids_by_gpu"]))
    return state


def stop_owned(proc: subprocess.Popen) -> dict:
    if proc.poll() is not None:
        return {"pid": proc.pid, "already_exited": True, "returncode": proc.returncode}
    exact = {item["pid"]: item for item in inference_processes()}.get(proc.pid)
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
            return {"pid": proc.pid, "stopped": False, "reason": "owned process ignored SIGINT and SIGTERM"}
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and not port_is_free():
        time.sleep(0.25)
    return {"pid": proc.pid, "stopped": proc.poll() is not None, "returncode": code,
            "port_free": port_is_free()}


def start_server(label: str, result: dict, active: list[subprocess.Popen | None], abort: threading.Event) -> tuple[subprocess.Popen, dict]:
    ensure_no_foreign_server()
    if not port_is_free():
        raise RuntimeError("puerto ocupado antes de iniciar")
    log_path = LOGS / f"ninfer-device-dual-{label}.log"
    log_stream = log_path.open("w", encoding="utf-8")
    started = time.monotonic()
    proc = subprocess.Popen(server_command(), stdout=log_stream, stderr=subprocess.STDOUT,
                            start_new_session=True, close_fds=True)
    active[0] = proc
    entry = {"label": label, "pid": proc.pid, "started_utc": now(), "argv": server_command(),
             "log": str(log_path.relative_to(ART)), "status": "starting"}
    result["initialization_runs"].append(entry)
    atomic_json(OUT, result)
    deadline = time.monotonic() + STARTUP_TIMEOUT_S
    last_error = None
    try:
        while time.monotonic() < deadline:
            check_lock()
            if abort.is_set():
                raise RuntimeError("guard de memoria canceló el inicio")
            if proc.poll() is not None:
                raise RuntimeError(f"server terminó antes de readiness, exit={proc.returncode}")
            state = read_resources()
            append_jsonl(RESOURCES, {"phase": label, **state})
            if state["mem_available_kib"] < MIN_AVAILABLE_KIB:
                raise RuntimeError("MemAvailable debajo de 32 GiB durante startup")
            try:
                status, health = get_json("/health", timeout=10)
                if status == 200 and health.get("status") == "ok":
                    dual = check_dual(proc)
                    models_status, models = get_json("/v1/models", timeout=15)
                    ids = [entry.get("id") for entry in models.get("data", [])]
                    if models_status != 200 or MODEL_ID not in ids:
                        raise RuntimeError(f"/v1/models no anuncia {MODEL_ID}: {models}")
                    entry.update({"status": "ready", "ready_utc": now(),
                                  "ready_seconds": round(time.monotonic() - started, 3),
                                  "health": health, "models_http": models_status,
                                  "model_ids": ids, "resources_at_ready": dual})
                    atomic_json(OUT, result)
                    return proc, entry
            except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as exc:
                last_error = str(exc)
            time.sleep(1)
        raise TimeoutError(f"server no llegó a readiness en {STARTUP_TIMEOUT_S}s; último error={last_error}")
    except Exception as exc:
        entry.update({"status": "failed_before_ready", "error": f"{type(exc).__name__}: {exc}",
                      "cleanup": stop_owned(proc)})
        active[0] = None
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
                proc = active[0]
                if proc is not None and proc.poll() is None:
                    proc.send_signal(signal.SIGINT)
                append_jsonl(RESOURCES, {"timestamp_utc": now(),
                    "stop_guard": "MemAvailable <32 GiB for four consecutive 15-second samples"})
                return
        except Exception as exc:
            append_jsonl(RESOURCES, {"timestamp_utc": now(),
                "monitor_error": f"{type(exc).__name__}: {exc}"})


def bench_command(contexts: list[int], runs: int, result_path: pathlib.Path, events_path: pathlib.Path) -> list[str]:
    return [str(BENCHY), "--base-url", f"http://{HOST}:{PORT}/v1", "--model", MODEL_ID,
            "--tokenizer", str(TOKENIZER), "--pp", *[str(n) for n in contexts],
            "--tg", str(OUTPUT_TOKENS), "--exact-tg", "--depth", "0", "--concurrency", "1",
            "--runs", str(runs), "--latency-mode", "generation", "--no-cache",
            "--skip-coherence", "--no-adapt-prompt", "--no-warmup",
            "--extra-body", "repetition_penalty=1.0,presence_penalty=0.0,seed=42",
            "--format", "json", "--exit-on-first-fail", "--save-result", str(result_path),
            "--emit-progress", str(events_path)]


def derive_events(path: pathlib.Path) -> dict:
    groups: dict[int, list[dict]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("request_id") is not None:
            groups.setdefault(int(event["request_id"]), []).append(event)
    rows = []
    for request_id, events in sorted(groups.items()):
        start = next((e for e in events if e.get("type") == "request_start"), {})
        first = next((e for e in events if e.get("type") == "request_first_token"), {})
        end = next((e for e in events if e.get("type") == "request_end"), {})
        if not start or not end or end.get("error"):
            continue
        prompt = end.get("prompt_tokens") or start.get("prompt_size")
        completion = end.get("total_tokens", 0)
        ttft = first.get("ttft_s")
        decode = end.get("decode_seconds")
        rows.append({"request_id": request_id, "run_index": start.get("run_index"),
                     "requested_prompt_tokens": start.get("prompt_size"),
                     "actual_prompt_tokens": prompt, "actual_completion_tokens": completion,
                     "ttft_seconds_client_observed": ttft, "decode_seconds_client_observed": decode,
                     "prefill_tok_s_client_observed": prompt / ttft if prompt and ttft else None,
                     "decode_tok_s_client_observed": completion / decode if completion and decode else None})
    return {"events_sha256": sha(path), "requests": rows}


def run_bench(label: str, contexts: list[int], runs: int, active_proc: subprocess.Popen,
              result: dict, abort: threading.Event) -> None:
    result_path = RUNS / f"{label}.json"
    events_path = RUNS / f"{label}-events.jsonl"
    for p in (result_path, events_path):
        if p.exists():
            raise RuntimeError(f"refusing to overwrite existing benchmark output: {p}")
    before = check_dual(active_proc)
    argv = bench_command(contexts, runs, result_path, events_path)
    started = time.monotonic()
    log = LOGS / f"{label}.log"
    with log.open("w", encoding="utf-8") as stream:
        proc = subprocess.Popen(argv, stdout=stream, stderr=subprocess.STDOUT,
                                start_new_session=True, close_fds=True)
        while proc.poll() is None:
            check_lock()
            if abort.is_set():
                raise RuntimeError("guard de memoria canceló el benchmark")
            check_dual(active_proc)
            time.sleep(5)
        rc = proc.returncode
    elapsed = round(time.monotonic() - started, 3)
    if rc != 0 or not events_path.exists() or not result_path.exists():
        raise RuntimeError(f"llama-benchy {label} falló rc={rc}; ver {log.relative_to(ART)}")
    derived = derive_events(events_path)
    expected_counts = {target: repetitions for target, repetitions in LEVELS if target in contexts}
    by_context: dict[int, list[dict]] = {target: [] for target in contexts}
    for request in derived["requests"]:
        target = int(request["requested_prompt_tokens"])
        if target not in by_context:
            raise RuntimeError(f"prompt_size inesperado {target} en {label}")
        if request["actual_completion_tokens"] != OUTPUT_TOKENS:
            raise RuntimeError(f"output no fue exactamente {OUTPUT_TOKENS} tokens en {label}")
        if request["actual_prompt_tokens"] + OUTPUT_TOKENS > 262144:
            raise RuntimeError(f"prompt + salida excede max-context en {label}")
        by_context[target].append(request)
    summaries = []
    for target in contexts:
        samples = by_context[target]
        if len(samples) != expected_counts[target]:
            raise RuntimeError(f"esperaba {expected_counts[target]} muestras para {target}, recibí {len(samples)}")
        prefill = [s["prefill_tok_s_client_observed"] for s in samples]
        decode = [s["decode_tok_s_client_observed"] for s in samples]
        ttft = [s["ttft_seconds_client_observed"] for s in samples]
        if any(v is None or v <= 0 for v in prefill + decode + ttft):
            raise RuntimeError(f"muestra sin timing válido en {label}/{target}")
        summaries.append({"requested_prompt_tokens": target, "repetitions": len(samples),
                          "prefill_tok_s_median": statistics.median(prefill),
                          "decode_tok_s_median": statistics.median(decode),
                          "ttft_seconds_median": statistics.median(ttft), "samples": samples})
    record = {"label": label, "argv": argv, "log": str(log.relative_to(ART)),
              "result_json": str(result_path.relative_to(ART)),
              "progress_jsonl": str(events_path.relative_to(ART)), "exit_code": rc,
              "elapsed_seconds": elapsed, "gpu_resources_before": before,
              "event_summary": derived, "context_summary": summaries,
              "method_note": "client-observed rates; prefill=actual prompt tokens/TTFT, decode=exact output tokens/decode seconds"}
    result["benchmark_runs"].append(record)
    atomic_json(OUT, result)


def main() -> None:
    RUNS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    check_lock()
    baseline = verify_pins()
    atomic_json(ART / "receipts/preflight-amendment-05-device-dual.json", baseline)
    result = {"task_id": "Q178-A05-Qwen-FlashNext-NInfer-all-device-dual3090",
              "started_utc": now(), "status": "running", "runtime_sha256": RUNTIME_SHA,
              "runtime_commit": "3d882fc116941d9233c40bf30f4d66dbaa3d24bd",
              "model_sha256": ARTIFACTS[0][1], "part_sha256": ARTIFACTS[1][1],
              "ngram_sha256": ARTIFACTS[2][1], "model": "Qwen3.8 Flash-Next RCO IQ2_XS; A03 NInfer v3 reconversion",
              "gpu_topology": "NInfer-all device-resident experts; one pipeline stage on each of GPU0 and GPU1; KV resident on GPU through 32K then streamed to host; not tensor-parallel",
              "baseline": baseline, "max_context": 262144, "context_levels": LEVELS,
              "output_tokens": OUTPUT_TOKENS, "sampling": SAMPLING,
              "initialization_runs": [], "benchmark_runs": [],
              "quality_note": "Q172 77/100 belongs to historical Q173 NInfer preview v0.16.1 on GPU1; not rerun or attributed to this runtime.",
              "cache_note": baseline["cache_note"]}
    atomic_json(OUT, result)
    active: list[subprocess.Popen | None] = [None]
    stop = threading.Event()
    abort = threading.Event()
    monitor = threading.Thread(target=monitor_resources, args=(stop, abort, active), daemon=True)
    monitor.start()
    current: subprocess.Popen | None = None
    try:
        current, _ = start_server("process-cold-page-cache-uncontrolled", result, active, abort)
        first = stop_owned(current)
        active[0] = None
        result["initialization_runs"][-1]["cleanup"] = first
        current = None
        if not first.get("stopped") or not first.get("port_free"):
            raise RuntimeError("primer proceso no se limpió o puerto ocupado")
        current, _ = start_server("immediate-hot-likely-relaunch", result, active, abort)
        active[0] = current
        result["initialization_runs"][-1]["cleanup_note"] = "will be stopped after serial ladder"
        atomic_json(OUT, result)
        run_bench("ninfer-device-dual-8k", [8192], 3, current, result, abort)
        run_bench("ninfer-device-dual-contexts", [32768, 65536, 131072, 261888], 1,
                  current, result, abort)
        result["status"] = "complete"
    except Exception as exc:
        result["status"] = "failed_or_interrupted"
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        if current is not None:
            result["final_cleanup"] = stop_owned(current)
            active[0] = None
        stop.set()
        monitor.join(timeout=3)
        result["finished_utc"] = now()
        try:
            result["postflight"] = read_resources()
        except Exception as exc:
            result["postflight_error"] = f"{type(exc).__name__}: {exc}"
        result["port_free_after_cleanup"] = port_is_free()
        result["remaining_inference_servers"] = inference_processes()
        atomic_json(OUT, result)


if __name__ == "__main__":
    main()
