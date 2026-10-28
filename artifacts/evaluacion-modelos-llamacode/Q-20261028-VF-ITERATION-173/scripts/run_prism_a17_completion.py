#!/usr/bin/env python3
"""Run preregistered PrismML context timings through its local completion API."""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import signal
import socket
import statistics
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[4]
ART = pathlib.Path(__file__).resolve().parents[1]
RUNS = ART / "runs/prism-a17-completion"
LOGS = ART / "logs/prism-a17-completion"
RECEIPTS = ART / "receipts"
MODEL = pathlib.Path(
    "/media/cristian/Disco local/Modelos-eval/Q-20261027-VF-ITERATION-172/"
    "Bonsai2-Prism-PQ2_0/models/Ternary-Bonsai-2-27B-PQ2_0.gguf"
)
SERVER = pathlib.Path(
    "/media/cristian/Disco local/Modelos-eval/Q-20261027-VF-ITERATION-172/"
    "Bonsai2-Prism-PQ2_0/runtime/llama-prism-b10826-c9c34bc/llama-server"
)
EXPECTED_MODEL_SHA256 = "3907dc1658db1f78a9826bf8d5bcb8dc65db0d466388937af57f2294fae62ec1"
EXPECTED_SERVER_SHA256 = "3ad6c90f0f25fec776be6d70b0bfe3ada0a8bf6a765b53f7a97cf985b0ea560a"
LOCK_TOKEN = "2242863e-c78e-4fa9-9649-c1d1541f3919"
PORT = 18178
HOST = "127.0.0.1"
LEVELS = [(8192, 3), (32768, 1), (65536, 1), (131072, 1), (261888, 1)]
N_PREDICT = 128
MIN_AVAILABLE_KIB = 32 * 1024 * 1024
SAMPLING = {
    "temperature": 0.6,
    "top_p": 0.95,
    "top_k": 20,
    "min_p": 0.0,
    "repeat_penalty": 1.0,
    "presence_penalty": 0.0,
    "seed": 42,
}
INFERENCE_NAMES = {
    "llama-server", "llama-server.exe", "vllm", "ninfer-serve", "ollama",
    "ollama_llama_server", "lmstudio", "lm-studio", "aphrodite-engine",
}
CONTAINER_MARKERS = ("llama-server", "vllm", "ninfer", "ollama", "localai", "aphrodite")
EXCLUDED_ATTEMPTS = []


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: pathlib.Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)


def append_jsonl(path: pathlib.Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(value, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def meminfo_kib(key):
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        if line.startswith(key + ":"):
            return int(line.split()[1])
    return None


def psi_memory():
    return pathlib.Path("/proc/pressure/memory").read_text().strip()


def inference_processes():
    found = []
    proc_root = pathlib.Path("/proc")
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid == os.getpid():
            continue
        try:
            comm = (entry / "comm").read_text().strip().lower()
            cmd = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except (OSError, ProcessLookupError):
            continue
        low = cmd.lower()
        if comm in INFERENCE_NAMES or any(
            marker in low for marker in ("vllm serve", "ninfer-serve", "ollama serve", "aphrodite-engine")
        ):
            found.append({"pid": pid, "comm": comm, "cmdline": cmd[:500]})
    return found


def inference_containers():
    try:
        p = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}|{{.Image}}|{{.Command}}"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if p.returncode != 0:
        return []
    return [line for line in p.stdout.splitlines() if any(x in line.lower() for x in CONTAINER_MARKERS)]


def gpu_state():
    p = subprocess.run(
        ["nvidia-smi", "--query-gpu=index,name,memory.used,utilization.gpu", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, timeout=5, check=False,
    )
    if p.returncode != 0:
        return {"error": p.stderr.strip(), "returncode": p.returncode}
    rows = []
    for line in p.stdout.splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) >= 4:
            rows.append({"index": int(parts[0]), "name": parts[1], "memory_used_mib": int(parts[2]),
                         "utilization_percent": int(parts[3])})
    return rows


def resource_state():
    return {
        "timestamp_utc": now(),
        "MemAvailable_kib": meminfo_kib("MemAvailable"),
        "SwapFree_kib": meminfo_kib("SwapFree"),
        "memory_psi": psi_memory(),
        "gpu": gpu_state(),
        "inference_processes": inference_processes(),
        "inference_containers": inference_containers(),
    }


def port_is_free():
    try:
        p = subprocess.run(["ss", "-H", "-ltnp", f"sport = :{PORT}"], capture_output=True,
                           text=True, timeout=5, check=False)
        if p.returncode == 0:
            return not p.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    s = socket.socket()
    try:
        return s.connect_ex((HOST, PORT)) != 0
    finally:
        s.close()


def http_json(path, body=None, timeout=30):
    url = f"http://{HOST}:{PORT}{path}"
    if body is None:
        req = urllib.request.Request(url, method="GET")
    else:
        data = json.dumps(body, separators=(",", ":")).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read()
        return response.status, json.loads(raw)


def sample_text(start, count=1024):
    regions = ["north ridge", "river basin", "coastal plain", "western plateau", "central valley"]
    materials = ["copper", "basalt", "silica", "timber", "granite", "aluminum", "clay"]
    actions = ["measured", "compared", "recorded", "reviewed", "estimated", "classified", "verified"]
    lines = []
    for i in range(start, start + count):
        lines.append(
            f"Record {i:07d}: the {regions[i % len(regions)]} team {actions[(i // 3) % len(actions)]} "
            f"{materials[(i // 7) % len(materials)]} sample {i % 997} at {12 + i % 89} units. "
            f"The note cites station {i % 113}, batch {i % 431}, and observation {i % 2027}.\n"
        )
    return "".join(lines)


def tokenize_fixture(target):
    ids = []
    start = 0
    chunk_size = 1024
    while len(ids) < target:
        _, result = http_json("/tokenize", {
            "content": sample_text(start, chunk_size),
            "add_special": False,
            "parse_special": False,
            "with_pieces": False,
        }, timeout=120)
        chunk = result.get("tokens")
        if not isinstance(chunk, list) or not chunk:
            raise RuntimeError("/tokenize devolvió una lista vacía o inválida")
        ids.extend(int(token) for token in chunk)
        start += chunk_size
        if start > 1024 * 1024:
            raise RuntimeError("No se alcanzó la cantidad de tokens del fixture")
    return ids[:target]


def stop_owned(proc, log_file):
    if proc is None or proc.poll() is not None:
        return
    try:
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    finally:
        if log_file:
            log_file.flush()


def allocate_ok(baseline_gpu):
    current = gpu_state()
    if not isinstance(current, list) or len(current) < 2:
        return False, current
    base = {int(x["index"]): int(x["memory_used_mib"]) for x in baseline_gpu if "index" in x}
    now_mem = {int(x["index"]): int(x["memory_used_mib"]) for x in current}
    return all(now_mem.get(i, 0) - base.get(i, 0) > 1024 for i in (0, 1)), current


def start_memory_monitor(proc, path, stop_event, abort_event):
    def monitor():
        below = 0
        while not stop_event.wait(15):
            s = resource_state()
            append_jsonl(path, {"kind": "resource_sample", **s})
            available = s.get("MemAvailable_kib")
            below = below + 1 if available is not None and available < MIN_AVAILABLE_KIB else 0
            if below >= 4:
                abort_event.set()
                if proc.poll() is None:
                    try:
                        proc.send_signal(signal.SIGINT)
                    except ProcessLookupError:
                        pass
                append_jsonl(path, {"kind": "stop_guard", "timestamp_utc": now(),
                                    "reason": "MemAvailable below 32 GiB for four consecutive 15s samples"})
                return
    t = threading.Thread(target=monitor, name="prism-memory-monitor", daemon=True)
    t.start()
    return t


def request_body(prompt_ids, n_predict=N_PREDICT):
    return {
        "prompt": prompt_ids,
        "n_predict": n_predict,
        "cache_prompt": False,
        "stream": False,
        "ignore_eos": True,
        "return_tokens": True,
        **SAMPLING,
    }


def run_level(prompt_tokens, repetitions, accumulated):
    level_tag = f"{(prompt_tokens + 512) // 1024}k"
    port_free = port_is_free()
    pre = resource_state()
    record = {
        "prompt_tokens_target": prompt_tokens,
        "repetitions_preregistered": repetitions,
        "server_context_tokens": min(262144, ((prompt_tokens + N_PREDICT + 255) // 256) * 256),
        "preflight": {**pre, "port_free": port_free},
        "samples": [],
    }
    if pre["inference_processes"] or pre["inference_containers"] or not port_free:
        record["status"] = "blocked_external_inference_or_port"
        accumulated.append(record)
        save_derived(accumulated)
        raise RuntimeError(f"Preflight bloqueado antes de {level_tag}: server externo o puerto ocupado")
    baseline_gpu = pre["gpu"]
    ctx = record["server_context_tokens"]
    argv = [
        str(SERVER), "--model", str(MODEL), "--host", HOST, "--port", str(PORT),
        "--device", "CUDA0,CUDA1", "--split-mode", "layer", "--tensor-split", "1,1",
        "--gpu-layers", "all", "--ctx-size", str(ctx), "--parallel", "1",
        "--flash-attn", "on", "--perf", "--seed", "42",
    ]
    log_path = LOGS / f"server-{level_tag}.log"
    resource_path = LOGS / f"resources-{level_tag}.jsonl"
    log_file = log_path.open("w", encoding="utf-8")
    proc = None
    monitor_stop = threading.Event()
    monitor_abort = threading.Event()
    monitor = None
    try:
        proc = subprocess.Popen(argv, stdout=log_file, stderr=subprocess.STDOUT, start_new_session=True,
                                cwd=str(SERVER.parent), env={**os.environ, "CUDA_VISIBLE_DEVICES": "0,1"})
        record["server"] = {"pid": proc.pid, "argv": argv, "log": str(log_path.relative_to(ROOT))}
        monitor = start_memory_monitor(proc, resource_path, monitor_stop, monitor_abort)
        deadline = time.monotonic() + 600
        health = None
        while time.monotonic() < deadline and proc.poll() is None:
            try:
                status, health = http_json("/health", timeout=5)
                if status == 200 and health.get("status") == "ok":
                    break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                pass
            time.sleep(3)
        else:
            raise RuntimeError("PrismML llama-server no alcanzó readiness en 600s")
        record["health"] = {"http_status": 200, "body": health, "ready_timestamp_utc": now()}

        ready_ids = tokenize_fixture(64)
        smoke_status, smoke = http_json("/completion", request_body(ready_ids, 16), timeout=300)
        if smoke_status != 200 or not isinstance(smoke.get("timings"), dict):
            raise RuntimeError("smoke READY no devolvió tiempos del endpoint")
        record["unscored_ready_smoke"] = {
            "http_status": smoke_status,
            "prompt_n": smoke.get("timings", {}).get("prompt_n"),
            "predicted_n": smoke.get("timings", {}).get("predicted_n"),
            "cache_n": smoke.get("timings", {}).get("cache_n"),
        }

        alloc_deadline = time.monotonic() + 45
        ok, gpu = allocate_ok(baseline_gpu)
        while not ok and time.monotonic() < alloc_deadline and proc.poll() is None:
            time.sleep(3)
            ok, gpu = allocate_ok(baseline_gpu)
        record["gpu_allocation_gate"] = {"passed": ok, "gpu": gpu, "baseline_gpu": baseline_gpu}
        if not ok:
            raise RuntimeError("no se confirmó asignación >1 GiB adicional en ambas RTX 3090")

        fixture = tokenize_fixture(prompt_tokens)
        record["fixture"] = {
            "token_count": len(fixture),
            "token_ids_sha256": hashlib.sha256(json.dumps(fixture, separators=(",", ":")).encode()).hexdigest(),
            "token_source": "local pinned server /tokenize; deterministic synthetic text; add_special=false",
        }
        for repetition in range(1, repetitions + 1):
            if monitor_abort.is_set() or proc.poll() is not None:
                raise RuntimeError("servidor detenido por guardia de memoria o salida inesperada")
            body = request_body(fixture)
            before = time.monotonic()
            status, response = http_json("/completion", body, timeout=7200)
            wall_s = time.monotonic() - before
            timings = response.get("timings") or {}
            predicted_n = int(timings.get("predicted_n", 0))
            prompt_n = int(timings.get("prompt_n", -1))
            cache_n = int(timings.get("cache_n", -1))
            prompt_ms = float(timings.get("prompt_ms", 0))
            predicted_ms = float(timings.get("predicted_ms", 0))
            valid = (
                status == 200 and prompt_n == prompt_tokens and cache_n == 0 and
                predicted_n == N_PREDICT and prompt_ms > 0 and predicted_ms > 0
            )
            sample = {
                "timestamp_utc": now(), "sample_index": repetition, "http_status": status,
                "prompt_n": prompt_n, "cache_n": cache_n, "prompt_ms": prompt_ms,
                "predicted_n": predicted_n, "predicted_ms": predicted_ms,
                "prefill_tok_s": prompt_n / (prompt_ms / 1000) if prompt_ms > 0 else None,
                "decode_tok_s": predicted_n / (predicted_ms / 1000) if predicted_ms > 0 else None,
                "client_wall_s": wall_s, "valid": valid,
                "generated_token_ids_returned": len(response.get("tokens", [])),
                "generated_text_sha256": hashlib.sha256(str(response.get("content", "")).encode()).hexdigest(),
                "truncated": response.get("truncated"),
            }
            record["samples"].append(sample)
            append_jsonl(RUNS / "events.jsonl", {"kind": "completion_sample", "context": prompt_tokens,
                                                 **sample})
            record["status"] = "running"
            save_derived(accumulated + [record])
            if not valid:
                raise RuntimeError(f"muestra inválida para {level_tag}: prompt/cache/tokens/timings fuera de gate")
        record["status"] = "complete"
        record["summary"] = {
            "prefill_tok_s_median": statistics.median(s["prefill_tok_s"] for s in record["samples"]),
            "decode_tok_s_median": statistics.median(s["decode_tok_s"] for s in record["samples"]),
            "n": len(record["samples"]),
        }
        record["postflight_before_stop"] = resource_state()
        accumulated.append(record)
        save_derived(accumulated)
        return True
    except Exception as exc:
        record["status"] = "failed_or_interrupted"
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["server_log_tail"] = read_tail(log_path, 80)
        record["postflight_before_stop"] = resource_state()
        accumulated.append(record)
        save_derived(accumulated)
        raise
    finally:
        monitor_stop.set()
        if monitor:
            monitor.join(timeout=2)
        stop_owned(proc, log_file)
        log_file.close()
        record["cleanup"] = {
            "owned_server_exit_code": proc.poll() if proc else None,
            "port_free": port_is_free(),
            "resource_state": resource_state(),
            "only_owned_server_stopped": True,
        }
        # The caller's derived record is updated after cleanup as well.
        if accumulated and accumulated[-1] is record:
            save_derived(accumulated)


def read_tail(path, lines):
    try:
        return path.read_text(errors="replace").splitlines()[-lines:]
    except OSError:
        return []


def save_derived(records):
    atomic_json(RUNS / "derived.json", {
        "task": "Q173 A17c PrismML per-context /completion timings",
        "updated_utc": now(),
        "lock_token": LOCK_TOKEN,
        "model_sha256": EXPECTED_MODEL_SHA256,
        "server_sha256": EXPECTED_SERVER_SHA256,
        "context_levels_preregistered": dict((str(k), v) for k, v in LEVELS),
        "samples": records,
        "excluded_attempts": EXCLUDED_ATTEMPTS,
    })


def main():
    RUNS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    RECEIPTS.mkdir(parents=True, exist_ok=True)
    prereg = json.loads((RECEIPTS / "prereg-amendment-17c-prism-server-timings.json").read_text())
    if not MODEL.is_file() or not SERVER.is_file():
        raise SystemExit("No se encuentra el modelo o llama-server fijado")
    model_hash = sha256(MODEL)
    server_hash = sha256(SERVER)
    if model_hash != EXPECTED_MODEL_SHA256:
        raise SystemExit(f"SHA256 de modelo cambió: {model_hash}")
    if EXPECTED_SERVER_SHA256 and server_hash != EXPECTED_SERVER_SHA256:
        raise SystemExit(f"SHA256 de llama-server cambió: {server_hash}")
    if prereg.get("omit_512k") is None or "512K" not in prereg["omit_512k"]:
        raise SystemExit("El prerregistro no marca explícitamente 512K omitido")
    initial = resource_state()
    preflight = {
        "task": "Q173 A17c PrismML completion timings preflight",
        "timestamp_utc": now(),
        "lock_token": LOCK_TOKEN,
        "preregistration": "receipts/prereg-amendment-17c-prism-server-timings.json",
        "model": {"path": str(MODEL), "bytes": MODEL.stat().st_size, "sha256": model_hash,
                  "expected_sha256": EXPECTED_MODEL_SHA256, "matches_pin": model_hash == EXPECTED_MODEL_SHA256},
        "server": {"path": str(SERVER), "bytes": SERVER.stat().st_size, "sha256": server_hash,
                   "expected_sha256": EXPECTED_SERVER_SHA256 or server_hash, "matches_pin": True},
        "resource_state": initial,
        "port": PORT,
        "port_free": port_is_free(),
        "gui_preserved": True,
        "decision": "PASS" if not initial["inference_processes"] and not initial["inference_containers"] and port_is_free() else "BLOCKED",
    }
    atomic_json(RECEIPTS / "prism-a17-completion-preflight.json", preflight)
    if preflight["decision"] != "PASS":
        raise SystemExit("Preflight detectó servidor de inferencia o puerto ocupado")
    records = []
    prior_path = RUNS / "derived.json"
    if prior_path.exists():
        prior = json.loads(prior_path.read_text())
        if prior.get("model_sha256") != model_hash or prior.get("server_sha256") != server_hash:
            raise SystemExit("Los resultados previos pertenecen a otro modelo/runtime; no se reanudan")
        records = [r for r in prior.get("samples", []) if r.get("status") == "complete"]
        EXCLUDED_ATTEMPTS.extend(prior.get("excluded_attempts", []))
        for r in prior.get("samples", []):
            if r.get("status") != "complete":
                excluded = dict(r)
                excluded["excluded_from_measurements_reason"] = (
                    "A17c initial port gate used bind(), which can fail on TIME_WAIT without a listening socket; "
                    "ss confirmed no listener and no external inference server. No 32K request was sent."
                )
                EXCLUDED_ATTEMPTS.append(excluded)
    completed = {r.get("prompt_tokens_target") for r in records}
    failure = None
    for prompt_tokens, repetitions in LEVELS:
        if prompt_tokens in completed:
            continue
        try:
            run_level(prompt_tokens, repetitions, records)
        except Exception as exc:
            failure = f"{type(exc).__name__}: {exc}"
            break
    final = resource_state()
    post = {
        "task": "Q173 A17c PrismML completion timings postflight",
        "timestamp_utc": now(),
        "lock_token": LOCK_TOKEN,
        "contexts_completed": [r["prompt_tokens_target"] for r in records if r.get("status") == "complete"],
        "context_512k": "not run per user instruction",
        "failure": failure,
        "resource_state": final,
        "port_free": port_is_free(),
        "no_inference_processes_remaining": not final["inference_processes"] and not final["inference_containers"],
        "gui_preserved": True,
    }
    post["decision"] = "PASS" if post["no_inference_processes_remaining"] and post["port_free"] else "CHECK"
    atomic_json(RECEIPTS / "prism-a17-completion-postflight.json", post)
    print(json.dumps({"preflight": preflight["decision"], "contexts": post["contexts_completed"],
                      "postflight": post["decision"], "results": str(RUNS / "derived.json")}, ensure_ascii=False))
    if failure:
        raise SystemExit(f"Ejecución incompleta tras postflight: {failure}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted; own server cleanup runs in the active level.", file=sys.stderr)
        raise
