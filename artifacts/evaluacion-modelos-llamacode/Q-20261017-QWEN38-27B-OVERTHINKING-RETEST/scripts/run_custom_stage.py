#!/usr/bin/env python3
"""Run and receipt one isolated LlamaCode custom benchmark stage."""
import argparse
import datetime as dt
import json
import pathlib
import subprocess
import time
import urllib.request


def request(url, body=None, timeout=60):
    data = None if body is None else json.dumps(body).encode()
    headers = {} if data is None else {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode()
        return json.loads(raw) if raw else {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--suite", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--expected-fingerprint", required=True)
    parser.add_argument("--global-deadline-utc", required=True)
    parser.add_argument("--max-stage-sec", type=int, default=900)
    parser.add_argument("--base", default="http://127.0.0.1:18219")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    event_path = out.with_suffix(".events.jsonl")
    events = []

    def prop(name):
        return request(f"{args.base}/prop?name={name}")["value"]

    def invoke(method, values):
        return request(f"{args.base}/invoke", {"method": method, "args": values}, 120)

    def record(event, **fields):
        row = {
            "time_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "event": event,
            **fields,
        }
        events.append(row)
        with event_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(json.dumps(row, ensure_ascii=False), flush=True)

    deadline_utc = dt.datetime.fromisoformat(args.global_deadline_utc.replace("Z", "+00:00"))
    global_remaining = max(0, (deadline_utc - dt.datetime.now(dt.timezone.utc)).total_seconds())
    stage_limit = max(1, min(args.max_stage_sec, int(global_remaining)))
    if global_remaining <= 0:
        raise SystemExit("global profile deadline already reached")

    request(args.base + "/health")
    if prop("benchmarkRunning"):
        raise SystemExit("another benchmark is already running")
    coverage = next((row for row in prop("benchmarkCoverage")
                     if row.get("profileId") == args.profile), None)
    if not coverage:
        raise SystemExit("profile missing from benchmark coverage")
    if coverage.get("profileConfigFingerprint") != args.expected_fingerprint:
        raise SystemExit("effective fingerprint changed: " + str(coverage.get("profileConfigFingerprint")))
    if args.stage in {"he0", "he20", "bcb"} and coverage.get("nextStage") != args.stage:
        raise SystemExit(f"gate mismatch: requested {args.stage}, nextStage={coverage.get('nextStage')}")

    started = dt.datetime.now(dt.timezone.utc)
    started_ms = int(started.timestamp() * 1000)
    deadline = time.monotonic() + stage_limit
    record("preflight", coverage=coverage, server_state=prop("serverState"),
           agent_running=prop("agentRunning"), timeout_sec=stage_limit)
    start_response = invoke("startCustomBenchmark",
                            [[args.profile], args.suite, 1, "agent", stage_limit, "agent-maximo"])
    record("start", response=start_response, stage=args.stage, suite_id=args.suite)

    last_resource = 0.0
    timed_out = False
    while True:
        running = prop("benchmarkRunning")
        status = prop("benchmarkStatus")
        progress = prop("benchmarkProgress")
        record("poll", running=running, status=status, progress=progress)
        now = time.monotonic()
        if not running:
            break
        if now >= deadline:
            timed_out = True
            record("global_cap", max_stage_sec=stage_limit)
            invoke("cancelBenchmark", [])
            cancel_deadline = time.monotonic() + 30
            while prop("benchmarkRunning") and time.monotonic() < cancel_deadline:
                time.sleep(1)
            break
        if now - last_resource >= 60:
            mem = {}
            for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
                key, value = line.split(":", 1)
                if key in {"MemAvailable", "SwapFree", "SwapTotal"}:
                    mem[key] = value.strip()
            psi = pathlib.Path("/proc/pressure/memory").read_text()
            gpu = subprocess.run(
                ["nvidia-smi", "--query-gpu=index,memory.used,utilization.gpu", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=10, check=False)
            record("resource", meminfo=mem, memory_pressure=psi,
                   gpu_query=gpu.stdout.strip(), gpu_query_exit=gpu.returncode)
            last_resource = now
        time.sleep(min(15, max(1, deadline - now)))

    finished = dt.datetime.now(dt.timezone.utc)
    result_rows = [row for row in prop("benchmarkResults")
                   if row.get("profileId") == args.profile
                   and int(row.get("timestamp", 0)) >= started_ms]
    current_coverage = next((row for row in prop("benchmarkCoverage")
                             if row.get("profileId") == args.profile), None)
    result = {
        "profile_id": args.profile,
        "stage": args.stage,
        "suite_id": args.suite,
        "started_utc": started.isoformat(timespec="seconds"),
        "finished_utc": finished.isoformat(timespec="seconds"),
        "elapsed_seconds": round((finished - started).total_seconds(), 3),
        "timeout_sec": stage_limit,
        "global_cap_reached": timed_out,
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
        "finished_utc", "elapsed_seconds", "global_cap_reached", "benchmark_status",
        "coverage", "results", "server_state", "agent_running")}, ensure_ascii=False), flush=True)
    if timed_out:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
