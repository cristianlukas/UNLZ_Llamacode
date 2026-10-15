#!/usr/bin/env python3
"""Observe host memory pressure and stop only this task's SOL container at emergency."""
import argparse
import json
import pathlib
import subprocess
import time


def read_values(path, keys):
    result = {}
    for line in pathlib.Path(path).read_text().splitlines():
        key, value = line.split(":", 1) if ":" in line else line.split()
        if key in keys:
            result[key] = int(value.strip().split()[0])
    return result


def read_psi():
    result = {}
    for line in pathlib.Path("/proc/pressure/memory").read_text().splitlines():
        kind, values = line.split(" ", 1)
        row = dict(item.split("=", 1) for item in values.split())
        result[kind] = float(row.get("avg10", 0))
    return result


def is_running(container):
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Running}}", container],
        text=True, capture_output=True, check=False)
    return result.returncode == 0 and result.stdout.strip() == "true"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--container", default="llamacode-sol-eval-20261015")
    parser.add_argument("--out", required=True, type=pathlib.Path)
    parser.add_argument("--interval", type=float, default=5)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    initial = read_values("/proc/vmstat", {"oom_kill"}).get("oom_kill", 0)
    low_mem_since = None
    high_psi_since = None
    while is_running(args.container):
        mem = read_values("/proc/meminfo", {"MemAvailable"}).get("MemAvailable", 0) * 1024
        psi = read_psi()
        oom = read_values("/proc/vmstat", {"oom_kill"}).get("oom_kill", 0)
        now = time.time()
        low_mem_since = now if mem < 4 * 1024**3 and low_mem_since is None else (
            None if mem >= 4 * 1024**3 else low_mem_since)
        high_psi_since = now if psi.get("full", 0) >= 80 and high_psi_since is None else (
            None if psi.get("full", 0) < 80 else high_psi_since)
        row = {
            "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
            "mem_available_bytes": mem,
            "psi_memory_avg10_percent": psi,
            "oom_kill": oom,
        }
        reason = None
        if low_mem_since is not None and now - low_mem_since >= 30:
            reason = "MemAvailable below 4 GiB for 30 seconds"
        elif high_psi_since is not None and now - high_psi_since >= 30:
            reason = "PSI full avg10 at least 80 percent for 30 seconds"
        elif oom > initial:
            reason = "kernel oom_kill counter increased"
        if reason:
            stopped = subprocess.run(
                ["docker", "stop", "--time", "3", args.container],
                text=True, capture_output=True, check=False)
            row["emergency_stop"] = {
                "reason": reason,
                "command": ["docker", "stop", "--time", "3", args.container],
                "return_code": stopped.returncode,
                "stdout": stopped.stdout.strip(),
                "stderr": stopped.stderr.strip(),
            }
            with args.out.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row) + "\n")
            print(json.dumps(row), flush=True)
            return 2
        with args.out.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")
        print(json.dumps(row), flush=True)
        time.sleep(args.interval)
    print(json.dumps({"event": "container_stopped",
                      "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}),
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
