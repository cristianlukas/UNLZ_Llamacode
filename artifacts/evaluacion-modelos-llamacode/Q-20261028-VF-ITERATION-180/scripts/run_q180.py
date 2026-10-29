#!/usr/bin/env python3
"""Q180: isolated Qwen3.6 dual-3090 Tool-Eval/context/startup experiment."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
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
DROOT = pathlib.Path("/media/cristian/Disco local/Modelos-eval/Q-20261028-VF-ITERATION-180")
MODEL = DROOT / "models/Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf"
TOKENIZER = DROOT / "tokenizer"
RUNTIME_SRC = DROOT / "llama.cpp"
SERVER_BIN = DROOT / "llama-build-cu128/bin/llama-server"
TOOL = pathlib.Path("/home/cristian/.cache/codex-tool-eval-bench-v2.8.0/.venv/bin/tool-eval-bench")
BENCHY = pathlib.Path("/home/cristian/.cache/q173-llama-benchy-0.4.0/bin/llama-benchy")
HOST, PORT = "127.0.0.1", 18481
MODEL_SHA = "55983c5a75a1ab969824077b3bb3de4146e82a9234072b48ad4e8f92ad3fe9f1"
RUNTIME_COMMIT = "2e0d86bebc210947680e8f0d67daa79f3260c106"
TOOL_SHA = "31e3c8f5fa9140738cde4e1cecc909f5335cf928a90fbdd062ec7935e0526472"
BENCHY_SHA = "e8a892fe937d5ae1b6a43c31e8cb286ce4774f70396f62ab71008c9ddb0a01a1"
MIN_DISK_BYTES, MIN_AVAILABLE_KIB = 55_000_000_000, 32 * 1024 * 1024
STARTUP_TIMEOUT_S, MONITOR_S = 1200, 15
RUNS, LOGS, RECEIPTS = ART / "runs", ART / "logs", ART / "receipts"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: pathlib.Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def sha(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def check_lock() -> None:
    data = json.loads((REPO / "WORK_QUEUE.lock").read_text(encoding="utf-8"))
    if data.get("token") != TOKEN:
        raise RuntimeError("WORK_QUEUE.lock cambió de dueño; se detiene Q180")


def mem_available_kib() -> int:
    return next(int(x.split()[1]) for x in pathlib.Path("/proc/meminfo").read_text().splitlines()
                if x.startswith("MemAvailable:"))


def gpu_state() -> dict:
    q = subprocess.run(["nvidia-smi", "--query-gpu=index,uuid,name,memory.used,memory.total,utilization.gpu",
                        "--format=csv,noheader,nounits"], text=True, capture_output=True, timeout=10)
    if q.returncode:
        raise RuntimeError("nvidia-smi GPU query falló: " + q.stderr.strip())
    gpus, by_uuid = {}, {}
    for row in q.stdout.splitlines():
        idx, uuid, name, used, total, util = [v.strip() for v in row.split(",")]
        idx = int(idx)
        gpus[idx] = {"uuid": uuid, "name": name, "used_mib": int(used),
                     "total_mib": int(total), "util_percent": int(util)}
        by_uuid[uuid] = idx
    apps = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,gpu_uuid,used_gpu_memory",
                          "--format=csv,noheader,nounits"], text=True, capture_output=True, timeout=10)
    compute = {0: [], 1: []}
    if apps.returncode == 0:
        for row in apps.stdout.splitlines():
            cols = [v.strip() for v in row.split(",")]
            if len(cols) >= 3 and by_uuid.get(cols[1]) in compute:
                compute[by_uuid[cols[1]]].append({"pid": int(cols[0]), "used_mib": int(cols[2])})
    return {"timestamp_utc": utc(), "mem_available_kib": mem_available_kib(),
            "memory_psi": pathlib.Path("/proc/pressure/memory").read_text(),
            "gpus": gpus, "compute_by_gpu": compute}


def is_inference_process(comm: str, argv: list[str]) -> bool:
    exact = {"llama-server", "llama.cpp", "ninfer-serve", "dsx-server", "strata", "ollama",
             "vllm", "aphrodite-engine", "koboldcpp", "lmstudio", "lm-studio"}
    comm = comm.lower()
    if comm in exact:
        return True
    if not argv:
        return False
    executable = pathlib.Path(argv[0]).name.lower()
    if executable in exact:
        return True

    # Python-based inference servers are identified by their module/script,
    # never by arbitrary shell text that happens to mention a server binary.
    if executable.startswith(("python", "pypy")):
        for i, arg in enumerate(argv[:-1]):
            if arg in {"-m", "--module"}:
                module = argv[i + 1].lower()
                if module.startswith(("vllm.", "aphrodite", "exllama", "sglang.", "ninfer", "dsx.")):
                    return True
        script = pathlib.Path(argv[1]).as_posix().lower() if len(argv) > 1 else ""
        if any(marker in script for marker in ("/vllm/", "/aphrodite/", "/exllama", "/sglang/")):
            return True
    return False


def inference_processes() -> list[dict]:
    ignore = {os.getpid()}
    parent = os.getpid()
    while parent > 1:
        try:
            stat = pathlib.Path(f"/proc/{parent}/stat").read_text()
            parent = int(stat[stat.rfind(")") + 2:].split()[1])
        except (OSError, ValueError, IndexError):
            break
        ignore.add(parent)
    found = []
    for p in pathlib.Path("/proc").iterdir():
        if not p.name.isdigit() or int(p.name) in ignore:
            continue
        try:
            comm = (p / "comm").read_text().strip().lower()
            argv = [arg.decode(errors="replace") for arg in (p / "cmdline").read_bytes().split(b"\0") if arg]
        except OSError:
            continue
        if is_inference_process(comm, argv):
            found.append({"pid": int(p.name), "comm": comm, "cmdline": " ".join(argv)[:1000]})
    return found


def ensure_no_foreign_server(owned_pid: int | None = None) -> None:
    check_lock()
    foreign = [x for x in inference_processes() if x["pid"] != owned_pid]
    if foreign:
        raise RuntimeError("Inference server ajeno detectado; no se lo detiene: " +
                           json.dumps(foreign, ensure_ascii=False))


def port_free() -> bool:
    with socket.socket() as s:
        return s.connect_ex((HOST, PORT)) != 0


def preflight() -> dict:
    check_lock()
    prereg = json.loads((RECEIPTS / "preregistration.json").read_text(encoding="utf-8"))
    runner_expected = prereg.get("runner", {}).get("sha256")
    tokenizer_expected = prereg.get("tokenizer", {}).get("tokenizer_json_sha256")
    tokenizer_config_expected = prereg.get("tokenizer", {}).get("tokenizer_config_sha256")
    runtime_expected = prereg.get("runtime", {}).get("server_sha256")
    if not runner_expected or sha(pathlib.Path(__file__)) != runner_expected:
        raise RuntimeError("SHA del runner Q180 no coincide con el prerregistro")
    if not tokenizer_expected or sha(TOKENIZER / "tokenizer.json") != tokenizer_expected:
        raise RuntimeError("Tokenizador exacto ausente o SHA mismatch")
    if not tokenizer_config_expected or sha(TOKENIZER / "tokenizer_config.json") != tokenizer_config_expected:
        raise RuntimeError("tokenizer_config exacto ausente o SHA mismatch")
    if not MODEL.is_file() or MODEL.stat().st_size != 22_853_663_008 or sha(MODEL) != MODEL_SHA:
        raise RuntimeError("GGUF Qwen3.6 falta, tiene tamaño distinto o SHA mismatch")
    if (not SERVER_BIN.is_file() or not TOOL.is_file() or not BENCHY.is_file() or
            not (TOKENIZER / "tokenizer.json").is_file()):
        raise RuntimeError("Falta runtime, tokenizer o benchmark fijado")
    if not runtime_expected or sha(SERVER_BIN) != runtime_expected:
        raise RuntimeError("llama-server no coincide con el binario fijado tras el build")
    if sha(TOOL) != TOOL_SHA or sha(BENCHY) != BENCHY_SHA:
        raise RuntimeError("SHA mismatch en Tool-Eval o llama-benchy")
    commit = subprocess.run(["git", "-C", str(RUNTIME_SRC), "rev-parse", "HEAD"],
                            text=True, capture_output=True, check=True).stdout.strip()
    if commit != RUNTIME_COMMIT:
        raise RuntimeError(f"llama.cpp commit inesperado: {commit}")
    v = subprocess.run([str(SERVER_BIN), "--version"], text=True, capture_output=True, timeout=30)
    if v.returncode:
        raise RuntimeError("llama-server --version falló: " + v.stderr[-1000:])
    free = os.statvfs(DROOT).f_bavail * os.statvfs(DROOT).f_frsize
    state = gpu_state()
    if free < MIN_DISK_BYTES:
        raise RuntimeError(f"D libre <55 GB: {free} bytes")
    if state["mem_available_kib"] < MIN_AVAILABLE_KIB:
        raise RuntimeError("MemAvailable <32 GiB")
    for idx in (0, 1):
        g = state["gpus"].get(idx, {})
        if "RTX 3090" not in g.get("name", ""):
            raise RuntimeError(f"GPU{idx} no es RTX 3090 visible")
    ensure_no_foreign_server()
    if not port_free():
        raise RuntimeError(f"127.0.0.1:{PORT} está ocupado")
    if any(state["compute_by_gpu"][idx] for idx in (0, 1)):
        raise RuntimeError("Hay procesos CUDA de cómputo antes de iniciar; no se detienen procesos ajenos")
    return {"decision": "PASS", "timestamp_utc": utc(), "lock_token": TOKEN,
            "model_sha256": MODEL_SHA, "llama_cpp_commit": commit,
            "server_version": v.stdout.strip(), "tool_sha256": TOOL_SHA, "benchy_sha256": BENCHY_SHA,
            "D_free_bytes": free, "baseline": state, "inference_servers": [], "port_free": True}


def server_argv() -> list[str]:
    return [str(SERVER_BIN), "--model", str(MODEL), "--ctx-size", "262144",
            "--n-gpu-layers", "999", "--split-mode", "layer", "--tensor-split", "1,1",
            "--parallel", "1", "--flash-attn", "on", "--jinja", "--reasoning-effort", "medium", "--host", HOST,
            "--port", str(PORT), "--batch-size", "2048",
            "--ubatch-size", "512", "--temp", "0.6", "--top-p", "0.95", "--top-k", "20",
            "--min-p", "0.0", "--repeat-penalty", "1.0", "--presence-penalty", "0.0"]


def get_json(url: str, timeout: float = 5) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def start_server() -> tuple[subprocess.Popen, dict]:
    global p_server
    check_lock()
    ensure_no_foreign_server()
    if not port_free():
        raise RuntimeError("Puerto Q180 ocupado al lanzar")
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": "0,1"}
    log = (LOGS / "llama-server.log").open("a", encoding="utf-8")
    t0 = time.monotonic()
    p = subprocess.Popen(server_argv(), stdout=log, stderr=subprocess.STDOUT, env=env,
                         start_new_session=True, close_fds=True)
    p_server = p
    info = {"pid": p.pid, "argv": server_argv(), "started_utc": utc()}
    deadline = time.monotonic() + STARTUP_TIMEOUT_S
    low_count = 0
    while time.monotonic() < deadline:
        check_lock()
        ensure_no_foreign_server(p.pid)
        if p.poll() is not None:
            raise RuntimeError(f"llama-server terminó antes de readiness, rc={p.returncode}")
        state = gpu_state()
        low_count = low_count + 1 if state["mem_available_kib"] < MIN_AVAILABLE_KIB else 0
        if low_count >= 4:
            raise RuntimeError("MemAvailable <32 GiB en 4 muestras consecutivas")
        if any(i not in state["gpus"] for i in (0, 1)):
            raise RuntimeError("Una RTX 3090 dejó de estar visible")
        try:
            with urllib.request.urlopen(f"http://{HOST}:{PORT}/health", timeout=3) as r:
                if r.status == 200:
                    models = get_json(f"http://{HOST}:{PORT}/v1/models")
                    info.update({"ready_utc": utc(), "ready_seconds": round(time.monotonic()-t0, 3),
                                 "health_status": r.status, "models": models,
                                 "gpu_state": state})
                    info["served_model"] = models["data"][0]["id"]
                    # Require this owned PID to be a CUDA compute process on both cards.
                    for idx in (0, 1):
                        own = [x for x in state["compute_by_gpu"][idx] if x["pid"] == p.pid]
                        if not own or own[0]["used_mib"] < 1024:
                            # Allow a short settling interval for driver accounting.
                            time.sleep(5)
                            state = gpu_state()
                            own = [x for x in state["compute_by_gpu"][idx] if x["pid"] == p.pid]
                        if not own or own[0]["used_mib"] < 1024:
                            raise RuntimeError(f"PID propio no tiene >=1 GiB compute en GPU{idx}: {state}")
                    info["dual_gpu_gate"] = "PASS: mismo PID CUDA visible con >=1GiB en GPU0 y GPU1"
                    write_json(RECEIPTS / "q180-launch.json", info)
                    return p, info
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
            pass
        time.sleep(5)
    raise TimeoutError(f"llama-server no llegó a readiness en {STARTUP_TIMEOUT_S}s")


def monitor(proc: subprocess.Popen, duration_s: float) -> list[dict]:
    end = time.monotonic() + duration_s
    samples = []
    low = 0
    while time.monotonic() < end:
        check_lock()
        ensure_no_foreign_server(proc.pid)
        state = gpu_state()
        samples.append(state)
        low = low + 1 if state["mem_available_kib"] < MIN_AVAILABLE_KIB else 0
        if low >= 4:
            raise RuntimeError("MemAvailable <32 GiB durante cuatro muestras consecutivas")
        if any(idx not in state["gpus"] for idx in (0, 1)):
            raise RuntimeError("Se perdió una RTX 3090")
        if proc.poll() is not None:
            raise RuntimeError(f"llama-server terminó durante la prueba, rc={proc.returncode}")
        time.sleep(min(MONITOR_S, max(0, end-time.monotonic())))
    return samples


def benchy_argv(model_id: str, pp: int, tg: int, runs: int, out: pathlib.Path,
                 progress: pathlib.Path) -> list[str]:
    return [str(BENCHY), "--base-url", f"http://{HOST}:{PORT}/v1", "--model", model_id,
            "--tokenizer", str(TOKENIZER), "--pp", str(pp), "--tg", str(tg), "--exact-tg",
            "--depth", "0", "--concurrency", "1", "--runs", str(runs),
            "--latency-mode", "generation", "--no-cache", "--skip-coherence",
            "--no-adapt-prompt", "--no-warmup", "--extra-body",
            "temperature=0.6,top_p=0.95,top_k=20,min_p=0.0,repetition_penalty=1.0,presence_penalty=0.0,seed=42",
            "--format", "json", "--exit-on-first-fail", "--save-result", str(out),
            "--emit-progress", str(progress)]


def q172_argv(model_id: str, seed: int) -> list[str]:
    return [str(TOOL), "run", "--model", model_id, "--backend", "llamacpp",
            "--base-url", f"http://{HOST}:{PORT}/v1", "--format", "openai",
            "--temperature", "0.6", "--top-p", "0.95", "--top-k", "20", "--min-p", "0.0",
            "--repeat-penalty", "1.0", "--seed", str(seed), "--backend-kwargs",
            json.dumps({"reasoning_effort": "medium", "presence_penalty": 0.0}),
            "--variant-seed", "20261010", "--hardmode", "--scenarios",
            *[f"TC-{i}" for i in range(70, 98)], "--timeout", "120", "--max-turns", "8",
            "--trials", "1", "--parallel", "1", "--no-warmup", "--fail-on-safety",
            "--label", f"Q180-Qwen36-llama.cpp-dual-Q172-seed{seed}", "--redact-url",
            "--output-dir", str(RUNS / "reports"), "--json-file", str(RUNS / f"q172-seed{seed}.json")]


def run_client(argv: list[str], log: pathlib.Path, expected=(0,)) -> int:
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": ""}
    with log.open("w", encoding="utf-8") as f:
        p = subprocess.Popen(argv, stdout=f, stderr=subprocess.STDOUT, env=env,
                             start_new_session=True, close_fds=True)
        while p.poll() is None:
            monitor(p_server, MONITOR_S)
        rc = p.returncode
    if rc not in expected:
        raise RuntimeError(f"Cliente rc={rc}; log: {log}")
    return rc


def stop_server(p: subprocess.Popen) -> dict:
    before = utc()
    if p.poll() is None:
        os.killpg(p.pid, signal.SIGINT)
        try:
            rc = p.wait(timeout=30)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGTERM)
            try:
                rc = p.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                rc = p.wait(timeout=10)
    else:
        rc = p.returncode
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and not port_free():
        time.sleep(0.25)
    return {"stopped_utc": utc(), "signal_phase_started_utc": before,
            "returncode": rc, "port_free": port_free(), "gpu_state": gpu_state()}


def main() -> int:
    global p_server
    p_server = None
    RUNS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    try:
        pre = preflight()
        write_json(RECEIPTS / "q180-preflight.json", pre)
    except Exception as e:
        write_json(RECEIPTS / "q180-preflight-blocked.json", {"timestamp_utc": utc(), "status": "BLOCKED", "error": str(e)})
        raise
    summary = {"task": "Q180 Qwen3.6 dual-RTX3090 screen", "started_utc": utc(),
               "preflight": pre, "quality": {}, "throughput": {}, "init": {}}
    try:
        p_server, launch = start_server()
        summary["init"]["initial_process_to_health_s"] = launch["ready_seconds"]
        model_id = launch["served_model"]
        # Exact 16-token API smoke; this is not a scored benchmark sample.
        smoke = RUNS / "smoke-pp32-tg16.json"
        run_client(benchy_argv(model_id, 32, 16, 1, smoke, RUNS / "smoke-events.jsonl"),
                   LOGS / "smoke.log", expected=(0,))
        summary["smoke"] = {"status": "passed", "result": str(smoke)}

        q172_continue = True
        for seed in (42, 43, 44):
            if seed != 42 and not q172_continue:
                break
            result_path = RUNS / f"q172-seed{seed}.json"
            try:
                rc = run_client(q172_argv(model_id, seed), LOGS / f"q172-seed{seed}.log", expected=(0, 2))
            except RuntimeError as e:
                # A harness/API incompatibility should not erase the independent throughput result.
                # Resource guards, foreign servers, and server faults still abort the whole run.
                if not str(e).startswith("Cliente rc="):
                    raise
                summary["quality"][str(seed)] = {"status": "harness_failed", "error": str(e)}
                q172_continue = False
                break
            if not result_path.is_file():
                summary["quality"][str(seed)] = {"status": "no-result-json", "tool_exit_code": rc}
                q172_continue = False
                break
            result = json.loads(result_path.read_text(encoding="utf-8"))
            complete = result.get("status") == "completed" and int(result.get("total_scenarios", 0)) == 28
            safety = result.get("safety_gate", {}).get("passed") is True
            summary["quality"][str(seed)] = {"status": result.get("status"),
                "scenarios": result.get("total_scenarios"), "score": result.get("final_score"),
                "points": result.get("scores", {}).get("total_points"),
                "max_points": result.get("scores", {}).get("max_points"),
                "safety_gate_passed": safety, "safety_warnings": result.get("safety_warnings", []),
                "tool_exit_code": rc}
            if not complete or not safety:
                q172_continue = False
                break

        # A quality/safety failure does not suppress the independent throughput screen.
        for pp, runs in ((8192, 3), (32768, 1), (65536, 1), (131072, 1), (261888, 1)):
            out = RUNS / f"context-{pp}.json"
            prog = RUNS / f"context-{pp}-events.jsonl"
            try:
                run_client(benchy_argv(model_id, pp, 128, runs, out, prog),
                           LOGS / f"context-{pp}.log", expected=(0,))
                summary["throughput"][str(pp)] = {"status": "completed", "result": str(out),
                                                  "runs": runs, "target_output_tokens": 128}
            except Exception as e:
                summary["throughput"][str(pp)] = {"status": "failed", "error": str(e)}
                break

        summary["first_server_stop"] = stop_server(p_server)
        p_server = None
        if summary["first_server_stop"]["port_free"]:
            p_server, hot = start_server()
            summary["init"]["immediate_relaunch_to_health_s"] = hot["ready_seconds"]
            summary["hot_server_stop"] = stop_server(p_server)
            p_server = None
        else:
            summary["init"]["immediate_relaunch_to_health_s"] = "N/D: primer proceso no limpió puerto"
        summary["status"] = "completed" if summary["smoke"]["status"] == "passed" else "failed"
    except Exception as e:
        summary["status"] = "failed"
        summary["error"] = f"{type(e).__name__}: {e}"
        raise
    finally:
        if p_server is not None:
            summary["final_server_stop"] = stop_server(p_server)
        summary["finished_utc"] = utc()
        write_json(RUNS / "q180-summary.json", summary)
        write_json(RECEIPTS / "q180-postflight.json", {"timestamp_utc": utc(),
            "summary_status": summary.get("status"), "server_processes": inference_processes(),
            "port_free": port_free(), "resources": gpu_state()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
