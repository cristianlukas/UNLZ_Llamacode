#!/usr/bin/env python3
"""Q81 host guard: inference servers and registered resource limits only.

GPU compute-app listings are recorded as telemetry. They do not block a run;
desktop applications such as ArtCraft are intentionally allowed to remain open.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import signal
import subprocess
import time
import urllib.request
from datetime import datetime, timezone


OWNED_UNIT = "q81-flashnext-app.service"
DEFAULT_API = "http://127.0.0.1:18129"
GIB = 1024 ** 3
MIN_MEM_AVAILABLE = 40 * GIB
MIN_SWAP_FREE = GIB

SERVER_EXE_NAMES = {
    "llama-server", "llama-server.exe", "ollama", "vllm",
    "text-generation-launcher", "text-generation-inference",
    "text_generation_server", "tritonserver", "aphrodite-engine",
    "koboldcpp", "koboldcpp.exe", "lmstudio", "local-ai",
    "llamafile", "llamafile.exe", "tabbyapi", "tabbyapi.exe",
}
SERVER_MODULES = {
    "vllm.entrypoints.openai.api_server", "sglang.launch_server",
    "aphrodite.endpoints.openai.api_server", "text_generation_server.cli",
    "mlx_lm.server", "lmdeploy.serve",
}
MODEL_FLAGS = {"--model", "--model-path", "--model-id", "--gguf", "--weights", "--checkpoint"}
SERVER_WORDS = {"server", "serve", "api", "inference", "openai"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def run(argv: list[str], timeout: int = 10) -> dict:
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
        return {"exit_code": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    except Exception as exc:  # record unavailability without a traceback
        return {"exit_code": None, "stdout": "", "stderr": f"{type(exc).__name__}: {exc}"}


def read_meminfo() -> dict[str, int]:
    result: dict[str, int] = {}
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        key, _, raw = line.partition(":")
        if key in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
            result[key] = int(raw.strip().split()[0]) * 1024
    return result


def read_vmstat() -> dict[str, int]:
    wanted = {"oom_kill", "pswpin", "pswpout"}
    result: dict[str, int] = {}
    for line in pathlib.Path("/proc/vmstat").read_text().splitlines():
        key, value = line.split()
        if key in wanted:
            result[key] = int(value)
    return result


def _proc_stat(pid: int) -> tuple[int, int] | None:
    try:
        raw = pathlib.Path(f"/proc/{pid}/stat").read_text()
        fields = raw.rsplit(")", 1)[1].strip().split()
        return int(fields[1]), int(fields[19])  # ppid, start ticks
    except (OSError, ValueError, IndexError):
        return None


def _peritosoft_path(value: str) -> bool:
    normalized = value.replace("\\", "/").lower()
    return any("peritosoft" in part for part in normalized.split("/"))


def is_peritosoft_process(comm: str, exe: str, argv: list[str]) -> bool:
    if _peritosoft_path(exe) or _peritosoft_path(comm):
        return True
    for arg in argv:
        # Ignore option names such as --kill-peritosoft-if-server. Accept
        # filesystem paths and Python module names that identify the app.
        if arg.startswith("-"):
            continue
        if ("/" in arg or "\\" in arg) and _peritosoft_path(arg):
            return True
        module_root = arg.lower().split(".", 1)[0]
        if module_root in {"peritosoft", "peritosoftserver"}:
            return True
    return False


def process_snapshot() -> dict[int, dict]:
    processes: dict[int, dict] = {}
    try:
        entries = list(pathlib.Path("/proc").iterdir())
    except OSError:
        return processes
    for entry in entries:
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            comm = (entry / "comm").read_text().strip()
            argv = [x.decode(errors="replace") for x in (entry / "cmdline").read_bytes().split(b"\0") if x]
            exe = os.readlink(entry / "exe")
            cgroups = (entry / "cgroup").read_text()
        except (OSError, PermissionError):
            continue
        stat = _proc_stat(pid)
        if stat is None:
            continue
        ppid, start_ticks = stat
        perito = is_peritosoft_process(comm, exe, argv)
        processes[pid] = {
            "pid": pid,
            "ppid": ppid,
            "start_ticks": start_ticks,
            "comm": comm,
            "exe": exe,
            "argv": argv,
            "cgroups": cgroups,
            "peritosoft": perito,
            "owned": OWNED_UNIT in cgroups,
        }
    return processes


def _python_module(record: dict) -> str | None:
    exe_name = pathlib.Path(record["exe"]).name.lower()
    if not (exe_name.startswith("python") or exe_name in {"pypy", "pypy3"}):
        return None
    argv = record["argv"]
    for i, arg in enumerate(argv[:-1]):
        if arg == "-m":
            return argv[i + 1].lower()
    return None


def server_process_reason(record: dict, listener_pids: set[int]) -> str | None:
    exe_name = pathlib.Path(record["exe"]).name.lower()
    comm = record["comm"].lower()
    if exe_name in SERVER_EXE_NAMES or comm in SERVER_EXE_NAMES:
        return "known_inference_server_executable"
    module = _python_module(record)
    if module in SERVER_MODULES:
        return "known_inference_server_python_module"
    if record["pid"] in listener_pids:
        argv_lower = [a.lower() for a in record["argv"]]
        has_model_arg = any(a in MODEL_FLAGS for a in argv_lower) or any(
            any(a.startswith(flag + "=") for flag in MODEL_FLAGS) for a in argv_lower
        )
        has_server_arg = any(
            word in pathlib.Path(a).name.lower() or word in a.lower()
            for a in argv_lower for word in SERVER_WORDS
        )
        if has_model_arg and has_server_arg:
            return "listener_with_model_and_server_arguments"
    return None


def listen_snapshot() -> dict:
    return run(["ss", "-ltnp"])


def listener_pids(ss_text: str) -> set[int]:
    return {int(x) for x in re.findall(r"pid=(\d+)", ss_text)}


def _is_descendant(pid: int, ancestor: int, processes: dict[int, dict]) -> bool:
    current = pid
    seen: set[int] = set()
    while current in processes and current not in seen:
        if current == ancestor:
            return True
        seen.add(current)
        current = processes[current]["ppid"]
    return False


def detect_external_servers(processes: dict[int, dict], ss: dict) -> tuple[list[dict], list[int], set[int]]:
    sockets_text = ss.get("stdout", "")
    pids = listener_pids(sockets_text)
    perito_roots = [pid for pid, p in processes.items() if p["peritosoft"] and not p["owned"]]
    servers: list[dict] = []
    perito_server_pids: set[int] = set()
    for pid, p in processes.items():
        if p["owned"]:
            continue
        reason = server_process_reason(p, pids)
        is_perito_listener = p["peritosoft"] and pid in pids
        perito_ancestor = any(_is_descendant(pid, root, processes) for root in perito_roots)
        if reason or is_perito_listener or (reason and perito_ancestor):
            tags = []
            if reason:
                tags.append(reason)
            if is_perito_listener or perito_ancestor:
                tags.append("peritosoft_tree")
                perito_server_pids.add(pid)
            servers.append({
                "pid": pid,
                "comm": p["comm"],
                "exe_basename": pathlib.Path(p["exe"]).name,
                "reasons": tags,
                "listening": pid in pids,
            })
    # A known inference-server child of PeritoSoft is covered even if the app
    # process itself does not own a listening socket.
    for server in servers:
        pid = server["pid"]
        if any(_is_descendant(pid, root, processes) for root in perito_roots):
            if "peritosoft_tree" not in server["reasons"]:
                server["reasons"].append("peritosoft_tree")
            perito_server_pids.add(pid)
    return servers, perito_roots, perito_server_pids


def _safe_identity(pid: int, start_ticks: int) -> bool:
    stat = _proc_stat(pid)
    return stat is not None and stat[1] == start_ticks


def terminate_peritosoft(processes: dict[int, dict], roots: list[int], server_pids: set[int]) -> dict:
    kill_pids = set(roots)
    for pid in list(processes):
        if any(_is_descendant(pid, root, processes) for root in roots):
            kill_pids.add(pid)
    kill_pids.update(server_pids)
    current_uid = os.getuid()
    sent: list[dict] = []
    for pid in sorted(kill_pids, reverse=True):
        p = processes.get(pid)
        if not p or p["owned"] or (not p["peritosoft"] and pid not in server_pids):
            continue
        try:
            status_info = pathlib.Path(f"/proc/{pid}/status").read_text()
            uid_line = next(x for x in status_info.splitlines() if x.startswith("Uid:"))
            real_uid = int(uid_line.split()[1])
            if real_uid != current_uid or not _safe_identity(pid, p["start_ticks"]):
                continue
            os.kill(pid, signal.SIGTERM)
            sent.append({"pid": pid, "signal": "SIGTERM", "comm": p["comm"]})
        except (OSError, StopIteration, ValueError):
            continue
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline and any(pathlib.Path(f"/proc/{x['pid']}").exists() for x in sent):
        time.sleep(0.2)
    for item in sent:
        p = processes.get(item["pid"])
        if p and pathlib.Path(f"/proc/{item['pid']}").exists() and _safe_identity(item["pid"], p["start_ticks"]):
            try:
                os.kill(item["pid"], signal.SIGKILL)
                item["escalated"] = True
            except OSError:
                pass
    return {"terminated": sent, "scope": "identified PeritoSoft process tree and its server only"}


def gpu_telemetry() -> dict:
    gpu = run([
        "nvidia-smi", "--query-gpu=index,name,memory.used,memory.total,temperature.gpu,utilization.gpu,power.draw",
        "--format=csv,noheader,nounits",
    ])
    compute = run([
        "nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader,nounits",
    ])
    return {"gpus": gpu, "compute_apps_telemetry_only": compute}


def disk_telemetry(model_path: str, output_path: str) -> dict:
    result = {}
    for key, path in (("model", model_path), ("output", output_path)):
        try:
            stat = os.statvfs(path)
            result[key] = {
                "path": path,
                "free_bytes": stat.f_bavail * stat.f_frsize,
                "total_bytes": stat.f_blocks * stat.f_frsize,
            }
        except OSError as exc:
            result[key] = {"path": path, "error": f"{type(exc).__name__}: {exc}"}
    return result


def collect(model_path: str, output_path: str) -> dict:
    processes = process_snapshot()
    ss = listen_snapshot()
    servers, perito_roots, perito_server_pids = detect_external_servers(processes, ss)
    pressure_path = pathlib.Path("/proc/pressure/memory")
    return {
        "at_utc": utc_now(),
        "memory_bytes": read_meminfo(),
        "vmstat": read_vmstat(),
        "memory_pressure": pressure_path.read_text() if pressure_path.exists() else "unavailable",
        "external_inference_servers": servers,
        "peritosoft_process_pids": perito_roots,
        "peritosoft_server_pids": sorted(perito_server_pids),
        "listeners": ss,
        "gpu": gpu_telemetry(),
        "disk": disk_telemetry(model_path, output_path),
        "processes": processes,
    }


def redact_sample(sample: dict) -> dict:
    result = dict(sample)
    result.pop("processes", None)
    return result


def evaluate(sample: dict, baseline_swap_used: int, baseline_oom: int) -> list[str]:
    mem = sample["memory_bytes"]
    breaches: list[str] = []
    if mem["MemAvailable"] < MIN_MEM_AVAILABLE:
        breaches.append("MemAvailable below 40 GiB")
    if mem["SwapFree"] < MIN_SWAP_FREE:
        breaches.append("SwapFree below 1 GiB")
    if sample["vmstat"].get("oom_kill", 0) > baseline_oom:
        breaches.append("kernel OOM-kill counter increased")
    if sample["external_inference_servers"]:
        breaches.append("external inference server detected")
    for label, result in sample["gpu"].items():
        if result.get("exit_code") != 0:
            breaches.append(f"GPU telemetry unavailable: {label}")
    if len(sample["gpu"]["gpus"].get("stdout", "").splitlines()) != 2:
        breaches.append("expected two GPUs; inventory differs or is unavailable")
    for disk in sample["disk"].values():
        if "error" in disk or disk.get("free_bytes", 0) <= 0:
            breaches.append("model or output disk unavailable/full")
    return breaches


def append_jsonl(path: pathlib.Path, item: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def request(base: str, path: str, body: dict | None = None, timeout: int = 8) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, headers={"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read()
        return json.loads(raw or b"{}")


def stop_owned_q81(base: str) -> dict:
    actions = []
    for method in ("cancelBenchmark", "stopServer"):
        try:
            response = request(base, "/invoke", {"method": method, "args": []})
            actions.append({"method": method, "response": response})
        except Exception as exc:
            actions.append({"method": method, "error": f"{type(exc).__name__}: {exc}"})
    systemd = run(["systemctl", "--user", "stop", OWNED_UNIT], timeout=15)
    actions.append({"systemd_user_stop_owned_unit": systemd})
    return {"actions": actions, "scope": OWNED_UNIT}


def self_test() -> dict:
    def record(pid: int, comm: str, exe: str, argv: list[str]) -> dict:
        return {"pid": pid, "ppid": 1, "start_ticks": 1, "comm": comm, "exe": exe, "argv": argv,
                "cgroups": "0::/user.slice", "peritosoft": False, "owned": False}
    artcraft = record(1, "artcraft-launch", "/tmp/artcraft-launch", ["/tmp/artcraft-launch"])
    llama = record(2, "llama-server", "/opt/llama-server", ["llama-server", "--port", "5001"])
    vllm = record(3, "python", "/usr/bin/python3", ["python3", "-m", "vllm.entrypoints.openai.api_server"])
    perito = record(4, "PeritoSoft", "/opt/PeritoSoft/server", ["/opt/PeritoSoft/server"])
    perito["peritosoft"] = True
    model_api = record(5, "python", "/usr/bin/python3", ["python3", "api_server.py", "--model", "/models/m.gguf"])
    owned_llama = record(6, "llama-server", "/opt/llama-server", ["llama-server", "--port", "5002"])
    owned_llama["cgroups"] = f"0::/user.slice/{OWNED_UNIT}"
    owned_llama["owned"] = True
    sample = {
        "memory_bytes": {"MemAvailable": 64 * GIB, "SwapTotal": 8 * GIB, "SwapFree": 7 * GIB},
        "vmstat": {"oom_kill": 0},
        "external_inference_servers": [],
        "gpu": {
            "gpus": {"exit_code": 0, "stdout": "0, RTX 3090\n1, RTX 3090"},
            "compute_apps_telemetry_only": {"exit_code": 0, "stdout": "44, artcraft-launch, 205 MiB"},
        },
        "disk": {"model": {"free_bytes": GIB}, "output": {"free_bytes": GIB}},
    }
    perito_servers, perito_roots, perito_server_pids = detect_external_servers(
        {4: perito}, {"stdout": "LISTEN 127.0.0.1:8900 users:((\"PeritoSoft\",pid=4,fd=5))"},
    )
    tests = {
        "gui_not_inference": server_process_reason(artcraft, {1}) is None,
        "peritosoft_option_flag_not_a_process": not is_peritosoft_process(
            "python3", "/usr/bin/python3",
            ["python3", "q81_resource_guard.py", "--kill-peritosoft-if-server"],
        ),
        "peritosoft_python_module_detected": is_peritosoft_process(
            "python3", "/usr/bin/python3", ["python3", "-m", "peritosoft.server"],
        ),
        "llama_server_detected": server_process_reason(llama, {2}) == "known_inference_server_executable",
        "vllm_module_detected": server_process_reason(vllm, {3}) == "known_inference_server_python_module",
        "peritosoft_listener_detected": bool(perito_servers) and perito_roots == [4] and perito_server_pids == {4},
        "model_api_listener_detection": server_process_reason(model_api, {5}) == "listener_with_model_and_server_arguments",
        "owned_q81_server_excluded": detect_external_servers(
            {6: owned_llama}, {"stdout": "LISTEN 127.0.0.1:5002 users:((\"llama-server\",pid=6,fd=5))"},
        )[0] == [],
        "gui_gpu_compute_does_not_block": evaluate(sample, 1 * GIB, 0) == [],
        "retained_swap_allocation_with_headroom_does_not_block": evaluate(
            {**sample, "memory_bytes": {**sample["memory_bytes"], "SwapTotal": 8 * GIB,
                                        "SwapFree": 6 * GIB}}, 0, 0,
        ) == [],
        "registered_memory_threshold_blocks": "MemAvailable below 40 GiB" in evaluate(
            {**sample, "memory_bytes": {**sample["memory_bytes"], "MemAvailable": 39 * GIB}}, 1 * GIB, 0,
        ),
        "registered_swap_free_floor_blocks": "SwapFree below 1 GiB" in evaluate(
            {**sample, "memory_bytes": {**sample["memory_bytes"], "SwapFree": GIB // 2}}, 0, 0,
        ),
        "registered_oom_counter_blocks": "kernel OOM-kill counter increased" in evaluate(
            {**sample, "vmstat": {**sample["vmstat"], "oom_kill": 1}}, 0, 0,
        ),
    }
    return {"at_utc": utc_now(), "self_test": tests, "passed": all(tests.values())}


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true", help="one-shot host preflight")
    mode.add_argument("--watch", action="store_true", help="monitor a live Q81 run")
    mode.add_argument("--self-test", action="store_true", help="CPU-only classifier checks")
    parser.add_argument("--out", required=False)
    parser.add_argument("--model-path", default="/media/cristian/Disco local/Strata-UD-Q4-review-20261003/models/unsloth-UD-Q4_K_XL")
    parser.add_argument(
        "--output-path",
        default=str(pathlib.Path(__file__).resolve().parents[1] / "runs"),
    )
    parser.add_argument("--api", default=DEFAULT_API)
    parser.add_argument("--baseline-swap-used", type=int)
    parser.add_argument("--baseline-oom-kill", type=int)
    parser.add_argument("--interval", type=int, default=10)
    parser.add_argument("--max-seconds", type=int, default=7200)
    parser.add_argument("--kill-peritosoft-if-server", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        result = self_test()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["passed"] else 1
    if not args.out:
        parser.error("--out is required for --once and --watch")

    out = pathlib.Path(args.out)
    sample = collect(args.model_path, args.output_path)
    mem = sample["memory_bytes"]
    swap_used = mem["SwapTotal"] - mem["SwapFree"]
    baseline_swap = args.baseline_swap_used if args.baseline_swap_used is not None else swap_used
    baseline_oom = args.baseline_oom_kill if args.baseline_oom_kill is not None else sample["vmstat"].get("oom_kill", 0)
    breaches = evaluate(sample, baseline_swap, baseline_oom)
    perito_stop = None
    if sample["peritosoft_server_pids"] and args.kill_peritosoft_if_server:
        perito_stop = terminate_peritosoft(sample["processes"], sample["peritosoft_process_pids"], set(sample["peritosoft_server_pids"]))
        breaches.append("PeritoSoft inference server detected; identified app/server tree stopped; re-preflight required")
    initial = redact_sample(sample)
    initial.update({
        "baseline_swap_used_bytes": baseline_swap,
        "baseline_oom_kill": baseline_oom,
        "breaches": breaches,
        "peritosoft_stop": perito_stop,
        "gpu_compute_apps_are_telemetry_only": True,
    })
    if args.once:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(initial, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(initial, ensure_ascii=False, indent=2))
        return 0 if not breaches else 3

    append_jsonl(out, initial)
    if breaches:
        cleanup = stop_owned_q81(args.api)
        failure = {"at_utc": utc_now(), "event": "guard_breach", "breaches": breaches, "cleanup": cleanup}
        append_jsonl(out, failure)
        print(json.dumps(failure, ensure_ascii=False), flush=True)
        return 3

    seen_running = False
    idle_after_run = 0
    deadline = time.monotonic() + max(1, args.max_seconds)
    while time.monotonic() < deadline:
        time.sleep(max(1, args.interval))
        sample = collect(args.model_path, args.output_path)
        breaches = evaluate(sample, baseline_swap, baseline_oom)
        try:
            running = bool(request(args.api, "/prop?name=benchmarkRunning").get("value"))
            status = request(args.api, "/prop?name=benchmarkStatus").get("value")
            progress = request(args.api, "/prop?name=benchmarkProgress").get("value")
        except Exception as exc:
            running, status, progress = False, None, None
            sample["api_probe_error"] = f"{type(exc).__name__}: {exc}"
        sample["benchmark_running"] = running
        sample["benchmark_status"] = status
        sample["benchmark_progress"] = progress
        sample["baseline_swap_used_bytes"] = baseline_swap
        sample["baseline_oom_kill"] = baseline_oom
        sample["breaches"] = breaches
        sample["gpu_compute_apps_are_telemetry_only"] = True
        append_jsonl(out, redact_sample(sample))
        print(json.dumps(redact_sample(sample), ensure_ascii=False), flush=True)
        if breaches:
            perito_stop = None
            if sample["peritosoft_server_pids"] and args.kill_peritosoft_if_server:
                perito_stop = terminate_peritosoft(sample["processes"], sample["peritosoft_process_pids"], set(sample["peritosoft_server_pids"]))
            cleanup = stop_owned_q81(args.api)
            failure = {"at_utc": utc_now(), "event": "guard_breach", "breaches": breaches,
                       "peritosoft_stop": perito_stop, "cleanup": cleanup}
            append_jsonl(out, failure)
            return 3
        if running:
            seen_running, idle_after_run = True, 0
        elif seen_running:
            idle_after_run += 1
            if idle_after_run >= 2:
                return 0

    timeout_event = {"at_utc": utc_now(), "event": "monitor_deadline", "max_seconds": args.max_seconds}
    append_jsonl(out, timeout_event)
    cleanup = stop_owned_q81(args.api)
    timeout_event["cleanup"] = cleanup
    append_jsonl(out, timeout_event)
    print(json.dumps(timeout_event, ensure_ascii=False), flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
