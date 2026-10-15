#!/usr/bin/env python3
"""Record a non-invasive GPU/RAM/port preflight before Strata load."""
import argparse
import json
import pathlib
import re
import subprocess
import time


def command(*args):
    return subprocess.run(args, capture_output=True, text=True, check=False).stdout.strip()


def vmstat():
    values = {}
    for line in pathlib.Path("/proc/vmstat").read_text().splitlines():
        key, value = line.split()
        if key in {"pswpin", "pswpout"}:
            values[key] = int(value)
    return values


def meminfo():
    values = {}
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        key, value = line.split(":", 1)
        if key in {"MemAvailable", "SwapTotal", "SwapFree"}:
            values[key] = int(value.split()[0]) * 1024
    return values


def psi_avg10():
    lines = pathlib.Path("/proc/pressure/memory").read_text().splitlines()
    vals = {}
    for line in lines:
        kind, rest = line.split(" ", 1)
        match = re.search(r"avg10=([0-9.]+)", rest)
        vals[kind] = float(match.group(1)) if match else None
    return vals


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args()
    start_swap = vmstat()
    time.sleep(8)
    end_swap = vmstat()
    mem = meminfo()
    psi = psi_avg10()
    gpu = command("nvidia-smi", "--query-gpu=index,name,memory.used,memory.total,utilization.gpu", "--format=csv,noheader")
    ports = command("ss", "-ltnH")
    target_ports = [8350, 8351, 8352, 8877, 8898]
    listening = [line for line in ports.splitlines() if any(re.search(rf":{port}(?:\s|$)", line) for port in target_ports)]
    process_names = command("ps", "-eo", "pid,comm")
    relevant = [line.strip() for line in process_names.splitlines()
                if re.search(r"strata|llama|vllm|LlamaCode", line, re.I)]
    swap_delta = {key: end_swap[key] - start_swap[key] for key in start_swap}
    passed = (
        mem.get("MemAvailable", 0) >= 60 * 1024**3
        and max(psi.values(), default=1.0) < 0.1
        and all(value == 0 for value in swap_delta.values())
        and not listening
        and not relevant
    )
    receipt = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "meminfo_bytes": mem,
        "memory_psi_avg10_percent": psi,
        "swap_pages_delta_over_8s": swap_delta,
        "gpu_query": gpu,
        "candidate_ports_checked": target_ports,
        "listeners_on_candidate_ports": listening,
        "relevant_process_names": relevant,
        "thresholds": {
            "MemAvailable_min_bytes": 60 * 1024**3,
            "memory_psi_avg10_max": 0.1,
            "swap_activity_delta_required": 0,
            "candidate_ports_must_be_free": True,
            "inference_processes_must_be_absent": True,
        },
        "decision": "pass" if passed else "abort",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": receipt["decision"], "receipt": str(args.out),
                      "MemAvailable_bytes": mem.get("MemAvailable"),
                      "memory_psi_avg10_percent": psi,
                      "swap_pages_delta_over_8s": swap_delta,
                      "listeners": listening, "processes": relevant}), flush=True)
    return 0 if passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
