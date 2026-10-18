#!/usr/bin/env python3
"""Run the remaining BCB8 control screen against the isolated LlamaCode API."""
import argparse
import json
import pathlib
import time
import urllib.request


def request(url, body=None, timeout=60):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode()
        return json.loads(raw) if raw else {}


def invoke(base, method, args):
    return request(base + "/invoke", {"method": method, "args": args}, timeout=120)


def prop(base, name):
    return request(base + "/prop?name=" + name)["value"]


def setprop(base, name, value):
    return request(base + "/setprop", {"name": name, "value": value})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="q4-mtp-off-he-20261013")
    parser.add_argument("--suite", default="05c28394-11d0-41fe-a55f-b3cb69db9c15")
    parser.add_argument("--label", default="Q4 MTP-off BCB8 follow-up")
    parser.add_argument("--timeout", type=int, default=10800,
                        help="hard timeout for the whole run; default 3 hours")
    parser.add_argument("--max-wait", type=int, default=11100)
    parser.add_argument("--base", default="http://127.0.0.1:18119")
    parser.add_argument("--expected-fingerprint",
                        default="7f84727070a2fb93d008a42c90391f3904d800f7d7c2e67f173813ab0435ff89")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    def record(event, **fields):
        row = {"time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "event": event, **fields}
        with out.with_suffix(".events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(json.dumps(row, ensure_ascii=False), flush=True)

    base = args.base
    request(base + "/health")
    menu = invoke(base, "launchMenu", []).get("result", [])
    launch = next((item for item in menu if item.get("id") == args.profile), None)
    if not launch or not launch.get("ready"):
        raise SystemExit(f"Launch profile missing/not ready: {launch}")
    suite = next((item for item in prop(base, "customBenchmarks")
                  if item.get("id") == args.suite), None)
    if not suite or len(suite.get("prompts", [])) != 8:
        raise SystemExit(f"Expected the pinned 8-prompt BCB suite, found: {suite}")
    if prop(base, "benchmarkRunning"):
        raise SystemExit("A benchmark is already running")
    if prop(base, "serverState") != "stopped" or prop(base, "agentRunning"):
        raise SystemExit("Expected an unloaded isolated app before the BCB gate probe")
    record("set_approval", response=setprop(base, "agentApprovalMode", "super"))
    record("set_thinking", response=setprop(base, "agentThinkingEnabled", True))
    # Set the same agent profile that the real run uses before checking coverage.
    # An unknown suite returns before loading a model, but leaves the benchmark
    # agent selection in place for benchmarkCoverage and the actual run.
    record("gate_probe", response=invoke(base, "startCustomBenchmark",
           [[args.profile], "__preflight_missing_suite__", 1, "agent", args.timeout, "agent-maximo"]))
    coverage = next((row for row in prop(base, "benchmarkCoverage")
                     if row.get("profileId") == args.profile), None)
    record("preflight", launch=launch,
           suite={"id": suite.get("id"), "name": suite.get("name"),
                  "prompt_count": len(suite.get("prompts", []))},
           coverage=coverage)
    if not coverage or coverage.get("profileConfigFingerprint") != args.expected_fingerprint:
        raise SystemExit(f"Profile fingerprint mismatch; refusing model load: {coverage}")
    stages = coverage.get("stageStates", {})
    if stages.get("he0") != "valid" or stages.get("he20") != "valid" or stages.get("bcb") != "pending":
        raise SystemExit(f"BCB gate prerequisites are not valid; refusing model load: {coverage}")
    if prop(base, "benchmarkRunning"):
        raise SystemExit("Gate probe unexpectedly started a benchmark")
    if not prop(base, "agentRunning"):
        record("start_agent", response=invoke(base, "startServerAndAgent", [args.profile]))
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline and not prop(base, "agentRunning"):
            time.sleep(3)
        if not prop(base, "agentRunning"):
            raise SystemExit("Agent failed to become ready within 300 seconds")
    record("agent_ready", server_state=prop(base, "serverState"))

    response = invoke(base, "startCustomBenchmark",
                      [[args.profile], args.suite, 1, "agent", args.timeout, "agent-maximo"])
    record("benchmark_start", response=response, timeout_sec=args.timeout)
    deadline = time.monotonic() + args.max_wait
    while time.monotonic() < deadline:
        running = prop(base, "benchmarkRunning")
        status = prop(base, "benchmarkStatus")
        progress = prop(base, "benchmarkProgress")
        record("benchmark_poll", running=running, status=status, progress=progress)
        if not running:
            break
        time.sleep(20)
    else:
        record("benchmark_timeout", max_wait_sec=args.max_wait)
        raise SystemExit("Wait limit reached; benchmark state left intact for recovery")

    result = {
        "label": args.label,
        "profileId": args.profile,
        "suiteId": args.suite,
        "agentProfileId": "agent-maximo",
        "serverState": prop(base, "serverState"),
        "agentRunning": prop(base, "agentRunning"),
        "benchmarkStatus": prop(base, "benchmarkStatus"),
        "benchmarkProgress": prop(base, "benchmarkProgress"),
        "benchmarkResults": prop(base, "benchmarkResults"),
        "benchmarkCoverage": [row for row in prop(base, "benchmarkCoverage")
                              if row.get("profileId") == args.profile],
    }
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    record("benchmark_complete", status=result["benchmarkStatus"], results_file=str(out))


if __name__ == "__main__":
    main()
