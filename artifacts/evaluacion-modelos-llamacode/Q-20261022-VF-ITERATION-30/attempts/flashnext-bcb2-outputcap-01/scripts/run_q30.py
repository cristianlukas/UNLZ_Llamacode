#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import signal
import subprocess
import threading
import time
import urllib.request

ROOT = pathlib.Path("/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode")
ATTEMPT = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261022-VF-ITERATION-30/attempts/flashnext-bcb2-outputcap-01"
RUNTIME = ATTEMPT / "work/isolated-runtime"
OUT = ATTEMPT / "receipts"
APP = pathlib.Path("/home/cristian/.cache/llamacode/build_linux/LlamaCode")
OLD = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261021-VF-ITERATION-26/attempts/bcb-01"
STRATA_CONFIG_SOURCE = OLD / "receipts/strata-server-config.json"
STRATA = pathlib.Path("/home/cristian/.cache/strata-udiq4xs-screen-20261018/engine/strata")
STRATA_ROOT = STRATA.parents[1]
SERVER_SCRIPT = STRATA_ROOT / "serve/server.py"
SERVER_PYTHON = STRATA_ROOT / ".venv/bin/python"
MODEL_ROOT = pathlib.Path("/media/cristian/HDD extra/Models/LlamaCodeEval/Q-20261010-STRATA-UDIQ4XS-POST")
PACK = MODEL_ROOT / "strata-data/packs/unsloth-ud-iq4_xs"
NATIVE = MODEL_ROOT / "models/unsloth-UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf"
PROFILE_ID = "q14-udiq4xs-he0"
PROFILE_FP = "a56c723fde568b4db160bbb48ccc9e378aa221bdcaffe544ee957e3ba666dd86"
SUITE_ID = "vf-q30-bcb2-token-cap-diagnostic"
LOCK_TOKEN = "4c3101a9-2bca-4b9d-9ab9-acc1024075a5"
SYSTEMD_UNIT = "llamacode-vf-q30-bcb2-outputcap.scope"
CONTROL_PORT = 18766
SERVER_PORT = 8354
TIMEOUT = 1800
MIN_AVAILABLE_BEFORE_MODEL_GIB = 80.0
MIN_AVAILABLE_GIB = 24.0
MIN_SWAP_GIB = 1.0
MAX_APP_RSS_GIB = 60.0
SERVER_NAMES = {"strata", "llama-server", "vllm", "ollama", "sglang", "aphrodite", "koboldcpp", "localai", "local-ai"}
BASE = f"http://127.0.0.1:{CONTROL_PORT}"
SERVER = f"http://127.0.0.1:{SERVER_PORT}"


def write_json(path: pathlib.Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def request(base: str, path: str, body: dict | None = None, timeout: float = 20) -> dict:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(base + path, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read()
    return json.loads(raw) if raw else {}


def value(name: str) -> object:
    return request(BASE, "/prop?name=" + name).get("value")


def process_tree(root_pid: int | None) -> list[dict]:
    if not root_pid:
        return []
    todo, seen, rows = [root_pid], set(), []
    while todo:
        pid = todo.pop()
        if pid in seen:
            continue
        seen.add(pid)
        base = pathlib.Path("/proc") / str(pid)
        try:
            comm = (base / "comm").read_text().strip()
            status = (base / "status").read_text()
        except OSError:
            continue
        if any(line.startswith("State:") and "Z" in line.split() for line in status.splitlines()):
            continue  # a zombie has no server, listener, model memory, or GPU context
        rss = 0
        for line in status.splitlines():
            if line.startswith("VmRSS:"):
                rss = int(line.split()[1])
                break
        rows.append({"pid": pid, "comm": comm, "rss_kib": rss})
        try:
            children = (base / "task" / str(pid) / "children").read_text().split()
        except OSError:
            children = []
        todo.extend(int(x) for x in children if x.isdigit())
    return rows


def memory_snapshot(app: subprocess.Popen | None = None, server: subprocess.Popen | None = None) -> dict:
    mem = {}
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        parts = line.split()
        if parts and parts[0].rstrip(":") in {"MemAvailable", "SwapFree"}:
            mem[parts[0].rstrip(":")] = int(parts[1]) * 1024
    app_rows = process_tree(app.pid if app else None)
    server_rows = process_tree(server.pid if server else None)
    gib = 1024 ** 3
    return {
        "at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mem_available_gib": round(mem.get("MemAvailable", 0) / gib, 2),
        "swap_free_gib": round(mem.get("SwapFree", 0) / gib, 2),
        "app_tree_rss_gib": round(sum(x["rss_kib"] for x in app_rows) / 1024**2, 2),
        "app_tree": app_rows,
        "server_tree_rss_gib": round(sum(x["rss_kib"] for x in server_rows) / 1024**2, 2),
        "server_tree": server_rows,
    }


def inference_processes(owned: set[int]) -> list[dict]:
    active = []
    for proc in pathlib.Path("/proc").iterdir():
        if not proc.name.isdigit() or int(proc.name) in owned:
            continue
        try:
            comm = (proc / "comm").read_text().strip().lower()
            argv = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
        except OSError:
            continue
        lower = argv.lower()
        python_server = comm in {"python", "python3"} and any(
            x in lower for x in ("-m vllm", "vllm serve", "-m sglang", "sglang serve", "serve/server.py --engine strata", "-m aphrodite")
        )
        if comm in SERVER_NAMES or python_server:
            active.append({"pid": int(proc.name), "comm": comm, "argv": argv[:500]})
    return active


def listener_check(allowed_controller_pid: int | None = None,
                   allowed_server_pid: int | None = None) -> dict:
    out = subprocess.run(["ss", "-ltnp"], capture_output=True, text=True, timeout=10).stdout.splitlines()
    target = [row for row in out if re.search(rf":(?:{CONTROL_PORT}|{SERVER_PORT})(?:\s|$)", row)]
    allowed_controller, allowed_server, blocked = [], [], []
    for row in target:
        pids = set(re.findall(r"pid=(\d+)", row))
        port_match = re.search(rf":({CONTROL_PORT}|{SERVER_PORT})(?:\s|$)", row)
        port = int(port_match.group(1)) if port_match else None
        if port == CONTROL_PORT and allowed_controller_pid is not None and pids == {str(allowed_controller_pid)}:
            allowed_controller.append(row)
        elif port == SERVER_PORT and allowed_server_pid is not None and pids == {str(allowed_server_pid)}:
            allowed_server.append(row)
        else:
            blocked.append(row)
    return {"target_listeners": target, "allowed_controller_listeners": allowed_controller,
            "allowed_server_listeners": allowed_server, "blocking_listeners": blocked}


def check_scope() -> dict:
    unit = subprocess.run(["systemctl", "--user", "show", "--property=OOMPolicy", "--value", SYSTEMD_UNIT],
                          capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    cgroup_line = next(x for x in pathlib.Path("/proc/self/cgroup").read_text().splitlines() if x.startswith("0::"))
    cgroup = (pathlib.Path("/sys/fs/cgroup") / cgroup_line.split("::", 1)[1].lstrip("/")).resolve()
    vals = {k: int((cgroup / f"memory.{k}").read_text().strip()) for k in ("high", "max", "swap.max")}
    expected = {"high": 86 * 1024**3, "max": 96 * 1024**3, "swap.max": 1 * 1024**3}
    if unit != "kill" or vals != expected:
        raise RuntimeError(f"Resource scope mismatch: OOMPolicy={unit!r}; cgroup={vals}")
    return {"unit": SYSTEMD_UNIT, "oom_policy": unit, "cgroup": str(cgroup), "effective_bytes": vals}


def check_preflight(phase: str, app: subprocess.Popen | None = None,
                    server: subprocess.Popen | None = None) -> dict:
    lock = json.loads((ROOT / "WORK_QUEUE.lock").read_text())
    if lock.get("token") != LOCK_TOKEN:
        raise RuntimeError("Lock token changed; stop before model work")
    spec = json.loads((ATTEMPT / "receipts/preregistration.json").read_text())
    for rel, expected in spec["instruction_hashes"].items():
        if sha(ROOT / rel) != expected:
            raise RuntimeError(f"Instruction/queue hash changed since preregistration: {rel}")
    if sha(ATTEMPT / "scripts/run_q30.py") != spec["runner_sha256"]:
        raise RuntimeError("Runner hash differs from preregistration")
    if sha(ATTEMPT / "work/diagnostic-suite.json") != spec["variant_suite_sha256"]:
        raise RuntimeError("Diagnostic suite hash differs from preregistration")
    owned = {os.getpid(), os.getppid()}
    if app is not None:
        owned.update(row["pid"] for row in process_tree(app.pid))
    if server is not None:
        owned.update(row["pid"] for row in process_tree(server.pid))
    servers = inference_processes(owned)
    listeners = listener_check(app.pid if app else None, server.pid if server else None)
    snap = memory_snapshot(app, server)
    min_before = MIN_AVAILABLE_BEFORE_MODEL_GIB if phase == "before_model" else MIN_AVAILABLE_GIB
    if servers or listeners["blocking_listeners"]:
        raise RuntimeError(f"Another inference server/listener is active: {servers} {listeners}")
    if snap["mem_available_gib"] < min_before or snap["swap_free_gib"] < MIN_SWAP_GIB:
        raise RuntimeError(f"Insufficient memory before {phase}: {snap}")
    result = {
        "checked_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "phase": phase,
        "lock_token": lock["token"],
        "instruction_hashes": spec["instruction_hashes"],
        "inference_processes": servers,
        "listeners": listeners,
        "memory": snap,
        "resource_scope": check_scope(),
        "gpu_compute_apps": subprocess.run(["nvidia-smi", "--query-compute-apps=gpu_uuid,pid,process_name,used_memory", "--format=csv,noheader"],
                                            capture_output=True, text=True, timeout=10).stdout.strip().splitlines(),
        "gpu_query_note": "GUI processes are recorded separately and do not block; this preflight is for inference servers and test ports.",
    }
    return result


def stop_owned(proc: subprocess.Popen | None, label: str) -> dict:
    if proc is None or proc.poll() is not None:
        return {"label": label, "pid": proc.pid if proc else None, "already_exited": True,
                "exit_code": proc.returncode if proc else None}
    try:
        proc.terminate()  # let the owned wrapper reap its child engine before escalating
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=25)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=10)
    return {"label": label, "pid": proc.pid, "exit_code": proc.returncode,
            "stopped_by_task": True, "shutdown": "SIGTERM to wrapper; process-group escalation only on timeout"}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    logs = ATTEMPT / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    if not RUNTIME.is_dir() or not APP.is_file() or not STRATA.is_file() or not SERVER_SCRIPT.is_file() or not SERVER_PYTHON.is_file():
        raise FileNotFoundError("Isolated runtime, LlamaCode, or pinned Strata runtime is missing")
    if not PACK.is_dir() or not NATIVE.is_file():
        raise FileNotFoundError("Pinned Flash-Next model files are missing; no download is permitted by this test")
    if sha(ATTEMPT / "work/diagnostic-suite.json") != json.loads((ATTEMPT / "receipts/preparation.json").read_text())["variant_suite_sha256"]:
        raise RuntimeError("Prepared diagnostic suite changed")

    env = os.environ.copy()
    env.update({
        "XDG_DATA_HOME": str(RUNTIME / "data"),
        "XDG_CONFIG_HOME": str(RUNTIME / "config"),
        "XDG_CACHE_HOME": str(RUNTIME / "cache"),
        "XDG_STATE_HOME": str(RUNTIME / "state"),
        "LLAMACODE_PROFILES_DIR": str(RUNTIME / "profiles"),
        "LLAMACODE_CONTROL_PORT": str(CONTROL_PORT),
        "QT_QPA_PLATFORM": "offscreen",
        "CUDA_VISIBLE_DEVICES": "0",
        "NO_PROXY": "127.0.0.1,localhost",
        "no_proxy": "127.0.0.1,localhost",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
    })
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env.pop(key, None)
    for key in ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"):
        pathlib.Path(env[key]).mkdir(parents=True, exist_ok=True)

    app_log = (logs / "llamacode-control.log").open("w", encoding="utf-8")
    server_log = (logs / "strata-server.log").open("w", encoding="utf-8")
    app: subprocess.Popen | None = None
    server: subprocess.Popen | None = None
    guard_stop = threading.Event()
    guard_state: dict = {}
    final = {"task": "Q-20261022-VF-ITERATION-30", "attempt": ATTEMPT.name,
             "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "diagnostic": {"suite_id": SUITE_ID, "prompt_id": "BigCodeBench/765", "max_tokens": 2400,
                            "profile_id": PROFILE_ID, "profile_fingerprint": PROFILE_FP}}

    def guard_loop() -> None:
        while not guard_stop.wait(5):
            snap = memory_snapshot(app, server)
            reasons = []
            if snap["mem_available_gib"] < MIN_AVAILABLE_GIB:
                reasons.append("MemAvailable below 24 GiB")
            if snap["swap_free_gib"] < MIN_SWAP_GIB:
                reasons.append("SwapFree below 1 GiB")
            if snap["app_tree_rss_gib"] >= MAX_APP_RSS_GIB:
                reasons.append("LlamaCode process tree RSS at or above 60 GiB")
            if reasons:
                guard_state["trip"] = {"reasons": reasons, **snap}
                write_json(OUT / "memory-guard-trip.json", guard_state["trip"])
                return
            guard_state["last"] = snap

    guard_thread: threading.Thread | None = None
    try:
        final["run_preflight"] = check_preflight("before_controller")
        app = subprocess.Popen([str(APP), "--agent-daemon"], cwd=APP.parent, env=env,
                               stdout=app_log, stderr=subprocess.STDOUT, start_new_session=True)
        guard_thread = threading.Thread(target=guard_loop, daemon=True)
        guard_thread.start()
        health_deadline = time.monotonic() + 120
        while time.monotonic() < health_deadline:
            if guard_state.get("trip"):
                raise RuntimeError(f"Memory guard tripped: {guard_state['trip']}")
            if app.poll() is not None:
                raise RuntimeError(f"LlamaCode controller exited before health: {app.returncode}")
            try:
                request(BASE, "/health", timeout=3)
                break
            except Exception:
                time.sleep(2)
        else:
            raise TimeoutError("LlamaCode control API did not become healthy within 120 seconds")

        methods = request(BASE, "/methods").get("methods", [])
        names = {x.get("name") for x in methods if isinstance(x, dict)}
        if "startCustomBenchmark" not in names:
            raise RuntimeError("startCustomBenchmark is unavailable")
        agent_select = request(BASE, "/invoke", {"method": "startCustomBenchmark",
              "args": [[PROFILE_ID], "__q30_agent_selection_only__", 1, "agent", TIMEOUT, "agent-maximo"]})
        if not agent_select.get("ok") or value("benchmarkRunning") or value("serverState") != "stopped":
            raise RuntimeError(f"Agent selection did not return before inference: {agent_select}")

        custom = value("customBenchmarks") or []
        suite = next((x for x in custom if isinstance(x, dict) and x.get("id") == SUITE_ID), None)
        if not suite or len(suite.get("prompts", [])) != 1 or suite.get("name") != "VF focused code-output-cap diagnostic":
            raise RuntimeError("LlamaCode did not load the isolated one-prompt diagnostic suite")
        if "bigcodebench" in suite.get("name", "").lower() or "bcb" in suite.get("name", "").lower():
            raise RuntimeError("Diagnostic label would trigger the full BCB stage gate; refusing to run")
        coverage = value("benchmarkCoverage") or []
        prof = next((x for x in coverage if x.get("profileId") == PROFILE_ID), None)
        if not prof or prof.get("profileConfigFingerprint") != PROFILE_FP:
            raise RuntimeError(f"Flash-Next profile fingerprint mismatch: {prof}")
        if value("benchmarkRunning"):
            raise RuntimeError("Another benchmark is already running")
        final["controller_pre_inference_gate"] = {"agent_selection": agent_select,
             "suite_loaded": True, "suite_prompt_count": 1, "profile": prof,
             "benchmark_running": False, "server_state": "stopped",
             "models_started_before_gate": False}

        final["model_start_preflight"] = check_preflight("before_model", app)
        config = json.loads(STRATA_CONFIG_SOURCE.read_text(encoding="utf-8"))
        config["log"] = str(logs / "strata-engine.log")
        config["host"] = "127.0.0.1"
        config["gpu"] = 0
        config_path = OUT / "strata-server-config.json"
        write_json(config_path, config)
        server_args = [str(SERVER_PYTHON), str(SERVER_SCRIPT), "--engine", "strata",
                       "--config", str(config_path), "--host", "127.0.0.1",
                       "--port", str(SERVER_PORT), "--gpu", "0"]
        server_env = env.copy()
        server_env["STRATA_ENGINE_READY_S"] = "1800"
        server = subprocess.Popen(server_args, cwd=STRATA_ROOT, env=server_env,
                                  stdout=server_log, stderr=subprocess.STDOUT, start_new_session=True)
        ready_deadline = time.monotonic() + 1800
        while time.monotonic() < ready_deadline:
            if guard_state.get("trip"):
                raise RuntimeError(f"Memory guard tripped during model startup: {guard_state['trip']}")
            if server.poll() is not None:
                raise RuntimeError(f"Strata exited before ready: {server.returncode}")
            try:
                models = request(SERVER, "/v1/models", timeout=10)
                if models:
                    final["server_ready"] = {"at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "models": models}
                    break
            except Exception:
                pass
            time.sleep(5)
        else:
            raise TimeoutError("Pinned Strata server did not answer /v1/models in 1800 seconds")

        final["benchmark_preflight"] = check_preflight("during_model", app, server)
        invoke_args = [[PROFILE_ID], SUITE_ID, 1, "agent", TIMEOUT, "agent-maximo"]
        start = request(BASE, "/invoke", {"method": "startCustomBenchmark", "args": invoke_args})
        if not start.get("ok"):
            raise RuntimeError(f"startCustomBenchmark rejected the diagnostic: {start}")
        write_json(OUT / "benchmark-invocation.json", {"at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "method": "startCustomBenchmark", "args": invoke_args, "response": start,
                   "suite_label": suite.get("name"), "task_id": "BigCodeBench/765", "max_tokens": 2400})
        progress_path = OUT / "benchmark-poll.jsonl"
        deadline = time.monotonic() + TIMEOUT + 120
        seen_running = False
        poll_started = time.monotonic()
        while time.monotonic() < deadline:
            if guard_state.get("trip"):
                raise RuntimeError(f"Memory guard tripped during benchmark: {guard_state['trip']}")
            running = value("benchmarkRunning")
            status = value("benchmarkStatus")
            progress = value("benchmarkProgress")
            entry = {"at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                     "running": running, "status": status, "progress": progress}
            with progress_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
            print(json.dumps(entry, ensure_ascii=False), flush=True)
            if running:
                seen_running = True
            if running is False and seen_running:
                break
            if running is False and not seen_running:
                early_results = value("benchmarkResults") or []
                if any(isinstance(x, dict) and x.get("benchmarkName") == suite.get("name") for x in early_results):
                    break
                if time.monotonic() - poll_started >= 60:
                    raise RuntimeError(f"Benchmark did not enter running state or produce a result after start: {entry}")
            time.sleep(5)
        else:
            raise TimeoutError("The one-prompt diagnostic exceeded the 1800-second app cap plus 120 seconds")

        results = value("benchmarkResults") or []
        coverage_after = value("benchmarkCoverage") or []
        matches = [x for x in results if isinstance(x, dict) and
                   x.get("benchmarkName") == suite.get("name")]
        final.update({"status": "completed_call", "finished_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      "benchmark_status": value("benchmarkStatus"), "benchmark_progress": value("benchmarkProgress"),
                      "benchmark_running": value("benchmarkRunning"), "matching_results": matches,
                      "coverage_after": [x for x in coverage_after if isinstance(x, dict) and x.get("profileId") == PROFILE_ID],
                      "memory_guard": guard_state})
        write_json(OUT / "benchmark-final.json", final)
    except Exception as exc:
        final["status"] = "aborted_or_failed"
        final["error"] = f"{type(exc).__name__}: {exc}"
        final["failed_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        final["memory_guard"] = guard_state
        try:
            final["benchmark_status"] = value("benchmarkStatus")
            final["benchmark_running"] = value("benchmarkRunning")
            final["matching_results"] = value("benchmarkResults") or []
        except Exception:
            pass
        write_json(OUT / "benchmark-final.json", final)
        raise
    finally:
        guard_stop.set()
        if guard_thread is not None:
            guard_thread.join(timeout=6)
        owned = [stop_owned(server, "strata"), stop_owned(app, "llamacode-controller")]
        write_json(OUT / "owned-process-cleanup.json", owned)
        guard_state["postflight"] = {"inference_processes": inference_processes({os.getpid(), os.getppid()}),
                                     "listeners": listener_check(), "memory": memory_snapshot()}
        write_json(OUT / "postflight.json", guard_state["postflight"])
        app_log.close()
        server_log.close()


if __name__ == "__main__":
    main()
