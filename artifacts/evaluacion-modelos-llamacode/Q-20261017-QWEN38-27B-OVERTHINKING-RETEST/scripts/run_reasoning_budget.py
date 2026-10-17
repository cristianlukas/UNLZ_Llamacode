#!/usr/bin/env python3
"""Run the preregistered direct-completion reasoning-budget probe."""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import time
import urllib.error
import urllib.request


def request(url, body=None, timeout=30):
    data = None if body is None else json.dumps(body).encode()
    headers = {} if data is None else {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode()
        return response.status, json.loads(raw) if raw else {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--expected-fingerprint", required=True)
    parser.add_argument("--deadline-utc", required=True)
    parser.add_argument("--suite", required=True)
    parser.add_argument("--base", default="http://127.0.0.1:18219")
    parser.add_argument("--server", default="http://127.0.0.1:8021")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    event_path = out.with_suffix(".events.jsonl")
    events = []
    results = []

    def prop(name):
        return request(f"{args.base}/prop?name={name}")[1]["value"]

    def invoke(method, values):
        return request(args.base + "/invoke", {"method": method, "args": values}, 120)[1]

    def record(event, **fields):
        row = {"time_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "event": event, **fields}
        events.append(row)
        with event_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        shown = dict(row)
        if event == "request_complete":
            shown.pop("content", None)
            shown.pop("reasoning_content", None)
            shown["content_chars"] = len(fields.get("content", ""))
            shown["reasoning_chars"] = len(fields.get("reasoning_content") or "")
        print(json.dumps(shown, ensure_ascii=False), flush=True)

    deadline_utc = dt.datetime.fromisoformat(args.deadline_utc.replace("Z", "+00:00"))
    suite_path = pathlib.Path(args.suite)
    suite = json.loads(suite_path.read_text())
    if prop("benchmarkRunning"):
        raise SystemExit("benchmark is active; refusing concurrent request")
    coverage = next(row for row in prop("benchmarkCoverage")
                    if row.get("profileId") == args.profile)
    if coverage.get("profileConfigFingerprint") != args.expected_fingerprint:
        raise SystemExit("effective fingerprint changed")
    record("preflight", profile_id=args.profile, fingerprint=coverage["profileConfigFingerprint"],
           deadline_utc=args.deadline_utc, server_state=prop("serverState"),
           agent_running=prop("agentRunning"), suite_sha256=hashlib.sha256(suite_path.read_bytes()).hexdigest())

    if prop("agentRunning"):
        record("stop_agent", response=invoke("stopAgent", []))
        stop_deadline = time.monotonic() + 30
        while prop("agentRunning") and time.monotonic() < stop_deadline:
            time.sleep(1)
    if prop("serverState") != "running":
        record("start_server", response=invoke("startServer", [args.profile]))

    ready_deadline = time.monotonic() + 240
    while time.monotonic() < ready_deadline:
        try:
            status, health = request(args.server + "/health", timeout=5)
            if status == 200 and health.get("status") == "ok":
                record("server_ready", health=health, server_state=prop("serverState"))
                break
        except Exception as error:
            record("server_loading", error=repr(error), server_state=prop("serverState"))
        time.sleep(10)
    else:
        raise SystemExit("server did not become healthy within 240 seconds")

    started = dt.datetime.now(dt.timezone.utc)
    aborted_by_deadline = False
    for task in suite["tasks"]:
        for budget in [0, 512, 2048]:
            if dt.datetime.now(dt.timezone.utc) >= deadline_utc:
                aborted_by_deadline = True
                break
            payload = {
                "model": "Qwen3.8-27B",
                "messages": [{"role": "user", "content": task["prompt"]}],
                "temperature": 0.6,
                "top_p": 0.95,
                "top_k": 20,
                "min_p": 0.0,
                "repeat_penalty": 1.0,
                "presence_penalty": 0.0,
                "seed": 4242,
                "max_tokens": 512,
                "reasoning_budget_tokens": budget,
                "chat_template_kwargs": {
                    "enable_thinking": budget > 0,
                    "reasoning_effort": "medium",
                },
                "stream": False,
            }
            body_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
            began = time.monotonic()
            record("request_start", task_id=task["id"], budget_tokens=budget,
                   seed=4242, payload_sha256=body_hash)
            row = {"task_id": task["id"], "category": task.get("category"),
                   "budget_tokens": budget, "seed": 4242,
                   "payload_sha256": body_hash, "request_started_utc":
                   dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
            try:
                status, response = request(args.server + "/v1/chat/completions", payload, timeout=120)
                choice = (response.get("choices") or [{}])[0]
                message = choice.get("message") or {}
                content = message.get("content") or ""
                lower = content.casefold()
                acceptance = task.get("acceptance", {})
                required = [str(value).casefold() for value in acceptance.get("contains", [])]
                forbidden = [str(value).casefold() for value in acceptance.get("forbid", [])]
                row.update({
                    "http_status": status,
                    "finish_reason": choice.get("finish_reason"),
                    "content": content,
                    "reasoning_content": message.get("reasoning_content"),
                    "usage": response.get("usage"),
                    "accepted": all(value in lower for value in required)
                                and not any(value in lower for value in forbidden),
                    "transport_valid": status == 200 and bool(response.get("choices")),
                })
                if choice.get("finish_reason") == "length":
                    row["incomplete_output"] = True
            except (urllib.error.URLError, TimeoutError, ValueError) as error:
                row.update({"transport_valid": False, "error": repr(error)})
            row["elapsed_seconds"] = round(time.monotonic() - began, 3)
            results.append(row)
            record("request_complete", **row)
        if aborted_by_deadline:
            break

    finished = dt.datetime.now(dt.timezone.utc)
    result = {
        "profile_id": args.profile,
        "profile_config_fingerprint": args.expected_fingerprint,
        "harness_spec_hash": "sha256:cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef",
        "suite_id": suite.get("id"),
        "suite_sha256": hashlib.sha256(suite_path.read_bytes()).hexdigest(),
        "started_utc": started.isoformat(timespec="seconds"),
        "finished_utc": finished.isoformat(timespec="seconds"),
        "elapsed_seconds": round((finished - started).total_seconds(), 3),
        "deadline_reached": aborted_by_deadline,
        "expected_requests": len(suite["tasks"]) * 3,
        "completed_requests": len(results),
        "results": results,
        "events": events,
    }
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        record("stop_server", response=invoke("stopServer", []))
    except Exception as error:
        record("stop_server_error", error=repr(error))
    print("RESULT " + json.dumps({key: result[key] for key in (
        "finished_utc", "elapsed_seconds", "deadline_reached", "expected_requests",
        "completed_requests")}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
