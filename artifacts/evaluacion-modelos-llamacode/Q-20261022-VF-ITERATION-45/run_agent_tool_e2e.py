#!/usr/bin/env python3
"""Run Q45 through the real AgentToolRunner and the verified local EG2 server."""
from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socketserver
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import urllib.error
import urllib.request

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
Q44 = REPO / "artifacts/evaluacion-modelos-llamacode/Q-20261022-VF-ITERATION-44"
MODEL = Path("/media/cristian/Disco local/LlamaCode-cache/embeddinggemma2-eval/embeddinggemma-2-Q8_0.gguf")
RUNTIME = Path("/media/cristian/Disco local/LlamaCode-cache/embeddinggemma2-eval/runtime/llama-b11554")
SERVER = RUNTIME / "llama-server"
MODEL_SHA = "2188ac1deca4b77dffefd603c2776a9d76d9d74ec01841392982ebb840b09135"
SERVER_SHA = "fe8a7d6073d3e3a276193fcaec162cbf280d2572ad2016c9100fd924be19c6ed"
HEAD = "51acfeb1299231b6678bc2e9a56ba6f07254165e"
UPSTREAM_PORT = 8397
PROXY_PORT = 8398


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inference_processes() -> list[dict]:
    markers = ("llama-server", "ollama", "vllm", "sglang", "aphrodite", "tritonserver",
               "text-generation-launcher", "llamafile", "koboldcpp", "tabbyapi", "lmstudio",
               "local-ai", "nim")
    python_markers = ("vllm.entrypoints", "sglang.launch_server", "aphrodite.endpoints",
                      "text_generation_server", "mlx_lm.server", "llama_cpp.server")
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            comm = (entry / "comm").read_text(errors="replace").strip().lower()
            cmdline = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").lower()
            exe = Path(os.readlink(entry / "exe")).name.lower()
        except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
            continue
        if any(marker in comm or marker in exe for marker in markers):
            found.append({"pid": int(entry.name), "comm": comm, "exe": exe, "cmdline": cmdline[:400]})
        elif ("python" in comm or "python" in exe) and any(marker in cmdline for marker in python_markers):
            found.append({"pid": int(entry.name), "comm": comm, "exe": exe, "cmdline": cmdline[:400]})
    return found


def listener_snapshot() -> str:
    result = subprocess.run(["ss", "-ltnp"], capture_output=True, text=True, check=True, timeout=5)
    return result.stdout


def assert_ports_free(snapshot: str) -> None:
    for port in (UPSTREAM_PORT, PROXY_PORT):
        if re.search(rf"(?:127\.0\.0\.1|0\.0\.0\.0|\*|\[::\]):{port}\b", snapshot):
            raise RuntimeError(f"port {port} already has a listener; no process was stopped")


def gpu_snapshot() -> dict:
    result = subprocess.run([
        "nvidia-smi", "--id=1", "--query-gpu=name,memory.used,memory.free,utilization.gpu",
        "--format=csv,noheader,nounits"], capture_output=True, text=True, check=True, timeout=5)
    fields = [part.strip() for part in result.stdout.strip().split(",")]
    if len(fields) != 4:
        raise RuntimeError(f"unexpected GPU1 query: {result.stdout!r}")
    return {"name": fields[0], "memory_used_mib": int(fields[1]),
            "memory_free_mib": int(fields[2]), "utilization_pct": int(fields[3])}


def create_snapshot(out: Path) -> tuple[Path, dict]:
    snapshot = Path(tempfile.mkdtemp(prefix="llamacode-q45-head-"))
    archive = out / "tracked-head.tar"
    with archive.open("wb") as target:
        subprocess.run(["git", "archive", "--format=tar", HEAD], cwd=REPO,
                       stdout=target, check=True, timeout=120)
    archive_hash = sha(archive)
    archive_bytes = archive.stat().st_size
    with tarfile.open(archive, "r") as tar:
        members = tar.getmembers()
        if any(member.islnk() for member in members):
            raise RuntimeError("git archive unexpectedly contains hard links")
        # Some historical evaluation artifacts are symlinks to model files on
        # mounted data disks. Omit all symlinks so the snapshot cannot read or
        # mutate outside the isolated repo tree.
        omitted_symlinks = [{"path": member.name, "target": member.linkname}
                            for member in members if member.issym()]
        extracted = [member for member in members if not member.issym()]
        tar.extractall(snapshot, members=extracted, filter="data")
    archive.unlink()
    manifest = {"head": HEAD, "archive_sha256": archive_hash,
                "archive_bytes": archive_bytes, "tracked_entries": len(members),
                "extracted_entries": len(extracted), "omitted_external_symlinks": omitted_symlinks,
                "snapshot_root": str(snapshot), "source": "git archive of HEAD; excludes dirty/untracked working-tree files"}
    return snapshot, manifest


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    upstream = f"http://127.0.0.1:{UPSTREAM_PORT}"
    log_path: Path
    query_texts: set[str]
    write_lock = threading.Lock()

    def log_message(self, _fmt, *_args):
        return

    def do_POST(self):
        started = time.monotonic()
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        try:
            obj = json.loads(body)
        except Exception:
            obj = {}
        raw_inputs = obj.get("input", [])
        if isinstance(raw_inputs, str):
            raw_inputs = [raw_inputs]
        if not isinstance(raw_inputs, list):
            raw_inputs = []
        documents = sum(1 for item in raw_inputs if isinstance(item, str) and item not in self.query_texts)
        queries = len(raw_inputs) - documents
        record = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                  "started_epoch_ms": time.time_ns() // 1_000_000,
                  "path": self.path, "model": obj.get("model"), "input_count": len(raw_inputs),
                  "query_input_count": queries, "document_input_count": documents,
                  "input_lengths": [len(item) for item in raw_inputs if isinstance(item, str)],
                  "request_sha256": hashlib.sha256(body).hexdigest()}
        status, response_body, content_type = 502, b"", "application/json"
        try:
            request = urllib.request.Request(self.upstream + self.path, data=body,
                headers={"Content-Type": self.headers.get("Content-Type", "application/json")}, method="POST")
            with urllib.request.urlopen(request, timeout=120) as response:
                status = response.status
                response_body = response.read()
                content_type = response.headers.get("Content-Type", content_type)
        except urllib.error.HTTPError as error:
            status = error.code
            response_body = error.read()
            content_type = error.headers.get("Content-Type", content_type)
        except Exception as error:
            response_body = json.dumps({"proxy_error": repr(error)}).encode()
        record.update({"status": status, "elapsed_s": round(time.monotonic() - started, 6),
                       "response_bytes": len(response_body),
                       "response_sha256": hashlib.sha256(response_body).hexdigest()})
        with self.write_lock:
            with self.log_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(response_body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(response_body)


def wait_health(child: subprocess.Popen, timeout_s: int = 90) -> bool:
    deadline = time.monotonic() + timeout_s
    request = urllib.request.Request(f"http://127.0.0.1:{UPSTREAM_PORT}/health", method="GET")
    while time.monotonic() < deadline:
        if child.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(request, timeout=2) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-exe", type=Path, required=True,
                        help="ruta al ejecutable QtTest ya compilado")
    parser.add_argument("--attempt", default="attempt-02",
                        help="subdirectorio nuevo para guardar este intento")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"attempt-[0-9]{2,}", args.attempt):
        parser.error("--attempt debe tener el formato attempt-NN")
    out = HERE / "receipts" / args.attempt
    out.mkdir(parents=True, exist_ok=True)
    orchestration_path = out / "orchestration.json"
    if orchestration_path.exists():
        raise SystemExit(f"refusing to overwrite {orchestration_path}")
    if sha(MODEL) != MODEL_SHA or sha(SERVER) != SERVER_SHA:
        raise SystemExit("model/server SHA-256 mismatch; no server started")
    if subprocess.run(["git", "rev-parse", HEAD], cwd=REPO, capture_output=True,
                       text=True, check=True).stdout.strip() != HEAD:
        raise SystemExit("frozen HEAD is not resolvable; no snapshot/server started")
    test_exe = args.test_exe
    if not test_exe.is_file():
        raise SystemExit(f"AgentToolRunner QtTest executable missing: {test_exe}")
    before_servers = inference_processes()
    before_listeners = listener_snapshot()
    assert_ports_free(before_listeners)
    if before_servers:
        raise SystemExit(f"preflight found inference server(s); no process was stopped: {before_servers}")
    gpu_before = gpu_snapshot()
    if gpu_before["memory_free_mib"] < 16384:
        raise SystemExit(f"GPU1 has less than the preregistered 16 GiB free: {gpu_before}")

    snapshot_root = None
    server_process = None
    server_log = None
    proxy = None
    proxy_thread = None
    record = {"schema": "q45-orchestration-v1", "status": "preflight_passed",
              "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "repo_head": HEAD, "model_path": str(MODEL), "model_sha256": MODEL_SHA,
              "server_path": str(SERVER), "server_sha256": SERVER_SHA,
              "test_executable": str(test_exe), "test_executable_sha256": sha(test_exe),
              "preflight_inference_processes": before_servers, "preflight_listeners": before_listeners,
              "preflight_gpu1": gpu_before, "ports": {"upstream": UPSTREAM_PORT, "proxy": PROXY_PORT},
              "resource_policy": "CUDA_VISIBLE_DEVICES=1; protected background.slice; no RAM/swap caps; minimum 16 GiB free before launch; 90 s health timeout; 720 s QtTest timeout; scoped process-tree cleanup"}
    try:
        snapshot_root, snapshot_manifest = create_snapshot(out)
        record["snapshot"] = snapshot_manifest
        fixture_queries = [json.loads(line) for line in (Q44 / "queries.jsonl").read_text().splitlines() if line]
        query_texts = {row["query"] for row in fixture_queries}
        proxy_log = out / "proxy-requests.jsonl"
        if proxy_log.exists():
            raise RuntimeError(f"refusing to overwrite {proxy_log}")
        ProxyHandler.log_path = proxy_log
        ProxyHandler.query_texts = query_texts

        server_args = [str(SERVER), "--model", str(MODEL), "--host", "127.0.0.1", "--port", str(UPSTREAM_PORT),
                       "--embeddings", "--pooling", "mean", "--ctx-size", "16384", "--batch-size", "16384",
                       "--ubatch-size", "16384", "--parallel", "1", "--n-gpu-layers", "99", "--device", "CUDA0"]
        server_env = os.environ.copy()
        server_env["CUDA_VISIBLE_DEVICES"] = "1"
        server_env["LD_LIBRARY_PATH"] = str(RUNTIME)
        server_log = (out / "server.log").open("wb")
        server_process = subprocess.Popen(server_args,
            cwd=REPO, env=server_env, stdout=server_log, stderr=subprocess.STDOUT, start_new_session=True)
        record["server_controller_pid"] = server_process.pid
        record["server_argv"] = server_args
        record["server_log"] = str(out / "server.log")
        if not wait_health(server_process):
            raise RuntimeError(f"EmbeddingGemma server failed health check; status={server_process.poll()}")
        servers = inference_processes()
        own = [row for row in servers if row["exe"] == "llama-server" and str(MODEL).lower() in row["cmdline"]]
        if len(servers) != 1 or len(own) != 1:
            raise RuntimeError(f"cannot attribute the sole inference process to Q45: {servers}")
        record["server_pid"] = own[0]["pid"]
        record["server_process"] = own[0]
        record["status"] = "server_healthy"

        proxy = http.server.ThreadingHTTPServer(("127.0.0.1", PROXY_PORT), ProxyHandler)
        proxy_thread = threading.Thread(target=proxy.serve_forever, name="q45-audit-proxy", daemon=True)
        proxy_thread.start()
        xdg = out / "xdg-data"
        xdg.mkdir(exist_ok=True)
        result_path = out / "agenttoolrunner-results.json"
        test_env = os.environ.copy()
        test_env.update({"QT_QPA_PLATFORM": "offscreen", "QT_ASSUME_STDERR_HAS_CONSOLE": "1",
                         "LC_Q45_FIXTURE_DIR": str(Q44), "LC_Q45_REPO_ROOT": str(snapshot_root),
                         "LC_Q45_ENDPOINT": f"http://127.0.0.1:{PROXY_PORT}",
                         "LC_Q45_RECEIPT_FILE": str(result_path), "XDG_DATA_HOME": str(xdg)})
        test_output = (out / "agenttoolrunner-test.log").open("wb")
        record["status"] = "running_agenttoolrunner"
        test_started = time.monotonic()
        test = subprocess.run([str(test_exe), "hybridSearch_embeddingGemmaQ44E2E"], cwd=REPO,
                              env=test_env, stdout=test_output, stderr=subprocess.STDOUT,
                              timeout=720, check=False)
        test_output.close()
        record["test_exit_code"] = test.returncode
        record["test_elapsed_s"] = round(time.monotonic() - test_started, 3)
        record["test_log"] = str(out / "agenttoolrunner-test.log")
        if not result_path.is_file():
            raise RuntimeError("AgentToolRunner test exited without writing its receipt")
        record["test_result"] = json.loads(result_path.read_text())
        record["proxy_request_count"] = sum(1 for line in proxy_log.read_text().splitlines() if line)
        record["test_passed"] = test.returncode == 0
        record["status"] = "complete" if test.returncode == 0 else "test_failed"
        return 0 if test.returncode == 0 else 1
    except BaseException as error:
        record["status"] = "failed"
        record["error"] = repr(error)
        raise
    finally:
        if proxy is not None:
            proxy.shutdown()
            proxy.server_close()
        if proxy_thread is not None:
            proxy_thread.join(timeout=5)
        if server_process is not None:
            if server_process.poll() is None:
                # Signal timeout only; it forwards one configured SIGTERM to
                # llama-server. Signalling the whole group produced duplicate
                # interrupts in llama.cpp during the first completed request.
                server_process.terminate()
                try:
                    server_process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(server_process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    server_process.wait(timeout=5)
            record["server_controller_exit_code"] = server_process.returncode
        if server_log is not None and not server_log.closed:
            server_log.flush()
            server_log.close()
        record["postflight_inference_processes"] = inference_processes()
        try:
            record["postflight_listeners"] = listener_snapshot()
        except Exception as error:
            record["postflight_listener_error"] = repr(error)
        try:
            record["postflight_gpu1"] = gpu_snapshot()
        except Exception as error:
            record["postflight_gpu_error"] = repr(error)
        record["finished_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            orchestration_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
        finally:
            if snapshot_root is not None:
                shutil.rmtree(snapshot_root, ignore_errors=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BaseException as error:
        attempt = "attempt-02"
        if "--attempt" in sys.argv:
            position = sys.argv.index("--attempt")
            if position + 1 < len(sys.argv):
                attempt = sys.argv[position + 1]
        failure = HERE / "receipts" / attempt / "preflight-or-controller-failure.json"
        orchestration = HERE / "receipts" / attempt / "orchestration.json"
        if not orchestration.exists() and not failure.exists():
            failure.parent.mkdir(parents=True, exist_ok=True)
            failure.write_text(json.dumps({"schema": "q45-preflight-failure-v1",
                                           "error": repr(error),
                                           "at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                                          ensure_ascii=False, indent=2) + "\n")
        raise
