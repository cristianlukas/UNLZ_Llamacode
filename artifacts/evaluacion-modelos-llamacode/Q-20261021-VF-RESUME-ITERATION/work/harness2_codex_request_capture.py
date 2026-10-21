#!/usr/bin/env python3
"""Capture only structural metadata for one Codex Responses request."""

from __future__ import annotations

import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

TASK = Path(__file__).resolve().parents[1]
WORK = TASK / "work/harness2-codex-request-structure"
CODEX = Path("/home/cristian/.local/bin/codex").resolve()
PORT = 18104


def summarize(body: bytes) -> dict:
    payload = json.loads(body)
    items = payload.get("input", [])
    if isinstance(items, str):
        items = [{"type": "input_text", "role": "user", "text": items}]
    item_summaries = []
    for index, item in enumerate(items if isinstance(items, list) else []):
        if not isinstance(item, dict):
            item_summaries.append({"index": index, "value_type": type(item).__name__})
            continue
        contents = item.get("content", [])
        if isinstance(contents, str):
            contents = [{"type": "text", "text": contents}]
        content_summaries = []
        for content in contents if isinstance(contents, list) else []:
            if isinstance(content, dict):
                text = content.get("text")
                content_summaries.append({
                    "type": content.get("type"),
                    "keys": sorted(content.keys()),
                    "text_length": len(text) if isinstance(text, str) else None,
                })
        item_summaries.append({
            "index": index,
            "type": item.get("type"),
            "role": item.get("role"),
            "name": item.get("name"),
            "call_id": item.get("call_id"),
            "keys": sorted(item.keys()),
            "content": content_summaries,
        })
    tools = payload.get("tools", [])
    tool_summaries = []
    for tool in tools if isinstance(tools, list) else []:
        if isinstance(tool, dict):
            tool_summaries.append({
                "type": tool.get("type"),
                "name": tool.get("name"),
                "namespace": tool.get("namespace"),
                "keys": sorted(tool.keys()),
            })
    instructions = payload.get("instructions")
    return {
        "method": "POST",
        "path": "/v1/responses",
        "top_level_keys": sorted(payload.keys()),
        "instructions": {
            "present": isinstance(instructions, str),
            "length": len(instructions) if isinstance(instructions, str) else None,
            "sha256": hashlib.sha256(instructions.encode()).hexdigest() if isinstance(instructions, str) else None,
        },
        "input_item_count": len(items) if isinstance(items, list) else None,
        "input_items": item_summaries,
        "tools": tool_summaries,
        "raw_body_saved": False,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "LocalStructureCapture/1"

    def do_GET(self) -> None:
        body = json.dumps({"object": "list", "data": [{"id": "qwen-local", "object": "model"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        self.server.capture = summarize(body)  # type: ignore[attr-defined]
        self.server.received.set()  # type: ignore[attr-defined]
        response = json.dumps({"error": {"message": "intentional request-structure capture; no inference"}}).encode()
        self.send_response(500)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, fmt: str, *args: object) -> None:
        return


def inside() -> dict:
    subprocess.run(["ip", "link", "set", "lo", "up"], check=True, capture_output=True)
    workspace = Path("/tmp/workspace")
    codex_home = Path("/tmp/codex-home")
    config = '''model = "qwen-local"
model_provider = "capture"
model_context_window = 16384
model_reasoning_effort = "low"
approval_policy = "never"
sandbox_mode = "danger-full-access"

[model_providers.capture]
name = "Local structure capture"
base_url = "http://127.0.0.1:18104/v1"
env_key = "HARNESS2_CODEX_API_KEY"
wire_api = "responses"
requires_openai_auth = false
request_max_retries = 0
stream_max_retries = 0
'''
    (codex_home / "config.toml").write_text(config, encoding="utf-8")
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    server.received = threading.Event()  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    env = {
        "HOME": "/tmp/codex-home",
        "CODEX_HOME": "/tmp/codex-home",
        "HARNESS2_CODEX_API_KEY": "local-structure-capture-only",
        "PATH": "/tmp/tools:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "NO_PROXY": "127.0.0.1,localhost",
        "no_proxy": "127.0.0.1,localhost",
    }
    prompt = "Use a file tool to create canary.txt with exactly TOOL_LOOP_OK, then read it back."
    cmd = [
        "/tmp/tools/codex", "exec", prompt, "--model", "qwen-local",
        "--skip-git-repo-check", "--dangerously-bypass-approvals-and-sandbox",
        "--dangerously-bypass-hook-trust", "--ephemeral", "--json", "-C", "/tmp/workspace",
        "--add-dir", "/tmp/workspace", "--color", "never",
    ]
    try:
        result = subprocess.run(cmd, cwd=workspace, env=env, capture_output=True, text=True, timeout=60)
        got_request = server.received.wait(timeout=5)  # type: ignore[attr-defined]
        return {
            "status": "request_captured" if got_request else "no_request",
            "codex_exit_code": result.returncode,
            "request_structure": getattr(server, "capture", None),
            "codex_error_tail": result.stderr[-2000:],
            "codex_stdout_tail": result.stdout[-3000:],
            "workspace_files": sorted(path.name for path in workspace.iterdir()),
            "network_namespace": "bubblewrap-inherited user+network namespace; loopback only",
            "model_loaded": False,
            "gpu_used": False,
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def outer_child() -> int:
    subprocess.run(["ip", "link", "set", "lo", "up"], check=True, capture_output=True)
    attempt = WORK / "attempt-01"
    workspace = attempt / "workspace"
    codex_home = attempt / "codex-home"
    workspace.mkdir(parents=True, exist_ok=False)
    codex_home.mkdir(parents=True, exist_ok=False)
    bwrap = [
        "bwrap", "--die-with-parent", "--ro-bind", "/", "/", "--tmpfs", "/tmp",
        "--dir", "/tmp/tools", "--dir", "/tmp/workspace", "--dir", "/tmp/codex-home",
        "--ro-bind", str(Path(__file__).resolve()), "/tmp/tools/capture.py",
        "--ro-bind", str(CODEX), "/tmp/tools/codex",
        "--tmpfs", "/home", "--tmpfs", "/root", "--tmpfs", "/media", "--tmpfs", "/mnt", "--tmpfs", "/run",
        "--bind", str(workspace), "/tmp/workspace", "--bind", str(codex_home), "/tmp/codex-home",
        "--dev", "/dev", "--proc", "/proc", "--unshare-pid",
        "--setenv", "HOME", "/tmp/codex-home", "--setenv", "CODEX_HOME", "/tmp/codex-home",
        "--setenv", "PATH", "/tmp/tools:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "/usr/bin/python3", "/tmp/tools/capture.py", "--inside",
    ]
    result = subprocess.run(bwrap, env={"PATH": "/usr/bin:/bin", "HOME": "/tmp"}, capture_output=True, text=True, timeout=90)
    try:
        payload = json.loads(result.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        payload = {"status": "sandbox_failed", "stdout": result.stdout[-4000:], "stderr": result.stderr[-4000:]}
    (attempt / "structure-result.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload.get("status"), "receipt": str(attempt / "structure-result.json"), "bwrap_exit_code": result.returncode}))
    return 0


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) > 1 and sys.argv[1] == "--inside":
        print(json.dumps(inside(), sort_keys=True))
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "--outer-child":
        return outer_child()
    result = subprocess.run(["unshare", "-Urn", sys.executable, str(Path(__file__).resolve()), "--outer-child"], timeout=100)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
