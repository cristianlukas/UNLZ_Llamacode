import json
import time
from pathlib import Path
from urllib.request import Request, urlopen

base = "http://127.0.0.1:8877"
launch_id = "60d6902d-f8c2-481a-84c1-1ef52fa169b4"
out = Path(__file__).with_name("llamacode-agent-start-32k.json")


def request(path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = Request(base + path, data=data,
                  headers={"Content-Type": "application/json"} if data else {})
    with urlopen(req, timeout=30) as response:
        raw = response.read()
    return json.loads(raw) if raw else {}


def invoke(method, args):
    result = request("/invoke", {"method": method, "args": args})
    if result.get("ok") is False:
        raise RuntimeError(result)
    return result.get("result")


def setprop(name, value):
    result = request("/setprop", {"name": name, "value": value})
    if result.get("ok") is False:
        raise RuntimeError(result)
    return result


def prop(name):
    return request("/prop?name=" + name).get("value")


events = [
    {"event": "approval", "result": setprop("agentApprovalMode", "super")},
    {"event": "thinking", "result": setprop("agentThinkingEnabled", True)},
    {"event": "active_agent_profile", "result": setprop("activeAgentProfileId", "agent-maximo")},
    {"event": "start", "result": invoke("startServerAndAgent", [launch_id])},
]
deadline = time.monotonic() + 240
while time.monotonic() < deadline:
    state = {
        "event": "poll",
        "serverState": prop("serverState"),
        "serverReady": prop("serverReady"),
        "agentRunning": prop("agentRunning"),
        "agentStarting": prop("agentStarting"),
    }
    events.append(state)
    if state["agentRunning"]:
        break
    time.sleep(3)

result = {
    "launchProfileId": launch_id,
    "profileContext": 32768,
    "events": events,
    "serverState": prop("serverState"),
    "serverReady": prop("serverReady"),
    "agentRunning": prop("agentRunning"),
    "agentStarting": prop("agentStarting"),
    "agentLog": prop("agentLog"),
}
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in result.items() if k != "agentLog"},
                 ensure_ascii=False, indent=2))
if not result["agentRunning"]:
    raise SystemExit("Agent did not become ready")
