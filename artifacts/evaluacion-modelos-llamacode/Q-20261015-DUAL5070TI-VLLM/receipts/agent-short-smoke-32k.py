import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

base = "http://127.0.0.1:8877"
server = "http://127.0.0.1:18888"
prompt = "Responde exactamente OK, sin usar herramientas."
out = Path(__file__).with_name("agent-short-smoke-32k.json")


def get_json(url):
    with urlopen(url, timeout=15) as response:
        return json.loads(response.read())


def get_health(url):
    with urlopen(url, timeout=15) as response:
        return {"statusCode": response.status, "body": response.read().decode("utf-8", "replace")}


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


def prop(name):
    return request("/prop?name=" + name).get("value")


started_at = datetime.now(timezone.utc).isoformat()
health = get_health(server + "/health")
models = get_json(server + "/v1/models")
model = next(row for row in models["data"] if row["id"] == "qwen3.8-27b")
messages_before = prop("agentMessages") or []
context_limit = prop("agentContextLimit")
if model.get("max_model_len") != 32768:
    raise RuntimeError(f"server model length is {model.get('max_model_len')}, expected 32768")
if context_limit != 32768:
    raise RuntimeError(f"agent context is {context_limit}, expected 32768")
if prop("agentRunning") is not True:
    raise RuntimeError("LlamaCode agent backend is not running")

invoke("sendToAgent", [prompt])
deadline = time.monotonic() + 600
messages_after = messages_before
while time.monotonic() < deadline:
    messages_after = prop("agentMessages") or []
    new_messages = messages_after[len(messages_before):]
    assistant = [m for m in new_messages if m.get("role") == "assistant"]
    if assistant and assistant[-1].get("typing") is False:
        break
    time.sleep(2)

new_messages = messages_after[len(messages_before):]
assistant = [m for m in new_messages if m.get("role") == "assistant"]
agent_log = prop("agentLog") or ""
result = {
    "startedAtUtc": started_at,
    "finishedAtUtc": datetime.now(timezone.utc).isoformat(),
    "elapsedSec": 600 - max(0, deadline - time.monotonic()),
    "prompt": prompt,
    "expectedContext": 32768,
    "agentContextLimit": context_limit,
    "serverHealth": health,
    "model": model,
    "messageCountBefore": len(messages_before),
    "messageCountAfter": len(messages_after),
    "messages": new_messages,
    "assistantMessages": assistant,
    "agentLog": agent_log,
}
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in result.items() if k != "agentLog"},
                 ensure_ascii=False, indent=2))

if not assistant:
    raise SystemExit("agent smoke timed out or returned no assistant message")
answer = assistant[-1].get("content", "").strip()
if answer != "OK":
    raise SystemExit(f"expected exactly 'OK', got {answer!r}")
if "no entran en n_ctx" in agent_log or "protocolo textual" in agent_log:
    raise SystemExit("agent fell back from native tools despite the 32k context")
