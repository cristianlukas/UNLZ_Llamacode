#!/usr/bin/env python3
"""Q178 A02: repeat the exact Q173 NInfer preview ladder on GPU0+GPU1."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import signal
import socket
import statistics
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ART = pathlib.Path(__file__).resolve().parents[1]
REPO = pathlib.Path(__file__).resolve().parents[4]
TOKEN = "2242863e-c78e-4fa9-9649-c1d1541f3919"
BIN = pathlib.Path("/media/cristian/Disco local/LlamaCode-cache/Q171-ninfer-build-r1/apps/ninfer-serve")
MODEL = pathlib.Path("/media/cristian/HDD extra/Modelos-eval/Q-20261027-VF-ITERATION-171/artifact/qwen4exp.ninfer")
PART = pathlib.Path(str(MODEL) + ".part-0001")
NGRAM = pathlib.Path("/media/cristian/Disco local/Modelos-eval/Q39-NInfer-v0.16.1-FlashNext-IQ2XS/qwen4exp.ninfer.ngram")
BENCH = pathlib.Path("/home/cristian/.cache/q173-llama-benchy-0.4.0/bin/llama-benchy")
TOKENIZER = pathlib.Path("/home/cristian/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9")
PORT = 18479
HOST = "127.0.0.1"
MODEL_ID = "q178-flashnext-ninfer-dual"
LEVELS = [(8192, 3), (32768, 1), (65536, 1), (131072, 1), (261888, 1)]
MIN_AVAILABLE_KIB = 32 * 1024 * 1024
RUNTIME_SHA = "59e5f3e21246ac9f4bd871943e1e1348fbcb7ad6b3d2d32d046b5d4595bb3bac"
MODEL_SHA = "6c3dd0a8a730566b3cda9b6c563a8a345d1986f930be409a0dca8bd2a9887584"
PART_SHA = "a089cb07a49c18b8eb942e89c4e3676f0b03adf0fdbd141dc8f5d4cf5418de1f"
NGRAM_SHA = "0478dd2f62a4d02b5cf3ab64d69229bd88dd95366498ad7c72828f95b99135b6"
RUNS = ART / "runs"
LOGS = ART / "logs"
RESULT = RUNS / "ninfer-preview-dual-context-ladder.json"
RESOURCES = LOGS / "ninfer-preview-dual-resources.jsonl"
SAMPLING = "repetition_penalty=1.0,presence_penalty=0.0,seed=42"


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


def inference_processes(owned_pid: int | None = None) -> list[dict]:
    found = []
    for ent in pathlib.Path("/proc").iterdir():
        if not ent.name.isdigit() or int(ent.name) in {os.getpid(), owned_pid}:
            continue
        try:
            comm = (ent / "comm").read_text().strip().lower()
            args = (ent / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            continue
        if comm in {"llama-server", "ninfer-serve", "dsx-server", "vllm", "aphrodite-engine", "strata", "ollama"}:
            found.append({"pid": int(ent.name), "comm": comm, "cmdline": args[:1000]})
    return found


def resources() -> dict:
    mem = next(int(line.split()[1]) for line in pathlib.Path("/proc/meminfo").read_text().splitlines()
               if line.startswith("MemAvailable:"))
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=index,uuid,name,memory.used,memory.total,utilization.gpu",
                          "--format=csv,noheader,nounits"], text=True, capture_output=True, timeout=10)
    if gpu.returncode:
        raise RuntimeError("nvidia-smi GPU query failed: " + gpu.stderr.strip())
    gpus = {}
    uuid_index = {}
    for line in gpu.stdout.splitlines():
        idx, uuid, name, used, total, util = [part.strip() for part in line.split(",")]
        gpus[int(idx)] = {"uuid": uuid, "name": name, "used_mib": int(used),
                          "total_mib": int(total), "util_percent": int(util)}
        uuid_index[uuid] = int(idx)
    app = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,gpu_uuid,used_gpu_memory",
                          "--format=csv,noheader,nounits"], text=True, capture_output=True, timeout=10)
    pids = {0: [], 1: []}
    if app.returncode == 0:
        for line in app.stdout.splitlines():
            row = [item.strip() for item in line.split(",")]
            if len(row) >= 2:
                idx = uuid_index.get(row[1])
                if idx in pids:
                    pids[idx].append(int(row[0]))
    return {"timestamp_utc": now(), "mem_available_kib": mem,
            "memory_psi": pathlib.Path("/proc/pressure/memory").read_text(),
            "gpus": gpus, "compute_pids_by_gpu": pids}


def file_sha(path: pathlib.Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def port_free() -> bool:
    with socket.socket() as sock:
        return sock.connect_ex((HOST, PORT)) != 0


def verify_pins() -> dict:
    check_lock()
    expected = [(BIN, RUNTIME_SHA, None), (MODEL, MODEL_SHA, 32000000000),
                (PART, PART_SHA, 7225180928), (NGRAM, NGRAM_SHA, 29127258112)]
    q173 = json.loads((REPO / "artifacts/evaluacion-modelos-llamacode/Q-20261028-VF-ITERATION-173/receipts/ninfer-flashnext-preflight-20261028T174312Z.json").read_text())
    q173_files = [
        q173["inputs"]["model_shard_1"], q173["inputs"]["model_shard_2"],
        q173["inputs"]["ngram_cache"], q173["inputs"]["runtime"]
    ]
    expected_q173 = {item["path"]: item for item in q173_files}
    verified = []
    for path, sha, size in expected:
        if not path.is_file():
            raise RuntimeError(f"missing pinned input: {path}")
        st = path.stat()
        if size is not None and st.st_size != size:
            raise RuntimeError(f"size mismatch: {path}={st.st_size}")
        prior = expected_q173.get(str(path))
        if prior and (prior.get("bytes") != st.st_size or prior.get("mtime_epoch") != int(st.st_mtime)):
            raise RuntimeError(f"size/mtime changed since Q173: {path}")
        got = file_sha(path) if path == BIN else sha
        if got != sha:
            raise RuntimeError(f"SHA mismatch for {path}: {got}")
        verified.append({"path": str(path), "bytes": st.st_size, "mtime_epoch": int(st.st_mtime),
                         "sha256": got, "validation": "fresh SHA" if path == BIN else "exact SHA inherited from Q171/Q173; size+mtime rechecked"})
    bench_version = subprocess.run([str(BENCH), "--version"], text=True, capture_output=True, timeout=10)
    if bench_version.returncode or "0.4.0" not in bench_version.stdout + bench_version.stderr:
        raise RuntimeError("llama-benchy version no longer matches Q173")
    bench_sha = file_sha(BENCH)
    prior_bench_sha = None
    if not TOKENIZER.is_dir():
        raise RuntimeError("Q173 tokenizer path missing")
    if not port_free():
        raise RuntimeError(f"port {PORT} already occupied")
    others = inference_processes()
    if others:
        raise RuntimeError("foreign inference server active: " + json.dumps(others))
    state = resources()
    if len(state["gpus"]) < 2:
        raise RuntimeError("two GPUs not visible")
    return {"task": "Q178 A02 fresh preflight", "timestamp_utc": now(), "lock_token": TOKEN,
            "files": verified, "llama_benchy": {"path": str(BENCH), "version": (bench_version.stdout + bench_version.stderr).strip(),
                                                   "sha256": bench_sha, "prior_sha": prior_bench_sha},
            "tokenizer_path": str(TOKENIZER), "tokenizer_dir_exists": True,
            "port_free": True, "inference_servers": [], "resources": state}


def server_command() -> list[str]:
    return [str(BIN), str(MODEL), "--host", HOST, "--port", str(PORT), "--model-id", MODEL_ID,
            "--max-context", "262144", "--kv-capacity", "262144", "--max-concurrency", "1",
            "--devices", "0,1", "--kv-dtype", "int8", "--ngram-volume", str(NGRAM),
            "--no-prefix-reuse", "--ngram-draft-tokens", "0", "--no-expert-state",
            "--default-max-tokens", "128", "--temperature", "0.6", "--top-p", "0.95",
            "--top-k", "20", "--min-p", "0", "--presence-penalty", "0", "--seed", "42",
            "--log-level", "info"]


def models_ready() -> tuple[int, dict | str]:
    request = urllib.request.Request(f"http://{HOST}:{PORT}/v1/models")
    with urllib.request.urlopen(request, timeout=10) as response:
        raw = response.read()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = raw.decode(errors="replace")
        return response.status, payload


def check_dual(pid: int, baseline: dict) -> dict:
    check_lock()
    others = inference_processes(pid)
    if others:
        raise RuntimeError("foreign inference server active: " + json.dumps(others))
    state = resources()
    if state["mem_available_kib"] < MIN_AVAILABLE_KIB:
        raise RuntimeError("MemAvailable below 32 GiB")
    for index in (0, 1):
        if pid not in state["compute_pids_by_gpu"].get(index, []):
            raise RuntimeError(f"Q178 PID {pid} is not CUDA compute on GPU{index}: {state['compute_pids_by_gpu']}")
        if state["gpus"][index]["used_mib"] <= baseline["gpus"][index]["used_mib"] + 1024:
            raise RuntimeError(f"GPU{index} memory did not rise by >1 GiB over baseline")
    return state


def start_server(label: str, baseline: dict, result: dict) -> tuple[subprocess.Popen, dict]:
    check_lock()
    if inference_processes():
        raise RuntimeError("foreign inference server active before launch")
    if not port_free():
        raise RuntimeError(f"port {PORT} occupied")
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = "0,1"
    started = time.monotonic()
    log_path = LOGS / f"ninfer-preview-dual-{label}.log"
    log_stream = log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(server_command(), stdout=log_stream, stderr=subprocess.STDOUT,
                            env=env, start_new_session=True, close_fds=True)
    entry = {"label": label, "pid": proc.pid, "started_utc": now(), "argv": server_command(),
             "log": str(log_path.relative_to(ART)), "ready_seconds": None, "status": "starting"}
    result["initialization_runs"].append(entry)
    atomic_json(RESULT, result)
    last_error = None
    try:
        deadline = time.monotonic() + 1200
        last_resource_sample = 0.0
        low_mem_samples = 0
        while time.monotonic() < deadline:
            check_lock()
            now_mono = time.monotonic()
            if now_mono - last_resource_sample >= 15:
                state = resources()
                append_jsonl(RESOURCES, {"phase": label, **state})
                low_mem_samples = low_mem_samples + 1 if state["mem_available_kib"] < MIN_AVAILABLE_KIB else 0
                last_resource_sample = now_mono
                if low_mem_samples >= 4:
                    raise RuntimeError("MemAvailable below 32 GiB for four consecutive 15-second samples during startup")
            if proc.poll() is not None:
                raise RuntimeError(f"server exited before readiness, rc={proc.returncode}")
            try:
                status, payload = models_ready()
                if status == 200:
                    dual = check_dual(proc.pid, baseline)
                    entry.update({"status": "ready", "ready_utc": now(),
                                  "ready_seconds": round(time.monotonic() - started, 3),
                                  "models_payload": payload, "resources_at_ready": dual})
                    atomic_json(RESULT, result)
                    return proc, entry
            except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as exc:
                last_error = str(exc)
            time.sleep(1)
        raise TimeoutError(f"readiness timed out; last error={last_error}")
    except Exception as exc:
        entry.update({"status": "failed_before_ready", "error": f"{type(exc).__name__}: {exc}"})
        cleanup = stop_server(proc)
        entry["cleanup"] = cleanup
        atomic_json(RESULT, result)
        raise
    finally:
        log_stream.flush()
        log_stream.close()


def stop_server(proc: subprocess.Popen) -> dict:
    if proc.poll() is not None:
        return {"pid": proc.pid, "already_exited": True, "returncode": proc.returncode, "port_free": port_free()}
    proc.send_signal(signal.SIGINT)
    try:
        code = proc.wait(timeout=40)
    except subprocess.TimeoutExpired:
        proc.send_signal(signal.SIGTERM)
        try:
            code = proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            return {"pid": proc.pid, "stopped": False, "reason": "owned server ignored SIGINT/SIGTERM"}
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and (not port_free() or proc.pid in [p["pid"] for p in inference_processes()]):
        time.sleep(0.25)
    return {"pid": proc.pid, "stopped": proc.poll() is not None, "returncode": code,
            "port_free": port_free(), "remaining_inference_processes": inference_processes()}


def run_client(label: str, prompts: list[int], runs: int,
               server: subprocess.Popen, baseline: dict) -> dict:
    name = "8k" if prompts == [8192] else "contexts"
    out_json = RUNS / f"ninfer-preview-dual-{name}.json"
    events = RUNS / f"ninfer-preview-dual-{name}-events.jsonl"
    command = [str(BENCH), "--base-url", f"http://{HOST}:{PORT}/v1", "--model", MODEL_ID,
               "--tokenizer", str(TOKENIZER), "--pp", *[str(x) for x in prompts],
               "--tg", "128", "--exact-tg", "--depth", "0", "--concurrency", "1",
               "--runs", str(runs), "--latency-mode", "generation", "--no-cache",
               "--skip-coherence", "--no-adapt-prompt", "--no-warmup", "--extra-body", SAMPLING,
               "--format", "json", "--save-result", str(out_json), "--emit-progress", str(events)]
    log = LOGS / f"ninfer-preview-dual-{name}-benchy.log"
    check_lock()
    with log.open("w", encoding="utf-8") as stream:
        proc = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, text=True)
        started = time.monotonic()
        low_mem_samples = 0
        try:
            while proc.poll() is None:
                check_lock()
                if time.monotonic() - started > 7200:
                    raise TimeoutError(f"llama-benchy {label} exceeded 7200 s")
                state = resources()
                append_jsonl(RESOURCES, {"phase": f"benchmark-{name}", **state})
                low_mem_samples = low_mem_samples + 1 if state["mem_available_kib"] < MIN_AVAILABLE_KIB else 0
                if low_mem_samples >= 4:
                    raise RuntimeError("MemAvailable below 32 GiB for four consecutive 15-second samples")
                if server.poll() is not None:
                    raise RuntimeError(f"inference server exited during {label}, rc={server.returncode}")
                check_dual(server.pid, baseline)
                try:
                    proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    continue
        except Exception:
            if proc.poll() is None:
                proc.send_signal(signal.SIGINT)
                try:
                    proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    proc.wait(timeout=15)
            raise
        returncode = proc.returncode
    if returncode:
        raise RuntimeError(f"llama-benchy {label} failed rc={returncode}; see {log}")
    data = json.loads(out_json.read_text(encoding="utf-8"))
    if len(data.get("benchmarks", [])) != (3 if prompts == [8192] else len(prompts)):
        raise RuntimeError(f"llama-benchy {label} returned an unexpected benchmark count")
    parsed = derive_events(events)
    expected_count = 3 if prompts == [8192] else len(prompts)
    if len(parsed) != expected_count or any(x["total_tokens"] != 128 or x["error"] for x in parsed):
        raise RuntimeError(f"progress events invalid for {label}: {parsed}")
    result = {"label": label, "command": command, "result_json": str(out_json.relative_to(ART)),
              "events": str(events.relative_to(ART)), "log": str(log.relative_to(ART)),
              "benchy_version": data.get("version"), "samples": parsed}
    append_jsonl(RUNS / "ninfer-preview-dual-derived.jsonl", result)
    return result


def derive_events(path: pathlib.Path) -> list[dict]:
    requests: dict[int, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        rid = event.get("request_id")
        if rid is None:
            continue
        item = requests.setdefault(int(rid), {})
        kind = event.get("type")
        if kind == "request_start":
            item["target_prompt_tokens"] = event.get("prompt_size")
        elif kind == "request_first_token":
            item["ttft_s"] = event.get("ttft_s")
        elif kind == "request_end":
            item.update({"prompt_tokens": event.get("prompt_tokens"),
                         "total_tokens": event.get("total_tokens"),
                         "decode_seconds": event.get("decode_seconds"),
                         "error": event.get("error", "")})
    result = []
    for rid, item in sorted(requests.items()):
        ttft, prompt, count, decode = (item.get("ttft_s"), item.get("prompt_tokens"),
                                       item.get("total_tokens"), item.get("decode_seconds"))
        item["request_id"] = rid
        item["prefill_tok_s"] = prompt / ttft if ttft and prompt else None
        item["decode_tok_s"] = count / decode if decode and count else None
        result.append(item)
    return result


def smoke(proc: subprocess.Popen, baseline: dict) -> dict:
    state = check_dual(proc.pid, baseline)
    payload = {"model": MODEL_ID, "messages": [{"role": "user", "content": "Respondé con una frase breve."}],
               "max_tokens": 16, "stream": False}
    body = json.dumps(payload).encode()
    req = urllib.request.Request(f"http://{HOST}:{PORT}/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read())
        code = resp.status
    choices = data.get("choices", [])
    text = choices[0].get("message", {}).get("content", "") if choices else ""
    return {"http_status": code, "text_nonempty": bool(text), "completion_tokens": data.get("usage", {}).get("completion_tokens"),
            "valid": code == 200 and bool(text), "gpu_resources": state}


def main() -> None:
    RUNS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    check_lock()
    outputs = [RESULT, RUNS / "ninfer-preview-dual-8k.json", RUNS / "ninfer-preview-dual-8k-events.jsonl",
               RUNS / "ninfer-preview-dual-contexts.json", RUNS / "ninfer-preview-dual-contexts-events.jsonl",
               RUNS / "ninfer-preview-dual-derived.jsonl"]
    existing = [str(path) for path in outputs if path.exists()]
    if existing:
        raise RuntimeError("refusing to overwrite prior Q178 A02 outputs; register a new attempt: " + ", ".join(existing))
    pins = verify_pins()
    atomic_json(ART / "receipts/ninfer-preview-dual-preflight.json", pins)
    baseline = pins["resources"]
    result = {"task_id": "Q178-A02-Q173-NInfer-preview-same-runtime-dual-3090",
              "started_utc": now(), "status": "running", "preflight": pins,
              "runtime_sha256": RUNTIME_SHA, "model_sha256": MODEL_SHA,
              "part_sha256": PART_SHA, "ngram_sha256": NGRAM_SHA,
              "gpu_topology": "GPU0+GPU1 pipeline stages, same NInfer v0.16.1 binary as historical Q173 GPU1-only",
              "levels": LEVELS, "initialization_runs": [], "smoke": None, "benchmarks": []}
    atomic_json(RESULT, result)
    active = None
    try:
        active, _ = start_server("cold-process", baseline, result)
        cold = result["initialization_runs"][-1]
        cold_cleanup = stop_server(active)
        cold["cleanup"] = cold_cleanup
        active = None
        if not cold_cleanup.get("stopped") or not cold_cleanup.get("port_free"):
            raise RuntimeError("cold process failed cleanup")

        active, _ = start_server("hot-likely-relaunch", baseline, result)
        result["smoke"] = smoke(active, baseline)
        atomic_json(RESULT, result)
        if not result["smoke"]["valid"]:
            raise RuntimeError("dual-GPU smoke did not return text")

        result["benchmarks"].append(run_client("8K x3", [8192], 3, active, baseline))
        check_dual(active.pid, baseline)
        result["benchmarks"].append(run_client("32K/64K/128K/261888 x1", [32768, 65536, 131072, 261888], 1, active, baseline))
        check_dual(active.pid, baseline)
        result["status"] = "complete"
    except Exception as exc:
        result["status"] = "failed_or_interrupted"
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        if active is not None:
            result["final_cleanup"] = stop_server(active)
        result["finished_utc"] = now()
        try:
            result["postflight"] = resources()
        except Exception as exc:
            result["postflight_error"] = f"{type(exc).__name__}: {exc}"
        result["port_free_after_cleanup"] = port_free()
        result["remaining_inference_processes"] = inference_processes()
        atomic_json(RESULT, result)


if __name__ == "__main__":
    main()
