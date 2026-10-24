#!/usr/bin/env python3
"""Loopback-only OpenAI proxy that limits Q100 model tool calls by role."""
from __future__ import annotations

import http.client
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

UPSTREAM_PORT = int(os.environ.get("Q100_UPSTREAM_PORT", "8363"))
LISTEN_PORT = int(os.environ.get("Q100_PROXY_PORT", "8364"))
LOG_PATH = Path(os.environ.get("Q100_PROXY_LOG", "/tmp/q100-tool-guard.jsonl"))
LOG_LOCK = threading.Lock()


def tool_name(tool: dict) -> str:
    return str(tool.get("function", {}).get("name", ""))


def is_subagent(payload: dict) -> bool:
    for message in payload.get("messages", []):
        if message.get("role") == "system":
            content = str(message.get("content", "")).lower()
            return "sub-agente" in content and "worktree" in content
    return False


def allowed_tools(payload: dict) -> tuple[set[str], str]:
    if is_subagent(payload):
        return {"read_file"}, "subagent"
    return {"task"}, "parent"


def filter_request_tools(payload: dict) -> tuple[str, set[str]]:
    allowed, role = allowed_tools(payload)
    filtered = [tool for tool in payload.get("tools", []) if tool_name(tool) in allowed]
    present = {tool_name(tool) for tool in filtered}
    if present != allowed:
        raise ValueError(f"expected tool schema missing for role={role}: {sorted(allowed - present)}")
    payload["tools"] = filtered
    return role, allowed


def extract_tool_names(body: bytes) -> list[str]:
    names: dict[int, str] = {}
    lines = body.splitlines()
    if not any(line.strip().startswith(b"data:") for line in lines):
        try:
            event = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return []
        for choice in event.get("choices", []):
            message = choice.get("message", {})
            for index, call in enumerate(message.get("tool_calls", [])):
                name = str(call.get("function", {}).get("name", ""))
                if name:
                    names[index] = name
        return [name for _, name in sorted(names.items())]
    for raw_line in lines:
        line = raw_line.strip()
        if not line.startswith(b"data:"):
            continue
        data = line[5:].strip()
        if not data or data == b"[DONE]":
            continue
        try:
            event = json.loads(data)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        for choice in event.get("choices", []):
            delta = choice.get("delta", {})
            message = choice.get("message", {})
            calls = delta.get("tool_calls", message.get("tool_calls", []))
            for call in calls:
                function = call.get("function", {})
                index = int(call.get("index", len(names)))
                names[index] = names.get(index, "") + str(function.get("name", ""))
    return [name for _, name in sorted(names.items()) if name]


def append_record(record: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_LOCK:
        with LOG_PATH.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, _format, *_args):
        return

    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return
        payload = b'{"status":"ok","q100ToolFilter":true}\n'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 16 * 1024 * 1024:
                raise ValueError("invalid request length")
            payload = json.loads(self.rfile.read(length))
            role, allow = filter_request_tools(payload)
            upstream_body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            conn = http.client.HTTPConnection("127.0.0.1", UPSTREAM_PORT, timeout=900)
            conn.request("POST", self.path, body=upstream_body,
                         headers={"Content-Type": "application/json", "Connection": "close"})
            upstream = conn.getresponse()
            response_body = upstream.read()
            status = upstream.status
            response_type = upstream.getheader("Content-Type", "application/json")
            conn.close()
            observed = extract_tool_names(response_body)
            violations = sorted(set(observed) - allow)
            record = {"atUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      "role": role, "allowedTools": sorted(allow),
                      "observedToolNames": observed, "upstreamStatus": status,
                      "responseBytes": len(response_body), "blockedToolCall": bool(violations)}
            append_record(record)
            if violations:
                body = json.dumps({"error": "Q100 tool guard rejected model response",
                                   "blockedTools": violations}).encode("utf-8")
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(status)
            self.send_header("Content-Type", response_type)
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)
        except Exception as exc:
            body = json.dumps({"error": "Q100 proxy failure", "detail": str(exc)}).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", LISTEN_PORT), Handler)
    server.daemon_threads = True
    server.serve_forever(poll_interval=0.25)
