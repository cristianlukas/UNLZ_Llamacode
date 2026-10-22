#!/usr/bin/env python3
"""Run the preregistered Qwen3.8-27B NInfer quality screen serially."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO = pathlib.Path(__file__).resolve().parents[4]
TOKEN = "4bb67f14-f9a8-4c64-971a-58ddfd497ab3"
LOCK = REPO / "WORK_QUEUE.lock"
MODEL = pathlib.Path("/media/cristian/HDD extra/Modelos-eval/Q-20261022-VF-ITERATION-32/models/qwen3_8_27b.ninfer")
MODEL_SIZE = 18_982_458_624
MODEL_SHA = "7f2a0086a071ee932c66106e1552d118a85cfec8ddef13c67a54cd64abb39706"
RUNTIME = pathlib.Path("/media/cristian/HDD extra/Modelos-eval/Q-20261022-VF-ITERATION-32/runtime/extracted/ninfer-rtx3090-linux-x64-0.16.0-rtx3090")
SERVER = RUNTIME / "ninfer-serve"
EVAL = pathlib.Path("/home/cristian/.cache/codex-tool-eval-bench-v2.8.0/.venv/bin/tool-eval-bench")
BASE_URL = "http://127.0.0.1:18132/v1"
PORT = 18132
UNIT = "q34-ninfer-speed.scope"
SEEDS = (42, 43, 44)
GPU_INDEX = "1"
MIN_MEM = 30 * 1024**3
MIN_SWAP = 1 * 1024**3
MAX_TEMP = 80
EXPECTED = {"TC-74", "TC-84", "TC-92"}
SERVER_EXE = {"llama-server", "ninfer-serve", "vllm", "ollama", "koboldcpp", "aphrodite", "sglang", "tabbyapi"}


def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path: pathlib.Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def proc_ancestors() -> set[int]:
    result: set[int] = set()
    pid = os.getpid()
    while pid > 1 and pid not in result:
        result.add(pid)
        try:
            pid = int(pathlib.Path(f"/proc/{pid}/stat").read_text().split()[3])
        except (OSError, ValueError, IndexError):
            break
    return result


def inference_processes(allow: set[int] | None = None) -> list[dict[str, object]]:
    allow = allow or set()
    ancestors = proc_ancestors()
    found = []
    for proc in pathlib.Path("/proc").iterdir():
        if not proc.name.isdigit() or int(proc.name) in ancestors | allow:
            continue
        try:
            comm = (proc / "comm").read_text().strip().lower()
            argv = [x.decode(errors="replace") for x in (proc / "cmdline").read_bytes().split(b"\0") if x]
            if not argv:
                continue
            exe = pathlib.Path(argv[0]).name.lower()
            module = " ".join(argv[:4]).lower()
        except (OSError, ProcessLookupError):
            continue
        is_server = exe in SERVER_EXE or comm in SERVER_EXE
        is_python_server = exe in {"python", "python3"} and any(x in module for x in ("vllm.entrypoints", "sglang.launch_server", "aphrodite.engine", "ollama serve"))
        if is_server or is_python_server:
            found.append({"pid": int(proc.name), "comm": comm, "cmdline": " ".join(argv)[:500]})
    return found


def compute_apps() -> list[dict[str, object]]:
    p = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader"], capture_output=True, text=True, timeout=10, check=True)
    rows = []
    for line in p.stdout.splitlines():
        if line.strip():
            fields = [x.strip() for x in line.split(",")]
            rows.append({"pid": int(fields[0]), "process_name": fields[1], "used_memory": fields[2]})
    return rows


def meminfo() -> dict[str, int]:
    result = {}
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        key, _, value = line.partition(":")
        if key in {"MemAvailable", "SwapFree"}:
            result[key] = int(value.split()[0]) * 1024
    return result


def gpu_temp() -> int:
    p = subprocess.run(["nvidia-smi", "-i", GPU_INDEX, "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10, check=True)
    return int(p.stdout.strip())


def port_free() -> None:
    with socket.socket() as s:
        s.bind(("127.0.0.1", PORT))


def cgroup_for(pid: int) -> pathlib.Path:
    for line in pathlib.Path(f"/proc/{pid}/cgroup").read_text().splitlines():
        if line.startswith("0::"):
            p = pathlib.Path("/sys/fs/cgroup") / line.split("::", 1)[1].lstrip("/")
            if p.exists():
                return p
    raise RuntimeError(f"No cgroup v2 for server pid {pid}")


def unit_props() -> dict[str, str]:
    p = subprocess.run(["systemctl", "--user", "show", UNIT, "-p", "ActiveState", "-p", "ControlGroup"], capture_output=True, text=True, timeout=10, check=True)
    return dict(line.split("=", 1) for line in p.stdout.splitlines() if "=" in line)


def preflight() -> dict[str, object]:
    if not LOCK.is_file() or json.loads(LOCK.read_text()).get("token") != TOKEN:
        raise RuntimeError("WORK_QUEUE.lock no longer belongs to Q32")
    if MODEL.stat().st_size != MODEL_SIZE:
        raise RuntimeError("Model size no longer matches pinned artifact")
    if not EVAL.is_file() or not os.access(EVAL, os.X_OK):
        raise RuntimeError("tool-eval-bench 2.8.0 executable is unavailable")
    servers = inference_processes()
    if servers:
        raise RuntimeError("An inference server is already running: " + json.dumps(servers))
    compute = compute_apps()  # recorded; user authorizes proceeding when no inference server is active
    port_free()
    mem = meminfo()
    if mem.get("MemAvailable", 0) < MIN_MEM or mem.get("SwapFree", 0) < MIN_SWAP:
        raise RuntimeError("RAM/swap preflight failed: " + json.dumps(mem))
    temperature = gpu_temp()
    if temperature >= MAX_TEMP:
        raise RuntimeError(f"RTX 3090 GPU{GPU_INDEX} temperature {temperature}C exceeds gate")
    version = subprocess.run([str(SERVER), "--version"], capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    return {"at_utc": utc(), "lock_token": TOKEN, "inference_servers": servers, "cuda_compute_apps": compute,
            "gui_preserved": True, "port": PORT, "mem_available_bytes": mem["MemAvailable"],
            "swap_free_bytes": mem["SwapFree"], "gpu_index": GPU_INDEX, "gpu_temp_c": temperature,
            "server_version": version, "model_path": str(MODEL), "model_size_bytes": MODEL_SIZE,
            "model_sha256_verified_receipt": str(ROOT / "receipts/model-download-verification.json"),
            "eval_cli": str(EVAL), "gate_passed": True}


def guard(server_pid: int, cg: pathlib.Path) -> dict[str, object]:
    mem = meminfo()
    temp = gpu_temp()
    events = {}
    ep = cg / "memory.events"
    if ep.exists():
        for line in ep.read_text().splitlines():
            k, v = line.split()
            events[k] = int(v)
    compute = compute_apps()
    unexpected_compute = [x for x in compute if x["pid"] != server_pid]
    foreign_servers = inference_processes({server_pid})
    state = {"at_utc": utc(), "server_pid": server_pid, "mem_available_bytes": mem.get("MemAvailable", 0),
             "swap_free_bytes": mem.get("SwapFree", 0), "gpu_temp_c": temp,
             "cuda_compute_apps": compute, "foreign_inference_servers": foreign_servers,
             "memory_current_bytes": int((cg / "memory.current").read_text().strip()), "memory_events": events}
    if state["mem_available_bytes"] < MIN_MEM or state["swap_free_bytes"] < MIN_SWAP:
        raise RuntimeError("RAM/swap guard tripped")
    if temp > MAX_TEMP:
        raise RuntimeError(f"RTX 3090 temperature exceeded {MAX_TEMP}C: {temp}")
    if foreign_servers:
        raise RuntimeError("Unexpected inference server appeared: " + json.dumps(foreign_servers))
    if events.get("max", 0) or events.get("oom", 0) or events.get("oom_kill", 0):
        raise RuntimeError("Memory cgroup reported max/OOM event")
    if not pathlib.Path(f"/proc/{server_pid}").exists():
        raise RuntimeError("NInfer server exited unexpectedly")
    return state


def wait_ready(proc: subprocess.Popen[bytes], log_path: pathlib.Path, receipt: pathlib.Path) -> tuple[int, pathlib.Path]:
    started = time.monotonic()
    next_guard = 0.0
    while time.monotonic() - started < 1800:
        props = unit_props()
        if proc.poll() is not None:
            raise RuntimeError(f"systemd-run exited during startup rc={proc.returncode}; see {log_path}")
        control_group = props.get("ControlGroup", "")
        cg = pathlib.Path("/sys/fs/cgroup") / control_group.lstrip("/") if control_group else None
        if props.get("ActiveState") == "active" and cg and cg.exists():
            pids = [int(x) for x in (cg / "cgroup.procs").read_text().splitlines() if x.isdigit()]
            server_pids = []
            for pid in pids:
                try:
                    if (pathlib.Path(f"/proc/{pid}/comm").read_text().strip() == "ninfer-serve"):
                        server_pids.append(pid)
                except (OSError, ProcessLookupError):
                    pass
            if not server_pids:
                time.sleep(1)
                continue
            pid = server_pids[0]
            now = time.monotonic()
            if now >= next_guard:
                state = guard(pid, cg)
                with (ROOT / "receipts/guard-progress.jsonl").open("a", encoding="utf-8") as f:
                    f.write(json.dumps(state) + "\n")
                next_guard = now + 20
            try:
                with urllib.request.urlopen(BASE_URL + "/models", timeout=3) as r:
                    body = r.read().decode("utf-8", "replace")
                    if r.status == 200:
                        write_json(receipt, {"at_utc": utc(), "pid": pid, "unit": UNIT, "cgroup": str(cg), "models_response": body})
                        return pid, cg
            except (urllib.error.URLError, TimeoutError, OSError):
                pass
        if int((time.monotonic() - started) // 30) != int((time.monotonic() - started - 5) // 30):
            print(f"STARTUP {int(time.monotonic()-started)}s", flush=True)
        time.sleep(5)
    raise RuntimeError("NInfer did not serve /v1/models within 30 minutes")


def smoke_tool_call() -> dict[str, object]:
    body = {"model": "qwen38-27b-ninfer-v3", "messages": [{"role": "user", "content": "Call append_note now with text exactly Q32_TOOL_SMOKE. Do not answer in prose."}],
            "tools": [{"type": "function", "function": {"name": "append_note", "description": "Append a note to an isolated test fixture.",
                        "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"], "additionalProperties": False}}}],
            "tool_choice": {"type": "function", "function": {"name": "append_note"}},
            "temperature": 0.0, "max_tokens": 128}
    req = urllib.request.Request(BASE_URL + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as response:
        raw = response.read().decode("utf-8", "replace")
        data = json.loads(raw)
    choice = data.get("choices", [{}])[0].get("message", {})
    calls = choice.get("tool_calls", [])
    parsed = {}
    if calls:
        function = calls[0].get("function", {})
        try:
            parsed = json.loads(function.get("arguments", "{}"))
        except json.JSONDecodeError:
            parsed = {"parse_error": True, "raw": function.get("arguments")}
    ok = bool(calls and calls[0].get("function", {}).get("name") == "append_note" and parsed.get("text") == "Q32_TOOL_SMOKE")
    result = {"at_utc": utc(), "http_status": 200, "model_returned": data.get("model"), "finish_reason": data.get("choices", [{}])[0].get("finish_reason"),
              "tool_calls": calls, "expected_exact_tool_call": "append_note(text='Q32_TOOL_SMOKE')", "passed": ok,
              "usage": data.get("usage"), "response_sha256": hashlib.sha256(raw.encode()).hexdigest()}
    write_json(ROOT / "receipts/tool-smoke.json", result)
    return result


def run_eval(seed: int, server_pid: int, cg: pathlib.Path) -> dict[str, object]:
    run_path = ROOT / "runs" / f"hardmode-seed-{seed}.json"
    reports = ROOT / "runs" / f"reports-seed-{seed}"
    log = ROOT / "logs" / f"tool-eval-seed-{seed}.log"
    cmd = [str(EVAL), "run", "--hardmode-only", "--base-url", BASE_URL,
           "--model", "qwen38-27b-ninfer-v3", "--backend", "ninfer",
           "--temperature", "0.6", "--top-p", "0.95", "--top-k", "20", "--min-p", "0",
           "--repeat-penalty", "1", "--seed", str(seed), "--variant-seed", "20261010",
           "--timeout", "120", "--max-turns", "8", "--parallel", "1", "--context-size", "32768",
           "--backend-kwargs", '{"reasoning_effort":"medium"}',
           "--label", f"Qwen3.8-27B-NInfer-v3-HardMode-seed-{seed}",
           "--json-file", str(run_path), "--output-dir", str(reports), "--no-live"]
    env = dict(os.environ)
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env.pop(key, None)
    env["NO_PROXY"] = "127.0.0.1,localhost"
    started = utc()
    print(f"SEED {seed} START {started}", flush=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("wb") as stream:
        p = subprocess.Popen(cmd, stdout=stream, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        try:
            deadline = time.monotonic() + 3600
            next_guard = 0.0
            while p.poll() is None:
                now = time.monotonic()
                if now >= next_guard:
                    state = guard(server_pid, cg)
                    with (ROOT / "receipts/guard-progress.jsonl").open("a", encoding="utf-8") as f:
                        f.write(json.dumps(state) + "\n")
                    next_guard = now + 20
                if now > deadline:
                    os.killpg(p.pid, signal.SIGTERM)
                    try:
                        p.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        os.killpg(p.pid, signal.SIGKILL)
                        p.wait(timeout=10)
                    raise TimeoutError(f"seed {seed} exceeded 3600 seconds")
                time.sleep(5)
        except BaseException:
            if p.poll() is None:
                try:
                    os.killpg(p.pid, signal.SIGTERM)
                    p.wait(timeout=10)
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    try:
                        os.killpg(p.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            raise
    result = {"seed": seed, "started_at_utc": started, "ended_at_utc": utc(), "exit_code": p.returncode,
              "json": str(run_path), "json_exists": run_path.is_file(), "log": str(log)}
    if run_path.is_file():
        result["json_sha256"] = sha256(run_path)
        try:
            raw = json.loads(run_path.read_text())
            result["run_id"] = raw.get("run_id")
            result["score"] = raw.get("score") or raw.get("overall_score") or raw.get("summary", {}).get("score")
            result["status"] = raw.get("status") or raw.get("overall_status")
            result["scenario_count"] = raw.get("summary", {}).get("scenario_count") or len(raw.get("results", []))
            result["critical_case_status"] = {case: raw.get("scenarios", {}).get(case) for case in sorted(EXPECTED)}
        except (OSError, json.JSONDecodeError):
            result["parse_error"] = "invalid benchmark JSON"
    print(f"SEED {seed} END rc={p.returncode} score={result.get('score', 'see raw JSON')}", flush=True)
    write_json(ROOT / "receipts/seed-progress.json", {"updated_at_utc": utc(), "completed": seed, "result": result})
    if p.returncode != 0 or not result["json_exists"]:
        raise RuntimeError(f"seed {seed} failed or returned no JSON; no automatic retry")
    return result


def stop_owned(proc: subprocess.Popen[bytes] | None) -> None:
    subprocess.run(["systemctl", "--user", "stop", UNIT], capture_output=True, text=True, timeout=30)
    if proc and proc.poll() is None:
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=10)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                pass


def main() -> int:
    receipts = ROOT / "receipts"
    logs = ROOT / "logs"
    (ROOT / "runs").mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    (receipts / "guard-progress.jsonl").write_text("", encoding="utf-8")
    server_proc: subprocess.Popen[bytes] | None = None
    results = []
    start = utc()
    try:
        pf = preflight()
        write_json(receipts / "gpu-preflight.json", pf)
        args = [str(SERVER), str(MODEL), "--host", "127.0.0.1", "--port", str(PORT),
                "--model-id", "qwen38-27b-ninfer-v3", "--max-context", "32768", "--kv-capacity", "32768",
                "--max-concurrency", "1", "--max-pending-requests", "1", "--pending-timeout-ms", "600000",
                "--prefill-chunk", "1024", "--kv-dtype", "int8", "--host-context-mib", "8192",
                "--default-max-tokens", "4096", "--default-thinking-budget", "4096",
                "--reasoning-effort", "medium", "--temperature", "0.6", "--top-p", "0.95", "--top-k", "20",
                "--min-p", "0", "--presence-penalty", "0", "--request-log-jsonl", str(logs / "requests.jsonl"),
                "--log-level", "info"]
        write_json(receipts / "server-invocation.json", {"at_utc": start, "unit": UNIT, "args": args,
                  "systemd_scope_memory_high": 86 * 1024**3, "systemd_scope_memory_max": 96 * 1024**3,
                  "systemd_scope_swap_max": 1 * 1024**3, "cuda_visible_devices": GPU_INDEX,
                  "model_sha256": MODEL_SHA, "server_version": pf["server_version"]})
        server_log = (logs / "ninfer-serve.log").open("wb")
        scope_cmd = ["systemd-run", "--user", "--scope", "--quiet", f"--unit={UNIT}",
                     "-p", "MemoryHigh=86G", "-p", "MemoryMax=96G", "-p", "MemorySwapMax=1G",
                     "/usr/bin/env", f"CUDA_VISIBLE_DEVICES={GPU_INDEX}", *args]
        server_proc = subprocess.Popen(scope_cmd, stdout=server_log, stderr=subprocess.STDOUT, start_new_session=True)
        write_json(receipts / "server-process.json", {"at_utc": utc(), "systemd_run_pid": server_proc.pid, "unit": UNIT})
        server_pid, cg = wait_ready(server_proc, logs / "ninfer-serve.log", receipts / "server-ready.json")
        props = unit_props()
        limits = {name: (cg / name).read_text().strip() for name in ("memory.high", "memory.max", "memory.swap.max")}
        if limits != {"memory.high": str(86 * 1024**3), "memory.max": str(96 * 1024**3), "memory.swap.max": str(1 * 1024**3)}:
            raise RuntimeError("Effective cgroup limits did not match preregistration: " + json.dumps(limits))
        write_json(receipts / "server-ready.json", {"at_utc": utc(), "pid": server_pid, "unit": UNIT, "control_group": props.get("ControlGroup"), "cgroup_limits": limits, "api": BASE_URL})
        smoke = smoke_tool_call()
        print("SMOKE " + json.dumps(smoke, ensure_ascii=False), flush=True)
        if not smoke["passed"]:
            raise RuntimeError("The required structured tool-call smoke did not pass; quality suite not started")
        for seed in SEEDS:
            results.append(run_eval(seed, server_pid, cg))
            write_json(receipts / "quality-progress.json", {"updated_at_utc": utc(), "seeds": results})
        write_json(receipts / "quality-final.json", {"status": "3_seeds_completed_pending_independent_audit", "started_at_utc": start,
                  "closed_at_utc": utc(), "suite": "Tool-Eval Bench 2.8.0 Hard Mode", "cases": 28, "seeds": results,
                  "decision": "pending score and critical-case audit; no production promotion"})
        return 0
    except BaseException as e:
        write_json(receipts / "quality-abort.json", {"status": "aborted_or_blocked", "at_utc": utc(), "error": f"{type(e).__name__}: {e}", "completed_seeds": results})
        raise
    finally:
        stop_owned(server_proc)
        post = {"at_utc": utc(), "inference_processes": inference_processes(), "cuda_compute_apps": compute_apps(),
                "meminfo": meminfo(), "gpu_temp_c": gpu_temp()}
        write_json(receipts / "gpu-postflight.json", post)
        print("POSTFLIGHT " + json.dumps(post, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
