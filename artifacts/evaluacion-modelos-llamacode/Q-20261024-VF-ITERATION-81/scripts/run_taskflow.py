#!/usr/bin/env python3
"""Run one imported LlamaCode custom suite against an isolated launch profile."""
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


def cancel_benchmark_and_wait(base, cancel_grace_sec, poll_sec, record):
    response = invoke(base, "cancelBenchmark", [])
    record("benchmark_cancel_requested", response=response)
    deadline = time.monotonic() + cancel_grace_sec
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        running = prop(base, "benchmarkRunning")
        status = prop(base, "benchmarkStatus")
        record("cancel_finalize_poll", running=running, status=status)
        if not running:
            return True
        time.sleep(min(poll_sec, remaining))
    return not prop(base, "benchmarkRunning")


def wait_for_benchmark(base, max_wait_sec, cancel_grace_sec, poll_sec, record):
    deadline = time.monotonic() + max_wait_sec
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        running = prop(base, "benchmarkRunning")
        status = prop(base, "benchmarkStatus")
        record("benchmark_poll", running=running, status=status)
        if not running:
            return {"runner_timed_out": False, "cancel_confirmed": None}
        time.sleep(min(poll_sec, remaining))

    record("benchmark_max_wait_reached", max_wait_sec=max_wait_sec)
    confirmed = cancel_benchmark_and_wait(base, cancel_grace_sec, poll_sec, record)
    record("benchmark_cancel_finalized", confirmed=confirmed,
           grace_sec=cancel_grace_sec)
    return {"runner_timed_out": True, "cancel_confirmed": confirmed}


def profile_fingerprint_matches(coverage, profile_id, expected_fingerprint):
    row = next((item for item in coverage or []
                if item.get("profileId") == profile_id), None)
    return bool(row and row.get("profileConfigFingerprint") == expected_fingerprint)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--suite", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--max-wait", type=int, default=1860)
    parser.add_argument("--cancel-grace", type=int, default=60)
    parser.add_argument("--poll-interval", type=int, default=15)
    parser.add_argument("--base", default="http://127.0.0.1:8877")
    parser.add_argument("--expected-fingerprint", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    events = []

    def record(event, **fields):
        row = {"time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "event": event, **fields}
        events.append(row)
        with out.with_suffix(".events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(json.dumps(row, ensure_ascii=False), flush=True)

    base = args.base
    request(base + "/health")
    menu = invoke(base, "launchMenu", []).get("result", [])
    launch = next((item for item in menu if item.get("id") == args.profile), None)
    if not launch or not launch.get("ready"):
        raise SystemExit(f"Launch profile missing/not ready: {launch}")
    if prop(base, "benchmarkRunning"):
        raise SystemExit("A benchmark is already running")
    suites = prop(base, "customBenchmarks")
    suite = next((item for item in suites if item.get("id") == args.suite), None)
    if not suite:
        raise SystemExit(f"Custom suite not available: {args.suite}")
    gate_probe = invoke(base, "startCustomBenchmark",
                        [[args.profile], "__preflight_missing_suite__", 1,
                         "agent", args.timeout, "agent-maximo"])
    record("profile_gate_probe", response=gate_probe)
    if prop(base, "benchmarkRunning"):
        raise SystemExit("Profile gate probe unexpectedly started a benchmark")
    coverage = prop(base, "benchmarkCoverage")
    if not profile_fingerprint_matches(coverage, args.profile, args.expected_fingerprint):
        raise SystemExit(f"Profile fingerprint mismatch; refusing model load: {coverage}")
    record("preflight", launch=launch,
           suite={"id": suite.get("id"), "name": suite.get("name"),
                  "prompt_count": len(suite.get("prompts", []))},
           expected_profile_fingerprint=args.expected_fingerprint)
    record("set_approval", response=setprop(base, "agentApprovalMode", "super"))
    record("set_thinking", response=setprop(base, "agentThinkingEnabled", True))
    if not prop(base, "agentRunning"):
        record("start_agent", response=invoke(base, "startServerAndAgent", [args.profile]))
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            if prop(base, "agentRunning"):
                break
            time.sleep(3)
        if not prop(base, "agentRunning"):
            raise SystemExit("Agent failed to become ready within 300 seconds")
    record("agent_ready", server_state=prop(base, "serverState"))

    start = invoke(base, "startCustomBenchmark",
                   [[args.profile], args.suite, 1, "agent", args.timeout, "agent-maximo"])
    record("benchmark_start", response=start, suite_id=args.suite,
           agent_profile="agent-maximo", timeout_sec=args.timeout)
    if start.get("ok") is False:
        raise SystemExit(f"Benchmark rejected: {start}")

    wait = wait_for_benchmark(base, args.max_wait, args.cancel_grace,
                              args.poll_interval, record)
    if wait["runner_timed_out"] and prop(base, "agentRunning"):
        record("residual_agent_stop_requested",
               response=invoke(base, "stopAgentByUser", []))
    if wait["runner_timed_out"] and prop(base, "serverState") == "running":
        record("residual_server_stop_requested", response=invoke(base, "stopServer", []))

    result = {
        "label": args.label,
        "profileId": args.profile,
        "agentProfileId": "agent-maximo",
        "serverState": prop(base, "serverState"),
        "agentRunning": prop(base, "agentRunning"),
        "benchmarkStatus": prop(base, "benchmarkStatus"),
        "benchmarkProgress": prop(base, "benchmarkProgress"),
        "benchmarkResults": prop(base, "benchmarkResults"),
        "benchmarkCoverage": [row for row in prop(base, "benchmarkCoverage")
                              if row.get("profileId") == args.profile],
        "runnerTimedOut": wait["runner_timed_out"],
        "cancelConfirmed": wait["cancel_confirmed"],
        "events": events,
    }
    if wait["runner_timed_out"]:
        record("benchmark_incomplete", status=result["benchmarkStatus"],
               cancel_confirmed=wait["cancel_confirmed"], results_file=str(out))
        result["events"] = events
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise SystemExit(2)
    record("benchmark_complete", status=result["benchmarkStatus"], results_file=str(out))
    result["events"] = events
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
