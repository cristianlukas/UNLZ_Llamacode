#!/usr/bin/env python3
"""Run the app's native Server Speed v1 benchmark against an external local model."""
import argparse
import json
import shutil
import time
import urllib.parse
import urllib.request
from pathlib import Path


def request(base, path, payload=None):
    body = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        base + path,
        data=body,
        headers={"Content-Type": "application/json"} if body is not None else {},
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def prop(base, name):
    query = urllib.parse.urlencode({"name": name})
    return request(base, "/prop?" + query)["value"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:8898")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--runtime-data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--passes", type=int, default=2)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--max-prefill-tokens", type=int, default=65536)
    args = parser.parse_args()

    request(args.endpoint, "/health")
    if prop(args.endpoint, "benchmarkRunning"):
        raise RuntimeError("another benchmark is already running")

    runs_root = args.runtime_data / "LlamaCode" / "LlamaCode" / "benchmark-runs"
    before = {p.name for p in runs_root.glob("server_speed_*") if p.is_dir()}
    started = request(args.endpoint, "/invoke", {
        "method": "startServerSpeedBenchmark",
        "args": [[args.profile], args.passes, args.warmup, True, False,
                 args.max_prefill_tokens, 1, 1],
    })
    if started.get("error"):
        raise RuntimeError(started["error"])

    began = time.monotonic()
    last = None
    observed_running = False
    while True:
        running = bool(prop(args.endpoint, "benchmarkRunning"))
        status = str(prop(args.endpoint, "benchmarkStatus"))
        progress = prop(args.endpoint, "benchmarkProgress")
        observed_running = observed_running or running
        state = {"running": running, "progress": progress, "status": status}
        if state != last:
            print(json.dumps(state, ensure_ascii=False), flush=True)
            last = state
        if not running and observed_running:
            break
        if not observed_running and time.monotonic() - began > 10:
            raise RuntimeError(f"benchmark did not start: {status}")
        if time.monotonic() - began > args.timeout:
            raise TimeoutError(status)
        time.sleep(2 if not observed_running else 5)

    candidates = [p for p in runs_root.glob("server_speed_*")
                  if p.is_dir() and p.name not in before]
    if len(candidates) != 1:
        raise RuntimeError(f"expected exactly one new native receipt, found {len(candidates)}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(candidates[0], args.out)
    print(json.dumps({"receipt": str(candidates[0]), "copiedTo": str(args.out)},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
