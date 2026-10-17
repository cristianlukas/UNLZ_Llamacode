#!/usr/bin/env python3
"""Attach to an already-running benchmark and enforce its profile deadline."""
import argparse
import datetime as dt
import json
import pathlib
import subprocess
import time
import urllib.request


def request(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        raw = response.read().decode()
        return json.loads(raw) if raw else {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--started-utc", required=True)
    parser.add_argument("--global-deadline-utc", required=True)
    parser.add_argument("--expected-fingerprint", required=True)
    parser.add_argument("--base", default="http://127.0.0.1:18219")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    event_path = out.with_suffix(".events.jsonl")
    events = []

    def prop(name):
        return request(f"{args.base}/prop?name={name}")["value"]

    def record(event, **fields):
        row = {"time_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "event": event, **fields}
        events.append(row)
        with event_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(json.dumps(row, ensure_ascii=False), flush=True)

    deadline_utc = dt.datetime.fromisoformat(args.global_deadline_utc.replace("Z", "+00:00"))
    started_utc = dt.datetime.fromisoformat(args.started_utc.replace("Z", "+00:00"))
    if not prop("benchmarkRunning"):
        raise SystemExit("no active benchmark to monitor")
    coverage = next(row for row in prop("benchmarkCoverage")
                    if row.get("profileId") == args.profile)
    if coverage.get("profileConfigFingerprint") != args.expected_fingerprint:
        raise SystemExit("effective fingerprint changed")
    record("attach", stage=args.stage, started_utc=args.started_utc,
           deadline_utc=args.global_deadline_utc, coverage=coverage,
           status=prop("benchmarkStatus"), progress=prop("benchmarkProgress"))

    deadline = time.monotonic() + max(0, (deadline_utc - dt.datetime.now(dt.timezone.utc)).total_seconds())
    next_resource = time.monotonic()
    cancelled_at_cap = False
    while True:
        running = prop("benchmarkRunning")
        record("poll", running=running, status=prop("benchmarkStatus"),
               progress=prop("benchmarkProgress"))
        if not running:
            break
        now = time.monotonic()
        if now >= deadline:
            cancelled_at_cap = True
            record("global_profile_cap", deadline_utc=args.global_deadline_utc)
            body = json.dumps({"method": "cancelBenchmark", "args": []}).encode()
            req = urllib.request.Request(args.base + "/invoke", data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as response:
                record("cancel", response=json.load(response))
            cancel_deadline = time.monotonic() + 30
            while prop("benchmarkRunning") and time.monotonic() < cancel_deadline:
                time.sleep(1)
            break
        if now >= next_resource:
            mem = {}
            for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
                key, value = line.split(":", 1)
                if key in {"MemAvailable", "SwapFree", "SwapTotal"}:
                    mem[key] = value.strip()
            psi = pathlib.Path("/proc/pressure/memory").read_text()
            gpu = subprocess.run(["nvidia-smi", "--query-gpu=index,memory.used,utilization.gpu",
                                  "--format=csv,noheader"], capture_output=True,
                                 text=True, timeout=10, check=False)
            record("resource", meminfo=mem, memory_pressure=psi,
                   gpu_query=gpu.stdout.strip(), gpu_query_exit=gpu.returncode)
            next_resource = now + 120
        time.sleep(min(30, max(1, deadline - now)))

    finished = dt.datetime.now(dt.timezone.utc)
    start_ms = int(started_utc.timestamp() * 1000)
    result_rows = [row for row in prop("benchmarkResults")
                   if row.get("profileId") == args.profile
                   and int(row.get("timestamp", 0)) >= start_ms]
    current_coverage = next(row for row in prop("benchmarkCoverage")
                            if row.get("profileId") == args.profile)
    result = {
        "profile_id": args.profile,
        "stage": args.stage,
        "started_utc": args.started_utc,
        "finished_utc": finished.isoformat(timespec="seconds"),
        "elapsed_seconds": round((finished - started_utc).total_seconds(), 3),
        "global_profile_cap_reached": cancelled_at_cap,
        "benchmark_status": prop("benchmarkStatus"),
        "benchmark_progress": prop("benchmarkProgress"),
        "coverage": current_coverage,
        "results": result_rows,
        "server_state": prop("serverState"),
        "agent_running": prop("agentRunning"),
        "events": events,
    }
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("RESULT " + json.dumps({key: result[key] for key in (
        "finished_utc", "elapsed_seconds", "global_profile_cap_reached",
        "benchmark_status", "coverage", "results", "server_state", "agent_running")},
        ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
