#!/usr/bin/env python3
"""Run one isolated cold speed sample for the Q4 MTP A/B."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "configs/ab-fingerprint.json").read_text())
FIXTURE_PATH = ROOT / "fixtures/speed-prompt.txt"


def get_json(url, payload=None, timeout=900):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="GET" if data is None else "POST")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def stop_own_server(proc, timeout=30):
    if proc.poll() is not None:
        return proc.returncode
    os.killpg(proc.pid, signal.SIGINT)
    try:
        return proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            return proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            return proc.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("control", "candidate"), required=True)
    parser.add_argument("--seed", type=int, choices=(42, 43, 44), required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    label = "mtp_off" if args.mode == "control" else "mtp_on"
    out_dir = ROOT / "receipts" / "speed" / args.mode
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / f"seed-{args.seed}.json"
    if result_path.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite existing result: {result_path}")

    fixture = FIXTURE_PATH.read_text()
    fixture_hash = hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest()
    binary = CONFIG["runtime"]["binary"]
    argv = [binary, *CONFIG["control_args"]]
    if args.mode == "candidate":
        argv.extend(CONFIG["candidate_additional_args"])
    log_path = ROOT / "receipts" / "logs" / f"speed-{args.mode}-seed{args.seed}-server.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = "0,1"

    launch_time = dt.datetime.now(dt.timezone.utc).isoformat()
    log_file = log_path.open("wb")
    proc = subprocess.Popen(argv, cwd="/home/cristian/.cache/llamacode/llama.cpp-spark-native-20261003", stdout=log_file, stderr=subprocess.STDOUT, env=env, start_new_session=True)
    launch = {"mode": label, "seed": args.seed, "started_at_utc": launch_time, "pid": proc.pid, "argv": argv, "log": str(log_path), "fixture_sha256": fixture_hash}
    (out_dir / f"seed-{args.seed}-launch.json").write_text(json.dumps(launch, indent=2) + "\n")

    base_url = CONFIG["api"]["base_url"]
    try:
        deadline = time.monotonic() + 120
        last_error = None
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(f"server exited before health check with code {proc.returncode}")
            try:
                health = get_json(base_url + "/health", timeout=2)
                if health.get("status") == "ok":
                    break
            except Exception as exc:  # health is polled while our own server loads
                last_error = repr(exc)
            time.sleep(1)
        else:
            raise RuntimeError(f"server health timeout; last error={last_error}")

        request = {
            "model": "qwen3.8-flash-next-unsloth-ud-q4_k_xl",
            "messages": [
                {"role": "system", "content": "You are an evaluator. Follow the user prompt exactly and keep output concise."},
                {"role": "user", "content": fixture},
            ],
            "max_tokens": 256,
            "ignore_eos": True,
            "temperature": 0.6,
            "top_p": 0.95,
            "top_k": 20,
            "min_p": 0.0,
            "repeat_penalty": 1.0,
            "presence_penalty": 0.0,
            "seed": args.seed,
            "chat_template_kwargs": {"enable_thinking": True, "reasoning_effort": "medium"},
        }
        start_utc = dt.datetime.now(dt.timezone.utc).isoformat()
        t0 = time.perf_counter()
        response = get_json(base_url + "/v1/chat/completions", request, timeout=900)
        elapsed = time.perf_counter() - t0
        record = {
            "status": "complete",
            "mode": label,
            "seed": args.seed,
            "server_launch_at_utc": launch_time,
            "request_started_at_utc": start_utc,
            "elapsed_wall_seconds": elapsed,
            "fixture_path": str(FIXTURE_PATH),
            "fixture_sha256": fixture_hash,
            "fixture_content_tokens": 23569,
            "prompt_cache_state": "fresh server process for this sample; no previous KV slot contents",
            "request_config": {k: v for k, v in request.items() if k != "messages"},
            "response": response,
        }
        result_path.write_text(json.dumps(record, indent=2) + "\n")
        timings = response.get("timings", {})
        usage = response.get("usage", {})
        print(json.dumps({"mode": label, "seed": args.seed, "elapsed_wall_seconds": round(elapsed, 3), "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"), "timings": timings}), flush=True)
    except BaseException as exc:
        error_path = out_dir / f"seed-{args.seed}-error.json"
        error_path.write_text(json.dumps({"status": "incomplete", "mode": label, "seed": args.seed, "time_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "error": repr(exc), "log": str(log_path), "fixture_sha256": fixture_hash}, indent=2) + "\n")
        raise
    finally:
        rc = stop_own_server(proc)
        log_file.close()
        cleanup = {"mode": label, "seed": args.seed, "server_pid": proc.pid, "exit_code": rc, "stopped_at_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
        (out_dir / f"seed-{args.seed}-cleanup.json").write_text(json.dumps(cleanup, indent=2) + "\n")


if __name__ == "__main__":
    main()
