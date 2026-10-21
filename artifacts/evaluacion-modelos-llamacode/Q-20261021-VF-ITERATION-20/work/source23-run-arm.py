#!/usr/bin/env python3
"""Run one isolated S23 arm/seed, with inference-server preflight and process-group cleanup."""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

REPO = pathlib.Path(__file__).resolve().parents[4]
TASK = REPO / "artifacts/evaluacion-modelos-llamacode/Q-20261020-VF-20261019-01"
SOURCE = pathlib.Path("/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source")
SERVER = SOURCE / "serve/server.py"
SERVER_PYTHON = SOURCE / ".venv/bin/python"
RUNNER = REPO / "artifacts/evaluacion-modelos-llamacode/Q-20261021-VF-ITERATION-20/work/source23-run-bcb.py"
LOCK_TOKEN = os.environ.get("LCA_WORK_QUEUE_LOCK_TOKEN", "916dae69-e04f-4429-b08b-bdf0cf9f34b3")
PORT = 8353


def lock_owned() -> bool:
    try:
        return json.loads((REPO / "WORK_QUEUE.lock").read_text(encoding="utf-8")).get("token") == LOCK_TOKEN
    except Exception:
        return False


def inference_processes() -> list[dict]:
    found = []
    markers = ("llama-server", "vllm", "sglang", "ollama serve", "lmstudio", "tritonserver",
               "text-generation-launcher", "aphrodite", "mlx_lm")
    for entry in os.scandir("/proc"):
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            cmd = open(entry.path + "/cmdline", "rb").read().replace(b"\0", b" ").decode(errors="replace").strip()
            comm = open(entry.path + "/comm", encoding="utf-8").read().strip()
        except (OSError, ProcessLookupError):
            continue
        text = (comm + " " + cmd).lower()
        if comm.lower() == "strata" or "--engine strata" in text or any(m in text for m in markers):
            found.append({"pid": int(entry.name), "comm": comm, "cmdline": cmd[:500]})
    return found


def http_status(url: str, timeout: float = 2) -> int | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
    except Exception:
        return None


def port_is_free(port: int) -> bool:
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=("stock", "fp8"), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--attempt", type=int, default=1)
    args = parser.parse_args()
    if args.seed <= 0 or args.attempt <= 0:
        parser.error("--seed and --attempt must be positive")
    if not lock_owned():
        raise SystemExit("WORK_QUEUE.lock ownership changed; refusing to start server")
    config = TASK / f"work/source23/configs/{args.arm}.json"
    suffix = "" if args.attempt == 1 else f"-attempt-{args.attempt:02d}"
    result = TASK / f"work/source23/results/{args.arm}-seed-{args.seed}{suffix}.json"
    receipt = TASK / f"receipts/source-23-{args.arm}-seed-{args.seed}{suffix}-execution.json"
    server_log = TASK / f"work/source23/server-{args.arm}-seed-{args.seed}{suffix}.log"
    if result.exists() or receipt.exists() or server_log.exists():
        raise SystemExit("refusing to overwrite prior result, receipt, or log")
    if not config.is_file() or not RUNNER.is_file() or not SERVER.is_file() or not SERVER_PYTHON.is_file():
        raise SystemExit("required config or runner is missing")
    probe = subprocess.run([str(SERVER_PYTHON), "-c", "import regex; print(regex.__version__)"],
                           capture_output=True, text=True, check=False)
    if probe.returncode:
        raise SystemExit("Strata evaluation Python is missing regex: " + probe.stderr[-1000:])
    processes = inference_processes()
    if processes:
        raise SystemExit("active inference server(s) detected; not starting GPU: " + json.dumps(processes))
    if not port_is_free(PORT):
        raise SystemExit(f"port {PORT} is occupied; not starting GPU")
    unknown_listener = {path: http_status("http://127.0.0.1:46363" + path)
                        for path in ("/v1/models", "/health", "/api/tags")}
    if any(code not in (None, 404) for code in unknown_listener.values()):
        raise SystemExit("unknown listener now responds to a standard inference health path; abort")
    result.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["CUDA_VISIBLE_DEVICES"] = "0,1"
    command = [str(SERVER_PYTHON), str(SERVER), "--engine", "strata", "--config", str(config),
               "--host", "127.0.0.1", "--port", str(PORT), "--gpu", "0,1"]
    process = None
    runner_result = None
    ready = False
    return_code = None
    failure = None
    cleanup_failure = None
    try:
        with server_log.open("xb") as log:
            process = subprocess.Popen(command, cwd=SOURCE, env=env, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            started = time.monotonic()
            while time.monotonic() - started < 600:
                if not lock_owned():
                    raise RuntimeError("lock changed during server start")
                if process.poll() is not None:
                    raise RuntimeError(f"server exited early with rc={process.returncode}")
                if http_status(f"http://127.0.0.1:{PORT}/health", timeout=2) == 200:
                    ready = True
                    break
                time.sleep(5)
            if not ready:
                raise TimeoutError("server did not become healthy within 600 seconds")
            model_status = http_status(f"http://127.0.0.1:{PORT}/v1/models", timeout=5)
            if model_status != 200:
                raise RuntimeError(f"/v1/models returned {model_status}")
            runner_result = subprocess.run([
                sys.executable, str(RUNNER), "--model", "vf-s23-iq3s", "--seed", str(args.seed),
                "--url", f"http://127.0.0.1:{PORT}/v1/chat/completions", "--out", str(result),
            ], cwd=REPO, env=env, timeout=8 * 900 + 180, check=False)
            return_code = runner_result.returncode
    except Exception as error:
        failure = f"{type(error).__name__}: {error}"
    finally:
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=45)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=15)
            except Exception as error:
                cleanup_failure = f"{type(error).__name__}: {error}"
    summary = {
        "arm": args.arm, "seed": args.seed, "serverPid": process.pid if process else None,
        "serverExitCode": process.returncode if process else None, "ready": ready,
        "runnerExitCode": return_code if runner_result else None,
        "result": str(result) if result.exists() else None, "serverLog": str(server_log),
        "portFreeAfterCleanup": port_is_free(PORT),
        "failure": failure, "cleanupFailure": cleanup_failure,
    }
    with receipt.open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return return_code if runner_result else 1


if __name__ == "__main__":
    raise SystemExit(main())
