#!/usr/bin/env python3
"""Run the LlamaCode ControlApi HE0 prerequisite, then one LC-H1 suite."""

import argparse
import json
import time
import urllib.request
from pathlib import Path


def call(base: str, path: str, payload=None):
    body = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        base + path,
        data=body,
        headers={"Content-Type": "application/json"} if body else {},
        method="POST" if body else "GET",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def prop(base: str, name: str):
    from urllib.parse import urlencode

    return call(base, "/prop?" + urlencode({"name": name}))["value"]


def invoke(base: str, method: str, args):
    return call(base, "/invoke", {"method": method, "args": args})


def run(base: str, profile: str, suite_id: str, timeout: int, out: Path):
    response = invoke(
        base,
        "startCustomBenchmark",
        [[profile], suite_id, 1, "agent", timeout, "agent-maximo"],
    )
    if response.get("error"):
        raise RuntimeError(response["error"])
    started = time.monotonic()
    last = None
    while True:
        running = prop(base, "benchmarkRunning")
        status = prop(base, "benchmarkStatus")
        progress = prop(base, "benchmarkProgress")
        state = (running, progress, status)
        if state != last:
            print(json.dumps({"running": running, "progress": progress, "status": status}), flush=True)
            last = state
        if not running:
            break
        if time.monotonic() - started > timeout + 300:
            raise TimeoutError(status)
        time.sleep(15)
    invoke(base, "loadBenchmarkResults", [])
    results = prop(base, "benchmarkResults")
    selected = [r for r in results if r.get("profileId") == profile]
    if not selected:
        selected = results[-3:]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(selected, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"saved": str(out), "resultCount": len(selected)}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:8898")
    parser.add_argument("--profile", default="test-strata-unsloth-udq4")
    parser.add_argument("--suite", required=True)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    call(args.endpoint, "/health")
    run(args.endpoint, args.profile, args.suite, args.timeout, Path(args.out))


if __name__ == "__main__":
    main()
