#!/usr/bin/env python3
"""One direct Qwen Responses function-call diagnostic in loopback-only isolation."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

TASK = Path(__file__).resolve().parents[1]
OUT = TASK / "receipts/harness2-qwen38-direct-function-tool-diagnostic-result-20261021.json"
LOG = TASK / "logs/harness2-qwen38-direct-function-tool-diagnostic-runner.log"
GUARD_SCRIPT = TASK / "work/harness2_qwen38_q4_codex_tool_canary.py"
PORT = 18107


def load_guard():
    spec = importlib.util.spec_from_file_location("qwen_canary_guard", GUARD_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def post_json(url: str, payload: dict, timeout: int):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer local-only-no-secret"}, method="POST")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            return r.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"unparsed_response_sha256": hashlib.sha256(raw.encode()).hexdigest(), "response_chars": len(raw)}


def inside() -> dict:
    def run(cmd, timeout=10):
        return subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout).stdout.strip()
    run(["ip", "link", "set", "lo", "up"])
    links = run(["ip", "-o", "link", "show"])
    names = sorted(re.match(r"\d+: ([^:@]+)", x).group(1) for x in links.splitlines())
    routes = run(["ip", "route", "show"])
    if names != ["lo"] or any(x.split()[:1] == ["default"] for x in routes.splitlines()):
        raise RuntimeError(f"network isolation mismatch: {names}, {routes}")
    s = socket.socket(); s.settimeout(1)
    try:
        testnet_errno = s.connect_ex(("192.0.2.1", 443))
    finally:
        s.close()
    if testnet_errno == 0:
        raise RuntimeError("TEST-NET connection unexpectedly succeeded")

    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/tmp", "LD_LIBRARY_PATH": "/tmp/runtime:/usr/local/cuda/targets/x86_64-linux/lib",
        "CUDA_DEVICE_ORDER": "PCI_BUS_ID", "CUDA_VISIBLE_DEVICES": "0", "HF_HUB_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1",
        "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost"}
    cmd = ["/tmp/runtime/llama-server", "-m", "/tmp/models/model.gguf", "--host", "127.0.0.1", "--port", str(PORT),
        "--parallel", "1", "--flash-attn", "on", "-ctk", "q8_0", "-ctv", "q8_0", "-ngl", "32", "-sm", "none", "-c", "16384",
        "--spec-type", "none", "--reasoning-budget", "64", "--alias", "qwen-local", "--no-webui"]
    server_log = Path("/tmp/server.log")
    with server_log.open("w") as log:
        server = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 300
            health = None
            while time.monotonic() < deadline:
                if server.poll() is not None:
                    return {"status": "server_start_failed", "exit_code": server.returncode}
                try:
                    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(f"http://127.0.0.1:{PORT}/health", timeout=2) as r:
                        health = json.loads(r.read())
                    if health.get("status") == "ok":
                        break
                except Exception:
                    time.sleep(1)
            if not health or health.get("status") != "ok":
                return {"status": "health_timeout"}
            tool = {"type": "function", "name": "write_file", "description": "Write text to a file in the disposable workspace.",
                "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                    "required": ["path", "content"], "additionalProperties": False}}
            payload = {"model": "qwen-local", "input": "Use write_file now to create canary.txt with exact content TOOL_LOOP_OK. Do not answer in prose.",
                "tools": [tool], "tool_choice": "auto", "max_output_tokens": 128, "temperature": 0, "reasoning": {"effort": "low"}}
            started = time.monotonic()
            status, body = post_json(f"http://127.0.0.1:{PORT}/v1/responses", payload, timeout=180)
            elapsed = time.monotonic() - started
            output = body.get("output", []) if isinstance(body, dict) else []
            calls = [x for x in output if isinstance(x, dict) and x.get("type") == "function_call"]
            parsed = []
            for call in calls:
                args = call.get("arguments")
                try:
                    args = json.loads(args) if isinstance(args, str) else args
                except json.JSONDecodeError:
                    args = {"invalid_json_sha256": hashlib.sha256(str(args).encode()).hexdigest()}
                parsed.append({"name": call.get("name"), "arguments": args})
            exact = len(parsed) == 1 and parsed[0].get("name") == "write_file" and parsed[0].get("arguments") == {"path": "canary.txt", "content": "TOOL_LOOP_OK"}
            return {"status": "pass" if status == 200 and isinstance(body, dict) and body.get("status") == "completed" and exact else "function_call_not_emitted_or_invalid",
                "namespace_interfaces": names, "namespace_routes": routes.splitlines(), "test_net_errno": testnet_errno,
                "health": health, "http_status": status, "response_status": body.get("status") if isinstance(body, dict) else None,
                "output_item_types": [x.get("type") for x in output if isinstance(x, dict)], "function_calls": parsed,
                "usage": body.get("usage") if isinstance(body, dict) else None, "elapsed_seconds": elapsed,
                "raw_request_saved": False, "raw_response_saved": False, "server_log": str(server_log)}
        finally:
            if server.poll() is None:
                server.send_signal(signal.SIGTERM)
                try: server.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    server.kill(); server.wait(timeout=5)


def child() -> int:
    try:
        result = inside()
    except Exception as e:
        result = {"status": "probe_error", "error": f"{type(e).__name__}: {e}"}
    print(json.dumps(result, sort_keys=True))
    return 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--inside":
        return child()
    guard = load_guard()
    pre = guard.preflight()
    pre["diagnostic_port"] = PORT
    with socket.socket() as s:
        try: s.bind(("127.0.0.1", PORT))
        except OSError as e: raise RuntimeError(f"diagnostic port {PORT} busy") from e
    bwrap = ["bwrap", "--die-with-parent", "--ro-bind", "/", "/", "--tmpfs", "/tmp", "--dir", "/tmp/tools", "--dir", "/tmp/runtime", "--dir", "/tmp/models",
        "--ro-bind", str(Path(__file__).resolve()), "/tmp/tools/probe.py", "--ro-bind", str(guard.LLAMA_LIBS), "/tmp/runtime", "--ro-bind", str(guard.MODEL), "/tmp/models/model.gguf",
        "--tmpfs", "/home", "--tmpfs", "/root", "--tmpfs", "/media", "--tmpfs", "/mnt", "--tmpfs", "/run", "--dev", "/dev", "--proc", "/proc", "--unshare-pid"]
    present = {p.name for p in Path("/dev").glob("nvidia*") if p.is_char_device()}
    required = {"nvidia0", "nvidiactl", "nvidia-uvm"}
    if not required <= present:
        raise RuntimeError(f"required GPU0 device nodes missing: {sorted(required-present)}")
    for name in sorted(required): bwrap.extend(["--dev-bind", f"/dev/{name}", f"/dev/{name}"])
    bwrap.extend(["--setenv", "PATH", "/usr/local/bin:/usr/bin:/bin", "--setenv", "HOME", "/tmp", "--setenv", "LD_LIBRARY_PATH", "/tmp/runtime:/usr/local/cuda/targets/x86_64-linux/lib",
        "--setenv", "CUDA_DEVICE_ORDER", "PCI_BUS_ID", "--setenv", "CUDA_VISIBLE_DEVICES", "0", "--setenv", "HF_HUB_OFFLINE", "1", "--setenv", "HF_DATASETS_OFFLINE", "1",
        "--setenv", "NO_PROXY", "127.0.0.1,localhost", "--setenv", "no_proxy", "127.0.0.1,localhost", "/usr/bin/python3", "/tmp/tools/probe.py", "--inside"])
    LOG.parent.mkdir(parents=True, exist_ok=True)
    out = {"test_id": "Q-20261021-H2-QWEN38-DIRECT-FUNCTION-CALL", "status": "running", "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "preflight": pre, "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    proc = subprocess.Popen(["unshare", "-Urn", *bwrap], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        stdout, _ = proc.communicate(timeout=420)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGTERM)
        try: stdout, _ = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL); stdout, _ = proc.communicate()
        out["guard"] = "420-second outer timeout"
    try: child_result = json.loads(stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError): child_result = {"status": "no_child_json", "output_tail": stdout[-4000:]}
    post_servers = guard.inference_processes()
    port_free = False
    with socket.socket() as s:
        try: s.bind(("127.0.0.1", PORT)); port_free = True
        except OSError: pass
    out.update({"status": out.get("guard") and "aborted_by_guard" or child_result.get("status", "unknown"), "child": child_result,
        "child_exit_code": proc.returncode, "postflight": {"inference_processes": post_servers, "port_free": port_free,
            "gpus": guard.gpu_snapshot(), "memavailable_bytes": guard.memavailable(), "memory_psi_full_avg10": guard.psi_full_avg10()}, "runner_log": str(LOG)})
    LOG.write_text(json.dumps(child_result, indent=2) + "\n")
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"status": out["status"], "receipt": str(OUT), "postflight": out["postflight"]}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
