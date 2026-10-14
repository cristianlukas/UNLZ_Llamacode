#!/usr/bin/env python3
"""Run the official LlamaCode HE0 -> HE20 -> BCB8 ladder through ControlApi."""
import argparse
import json
import pathlib
import time
import urllib.error
import urllib.request

HE0 = "059b6f00-7b4b-48ff-a3a2-2a71f900c1c0"
HE20 = "267bb33d-4510-417b-ae3c-6dbbfb2cb08d"
BCB8 = "05c28394-11d0-41fe-a55f-b3cb69db9c15"


def request(url, body=None, timeout=60):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else {}


def invoke(base, method, args):
    return request(base + "/invoke", {"method": method, "args": args}, timeout=120)


def prop(base, name):
    return request(base + "/prop?name=" + name)["value"]


def setprop(base, name, value):
    return request(base + "/setprop", {"name": name, "value": value})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--base", default="http://127.0.0.1:8877")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--max-wait", type=int, default=10800)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    events = []

    def record(event, **fields):
        row = {"time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "event": event, **fields}
        events.append(row)
        out.with_suffix(".events.jsonl").open("a", encoding="utf-8").write(json.dumps(row, ensure_ascii=False) + "\n")
        print(json.dumps(row, ensure_ascii=False), flush=True)

    base = args.base
    request(base + "/health")
    menu = invoke(base, "launchMenu", []).get("result", [])
    launch = next((p for p in menu if p.get("id") == args.profile), None)
    if not launch or not launch.get("ready"):
        raise SystemExit(f"Launch profile missing/not ready: {launch}")
    record("preflight", label=args.label, launch=launch)
    if prop(base, "benchmarkRunning"):
        raise SystemExit("A benchmark is already running")
    record("set_approval", response=setprop(base, "agentApprovalMode", "super"))
    record("set_thinking", response=setprop(base, "agentThinkingEnabled", True))
    record("start_agent", response=invoke(base, "startServerAndAgent", [args.profile]))

    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        running = prop(base, "agentRunning")
        starting = prop(base, "agentStarting")
        if running:
            break
        if not starting and not running:
            status = prop(base, "agentLog")
            if status:
                record("agent_log", tail=str(status)[-8000:])
            time.sleep(5)
        else:
            time.sleep(3)
    if not prop(base, "agentRunning"):
        raise SystemExit("Agent failed to become ready within 300 seconds")
    record("agent_ready", model=launch.get("name"), server_state=prop(base, "serverState"))

    start = invoke(base, "startThreeStageBenchmark", [[args.profile], HE0, HE20, BCB8,
                                                         1, "agent", args.timeout, "agent-maximo"])
    record("benchmark_start", response=start, stages={"he0": HE0, "he20": HE20, "bcb8": BCB8},
           passes=1, target="agent", agent_profile="agent-maximo", timeout_sec=args.timeout)
    if start.get("ok") is False:
        raise SystemExit(f"Benchmark rejected: {start}")

    deadline = time.monotonic() + args.max_wait
    while time.monotonic() < deadline:
        running = prop(base, "benchmarkRunning")
        progress = prop(base, "benchmarkProgress")
        status = prop(base, "benchmarkStatus")
        record("benchmark_poll", running=running, progress=progress, status=status)
        if not running:
            break
        time.sleep(15)
    else:
        record("benchmark_timeout", max_wait_sec=args.max_wait)
        raise SystemExit("Benchmark wait limit reached; preserve active benchmark and resume via API")

    result = {
        "label": args.label,
        "profileId": args.profile,
        "agentProfileId": "agent-maximo",
        "serverState": prop(base, "serverState"),
        "agentRunning": prop(base, "agentRunning"),
        "benchmarkStatus": prop(base, "benchmarkStatus"),
        "benchmarkProgress": prop(base, "benchmarkProgress"),
        "benchmarkResults": prop(base, "benchmarkResults"),
        "benchmarkCoverage": [x for x in prop(base, "benchmarkCoverage") if x.get("profileId") == args.profile],
        "events": events,
    }
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    record("benchmark_complete", status=result["benchmarkStatus"], results_file=str(out))


if __name__ == "__main__":
    main()
