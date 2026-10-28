#!/usr/bin/env python3
"""Run the preregistered Gemma 4 Q4_0 Q172 quality/safety screen."""

from __future__ import annotations

import json
import os
import pathlib
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

from run_gemma_a18_completion import (
    ART, HOST, LOCK_TOKEN, MODEL, PORT, SERVER, TEMPLATE,
    EXPECTED_MODEL_SHA256, EXPECTED_SERVER_SHA256, EXPECTED_TEMPLATE_SHA256,
    inference_processes, inference_containers, port_is_free, resource_state, gpu_state, sha256,
    now, atomic_json, append_jsonl, stop_owned,
)


ROOT = pathlib.Path(__file__).resolve().parents[4]
RUNS = ART / "runs/gemma-a18"
LOGS = ART / "logs/gemma-a18"
RECEIPTS = ART / "receipts"
TOOL_EVAL = pathlib.Path(
    "/home/cristian/.cache/codex-tool-eval-bench-v2.8.0/.venv/bin/tool-eval-bench"
)
TOOL_EVAL_COMMIT = "0a1ba68c7709f429298bc92417a9e003f61de4e3"
MODEL_ALIAS = "gemma-4-12b-it-qat-q4_0-q173-a18"
CONTEXT = 131072
MIN_AVAILABLE_KIB = 32 * 1024 * 1024


def http_json(path: str, body=None, timeout=30):
    url = f"http://{HOST}:{PORT}{path}"
    if body is None:
        req = urllib.request.Request(url, method="GET")
    else:
        data = json.dumps(body, separators=(",", ":")).encode()
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read()
        return response.status, json.loads(raw)


def request_readiness_smoke():
    body = {
        "model": MODEL_ALIAS,
        "messages": [{"role": "user", "content": "Use the calculator tool to multiply 17 by 19."}],
        "tools": [{
            "type": "function",
            "function": {
                "name": "calculator",
                "description": "Multiply two numbers.",
                "parameters": {
                    "type": "object",
                    "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                    "required": ["a", "b"],
                },
            },
        }],
        "tool_choice": "auto",
        "temperature": 0.6,
        "top_p": 0.95,
        "top_k": 20,
        "min_p": 0.0,
        "repeat_penalty": 1.0,
        "presence_penalty": 0.0,
        "seed": 42,
        "reasoning_effort": "medium",
        "max_tokens": 128,
        "stream": False,
    }
    status, result = http_json("/v1/chat/completions", body, timeout=300)
    choices = result.get("choices")
    if status != 200 or not isinstance(choices, list) or not choices:
        raise RuntimeError("OpenAI-compatible tool readiness smoke returned no valid choice")
    message = choices[0].get("message") or {}
    return {
        "timestamp_utc": now(),
        "http_status": status,
        "model": result.get("model"),
        "choice_count": len(choices),
        "assistant_message_present": bool(message),
        "tool_call_count": len(message.get("tool_calls") or []),
        "finish_reason": choices[0].get("finish_reason"),
        "unscored": True,
        "passed": True,
    }


def readiness(proc, log_path):
    deadline = time.monotonic() + 600
    last_error = None
    while time.monotonic() < deadline and proc.poll() is None:
        try:
            status, health = http_json("/health", timeout=5)
            if status == 200 and health.get("status") == "ok":
                _, models = http_json("/v1/models", timeout=10)
                ids = [x.get("id") for x in models.get("data", [])]
                if MODEL_ALIAS not in ids:
                    raise RuntimeError(f"API model alias mismatch: {ids}")
                return {"health": health, "model_ids": ids, "ready_utc": now()}
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(3)
    tail = log_path.read_text(errors="replace").splitlines()[-80:] if log_path.exists() else []
    raise RuntimeError(f"Gemma server readiness failed; exit={proc.poll()}; last={last_error}; log_tail={tail}")


def main():
    RUNS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    pre = resource_state()
    hashes = {
        "model_sha256": sha256(MODEL),
        "server_sha256": sha256(SERVER),
        "template_sha256": sha256(TEMPLATE),
        "tool_eval_source_commit": TOOL_EVAL_COMMIT,
    }
    pinned = (hashes["model_sha256"] == EXPECTED_MODEL_SHA256 and
              hashes["server_sha256"] == EXPECTED_SERVER_SHA256 and
              hashes["template_sha256"] == EXPECTED_TEMPLATE_SHA256 and TOOL_EVAL.is_file())
    preflight = {
        "task": "Q173 A18 Gemma Q172 Hard Mode seed42 preflight",
        "timestamp_utc": now(),
        "lock_token": LOCK_TOKEN,
        "preregistration": "receipts/prereg-amendment-18-gemma4-q4-context-and-q172.json",
        "hashes": hashes,
        "model_path": str(MODEL),
        "runtime_path": str(SERVER),
        "template_path": str(TEMPLATE),
        "tool_eval_path": str(TOOL_EVAL),
        "context_tokens": CONTEXT,
        "resource_state": pre,
        "port_free": port_is_free(),
        "decision": "PASS" if pinned and not pre["inference_processes"] and not pre["inference_containers"] and port_is_free() else "BLOCKED",
        "gui_preserved": True,
    }
    atomic_json(RECEIPTS / "gemma-a18-q172-preflight.json", preflight)
    if preflight["decision"] != "PASS":
        raise SystemExit("Gemma Q172 preflight blocked before model load")

    argv = [
        str(SERVER), "--model", str(MODEL), "--alias", MODEL_ALIAS,
        "--host", HOST, "--port", str(PORT), "--device", "CUDA0,CUDA1",
        "--split-mode", "layer", "--tensor-split", "1,1", "--gpu-layers", "all",
        "--ctx-size", str(CONTEXT), "--parallel", "1", "--flash-attn", "on",
        "--seed", "42", "--no-warmup", "--reasoning", "on", "--reasoning-effort", "medium",
        "--jinja", "--chat-template-file", str(TEMPLATE),
    ]
    server_log = LOGS / "q172-server.log"
    tool_log = LOGS / "q172-tool-eval.log"
    result_path = RUNS / "q172-seed42.json"
    report_dir = RUNS / "q172-reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    harness_argv = [
        str(TOOL_EVAL), "run", "--model", MODEL_ALIAS, "--backend", "llamacpp",
        "--base-url", f"http://{HOST}:{PORT}/v1", "--format", "openai",
        "--temperature", "0.6", "--top-p", "0.95", "--top-k", "20", "--min-p", "0.0",
        "--repeat-penalty", "1.0", "--seed", "42",
        "--backend-kwargs", json.dumps({"reasoning_effort": "medium", "presence_penalty": 0.0}),
        "--variant-seed", "20261010", "--hardmode", "--scenarios",
        *[f"TC-{n}" for n in range(70, 98)], "--timeout", "120", "--max-turns", "8",
        "--trials", "1", "--parallel", "1", "--no-warmup", "--fail-on-safety",
        "--label", "Q173-Gemma4-Q4_0-Q172-seed42", "--redact-url",
        "--output-dir", str(report_dir), "--json-file", str(result_path),
    ]

    server_proc = None
    tool_proc = None
    status = "failed"
    error = None
    smoke = None
    samples = []
    try:
        with server_log.open("w", encoding="utf-8") as sl:
            server_proc = subprocess.Popen(argv, stdout=sl, stderr=subprocess.STDOUT,
                                           start_new_session=True, cwd=str(SERVER.parent),
                                           env={**os.environ, "CUDA_VISIBLE_DEVICES": "0,1"})
            ready = readiness(server_proc, server_log)
            base_gpu = {int(x["index"]): int(x["memory_used_mib"]) for x in pre["gpu"]}
            allocation = gpu_state()
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                if isinstance(allocation, list) and all(
                    next((int(x["memory_used_mib"]) for x in allocation if int(x["index"]) == i), 0)
                    - base_gpu.get(i, 0) > 1024 for i in (0, 1)
                ):
                    break
                if server_proc.poll() is not None:
                    raise RuntimeError("Gemma server exited before dual-GPU allocation gate")
                time.sleep(3)
                allocation = gpu_state()
            if not isinstance(allocation, list) or any(
                next((int(x["memory_used_mib"]) for x in allocation if int(x["index"]) == i), 0)
                - base_gpu.get(i, 0) <= 1024 for i in (0, 1)
            ):
                raise RuntimeError(f"Dual-GPU allocation gate failed: baseline={base_gpu}, current={allocation}")
            ready["gpu_allocation_gate"] = {"passed": True, "baseline_memory_mib": base_gpu,
                                              "current_gpu": allocation}
            smoke = request_readiness_smoke()
            atomic_json(RECEIPTS / "gemma-a18-q172-smoke.json", {
                "task": "Q173 A18 unscored Gemma tool readiness smoke",
                "timestamp_utc": now(), "readiness": ready, **smoke,
            })
            with tool_log.open("w", encoding="utf-8") as tl:
                tool_proc = subprocess.Popen(harness_argv, stdout=tl, stderr=subprocess.STDOUT,
                                             start_new_session=True, cwd=str(ROOT), env=os.environ.copy())
                below = 0
                while tool_proc.poll() is None:
                    sample = resource_state()
                    append_jsonl(LOGS / "q172-resources.jsonl", sample)
                    available = sample.get("MemAvailable_kib")
                    below = below + 1 if available is not None and available < MIN_AVAILABLE_KIB else 0
                    if below >= 4:
                        tool_proc.send_signal(signal.SIGINT)
                        raise RuntimeError("MemAvailable stayed below 32 GiB for four 15s samples")
                    time.sleep(15)
                code = tool_proc.returncode
                if not result_path.exists():
                    raise RuntimeError(f"Tool-Eval returned {code} without a result JSON")
                result = json.loads(result_path.read_text())
                scenario_count = int(result.get("total_scenarios", 0))
                status = "complete" if result.get("status") == "completed" and scenario_count == 28 else "incomplete"
                if code not in (0, 2):
                    status = "failed"
                    raise RuntimeError(f"Tool-Eval exit={code}; status={result.get('status')}; scenario_count={scenario_count}")
                samples = result.get("scores") or []
                atomic_json(RECEIPTS / "gemma-a18-q172-launch.json", {
                    "task": "Q173 Gemma 4 Q4_0 Q172 Tool-Eval Hard Mode seed42",
                    "registered_utc": now(),
                    "preregistration": "receipts/prereg-amendment-18-gemma4-q4-context-and-q172.json",
                    "server": {"pid": server_proc.pid, "argv": argv,
                               "endpoint": f"http://{HOST}:{PORT}/v1", "context": CONTEXT,
                               "hashes": hashes, "readiness": ready},
                    "unscored_smoke": smoke,
                    "gpu_allocation_gate": ready["gpu_allocation_gate"],
                    "harness": {"version": "2.8.0", "source_commit": TOOL_EVAL_COMMIT,
                                "command": harness_argv, "seed": 42, "variant_seed": 20261010,
                                "scenarios": [f"TC-{n}" for n in range(70, 98)],
                                "context": CONTEXT, "parallel": 1, "exit_code": code},
                    "status": status,
                    "result_json": str(result_path.relative_to(ROOT)),
                    "log": str(tool_log.relative_to(ROOT)),
                    "score_scope": "quality/safety only; one seed; no speed claim",
                })
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        if not (RECEIPTS / "gemma-a18-q172-launch.json").exists():
            atomic_json(RECEIPTS / "gemma-a18-q172-launch.json", {
                "task": "Q173 Gemma 4 Q4_0 Q172 Tool-Eval Hard Mode seed42",
                "registered_utc": now(), "preregistration": "receipts/prereg-amendment-18-gemma4-q4-context-and-q172.json",
                "status": status, "error": error, "readiness_smoke": smoke,
                "result_json": str(result_path.relative_to(ROOT)),
            })
    finally:
        if tool_proc and tool_proc.poll() is None:
            tool_proc.send_signal(signal.SIGINT)
            try:
                tool_proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                tool_proc.terminate()
                try:
                    tool_proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    tool_proc.kill()
                    tool_proc.wait(timeout=5)
        if server_proc:
            stop_owned(server_proc, None)
        poststate = resource_state()
        postflight = {
            "task": "Q173 A18 Gemma Q172 Hard Mode seed42 postflight",
            "timestamp_utc": now(), "lock_token": LOCK_TOKEN,
            "status": status, "error": error,
            "tool_eval_exit_code": tool_proc.returncode if tool_proc else None,
            "result_json_exists": result_path.exists(),
            "result_json": str(result_path.relative_to(ROOT)),
            "inference_processes": poststate["inference_processes"],
            "inference_containers": poststate["inference_containers"],
            "port_free": port_is_free(), "resource_state": poststate,
            "gui_preserved": True,
        }
        postflight["decision"] = "PASS" if postflight["port_free"] and not postflight["inference_processes"] and not postflight["inference_containers"] else "CHECK"
        atomic_json(RECEIPTS / "gemma-a18-q172-postflight.json", postflight)
    print(json.dumps({"status": status, "error": error, "result_json": str(result_path),
                      "postflight": postflight["decision"]}, ensure_ascii=False))
    if error or status != "complete":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
