#!/usr/bin/env python3
"""Monitor the isolated benchmark using host pressure, not swap occupancy alone."""
import argparse
import json
import pathlib
import subprocess
import time
import urllib.request
from datetime import datetime, timezone

GIB = 1024 ** 3


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


def meminfo():
    result = {}
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        key, _, value = line.partition(":")
        if key in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
            result[key] = int(value.strip().split()[0]) * 1024
    return result


def vmstat():
    result = {}
    for line in pathlib.Path("/proc/vmstat").read_text().splitlines():
        key, value = line.split()
        if key in {"oom_kill", "pswpin", "pswpout"}:
            result[key] = int(value)
    return result


def psi_avg10():
    result = {}
    for line in pathlib.Path("/proc/pressure/memory").read_text().splitlines():
        fields = line.split()
        label = fields[0]
        result[label] = float(next(x.split("=", 1)[1] for x in fields if x.startswith("avg10=")))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:18119")
    parser.add_argument("--baseline-oom", type=int, required=True)
    parser.add_argument("--expected-server", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--interval", type=int, default=15)
    parser.add_argument("--max-seconds", type=int, default=11500)
    args = parser.parse_args()
    output = pathlib.Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    low_memory_samples = 0
    high_psi_samples = 0
    seen_activity = False
    idle_after_activity = 0
    startup_deadline = time.monotonic() + 420
    deadline = time.monotonic() + args.max_seconds

    while time.monotonic() < deadline:
        mem = meminfo()
        vm = vmstat()
        psi_raw = pathlib.Path("/proc/pressure/memory").read_text()
        psi = psi_avg10()
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
        active = running or server_state != "stopped"
        if active:
            seen_activity = True
            idle_after_activity = 0
        elif seen_activity:
            idle_after_activity += 1

        low_memory_samples = low_memory_samples + 1 if mem["MemAvailable"] < 20 * GIB else 0
        high_psi = psi.get("some", 0) >= 80 or psi.get("full", 0) >= 60
        high_psi_samples = high_psi_samples + 1 if high_psi else 0
        other_gpu = [line for line in compute.splitlines()
                     if line.strip() and args.expected_server not in line]
        breaches = []
        if low_memory_samples >= 15:
            breaches.append("MemAvailable <20 GiB for 15 consecutive samples")
        if high_psi_samples >= 15:
            breaches.append("memory PSI exceeded 80% some or 60% full for 15 consecutive samples")
        if vm.get("oom_kill", 0) > args.baseline_oom:
            breaches.append("kernel oom_kill counter increased")
        if other_gpu:
            breaches.append("unexpected GPU compute process appeared")

        sample = {
            "time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "memory_bytes": mem,
            "swap_used_bytes": mem["SwapTotal"] - mem["SwapFree"],
            "swap_free_bytes": mem["SwapFree"],
            "memory_pressure": psi_raw,
            "vmstat": vm,
            "gpu": gpu,
            "gpu_compute_apps": compute,
            "benchmark_running": running,
            "benchmark_status": status,
            "benchmark_progress": progress,
            "server_state": server_state,
            "low_memory_samples": low_memory_samples,
            "high_psi_samples": high_psi_samples,
            "breaches": breaches,
        }
        with output.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(sample, ensure_ascii=False) + "\n")
        print(json.dumps(sample, ensure_ascii=False), flush=True)

        if breaches:
            sample["action"] = "cancel isolated benchmark and stop isolated server"
            try:
                if running:
                    sample["cancel"] = invoke(args.base, "cancelBenchmark")
                    for _ in range(60):
                        if not prop(args.base, "benchmarkRunning"):
                            break
                        time.sleep(1)
                sample["stop_server"] = invoke(args.base, "stopServer")
            except Exception as exc:
                sample["stop_error"] = str(exc)
            with output.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(sample, ensure_ascii=False) + "\n")
            return 3

        if seen_activity and idle_after_activity >= 2:
            return 0
        if not seen_activity and time.monotonic() >= startup_deadline:
            return 2
        time.sleep(max(1, args.interval))

    print(json.dumps({"event": "monitor_deadline", "max_seconds": args.max_seconds}), flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
