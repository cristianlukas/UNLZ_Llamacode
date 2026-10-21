#!/usr/bin/env python3
"""One local Codex file-tool canary under an outer read-only bubblewrap sandbox."""

from __future__ import annotations

import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request

TASK = Path(__file__).resolve().parents[1]
OUT = TASK / "receipts/harness2-qwen38-q4-codex-tool-canary-attempt-11-result-20261021.json"
LOG = TASK / "logs/harness2-qwen38-q4-codex-tool-canary-attempt-11-runner.log"
SERVER = Path("/home/cristian/.cache/llamacode/embeddinggemma2-eval/runtime/llama-b11554/llama-server")
CODEX = Path("/home/cristian/.local/bin/codex").resolve()
LLAMA_LIBS = Path("/home/cristian/.cache/llamacode/embeddinggemma2-eval/runtime/llama-b11554")
MODEL = Path("/media/cristian/Disco local/Models/llamacpp/Qwen3.8-27B-GGUF-Q4_K_M/Qwen3.8-27B-Q4_K_M.gguf")
PORT = 18103
PROXY_PORT = 18105
TOKEN = "local-only-no-secret"


class ResponsesCompatHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = json.dumps({"status": "ok", "adapter": "test-only"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        size = int(self.headers.get("Content-Length", "0"))
        original = json.loads(self.rfile.read(size))
        payload = json.loads(json.dumps(original))
        instructions = payload.get("instructions")
        items = payload.get("input")
        if not isinstance(instructions, str) or not isinstance(items, list) or not items:
            self._respond(400, {"error": {"message": "expected instructions plus input array"}})
            return
        developer_index = next((i for i, item in enumerate(items)
                                if isinstance(item, dict) and item.get("role") == "developer"), None)
        if developer_index != 0:
            self._respond(400, {"error": {"message": "expected leading developer input item"}})
            return
        developer = items[0]
        developer_content = developer.get("content", [])
        if isinstance(developer_content, str):
            developer_content = [{"type": "input_text", "text": developer_content}]
        if not isinstance(developer_content, list):
            self._respond(400, {"error": {"message": "unsupported developer content shape"}})
            return
        developer["content"] = [{"type": "input_text", "text": instructions}] + developer_content
        payload.pop("instructions")
        instruction_bytes = instructions.encode("utf-8")
        self.server.adapter_audit = {
            "status": "forwarded",
            "instructions_sha256": hashlib.sha256(instruction_bytes).hexdigest(),
            "instructions_characters_merged": len(instructions),
            "developer_index": developer_index,
            "developer_content_items_before": len(developer_content),
            "developer_content_items_after": len(developer["content"]),
            "input_roles_after": [item.get("role") if isinstance(item, dict) else None for item in items],
            "top_level_instructions_removed": True,
            "other_top_level_keys_preserved": sorted(payload.keys()),
            "tool_types": [tool.get("type") for tool in payload.get("tools", []) if isinstance(tool, dict)],
            "raw_request_saved": False,
        }  # type: ignore[attr-defined]
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=300)
        try:
            conn.request("POST", self.path, body=encoded, headers={"Content-Type": "application/json"})
            response = conn.getresponse()
            response_body = response.read()
            self.send_response(response.status)
            self.send_header("Content-Type", response.getheader("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)
        except Exception as exc:
            self.server.adapter_audit["forward_error"] = f"{type(exc).__name__}: {exc}"  # type: ignore[attr-defined]
            self._respond(502, {"error": {"message": "local adapter forwarding failed"}})
        finally:
            conn.close()

    def _respond(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        return


def run(cmd: list[str], timeout: int = 20) -> str:
    return subprocess.run(cmd, check=True, text=True, capture_output=True, timeout=timeout).stdout.strip()


def memavailable() -> int:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    return 0


def psi_full_avg10() -> float:
    match = re.search(r"^full avg10=([0-9.]+)", Path("/proc/pressure/memory").read_text(), re.M)
    return float(match.group(1)) if match else 0.0


def gpu_snapshot() -> list[dict]:
    raw = run([
        "nvidia-smi", "--query-gpu=index,name,memory.total,memory.used,temperature.gpu",
        "--format=csv,noheader,nounits",
    ])
    rows = []
    for line in raw.splitlines():
        cols = [part.strip() for part in line.split(",")]
        rows.append({
            "index": int(cols[0]), "name": cols[1], "memory_total_mib": int(cols[2]),
            "memory_used_mib": int(cols[3]), "temperature_c": int(cols[4]),
        })
    return rows


def inference_processes() -> list[str]:
    rows = run(["ps", "-eo", "pid=,comm=,args="]).splitlines()
    pattern = re.compile(
        r"(^|[/ ])(llama-server|strata|vllm|ollama|openjet-engine|sglang|"
        r"text-generation-launcher|aphrodite-engine)([/ :]|$)", re.I
    )
    return [row.strip() for row in rows if pattern.search(row)]


def lock_owned() -> bool:
    lock = json.loads((TASK.parents[2] / "WORK_QUEUE.lock").read_text())
    return lock.get("task_id") == "Q-20261021-VF-RESUME-ITERATION" and lock.get("token") == "fc531551-b3f2-4861-989b-ef888550d735"


def preflight() -> dict:
    if not lock_owned():
        raise RuntimeError("current iteration no longer owns WORK_QUEUE.lock")
    servers = inference_processes()
    if servers:
        raise RuntimeError(f"an inference process/server is already active: {servers}")
    available = memavailable()
    if available < 60 * 1024**3:
        raise RuntimeError(f"MemAvailable below 60 GiB: {available}")
    psi = [psi_full_avg10()]
    if psi[0] > 10:
        time.sleep(10)
        psi.append(psi_full_avg10())
        if psi[-1] > 10:
            raise RuntimeError(f"memory PSI full avg10 remained above 10%: {psi}")
    gpus = gpu_snapshot()
    gpu0 = next((row for row in gpus if row["index"] == 0), None)
    if not gpu0:
        raise RuntimeError("GPU0 is not visible")
    gpu0_free = gpu0["memory_total_mib"] - gpu0["memory_used_mib"]
    if gpu0_free < 20 * 1024 or gpu0["temperature_c"] >= 85:
        raise RuntimeError(f"GPU0 gate failed: free_mib={gpu0_free}, gpu0={gpu0}")
    if not MODEL.is_file() or MODEL.stat().st_size != 18_973_870_528:
        raise RuntimeError("pinned GGUF is absent or its size differs from the recorded artifact")
    if not SERVER.is_file() or not CODEX.is_file() or not LLAMA_LIBS.is_dir():
        raise RuntimeError("pinned server, Codex CLI, or llama runtime libraries are unavailable")
    if shutil.which("bwrap") is None or shutil.which("unshare") is None or shutil.which("ip") is None:
        raise RuntimeError("bubblewrap, unshare, or ip is unavailable")
    disk = {"task": shutil.disk_usage(TASK).free, "model_volume": shutil.disk_usage(MODEL.parent).free}
    if min(disk.values()) < 20 * 1024**3:
        raise RuntimeError(f"free disk below 20 GiB: {disk}")
    for probe_port in (PORT, PROXY_PORT):
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", probe_port))
            except OSError as exc:
                raise RuntimeError(f"host probe port {probe_port} is busy") from exc
    return {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "lock_owned": True,
        "inference_processes": servers,
        "memavailable_bytes": available,
        "memory_psi_full_avg10": psi,
        "gpus": gpus,
        "gui_compute_apps_observed": run([
            "nvidia-smi", "--query-compute-apps=pid,process_name,used_memory",
            "--format=csv,noheader",
        ]).splitlines(),
        "free_disk_bytes": disk,
        "model_size_bytes": MODEL.stat().st_size,
        "model_sha256_pinned_from_prior_receipt": "c600de0300ae8a0eb3a6c0b8b5561b8b96f16bd2c863c2a66c42de29d391a747",
        "codex_cli_version": run([str(CODEX), "--version"]),
        "host_listeners": run(["ss", "-ltnp"]),
    }


def inside() -> dict:
    visible_nvidia_nodes = sorted(path.name for path in Path("/dev").glob("nvidia*") if path.exists())
    expected_nvidia_nodes = ["nvidia-uvm", "nvidia0", "nvidiactl"]
    if visible_nvidia_nodes != expected_nvidia_nodes:
        raise RuntimeError(
            f"GPU isolation mismatch: visible={visible_nvidia_nodes}, expected={expected_nvidia_nodes}"
        )
    run(["ip", "link", "set", "lo", "up"])
    links = run(["ip", "-o", "link", "show"])
    names = sorted(re.match(r"\d+: ([^:@]+)", line).group(1) for line in links.splitlines())
    routes = run(["ip", "route", "show"])
    if names != ["lo"] or any(line.split()[:1] == ["default"] for line in routes.splitlines()):
        raise RuntimeError(f"network namespace is not loopback-only: interfaces={names}, routes={routes}")
    with socket.socket() as sock:
        sock.settimeout(1)
        testnet_errno = sock.connect_ex(("192.0.2.1", 443))
    if testnet_errno == 0:
        raise RuntimeError("TEST-NET connect unexpectedly succeeded")

    workspace = Path("/tmp/workspace")
    codex_home = Path("/tmp/codex-home")
    conf = f'''model = "qwen-local"\nmodel_provider = "llamacpp"\nmodel_context_window = 16384\nmodel_reasoning_effort = "low"\napproval_policy = "never"\nsandbox_mode = "danger-full-access"\n\n[model_providers.llamacpp]\nname = "LlamaCode local llama.cpp via test-only adapter"\nbase_url = "http://127.0.0.1:{PROXY_PORT}/v1"\nenv_key = "HARNESS2_CODEX_API_KEY"\nwire_api = "responses"\nrequires_openai_auth = false\nrequest_max_retries = 0\nstream_max_retries = 0\n'''
    (codex_home / "config.toml").write_text(conf, encoding="utf-8")

    log_path = codex_home / "llama-server.log"
    server_cmd = [
        "/tmp/runtime/llama-server", "-m", "/tmp/models/model.gguf", "--host", "127.0.0.1",
        "--port", str(PORT), "--parallel", "1", "--flash-attn", "on", "-ctk", "q8_0",
        "-ctv", "q8_0", "-ngl", "32", "-sm", "none", "-c", "16384", "--spec-type", "none",
        "--reasoning-budget", "64", "--alias", "qwen-local", "--no-webui",
    ]
    server_env = {
        "PATH": "/tmp/tools:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "HOME": "/tmp/codex-home",
        "LD_LIBRARY_PATH": "/tmp/runtime:/usr/local/cuda/targets/x86_64-linux/lib",
        "CUDA_DEVICE_ORDER": "PCI_BUS_ID", "CUDA_VISIBLE_DEVICES": "0",
        "HF_HUB_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1",
        "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost",
    }
    device_probe = subprocess.run(
        ["/tmp/runtime/llama-server", "--list-devices"],
        capture_output=True, text=True, env=server_env, timeout=30,
    )
    device_text = device_probe.stdout + device_probe.stderr
    if device_probe.returncode != 0 or "CUDA0" not in device_text or "CUDA1" in device_text:
        return {
            "status": "cuda_device_gate_failed", "return_code": device_probe.returncode,
            "device_list": device_text[-8000:], "visible_nvidia_nodes": visible_nvidia_nodes,
        }
    with log_path.open("w", encoding="utf-8") as log:
        server = subprocess.Popen(server_cmd, stdout=log, stderr=subprocess.STDOUT, env=server_env, start_new_session=True)
        proxy = None
        proxy_thread = None
        try:
            deadline = time.monotonic() + 600
            health = None
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            while time.monotonic() < deadline:
                if server.poll() is not None:
                    return {"status": "server_start_failed", "server_exit_code": server.returncode}
                try:
                    with opener.open(f"http://127.0.0.1:{PORT}/health", timeout=2) as response:
                        health = json.loads(response.read())
                    if health.get("status") == "ok":
                        break
                except Exception:
                    time.sleep(1)
            if not health or health.get("status") != "ok":
                return {"status": "server_health_timeout"}

            proxy = ThreadingHTTPServer(("127.0.0.1", PROXY_PORT), ResponsesCompatHandler)
            proxy.daemon_threads = True
            proxy.adapter_audit = None
            proxy_thread = threading.Thread(target=proxy.serve_forever, daemon=True)
            proxy_thread.start()

            codex_env = dict(server_env)
            codex_env.update({
                "CODEX_HOME": "/tmp/codex-home", "HARNESS2_CODEX_API_KEY": TOKEN,
                "PATH": "/tmp/tools:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            })
            prompt = (
                "This is a disposable isolated workspace. Use your file or shell tool to create "
                "canary.txt containing exactly TOOL_LOOP_OK, then read it back. Do not create or "
                "modify any other workspace file. Reply with only TOOL_LOOP_OK after verifying it."
            )
            cmd = [
                "/tmp/tools/codex", "exec", prompt, "--model", "qwen-local",
                "--skip-git-repo-check", "--dangerously-bypass-approvals-and-sandbox",
                "--dangerously-bypass-hook-trust", "--ephemeral", "--json", "-C", "/tmp/workspace",
                "--add-dir", "/tmp/workspace", "--color", "never",
            ]
            try:
                result = subprocess.run(cmd, cwd="/tmp/workspace", env=codex_env, capture_output=True, text=True, timeout=480)
            except subprocess.TimeoutExpired as exc:
                stdout = exc.stdout or ""
                stderr = exc.stderr or ""
                if isinstance(stdout, bytes):
                    stdout = stdout.decode("utf-8", errors="replace")
                if isinstance(stderr, bytes):
                    stderr = stderr.decode("utf-8", errors="replace")
                content_path = workspace / "canary.txt"
                content = content_path.read_text(encoding="utf-8") if content_path.is_file() else None
                return {
                    "status": "codex_timeout", "timeout_seconds": exc.timeout,
                    "canary_content": content, "workspace_files": sorted(path.name for path in workspace.iterdir()),
                    "codex_stdout_tail": stdout[-5000:], "codex_stderr_tail": stderr[-3000:],
                    "health": health, "network_interfaces": names, "network_routes": routes.splitlines(),
                    "test_net_errno": testnet_errno, "compat_adapter_audit": getattr(proxy, "adapter_audit", None),
                    "server_log": str(log_path), "network_payload_to_external_hosts": False,
                }
            content_path = workspace / "canary.txt"
            content = content_path.read_text(encoding="utf-8") if content_path.is_file() else None
            passed = result.returncode == 0 and content is not None and content.strip() == "TOOL_LOOP_OK"
            return {
                "status": "pass" if passed else "codex_tool_loop_failed",
                "network_interfaces": names, "network_routes": routes.splitlines(),
                "test_net_errno": testnet_errno, "test_net_errno_name": __import__("errno").errorcode.get(testnet_errno, "UNKNOWN"),
                "health": health, "codex_exit_code": result.returncode,
                "canary_content": content, "workspace_files": sorted(path.name for path in workspace.iterdir()),
                "codex_stdout_tail": result.stdout[-12000:], "codex_stderr_tail": result.stderr[-6000:],
                "server_log": str(log_path), "network_payload_to_external_hosts": False,
                "compat_adapter_audit": getattr(proxy, "adapter_audit", None),
            }
        finally:
            if proxy is not None:
                proxy.shutdown()
                proxy.server_close()
            if proxy_thread is not None:
                proxy_thread.join(timeout=2)
            if server.poll() is None:
                server.send_signal(signal.SIGTERM)
                try:
                    server.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)


def child() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--inside":
        try:
            result = inside()
        except subprocess.TimeoutExpired as exc:
            result = {"status": "codex_timeout", "timeout_seconds": exc.timeout}
        except Exception as exc:
            result = {"status": "probe_error", "error": f"{type(exc).__name__}: {exc}"}
        print(json.dumps(result, sort_keys=True))
        return 0

    run(["ip", "link", "set", "lo", "up"])
    work = TASK / "work/harness2-qwen38-q4-codex-tool-canary/attempt-11"
    workspace = work / "workspace"
    codex_home = work / "codex-home"
    workspace.mkdir(parents=True, exist_ok=False)
    codex_home.mkdir(parents=True, exist_ok=False)
    child_env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/tmp/codex-home",
        "CODEX_HOME": "/tmp/codex-home", "HARNESS2_CODEX_API_KEY": TOKEN,
        "LD_LIBRARY_PATH": "/tmp/runtime:/usr/local/cuda/targets/x86_64-linux/lib",
        "CUDA_DEVICE_ORDER": "PCI_BUS_ID", "CUDA_VISIBLE_DEVICES": "0",
        "HF_HUB_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1",
        "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost",
    }
    bwrap = [
        "bwrap", "--die-with-parent", "--ro-bind", "/", "/", "--tmpfs", "/tmp",
        "--dir", "/tmp/tools", "--dir", "/tmp/runtime", "--dir", "/tmp/models",
        "--dir", "/tmp/workspace", "--dir", "/tmp/codex-home",
        "--ro-bind", str(Path(__file__).resolve()), "/tmp/tools/probe.py",
        "--ro-bind", str(LLAMA_LIBS), "/tmp/runtime",
        "--ro-bind", str(CODEX), "/tmp/tools/codex",
        "--ro-bind", str(LLAMA_LIBS), "/tmp/llama-libs",
        "--ro-bind", str(MODEL), "/tmp/models/model.gguf",
        "--tmpfs", "/home", "--tmpfs", "/root", "--tmpfs", "/media", "--tmpfs", "/mnt", "--tmpfs", "/run",
        "--bind", str(workspace), "/tmp/workspace", "--bind", str(codex_home), "/tmp/codex-home",
        "--dev", "/dev", "--proc", "/proc", "--unshare-pid",
    ]
    host_nvidia = sorted(Path("/dev").glob("nvidia*"))
    required = {"nvidia0", "nvidiactl", "nvidia-uvm"}
    present = {path.name for path in host_nvidia if path.is_char_device()}
    missing = required - present
    if missing:
        raise RuntimeError(f"required NVIDIA device nodes missing: {sorted(missing)}")
    allowed_nodes = {"nvidia0", "nvidiactl", "nvidia-uvm"}
    for path in host_nvidia:
        if path.name in allowed_nodes and path.is_char_device():
            bwrap.extend(["--dev-bind", f"/dev/{path.name}", f"/dev/{path.name}"])
    bwrap.extend([
        "--setenv", "HOME", "/tmp/codex-home", "--setenv", "CODEX_HOME", "/tmp/codex-home",
        "--setenv", "HARNESS2_CODEX_API_KEY", TOKEN,
        "--setenv", "PATH", "/tmp/tools:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "--setenv", "LD_LIBRARY_PATH", child_env["LD_LIBRARY_PATH"],
        "--setenv", "CUDA_DEVICE_ORDER", "PCI_BUS_ID", "--setenv", "CUDA_VISIBLE_DEVICES", "0",
        "--setenv", "HF_HUB_OFFLINE", "1", "--setenv", "HF_DATASETS_OFFLINE", "1",
        "--setenv", "NO_PROXY", "127.0.0.1,localhost", "--setenv", "no_proxy", "127.0.0.1,localhost",
        "/usr/bin/python3", "/tmp/tools/probe.py", "--inside",
    ])
    result = subprocess.run(bwrap, env={"PATH": "/usr/bin:/bin", "HOME": "/tmp"}, capture_output=True, text=True, timeout=900)
    print(result.stdout.strip().splitlines()[-1] if result.stdout.strip() else json.dumps({"status": "no_child_json", "stderr": result.stderr[-6000:]}))
    return 0


def monitor(proc: subprocess.Popen[str]) -> tuple[str | None, list[dict]]:
    deadline = time.monotonic() + 900
    psi_high = 0
    samples = []
    while proc.poll() is None:
        available = memavailable()
        psi = psi_full_avg10()
        gpus = gpu_snapshot()
        temp = next((row["temperature_c"] for row in gpus if row["index"] == 0), 100)
        samples.append({
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "memavailable_bytes": available, "memory_psi_full_avg10": psi,
            "gpu0_temperature_c": temp,
        })
        if available < 48 * 1024**3:
            return "MemAvailable fell below 48 GiB", samples
        psi_high = psi_high + 1 if psi > 25 else 0
        if psi_high >= 4:
            return "memory PSI full exceeded 25% for four consecutive 5-second samples", samples
        if temp >= 85:
            return "GPU0 reached 85 C", samples
        if time.monotonic() >= deadline:
            return "15-minute process-group timeout", samples
        time.sleep(5)
    return None, samples


def main() -> int:
    if len(sys.argv) > 1:
        return child()
    LOG.parent.mkdir(parents=True, exist_ok=True)
    pre = preflight()
    digest = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    out = {
        "test_id": "Q-20261021-H2-QWEN38-Q4-CODEX-TOOL-CANARY", "status": "running",
        "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "preflight": pre, "runner_sha256": digest,
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    cmd = ["unshare", "-Urn", sys.executable, str(Path(__file__).resolve()), "--child"]
    with LOG.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, text=True, start_new_session=True)
        guard, samples = monitor(proc)
        if guard:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)
    stdout = LOG.read_text(encoding="utf-8", errors="replace")
    try:
        child_result = json.loads(stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        child_result = {"status": "no_child_json", "runner_output_tail": stdout[-6000:]}
    time.sleep(1)
    post_servers = inference_processes()
    port_free = {}
    for probe_port in (PORT, PROXY_PORT):
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", probe_port))
                port_free[str(probe_port)] = True
            except OSError:
                port_free[str(probe_port)] = False
    out.update({
        "status": "aborted_by_guard" if guard else child_result.get("status", "unknown"),
        "guard": guard, "monitor_samples": samples, "child": child_result,
        "postflight": {"inference_processes": post_servers, "port_status": port_free,
                       "memavailable_bytes": memavailable(), "memory_psi_full_avg10": psi_full_avg10(),
                       "gpus": gpu_snapshot()},
        "runner_log": str(LOG),
    })
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": out["status"], "guard": guard, "postflight": out["postflight"], "receipt": str(OUT)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
