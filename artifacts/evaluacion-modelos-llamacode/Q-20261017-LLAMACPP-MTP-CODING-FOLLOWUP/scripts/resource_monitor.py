#!/usr/bin/env python3
"""Log resources during a run and stop only this isolated server on guard breach."""
import argparse
import json
import pathlib
import subprocess
import time
import urllib.request
from datetime import datetime, timezone


def request(base, path, body=None, timeout=10):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        base + path, data=data,
        headers={"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read() or b"{}")


def prop(base, name):
    return request(base, "/prop?name=" + name)["value"]


def invoke(base, method):
    return request(base, "/invoke", {"method": method, "args": []})


def read_meminfo():
    result = {}
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        key, _, value = line.partition(":")
        if key in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
            result[key] = int(value.strip().split()[0]) * 1024
    return result


def read_vmstat():
    result = {}
    for line in pathlib.Path("/proc/vmstat").read_text().splitlines():
        key, value = line.split()
        if key in {"oom_kill", "pswpin", "pswpout"}:
            result[key] = int(value)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:18119")
    parser.add_argument("--baseline-swap-used", type=int, required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--interval", type=int, default=15)
    parser.add_argument("--max-seconds", type=int, default=11500)
    args = parser.parse_args()
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    initial_vmstat = read_vmstat()
    seen_running = False
    idle_after_run = 0
    deadline = time.monotonic() + args.max_seconds

    while time.monotonic() < deadline:
        mem = read_meminfo()
        swap_used = mem["SwapTotal"] - mem["SwapFree"]
        psi = pathlib.Path("/proc/pressure/memory").read_text()
        vmstat = read_vmstat()
        gpu = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,memory.used,memory.total,utilization.gpu",
             "--format=csv,noheader"], check=True, capture_output=True, text=True).stdout.strip()
        compute = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory",
             "--format=csv,noheader"], check=True, capture_output=True, text=True).stdout.strip()
        running = bool(prop(args.base, "benchmarkRunning"))
        server_state = prop(args.base, "serverState")
        status = prop(args.base, "benchmarkStatus")
        progress = prop(args.base, "benchmarkProgress")
        if running:
            seen_running = True
            idle_after_run = 0
        elif seen_running:
            idle_after_run += 1

        other_gpu_processes = []
        for line in compute.splitlines():
            if "llama-server" not in line:
                other_gpu_processes.append(line)
        breaches = []
        if mem["MemAvailable"] < 40 * (1024 ** 3):
            breaches.append("MemAvailable fell below 40 GiB")
        if swap_used > args.baseline_swap_used + 1024 ** 3:
            breaches.append("swap grew more than 1 GiB above the preflight baseline")
        if vmstat.get("oom_kill", 0) > initial_vmstat.get("oom_kill", 0):
            breaches.append("kernel OOM kill counter increased")
        if other_gpu_processes:
            breaches.append("another GPU compute process appeared")

        sample = {
            "time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "memory_bytes": mem,
            "swap_used_bytes": swap_used,
            "swap_baseline_bytes": args.baseline_swap_used,
            "memory_pressure": psi,
            "vmstat": vmstat,
            "gpu": gpu,
            "gpu_compute_apps": compute,
            "benchmark_running": running,
            "benchmark_status": status,
            "benchmark_progress": progress,
            "server_state": server_state,
            "breaches": breaches,
        }
        with out.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(sample, ensure_ascii=False) + "\n")
        print(json.dumps(sample, ensure_ascii=False), flush=True)

        if breaches:
            sample["action"] = "stop isolated model server"
            try:
                if running:
                    sample["cancel"] = invoke(args.base, "cancelBenchmark")
                    for _ in range(60):
                        if not prop(args.base, "benchmarkRunning"):
                            break
                        time.sleep(1)
                sample["stop_server"] = invoke(args.base, "stopServer")
            except Exception as exc:  # record every guard action/failure
                sample["stop_error"] = str(exc)
            with out.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(sample, ensure_ascii=False) + "\n")
            return 3

        if seen_running and idle_after_run >= 2:
            return 0
        time.sleep(max(1, args.interval))

    print(json.dumps({"event": "monitor_deadline", "max_seconds": args.max_seconds}), flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
