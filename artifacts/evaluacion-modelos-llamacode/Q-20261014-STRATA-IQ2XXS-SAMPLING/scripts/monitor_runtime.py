#!/usr/bin/env python3
"""Log memory pressure; SIGINT only the task-owned Strata PID at emergency levels."""
import argparse
import json
import os
import pathlib
import signal
import time


def read_memavailable_bytes():
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    return 0


def read_psi():
    result = {}
    for line in pathlib.Path("/proc/pressure/memory").read_text().splitlines():
        kind, rest = line.split(" ", 1)
        fields = dict(part.split("=", 1) for part in rest.split())
        result[kind] = {"avg10": float(fields["avg10"]), "avg60": float(fields["avg60"]),
                        "avg300": float(fields["avg300"]), "total": int(fields["total"])}
    return result


def read_vmstat():
    names = {"pswpin", "pswpout", "oom_kill"}
    result = {}
    for line in pathlib.Path("/proc/vmstat").read_text().splitlines():
        key, value = line.split()
        if key in names:
            result[key] = int(value)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", required=True, type=int, help="exact task-owned Strata server PID")
    parser.add_argument("--out", required=True, type=pathlib.Path)
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--sustain-seconds", type=float, default=30.0)
    parser.add_argument("--emergency-mem-gib", type=float, default=4.0)
    parser.add_argument("--emergency-full-psi", type=float, default=80.0)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    oom_baseline = read_vmstat().get("oom_kill", 0)
    low_mem_since = None
    full_psi_since = None
    decision = "monitoring"
    with args.out.open("a", encoding="utf-8") as handle:
        while pathlib.Path(f"/proc/{args.pid}").exists():
            now = time.time()
            mem = read_memavailable_bytes()
            psi = read_psi()
            vmstat = read_vmstat()
            low_mem = mem < args.emergency_mem_gib * 1024**3
            full_psi = psi.get("full", {}).get("avg10", 0.0) >= args.emergency_full_psi
            low_mem_since = now if low_mem and low_mem_since is None else (None if not low_mem else low_mem_since)
            full_psi_since = now if full_psi and full_psi_since is None else (None if not full_psi else full_psi_since)
            oom_increase = vmstat.get("oom_kill", 0) > oom_baseline
            reason = None
            if oom_increase:
                reason = "kernel_oom_kill_counter_increased"
            elif low_mem_since is not None and now - low_mem_since >= args.sustain_seconds:
                reason = "MemAvailable_below_emergency_floor_sustained"
            elif full_psi_since is not None and now - full_psi_since >= args.sustain_seconds:
                reason = "memory_PSI_full_critical_sustained"
            row = {"timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
                   "pid": args.pid, "memavailable_bytes": mem, "memory_psi_percent": psi,
                   "vmstat": vmstat, "decision": "emergency_interrupt" if reason else "continue",
                   "reason": reason}
            handle.write(json.dumps(row) + "\n")
            handle.flush()
            print(json.dumps(row), flush=True)
            if reason:
                try:
                    os.kill(args.pid, signal.SIGINT)
                    decision = reason
                except ProcessLookupError:
                    decision = "server_exited_before_interrupt"
                break
            time.sleep(args.interval)
    print(json.dumps({"decision": decision, "pid": args.pid}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
