import json
import time
from pathlib import Path
from urllib.request import Request, urlopen

base = Path(__file__).parent
url = "http://127.0.0.1:18888"

def call(path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = Request(url + path, data=data, headers={"Content-Type": "application/json"} if data else {})
    start = time.monotonic()
    with urlopen(req, timeout=180) as resp:
        raw = resp.read()
        status = resp.status
    elapsed = time.monotonic() - start
    return status, raw, elapsed, json.loads(raw)

status, raw, elapsed, models = call("/v1/models")
(base / "api-models.json").write_bytes(raw + b"\n")
assert status == 200, status
assert any(item.get("id") == "qwen3.8-27b" for item in models.get("data", [])), models

common = {"model": "qwen3.8-27b", "temperature": 0.6, "top_p": 0.95, "top_k": 20, "min_p": 0.0, "seed": 4242}
plain = dict(common, messages=[{"role": "user", "content": "Cuánto es 2 + 2? Respondé únicamente con el resultado."}], max_tokens=32)
plain_status, plain_raw, plain_elapsed, plain_response = call("/v1/chat/completions", plain)
(base / "chat-smoke.json").write_bytes(plain_raw + b"\n")
assert plain_status == 200, plain_status
choice = plain_response["choices"][0]
content = choice["message"].get("content") or ""
assert content.strip(), plain_response

request = dict(common,
    messages=[{"role": "user", "content": "Usá la herramienta record_sum con a=2 y b=2. No respondas con texto."}],
    tools=[{"type": "function", "function": {"name": "record_sum", "description": "Registra dos enteros para sumar", "parameters": {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}, "required": ["a", "b"], "additionalProperties": False}}}],
    tool_choice="auto", max_tokens=96)
tool_status, tool_raw, tool_elapsed, tool_response = call("/v1/chat/completions", request)
(base / "tool-smoke.json").write_bytes(tool_raw + b"\n")
assert tool_status == 200, tool_status
choice = tool_response["choices"][0]
message = choice["message"]
calls = message.get("tool_calls") or []
parsed = []
for item in calls:
    fn = item.get("function", {})
    parsed.append({"name": fn.get("name"), "arguments": json.loads(fn.get("arguments") or "{}")})
summary = {
    "models_status": 200,
    "served_model": "qwen3.8-27b",
    "plain_status": plain_status,
    "plain_content": content,
    "plain_elapsed_sec": plain_elapsed,
    "plain_usage": plain_response.get("usage"),
    "tool_status": tool_status,
    "tool_calls": parsed,
    "tool_elapsed_sec": tool_elapsed,
    "tool_usage": tool_response.get("usage"),
}
(base / "api-smoke-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
assert any(c["name"] == "record_sum" and c["arguments"] == {"a": 2, "b": 2} for c in parsed), summary
print(json.dumps(summary, ensure_ascii=False, indent=2))
