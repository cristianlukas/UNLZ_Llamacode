#!/usr/bin/env python3
"""Durable, serial Q55 matched tool-quality holdout for Qwen3.8-27B MTP."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import socket
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request


TASK = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[4]
LOCK = REPO / "WORK_QUEUE.lock"
TOKEN = "d3542157-5398-49fd-9056-f896cb17dd63"
MODEL = Path("/media/cristian/HDD extra/Modelos-eval/Q47-OpenJet/Qwen3.8-27B-Q4_K_M.gguf")
MODEL_ANCHOR = REPO / "artifacts/evaluacion-modelos-llamacode/Q-20261022-VF-ITERATION-47/receipts/model-stat-anchor.json"
OPENJET = REPO / "artifacts/evaluacion-modelos-llamacode/Q-20261022-VF-ITERATION-47/work/open-jet"
BASELINE = OPENJET / "llama.cpp/build/bin/llama-server"
MK_SERVER = OPENJET / "megakernel/server/mk_server.py"
MK_LIB = OPENJET / "megakernel/libqwen38mk.so"
DRAFT_VOCAB = OPENJET / "megakernel/draft_vocab_32k.bin"
EVAL = Path("/home/cristian/.cache/codex-tool-eval-bench-v2.8.0/.venv/bin/tool-eval-bench")
EVAL_SRC = Path("/home/cristian/.cache/codex-tool-eval-bench-v2.8.0/src")
LOGS = TASK / "logs"
RUNS = TASK / "runs"
RECEIPTS = TASK / "receipts"
PROGRESS = RUNS / "progress.json"
GUARDS = RECEIPTS / "resource-guards.jsonl"
CTX = 16384
SEEDS = (43, 44, 45)
ARMS = (
    {"name": "baseline", "runtime": "llama.cpp MTP2", "draft": 2},
    {"name": "openjet_d3", "runtime": "OpenJet megakernel d3", "draft": 3},
    {"name": "openjet_d4", "runtime": "OpenJet megakernel d4", "draft": 4},
)
EXPECTED_SCENARIOS = [f"TC-{n}" for n in range(70, 98)]
EXPECTED_CHAT_KWARGS = {"chat_template_kwargs": {"reasoning_effort": "medium"}}
MIN_MEM = 24 * 1024**3
MIN_SWAP = 1 * 1024**3
MAX_GPU_TEMP = 85
MAX_FILE_BYTES = 16 * 1024 * 1024
INFERENCE_RE = re.compile(
    r"(?:^|/)(?:llama-server|ollama|vllm|sglang|aphrodite|tabbyapi)(?:\s|$)|"
    r"mk_server\.py|mlx_lm\.server|strata.{0,24}server",
    re.IGNORECASE,
)
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def atomic_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def append_jsonl(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, allow_nan=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def write_progress(progress: dict, *, stage: str | None = None) -> None:
    progress["updated_at_utc"] = utc()
    if stage:
        progress["stage"] = stage
    atomic_json(PROGRESS, progress)


def lock_record() -> dict:
    if not LOCK.is_file():
        raise RuntimeError("WORK_QUEUE.lock no existe; Q55 se detiene sin iniciar procesos")
    record = json.loads(LOCK.read_text(encoding="utf-8"))
    if record.get("token") != TOKEN or record.get("task_id") != "Q-20261023-VF-ITERATION-55":
        raise RuntimeError("WORK_QUEUE.lock ya no pertenece a Q55")
    return record


def model_stat() -> dict[str, int]:
    s = MODEL.stat()
    return {
        "device": s.st_dev, "inode": s.st_ino, "size": s.st_size,
        "mode": s.st_mode & 0o7777, "mtime_ns": s.st_mtime_ns, "ctime_ns": s.st_ctime_ns,
    }


def cgroup_dir() -> Path:
    for line in Path("/proc/self/cgroup").read_text().splitlines():
        if line.startswith("0::"):
            candidate = Path("/sys/fs/cgroup") / line.split("::", 1)[1].lstrip("/")
            if candidate.is_dir():
                return candidate
    raise RuntimeError("no hay cgroup v2 efectivo para el servicio Q55")


def memory_snapshot() -> dict[str, int]:
    values = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, _, rest = line.partition(":")
        if key in {"MemAvailable", "SwapFree"}:
            values[key] = int(rest.split()[0]) * 1024
    return values


def gpu_snapshot() -> dict:
    p = subprocess.run(
        ["nvidia-smi", "-i", "0", "--query-gpu=name,memory.total,memory.used,memory.free,temperature.gpu",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True, timeout=10, check=True,
    )
    fields = [v.strip() for v in p.stdout.strip().split(",")]
    if len(fields) != 5:
        raise RuntimeError(f"respuesta nvidia-smi inesperada: {p.stdout.strip()!r}")
    q = subprocess.run(
        ["nvidia-smi", "-i", "0", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader"],
        capture_output=True, text=True, timeout=10, check=True,
    )
    return {
        "name": fields[0], "memory_total_mib": int(fields[1]), "memory_used_mib": int(fields[2]),
        "memory_free_mib": int(fields[3]), "temperature_c": int(fields[4]),
        "compute_apps": [line.strip() for line in q.stdout.splitlines() if line.strip()],
    }


def inference_processes(exclude: set[int] | None = None) -> list[dict]:
    exclude = exclude or set()
    found = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit() or int(proc.name) in exclude:
            continue
        try:
            comm = (proc / "comm").read_text().strip()
            cmdline = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
        except (OSError, ProcessLookupError):
            continue
        if INFERENCE_RE.search(comm) or INFERENCE_RE.search(cmdline):
            found.append({"pid": int(proc.name), "comm": comm, "cmdline": cmdline[:600]})
    return found


def cgroup_properties(cg: Path) -> dict:
    expected = {
        "memory.high": 86 * 1024**3,
        "memory.max": 96 * 1024**3,
        "memory.swap.max": 1 * 1024**3,
    }
    actual = {}
    for name, want in expected.items():
        path = cg / name
        if not path.is_file():
            raise RuntimeError(f"cgroup Q55 no expone {name}")
        raw = path.read_text().strip()
        if raw == "max" or int(raw) != want:
            raise RuntimeError(f"límite Q55 {name}={raw}; se esperaba {want}")
        actual[name] = int(raw)
    actual["memory.current"] = int((cg / "memory.current").read_text().strip())
    actual["memory.events"] = parse_events(cg)
    return actual


def parse_events(cg: Path) -> dict[str, int]:
    path = cg / "memory.events"
    if not path.is_file():
        return {}
    return {k: int(v) for k, v in (line.split() for line in path.read_text().splitlines())}


def preflight(stage: str, cg: Path) -> dict:
    lock = lock_record()
    anchor = json.loads(MODEL_ANCHOR.read_text(encoding="utf-8"))
    current_stat = model_stat()
    if str(MODEL) != anchor.get("path") or current_stat != anchor.get("stat"):
        raise RuntimeError("stat del GGUF no coincide con el ancla de SHA verificado en Q47")
    for path in (BASELINE, MK_SERVER, MK_LIB, DRAFT_VOCAB, EVAL):
        if not path.is_file():
            raise RuntimeError(f"falta artefacto preregistrado: {path}")
    heads = {
        "openjet": git_head(OPENJET),
        "baseline": git_head(OPENJET / "llama.cpp"),
        "tool_eval_bench": git_head(EVAL_SRC),
    }
    expected_heads = {
        "openjet": "72ba4a7e587ed0cda1312e3384e415962eaa0db3",
        "baseline": "39eab74a05d3e68ac822b6dc6cd78c90cb985c19",
        "tool_eval_bench": "0a1ba68c7709f429298bc92417a9e003f61de4e3",
    }
    if heads != expected_heads:
        raise RuntimeError(f"revisiones de runtimes diferentes al prerregistro: {heads}")
    version = subprocess.run(
        [str(EVAL), "--version"], capture_output=True, text=True, timeout=15, check=True
    ).stdout.strip()
    if "2.8.0" not in version:
        raise RuntimeError(f"Tool-Eval diferente al prerregistro: {version!r}")
    if inference_processes():
        raise RuntimeError("hay un inference server externo activo; no se inicia ni detiene")
    memory = memory_snapshot()
    gpu = gpu_snapshot()
    if memory.get("MemAvailable", 0) < MIN_MEM:
        raise RuntimeError(f"MemAvailable menor a 24 GiB: {memory}")
    if memory.get("SwapFree", 0) < MIN_SWAP:
        raise RuntimeError(f"SwapFree menor a 1 GiB: {memory}")
    if gpu["temperature_c"] >= MAX_GPU_TEMP:
        raise RuntimeError(f"GPU0 llegó a {gpu['temperature_c']} °C (umbral {MAX_GPU_TEMP})")
    props = cgroup_properties(cg)
    return {
        "at_utc": utc(), "stage": stage, "lock": lock, "model_stat": current_stat,
        "model_sha256": anchor["sha256"], "runtime_commits": heads,
        "tool_eval_version": version,
        "artifact_sha256": {
            str(path): sha256(path) for path in (BASELINE, MK_SERVER, MK_LIB, DRAFT_VOCAB)
        },
        "memory": memory, "gpu0": gpu, "cgroup_path": str(cg), "cgroup": props,
        "external_inference_servers": [],
    }


def guard(stage: str, cg: Path, server_pid: int, progress: dict) -> dict:
    lock_record()
    others = inference_processes({server_pid} if server_pid else set())
    if others:
        raise RuntimeError("apareció un inference server externo durante Q55: " + json.dumps(others, ensure_ascii=False))
    memory = memory_snapshot()
    gpu = gpu_snapshot()
    props = cgroup_properties(cg)
    ev = props["memory.events"]
    state = {
        "at_utc": utc(), "stage": stage, "mem_available_bytes": memory.get("MemAvailable", 0),
        "swap_free_bytes": memory.get("SwapFree", 0), "gpu0": gpu,
        "server_pid": server_pid, "cgroup": props,
    }
    append_jsonl(GUARDS, state)
    if state["mem_available_bytes"] < MIN_MEM:
        raise RuntimeError("MemAvailable bajó de 24 GiB; se limpia sólo el proceso Q55")
    if state["swap_free_bytes"] < MIN_SWAP:
        raise RuntimeError("SwapFree bajó de 1 GiB; se limpia sólo el proceso Q55")
    if gpu["temperature_c"] > MAX_GPU_TEMP:
        raise RuntimeError(f"GPU0 superó {MAX_GPU_TEMP} °C ({gpu['temperature_c']} °C)")
    if ev.get("max", 0) or ev.get("oom", 0) or ev.get("oom_kill", 0) or ev.get("oom_group_kill", 0):
        raise RuntimeError("cgroup Q55 reporta max/OOM; no se repite automáticamente")
    if server_pid and not Path(f"/proc/{server_pid}").exists():
        raise RuntimeError(f"servidor Q55 PID {server_pid} terminó inesperadamente")
    write_progress(progress, stage=stage)
    return state


def choose_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def port_is_free(port: int) -> bool:
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def port_is_listening(port: int) -> bool:
    p = subprocess.run(["ss", "-ltnH"], capture_output=True, text=True, timeout=10, check=True)
    return any(re.search(rf":{port}\s", line) for line in p.stdout.splitlines())


def limit_file_size() -> None:
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_FILE_BYTES, MAX_FILE_BYTES))


def server_command(arm: dict, port: int) -> list[str]:
    common_model = ["-m", str(MODEL)]
    if arm["name"] == "baseline":
        return [
            str(BASELINE), *common_model, "--host", "127.0.0.1", "--port", str(port),
            "--parallel", "1", "--flash-attn", "on", "-ctk", "q8_0", "-ctv", "q8_0",
            "-ngl", "99", "-sm", "none", "-c", str(CTX), "--spec-type", "draft-mtp",
            "--spec-draft-n-max", "2", "--jinja",
        ]
    return [
        sys.executable, str(MK_SERVER), *common_model, "--host", "127.0.0.1", "--port", str(port),
        "-c", str(CTX), "-d", str(arm["draft"]), "--draft-vocab", str(DRAFT_VOCAB),
        "--lib", str(MK_LIB), "--kv", "q8",
    ]


def server_environment() -> dict[str, str]:
    env = os.environ.copy()
    # Do not inherit the experimental MK-prefill toggle; prior Q50 runs logged illegal CUDA access under MK_PREFILL=mk.
    env.pop("MK_PREFILL", None)
    env.update({
        "CUDA_DEVICE_ORDER": "PCI_BUS_ID", "CUDA_VISIBLE_DEVICES": "0",
        "LD_LIBRARY_PATH": str(BASELINE.parent), "HF_HUB_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1", "PYTHONNOUSERSITE": "1",
        "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost",
    })
    return env


def start_server(arm: dict, invocation: int, cg: Path, progress: dict, purpose: str):
    pre = preflight(f"{arm['name']} startup", cg)
    port = choose_port()
    if not port_is_free(port):
        raise RuntimeError(f"puerto loopback {port} ocupado antes de iniciar")
    log_path = LOGS / f"{arm['name']}-{purpose}-invocation-{invocation:02d}-server.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = log_path.open("wb")
    command = server_command(arm, port)
    proc = subprocess.Popen(
        command, cwd=TASK / "work", env=server_environment(), stdin=subprocess.DEVNULL,
        stdout=log, stderr=subprocess.STDOUT, start_new_session=True, preexec_fn=limit_file_size,
    )
    record = {
        "arm": arm["name"], "runtime": arm["runtime"], "invocation": invocation,
        "purpose": purpose, "command": command, "port": port, "server_pid": proc.pid,
        "server_log": str(log_path), "preflight": pre, "started_at_utc": utc(),
    }
    progress.setdefault("server_starts", []).append(record)
    write_progress(progress, stage=f"{arm['name']}: model loading on port {port}")
    deadline = time.monotonic() + 1800
    load_started = time.monotonic()
    next_guard = 0.0
    try:
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(f"{arm['name']} terminó al cargar (rc={proc.returncode}); ver {log_path}")
            now = time.monotonic()
            if now >= next_guard:
                state = guard(f"{arm['name']} startup", cg, proc.pid, progress)
                record["last_guard"] = state
                print(
                    f"STARTUP {arm['name']} {int(now - load_started)}s "
                    f"MemAvail={state['mem_available_bytes'] // 1024**3}GiB "
                    f"GPU0={state['gpu0']['memory_free_mib']}MiB/{state['gpu0']['temperature_c']}C",
                    flush=True,
                )
                next_guard = now + 30
            try:
                body = http_json(f"http://127.0.0.1:{port}/health", timeout=2)
                if body.get("status") == "ok":
                    record.update(healthy=True, ready_at_utc=utc())
                    write_progress(progress, stage=f"{arm['name']}: ready")
                    return proc, log, port, record
            except Exception:
                pass
            time.sleep(1)
        raise TimeoutError(f"{arm['name']} no respondió /health en 30 min; ver {log_path}")
    except Exception:
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=30)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    pass
        log.flush()
        log.close()
        raise


def http_json(url: str, body: dict | None = None, timeout: float = 10) -> dict:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"} if data else {})
    try:
        with HTTP.open(req, timeout=timeout) as response:
            raw = response.read()
            if response.status != 200:
                raise RuntimeError(f"HTTP {response.status}: {raw[:1000]!r}")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        detail = exc.read(1000).decode(errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {url}: {detail}") from exc


def run_tool_smoke(arm: dict, port: int) -> dict:
    base = f"http://127.0.0.1:{port}/v1"
    models = http_json(base + "/models", timeout=10)
    if not models.get("data"):
        raise RuntimeError("GET /v1/models no devolvió modelos")
    payload = {
        "model": "qwen3.8-27b-q4km",
        "messages": [
            {"role": "system", "content": "Use get_weather for weather questions and pass the requested location."},
            {"role": "user", "content": "What is the current weather in Buenos Aires, Argentina?"},
        ],
        "tools": [{
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather for a named location.",
                "parameters": {
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                    "required": ["location"],
                    "additionalProperties": False,
                },
            },
        }],
        "tool_choice": "auto", "temperature": 0.6, "top_p": 0.95,
        "top_k": 20, "min_p": 0.0, "repetition_penalty": 1.0, "seed": 42,
        "max_tokens": 1024, "stream": False, **EXPECTED_CHAT_KWARGS,
    }
    started = time.monotonic()
    response = http_json(base + "/chat/completions", payload, timeout=180)
    elapsed = (time.monotonic() - started) * 1000
    choices = response.get("choices") or []
    message = choices[0].get("message", {}) if choices else {}
    calls = message.get("tool_calls") or []
    parsed = []
    for call in calls:
        fn = call.get("function", {})
        raw_arguments = fn.get("arguments") or {}
        try:
            args = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
        except (json.JSONDecodeError, TypeError):
            args = None
        parsed.append({
            "name": fn.get("name"), "arguments": args,
            "raw_arguments": raw_arguments[:2000] if isinstance(raw_arguments, str) else raw_arguments,
        })
    valid = any(
        item["name"] == "get_weather" and isinstance(item["arguments"], dict)
        and isinstance(item["arguments"].get("location"), str)
        and "buenos aires" in item["arguments"]["location"].casefold()
        for item in parsed
    )
    return {
        "status": "passed" if valid else "failed", "arm": arm["name"],
        "runtime": arm["runtime"], "at_utc": utc(), "elapsed_ms": round(elapsed, 2),
        "model_ids": [m.get("id") for m in models.get("data", [])],
        "http_status": 200, "structured_tool_calls": parsed,
        "tool_contract_valid": valid, "finish_reason": choices[0].get("finish_reason") if choices else None,
        "max_tokens": payload["max_tokens"], "usage": response.get("usage"),
        "timings": response.get("timings"), "reasoning_effort_payload": EXPECTED_CHAT_KWARGS,
    }


def stop_server(proc: subprocess.Popen, log, arm: str, port: int) -> dict:
    signals = []
    if proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            signals.append("SIGTERM")
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
                signals.append("SIGKILL")
            except ProcessLookupError:
                pass
            proc.wait(timeout=10)
    rc = proc.poll()
    if not log.closed:
        log.flush()
        log.close()
    deadline = time.monotonic() + 10
    port_free = False
    while time.monotonic() < deadline:
        if proc.pid not in {p["pid"] for p in inference_processes()} and rc is not None and not port_is_listening(port):
            port_free = True
            break
        time.sleep(0.25)
    if not port_free:
        raise RuntimeError(f"cleanup de {arm} no quedó confirmado; se detiene Q55")
    return {"arm": arm, "stopped_at_utc": utc(), "exit_code": rc, "signals": signals, "process_and_port_absent": True}


def terminate_process_group(proc: subprocess.Popen, grace: float = 20) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=10)


def run_monitored(command: list[str], log_path: Path, arm: dict, seed: int,
                  cwd: Path, cg: Path, server_pid: int, progress: dict) -> tuple[int, dict]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    next_guard = started
    with log_path.open("wb") as out:
        proc = subprocess.Popen(
            command, cwd=cwd, env=server_environment(), stdin=subprocess.DEVNULL,
            stdout=out, stderr=subprocess.STDOUT, start_new_session=True, preexec_fn=limit_file_size,
        )
        progress.setdefault("tool_eval_processes", []).append({
            "arm": arm["name"], "seed": seed, "pid": proc.pid, "command": command,
            "log": str(log_path), "started_at_utc": utc(),
        })
        write_progress(progress, stage=f"{arm['name']} seed {seed}: running")
        try:
            while proc.poll() is None:
                now = time.monotonic()
                if now >= next_guard:
                    state = guard(f"{arm['name']} seed {seed}", cg, server_pid, progress)
                    elapsed = int(now - started)
                    print(
                        f"RUN {arm['name']} seed={seed} {elapsed}s "
                        f"MemAvail={state['mem_available_bytes'] // 1024**3}GiB "
                        f"GPU0={state['gpu0']['memory_free_mib']}MiB/{state['gpu0']['temperature_c']}C",
                        flush=True,
                    )
                    next_guard = now + 30
                if now - started > 5400:
                    raise TimeoutError(f"{arm['name']} seed {seed} excedió 90 minutos; no se reintenta")
                time.sleep(2)
        except Exception:
            terminate_process_group(proc)
            raise
        return int(proc.returncode), {
            "started_at_utc": progress["tool_eval_processes"][-1]["started_at_utc"],
            "ended_at_utc": utc(), "duration_seconds": round(time.monotonic() - started, 2),
            "log_path": str(log_path), "log_sha256": sha256(log_path),
        }


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git_head(path: Path) -> str:
    p = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=10, check=True,
    )
    return p.stdout.strip()


def validate_seed(json_path: Path, exit_code: int, seed: int) -> dict:
    if exit_code != 0:
        return {"valid": False, "reason": f"tool-eval-bench exit {exit_code}"}
    if not json_path.is_file():
        return {"valid": False, "reason": "faltó el JSON final del seed"}
    try:
        raw = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"valid": False, "reason": f"JSON inválido: {exc}"}
    scores = raw.get("scores") or {}
    scenarios = scores.get("scenario_results") or []
    ids = [item.get("scenario_id") for item in scenarios]
    if raw.get("status") not in {"completed", "complete", "success"}:
        return {"valid": False, "reason": f"status suite inesperado: {raw.get('status')!r}"}
    if raw.get("tool_eval_bench_version") != "2.8.0":
        return {"valid": False, "reason": f"versión suite inesperada: {raw.get('tool_eval_bench_version')!r}"}
    if len(scenarios) != 28 or ids != EXPECTED_SCENARIOS:
        return {"valid": False, "reason": f"esperaba 28 escenarios ordenados; recibí {len(scenarios)}"}
    if any(item.get("status") not in {"pass", "partial", "fail"} for item in scenarios):
        return {"valid": False, "reason": "hay escenario con status no puntuable"}
    if any(item.get("error") for item in scenarios):
        return {"valid": False, "reason": "la suite registró un error de API/parser por escenario"}
    config = raw.get("config") or {}
    params = config.get("extra_params") or {}
    if config.get("seed") != seed or config.get("backend") != "llamacpp" or config.get("scenario_count") != 28:
        return {"valid": False, "reason": "configuración/seed/backend no coincide con el preregistro"}
    if params.get("chat_template_kwargs") != EXPECTED_CHAT_KWARGS["chat_template_kwargs"]:
        return {"valid": False, "reason": "reasoning_effort no quedó registrado en chat_template_kwargs"}
    if params.get("top_p") != 0.95 or params.get("top_k") != 20 or params.get("min_p") != 0.0:
        return {"valid": False, "reason": "sampling registrado no coincide con el preregistro"}
    points = sum(int(item.get("points", 0)) for item in scenarios)
    max_points = int(scores.get("max_points", 0))
    if points != int(scores.get("total_points", -1)) or max_points <= 0:
        return {"valid": False, "reason": "auditoría independiente de puntos no coincide"}
    independent_score = round(points * 100 / max_points)
    score = int(scores.get("final_score", -1))
    if abs(score - independent_score) > 1 or raw.get("final_score") != score:
        return {"valid": False, "reason": "auditoría independiente del puntaje no coincide"}
    by_id = {item["scenario_id"]: item for item in scenarios}
    critical = {key: by_id[key]["status"] for key in ("TC-74", "TC-84", "TC-92")}
    warnings = raw.get("safety_warnings") or scores.get("safety_warnings") or []
    critical_warnings = [
        warning for warning in warnings if re.search(r"\bTC-(?:74|84|92)\b", str(warning))
    ]
    api_errors = []
    for item in scenarios:
        raw_log = item.get("raw_log") or ""
        if re.search(r"(?:HTTP\s+[45]\d\d|API request failed|response parse failed|invalid tool_calls payload)", raw_log, re.I):
            api_errors.append(item["scenario_id"])
    if api_errors:
        return {"valid": False, "reason": "errores API/parser en escenarios: " + ", ".join(api_errors)}
    return {
        "valid": True, "score": score, "points": points, "max_points": max_points,
        "rating": raw.get("rating"), "scenario_count": len(scenarios),
        "scenario_status_counts": {
            state: sum(item.get("status") == state for item in scenarios) for state in ("pass", "partial", "fail")
        },
        "critical_scenarios": critical, "critical_all_pass": all(v == "pass" for v in critical.values()),
        "critical_safety_warnings": critical_warnings,
        "safety_warnings": warnings, "run_id": raw.get("run_id"),
        "json_sha256": sha256(json_path),
    }


def tool_eval_command(arm: dict, port: int, seed: int, json_path: Path, report_dir: Path) -> list[str]:
    return [
        str(EVAL), "run", "--hardmode-only", "--base-url", f"http://127.0.0.1:{port}/v1",
        "--model", "qwen3.8-27b-q4km", "--backend", "llamacpp", "--format", "openai",
        "--temperature", "0.6", "--top-p", "0.95", "--top-k", "20",
        "--min-p", "0", "--repeat-penalty", "1", "--seed", str(seed),
        "--variant-seed", "20261010", "--timeout", "120", "--max-turns", "8",
        "--parallel", "1", "--context-size", str(CTX),
        "--backend-kwargs", json.dumps(EXPECTED_CHAT_KWARGS, separators=(",", ":")),
        "--label", f"Q55-{arm['name']}-seed-{seed}",
        "--json-file", str(json_path), "--output-dir", str(report_dir), "--no-live",
    ]


def save_smoke(progress: dict, arm: dict, result: dict, guard_state: dict | None) -> None:
    record = {
        **result, "resource_guard_after": guard_state,
    }
    progress.setdefault("smoke_attempts", []).append(record)
    progress.setdefault("smokes", {})[arm["name"]] = record
    write_progress(progress, stage=f"{arm['name']} tool-call smoke {result['status']}")
    atomic_json(RECEIPTS / f"smoke-{arm['name']}-invocation-{progress['invocation']:02d}.json", record)


def aggregate(progress: dict) -> dict:
    summary = {"at_utc": utc(), "arms": {}, "decision": {}}
    for arm in ARMS:
        name = arm["name"]
        results = progress.get("seeds", {}).get(name, {})
        valid = [results[str(seed)] for seed in SEEDS if str(seed) in results and results[str(seed)].get("valid")]
        summary["arms"][name] = {
            "runtime": arm["runtime"], "valid_seed_count": len(valid),
            "scores": {str(seed): results[str(seed)].get("score") for seed in SEEDS if str(seed) in results},
            "mean_score": statistics.mean(x["score"] for x in valid) if valid else None,
            "critical_scenarios": {str(seed): results[str(seed)].get("critical_scenarios") for seed in SEEDS if str(seed) in results},
            "critical_safety_warnings": {str(seed): results[str(seed)].get("critical_safety_warnings") for seed in SEEDS if str(seed) in results},
            "safety_warnings": {str(seed): results[str(seed)].get("safety_warnings") for seed in SEEDS if str(seed) in results},
        }
    baseline = summary["arms"]["baseline"]
    candidates = {}
    for name in ("openjet_d3", "openjet_d4"):
        arm_summary = summary["arms"][name]
        paired = []
        for seed in SEEDS:
            left = progress.get("seeds", {}).get(name, {}).get(str(seed), {})
            right = progress.get("seeds", {}).get("baseline", {}).get(str(seed), {})
            if left.get("valid") and right.get("valid"):
                paired.append({"seed": seed, "delta_points": left["score"] - right["score"]})
        critical_pass = (
            arm_summary["valid_seed_count"] == 3
            and all(
                progress["seeds"][name][str(seed)]["critical_all_pass"]
                and not progress["seeds"][name][str(seed)].get("critical_safety_warnings")
                for seed in SEEDS
            )
        )
        mean_delta = None
        if arm_summary["mean_score"] is not None and baseline["mean_score"] is not None:
            mean_delta = round(arm_summary["mean_score"] - baseline["mean_score"], 3)
        candidates[name] = {
            "paired_deltas": paired, "mean_delta_points": mean_delta,
            "within_noninferiority_mean": mean_delta is not None and mean_delta >= -3,
            "within_noninferiority_in_at_least_two_pairs": sum(x["delta_points"] >= -3 for x in paired) >= 2,
            "critical_scenarios_pass_all_seeds": critical_pass,
            "tool_smoke_passed": progress.get("smokes", {}).get(name, {}).get("status") == "passed",
        }
    summary["decision"]["candidates"] = candidates
    summary["decision"]["adoption_eligible"] = {
        name: (
            summary["arms"]["baseline"]["valid_seed_count"] == 3
            and summary["arms"][name]["valid_seed_count"] == 3
            and fields["within_noninferiority_mean"]
            and fields["within_noninferiority_in_at_least_two_pairs"]
            and fields["critical_scenarios_pass_all_seeds"]
            and fields["tool_smoke_passed"]
        )
        for name, fields in candidates.items()
    }
    summary["decision"]["adoption_requires_separate_agpl_review"] = True
    return summary


def import_q54_seed43(progress: dict) -> None:
    """Reuse only the exact, technically valid baseline seed43 from Q54."""
    q54 = REPO / "artifacts/evaluacion-modelos-llamacode/Q-20261023-VF-ITERATION-54"
    source_json = q54 / "runs/baseline-seed43.json"
    source_receipt = json.loads((q54 / "receipts/baseline-seed43-result.json").read_text(encoding="utf-8"))
    source_prereg = json.loads((q54 / "receipts/preregistration.json").read_text(encoding="utf-8"))
    if source_receipt.get("task_id") != "Q-20261023-VF-ITERATION-54" or source_receipt.get("seed") != 43 or source_receipt.get("status") != "valid_seed":
        raise RuntimeError("Q54 seed43 no es un resultado terminal válido; detener Q55")
    if source_prereg.get("baseline", {}).get("model_sha256") != "7e78da5d7e3ae28d178121f58646953305f3e5bd3cb46f4a75584e8b6c6fe169":
        raise RuntimeError("Q54 modelo no coincide con el artefacto preregistrado")
    if source_prereg.get("baseline", {}).get("baseline_commit") != "39eab74a05d3e68ac822b6dc6cd78c90cb985c19" or source_prereg.get("baseline", {}).get("tool_eval_commit") != "0a1ba68c7709f429298bc92417a9e003f61de4e3":
        raise RuntimeError("Q54 revisión runtime/harness distinta; no reutilizar seed43")
    if not source_json.is_file() or sha256(source_json) != source_receipt.get("json_sha256"):
        raise RuntimeError("Q54 JSON de seed43 no coincide con su SHA-256")
    validation = validate_seed(source_json, 0, 43)
    if not validation.get("valid") or validation.get("json_sha256") != source_receipt.get("json_sha256"):
        raise RuntimeError("revalidación independiente de Q54 seed43 falló")
    expected = progress.setdefault("seeds", {}).setdefault("baseline", {}).get("43")
    if expected:
        if not expected.get("valid") or expected.get("json_sha256") != validation["json_sha256"]:
            raise RuntimeError("checkpoint baseline43 no coincide con el resultado Q54")
        return
    result = {
        "valid": True, "arm": "baseline", "runtime": "llama.cpp MTP2", "seed": 43,
        "exit_code": 0, "json_path": str(source_json), "json_sha256": validation["json_sha256"],
        "tool_eval_log": source_receipt["timing"]["log_path"], "timing": source_receipt["timing"],
        "validation": validation,
    }
    result.update({key: validation[key] for key in (
        "score", "points", "max_points", "rating", "scenario_count",
        "scenario_status_counts", "critical_scenarios", "critical_all_pass",
        "critical_safety_warnings", "safety_warnings", "run_id",
    )})
    progress["seeds"]["baseline"]["43"] = result
    atomic_json(RECEIPTS / "baseline-seed43-import.json", {
        "task_id": "Q-20261023-VF-ITERATION-55", "source_task_id": "Q-20261023-VF-ITERATION-54",
        "source_lock_token": source_receipt.get("lock_token"), "source_json": str(source_json),
        "source_json_sha256": validation["json_sha256"], "revalidation": validation,
        "reused_as": "baseline seed43 only; no duplicate inference",
    })
    write_progress(progress, stage="Q54 baseline seed43 imported and independently revalidated")


def run(*, resume: bool) -> int:
    TASK.joinpath("work").mkdir(parents=True, exist_ok=True)
    for path in (LOGS, RUNS, RECEIPTS):
        path.mkdir(parents=True, exist_ok=True)
    cg = cgroup_dir()
    cgroup_properties(cg)
    if PROGRESS.is_file():
        progress = json.loads(PROGRESS.read_text(encoding="utf-8"))
        if progress.get("status") in {"completed", "seed_invalid"}:
            print(f"Q55 ya tiene estado terminal: {progress['status']}; inspeccionar antes de otra corrida.", flush=True)
            return 0 if progress["status"] == "completed" else 2
        if progress.get("status") in {"running", "blocked", "feasibility_failed"} and not resume:
            raise RuntimeError("hay checkpoint fallido/incompleto; reanudar requiere enmienda revisada y --resume")
        if progress.get("status") == "feasibility_failed":
            progress.setdefault("prior_feasibility_failures", []).append({
                "at_utc": utc(), "failure": progress.get("failure"),
                "smokes": progress.get("smokes", {}),
            })
    else:
        progress = {
            "task_id": "Q-20261023-VF-ITERATION-55", "lock_token": TOKEN,
            "status": "running", "created_at_utc": utc(), "smokes": {},
            "seeds": {}, "server_starts": [], "tool_eval_processes": [],
        }
    import_q54_seed43(progress)
    progress["status"] = "running"
    progress["invocation"] = int(progress.get("invocation", 0)) + 1
    invocation = progress["invocation"]
    progress.setdefault("invocation_history", []).append({
        "invocation": invocation, "started_at_utc": utc(), "resumed": resume,
        "cgroup_path": str(cg), "cgroup": cgroup_properties(cg),
    })
    write_progress(progress, stage="preflight")
    pre = preflight("Q55 controller start", cg)
    atomic_json(RECEIPTS / "preflight.json", pre)
    print(f"Q55 preflight PASS invocation={invocation} cgroup={cg}", flush=True)

    # All three runtime smokes must pass before the first quality suite starts.
    for arm in ARMS:
        previous = progress.get("smokes", {}).get(arm["name"])
        if previous and previous.get("status") == "passed":
            continue
        server = log = None
        try:
            server, log, port, start_record = start_server(arm, invocation, cg, progress, "smoke")
            smoke = run_tool_smoke(arm, port)
            state = guard(f"{arm['name']} smoke complete", cg, server.pid, progress)
            smoke.update(port=port, server_start=start_record, response_validated=True)
            save_smoke(progress, arm, smoke, state)
            cleanup = stop_server(server, log, arm["name"], port)
            progress.setdefault("cleanup", []).append(cleanup)
            write_progress(progress, stage=f"{arm['name']} smoke cleanup confirmed")
            if smoke["status"] != "passed":
                progress["status"] = "feasibility_failed"
                progress["failure"] = f"{arm['name']} no devolvió get_weather estructurado válido"
                write_progress(progress, stage="feasibility gate failed")
                atomic_json(RECEIPTS / "feasibility-gate.json", {
                    "status": "failed", "failure": progress["failure"],
                    "smokes": progress["smokes"], "cleanup": cleanup,
                })
                return 2
            print(f"SMOKE {arm['name']} PASS tool_calls={smoke['structured_tool_calls']}", flush=True)
        except Exception as exc:
            if server is not None and log is not None:
                try:
                    cleanup = stop_server(server, log, arm["name"], port)
                    progress.setdefault("cleanup", []).append(cleanup)
                except Exception as cleanup_error:
                    progress.setdefault("cleanup_errors", []).append(str(cleanup_error))
            progress["status"] = "feasibility_failed"
            progress["failure"] = f"{arm['name']} smoke/startup: {type(exc).__name__}: {exc}"
            write_progress(progress, stage="feasibility gate failed")
            atomic_json(RECEIPTS / "feasibility-gate.json", {
                "status": "failed", "failure": progress["failure"],
                "smokes": progress.get("smokes", {}), "cleanup": progress.get("cleanup", []),
            })
            raise
    atomic_json(RECEIPTS / "feasibility-gate.json", {
        "status": "passed", "smokes": progress["smokes"], "completed_at_utc": utc(),
    })

    # Quality holdout: one server load per arm, seeds in preregistered order.
    for arm in ARMS:
        name = arm["name"]
        results = progress.setdefault("seeds", {}).setdefault(name, {})
        missing = [seed for seed in SEEDS if str(seed) not in results]
        invalid = [seed for seed in SEEDS if str(seed) in results and not results[str(seed)].get("valid")]
        if invalid:
            progress["status"] = "seed_invalid"
            progress["failure"] = f"{name} has invalid prior seed(s) {invalid}; review/registration required before rerun"
            write_progress(progress, stage="invalid seed requires review")
            return 2
        if not missing:
            continue
        server = log = None
        try:
            server, log, port, start_record = start_server(arm, invocation, cg, progress, "quality")
            progress.setdefault("quality_servers", []).append(start_record | {"port": port})
            for seed in missing:
                guard(f"{name} seed {seed} preflight", cg, server.pid, progress)
                output = RUNS / name / f"invocation-{invocation:02d}" / f"seed-{seed}.json"
                reports = RUNS / name / f"invocation-{invocation:02d}" / f"reports-seed-{seed}"
                work = TASK / "work" / f"tool-eval-{name}-seed-{seed}-invocation-{invocation:02d}"
                work.mkdir(parents=True, exist_ok=True)
                output.parent.mkdir(parents=True, exist_ok=True)
                log_path = LOGS / f"{name}-invocation-{invocation:02d}-seed-{seed}-tool-eval.log"
                command = tool_eval_command(arm, port, seed, output, reports)
                progress.setdefault("seed_attempts", []).append({
                    "arm": name, "seed": seed, "invocation": invocation,
                    "started_at_utc": utc(), "command": command, "json": str(output),
                    "log": str(log_path), "status": "running",
                })
                write_progress(progress, stage=f"{name} seed {seed}: starting")
                rc, timing = run_monitored(command, log_path, arm, seed, work, cg, server.pid, progress)
                validation = validate_seed(output, rc, seed)
                result = {
                    "valid": validation["valid"], "arm": name, "runtime": arm["runtime"], "seed": seed,
                    "exit_code": rc, "json_path": str(output), "json_sha256": sha256(output) if output.is_file() else None,
                    "tool_eval_log": str(log_path), "timing": timing, "validation": validation,
                }
                if validation["valid"]:
                    result.update({k: validation[k] for k in (
                        "score", "points", "max_points", "rating", "scenario_count",
                        "scenario_status_counts", "critical_scenarios", "critical_all_pass",
                        "critical_safety_warnings", "safety_warnings", "run_id",
                    )})
                results[str(seed)] = result
                attempt = progress["seed_attempts"][-1]
                attempt.update(status="valid" if validation["valid"] else "invalid",
                               completed_at_utc=utc(), exit_code=rc, validation=validation)
                atomic_json(RECEIPTS / f"seed-{name}-{seed}-invocation-{invocation:02d}.json", result)
                write_progress(progress, stage=f"{name} seed {seed}: {'valid' if validation['valid'] else 'invalid'}")
                if not validation["valid"]:
                    progress["status"] = "seed_invalid"
                    progress["failure"] = f"{name} seed {seed}: {validation['reason']}"
                    write_progress(progress, stage="invalid seed; stop without retry")
                    return 2
                print(
                    f"SEED {name} {seed} PASS score={result['score']} "
                    f"critical={result['critical_scenarios']} warnings={len(result['safety_warnings'])}",
                    flush=True,
                )
            cleanup = stop_server(server, log, name, port)
            progress.setdefault("cleanup", []).append(cleanup)
            write_progress(progress, stage=f"{name} three-seed cleanup confirmed")
        except Exception as exc:
            if server is not None and log is not None:
                try:
                    cleanup = stop_server(server, log, name, port)
                    progress.setdefault("cleanup", []).append(cleanup)
                except Exception as cleanup_error:
                    progress.setdefault("cleanup_errors", []).append(str(cleanup_error))
            progress["status"] = "blocked"
            progress["failure"] = f"{name}: {type(exc).__name__}: {exc}"
            write_progress(progress, stage="blocked; preserve checkpoint")
            raise

    summary = aggregate(progress)
    atomic_json(RECEIPTS / "decision-audit.json", summary)
    progress["status"] = "completed"
    progress["summary"] = summary
    progress["completed_at_utc"] = utc()
    write_progress(progress, stage="all seeds complete")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true", help="continue an interrupted invocation from durable checkpoints")
    args = parser.parse_args()
    try:
        return run(resume=args.resume)
    except Exception as exc:
        try:
            if PROGRESS.is_file():
                progress = json.loads(PROGRESS.read_text(encoding="utf-8"))
                if progress.get("status") == "running":
                    progress["status"] = "blocked"
                    progress["failure"] = f"{type(exc).__name__}: {exc}"
                    write_progress(progress, stage="blocked; preserve checkpoint")
        except Exception:
            pass
        print(f"Q55 BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
