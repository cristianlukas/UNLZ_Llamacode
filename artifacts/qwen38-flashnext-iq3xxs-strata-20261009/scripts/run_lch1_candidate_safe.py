#!/usr/bin/env python3
"""Run one LlamaCode custom benchmark and save only its new, matching result."""
import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path


def call(base, path, payload=None):
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
    return call(base, "/prop?" + query)["value"]


def invoke(base, method, args):
    return call(base, "/invoke", {"method": method, "args": args})


def run(base, profile, suite_id, timeout, out, thinking_enabled):
    if prop(base, "benchmarkRunning"):
        raise RuntimeError("ya hay un benchmark activo; no se inició otro")

    setting = call(base, "/setprop", {
        "name": "agentThinkingEnabled", "value": thinking_enabled
    })
    if not setting.get("ok"):
        raise RuntimeError(f"no se pudo fijar agentThinkingEnabled: {setting}")
    if bool(prop(base, "agentThinkingEnabled")) != thinking_enabled:
        raise RuntimeError("agentThinkingEnabled no quedó con el valor solicitado")

    suites = prop(base, "customBenchmarks")
    suite = next((item for item in suites if item.get("id") == suite_id), None)
    if not suite:
        raise RuntimeError(f"suite desconocida: {suite_id}")
    expected_name = suite.get("name")
    before = prop(base, "benchmarkResults")
    prior_ids = {item.get("id") for item in before if item.get("id")}

    timeout = max(1, min(timeout, 1800))  # LlamaCode enforces a 30-minute cap.
    response = invoke(
        base,
        "startCustomBenchmark",
        [[profile], suite_id, 1, "agent", timeout, "agent-maximo"],
    )
    if response.get("error"):
        raise RuntimeError(response["error"])

    started = time.monotonic()
    last = None
    was_running = False
    while True:
        running = bool(prop(base, "benchmarkRunning"))
        status = str(prop(base, "benchmarkStatus"))
        progress = prop(base, "benchmarkProgress")
        was_running = was_running or running
        state = {"running": running, "progress": progress, "status": status}
        if state != last:
            print(json.dumps(state, ensure_ascii=False), flush=True)
            last = state
        if not running:
            if was_running:
                break
            if time.monotonic() - started > 10:
                raise RuntimeError(f"benchmark no inició; resultado/status: {status}")
        if time.monotonic() - started > timeout + 300:
            raise TimeoutError(status)
        time.sleep(2 if not was_running else 10)

    invoke(base, "loadBenchmarkResults", [])
    rows = prop(base, "benchmarkResults")
    selected = [
        item for item in rows
        if item.get("id") not in prior_ids
        and item.get("profileId") == profile
        and item.get("benchmarkName") == expected_name
    ]
    if not selected:
        raise RuntimeError(
            "la ejecución terminó sin una fila nueva que coincida con el perfil y la suite; "
            "no se guardará un resultado anterior"
        )

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "suiteId": suite_id,
        "suiteName": expected_name,
        "profileId": profile,
        "thinkingEnabled": thinking_enabled,
        "completedAtUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "results": selected,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"saved": str(out), "resultCount": len(selected)}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:8898")
    parser.add_argument("--profile", default="test-strata-unsloth-udq4")
    parser.add_argument("--suite", required=True)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--thinking", choices=("on", "off"), required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    call(args.endpoint, "/health")
    run(args.endpoint, args.profile, args.suite, args.timeout, args.out, args.thinking == "on")


if __name__ == "__main__":
    main()
