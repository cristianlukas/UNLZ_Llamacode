#!/usr/bin/env python3
"""Run three paired, isolated Strata cold-prefill/compaction comparisons."""
from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from prompt_utils import (TASK, base_request, load_scenario, make_tools, messages_for_compaction,
                          messages_for_initial)

HOST, PORT = "127.0.0.1", 8352
SOURCE = Path("/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source")
PYTHON = SOURCE / ".venv/bin/python"
ENGINE_RE = re.compile(
    r"prompt (?P<prompt>\d+) tokens = (?P<reused>\d+) reused \+ (?P<read>\d+)(?: of \d+)? read "
    r"in (?P<read_ms>[\d.]+) ms \((?P<pp>[\d.]+) tok/s\), (?P<gen>\d+) generated in "
    r"(?P<gen_ms>[\d.]+) ms \((?P<tg>[\d.]+) tok/s\)"
)
EXPECTED = {
    "beginning": "KEY-ALPHA-7319",
    "middle": "KEY-BRAVO-2846",
    "late": "KEY-CHARLIE-9052",
    "ending": "KEY-DELTA-4173",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get_json(url: str, timeout: int = 5) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, payload: dict, timeout: int = 1800) -> tuple[int, dict, float]:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=raw, headers={"Content-Type": "application/json"})
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8")), time.perf_counter() - start
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"raw_error": body}
        return error.code, parsed, time.perf_counter() - start


def text_output(response: dict) -> str:
    out = []
    for item in response.get("output", []):
        for content in item.get("content", []) if isinstance(item, dict) else []:
            if isinstance(content, dict) and content.get("type") in ("output_text", "text"):
                out.append(content.get("text", ""))
    return "\n".join(out)


def gpu_snapshot() -> str:
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total,utilization.gpu", "--format=csv,noheader"],
        check=False, capture_output=True, text=True, timeout=10,
    )
    return result.stdout.strip() if result.returncode == 0 else f"nvidia-smi exit={result.returncode}: {result.stderr.strip()}"


def telemetry(path: Path, stop: threading.Event) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write("observed_utc,device_timestamp,index,memory_used_mib,utilization_percent,temperature_c\n")
        while not stop.is_set():
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=timestamp,index,memory.used,utilization.gpu,temperature.gpu",
                 "--format=csv,noheader,nounits"],
                check=False, capture_output=True, text=True, timeout=10,
            )
            for row in result.stdout.splitlines():
                f.write(f"{utc_now()},{row}\n")
            f.flush()
            stop.wait(1.0)


def wait_ready(proc: subprocess.Popen, timeout_s: int = 600) -> tuple[dict, float]:
    start = time.perf_counter()
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"server exited during startup with code {proc.returncode}")
        try:
            last = get_json(f"http://{HOST}:{PORT}/health")
            if last.get("loaded") is True:
                return last, time.perf_counter() - start
        except (OSError, ValueError, urllib.error.URLError):
            pass
        time.sleep(2)
    raise TimeoutError(f"server was not loaded within {timeout_s}s; last health={last}")


def stop_server(proc: subprocess.Popen) -> dict:
    result = {"signal": "SIGINT", "exit_code": None, "forced_group_termination": False}
    if proc.poll() is None:
        try:
            proc.send_signal(signal.SIGINT)
            proc.wait(timeout=90)
        except subprocess.TimeoutExpired:
            result["forced_group_termination"] = True
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=10)
    result["exit_code"] = proc.returncode
    return result


def runtime_metrics(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    rows = []
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = ENGINE_RE.search(line)
        if match:
            row = {key: (float(value) if key in ("read_ms", "pp", "gen_ms", "tg") else int(value))
                   for key, value in match.groupdict().items()}
            row["raw_line"] = line.strip()
            rows.append(row)
    return rows


def run_one(index: int, arm: str, pair: int, scenario: dict) -> dict:
    enabled = arm == "B"
    run_id = f"pair-{pair:02d}-{arm}"
    out_dir = TASK / "receipts" / "runs" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    config_path = TASK / "configs" / ("candidate.json" if enabled else "control.json")
    effective = json.loads(config_path.read_text(encoding="utf-8"))
    effective["log"] = str(out_dir / "engine.log")
    effective["port"] = PORT
    runtime_config = out_dir / "runtime-config.json"
    runtime_config.write_text(json.dumps(effective, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tools = make_tools()
    first_req = base_request(messages_for_initial(scenario), "turn", "eval-session-20261012",
                             "cold-prefill-128k-thread", tools, 16)
    first_req["tool_choice"] = "auto"
    req_path = out_dir / "initial-request.json"
    req_path.write_text(json.dumps(first_req, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    port_guard = socket.socket()
    try:
        port_guard.settimeout(0.2)
        if port_guard.connect_ex((HOST, PORT)) == 0:
            raise RuntimeError(f"refusing to use occupied port {HOST}:{PORT}")
    finally:
        port_guard.close()

    before_gpu = gpu_snapshot()
    print(json.dumps({"event": "run_start", "run_id": run_id, "arm": arm, "codex_compaction_cache": enabled,
                      "utc": utc_now(), "gpu": before_gpu}, ensure_ascii=False), flush=True)
    env = os.environ.copy()
    lib_dirs = effective.get("lib_dirs", [])
    env["LD_LIBRARY_PATH"] = ":".join([*lib_dirs, env.get("LD_LIBRARY_PATH", "")]).rstrip(":")
    env["PYTHONUNBUFFERED"] = "1"
    log_path = out_dir / "server.log"
    telemetry_path = out_dir / "gpu-telemetry.csv"
    stop_event = threading.Event()
    server_log = log_path.open("w", encoding="utf-8")
    start = time.perf_counter()
    proc = subprocess.Popen(
        [str(PYTHON), str(SOURCE / "serve/server.py"), "--engine", "strata", "--config", str(runtime_config),
         "--host", HOST, "--port", str(PORT)],
        cwd=effective["cwd"], env=env, stdout=server_log, stderr=subprocess.STDOUT, start_new_session=True,
    )
    watcher = threading.Thread(target=telemetry, args=(telemetry_path, stop_event), daemon=True)
    watcher.start()
    outcome = {"run_id": run_id, "pair": pair, "arm": arm, "cache_enabled": enabled,
               "config_sha256": sha256(runtime_config), "request_sha256": sha256(req_path),
               "started_utc": utc_now(), "gpu_before": before_gpu, "classification": "incompleta"}
    try:
        health, load_s = wait_ready(proc)
        outcome["ready_health"] = health
        outcome["model_load_s"] = round(load_s, 3)
        outcome["server_start_to_ready_s"] = round(time.perf_counter() - start, 3)
        status, first_response, first_s = post_json(f"http://{HOST}:{PORT}/v1/responses", first_req)
        first_out = out_dir / "initial-response.json"
        first_out.write_text(json.dumps(first_response, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        outcome["initial"] = {"http_status": status, "wall_s": round(first_s, 3), "response_sha256": sha256(first_out),
                              "status": first_response.get("status"), "usage": first_response.get("usage"),
                              "text": text_output(first_response), "error": first_response.get("error")}
        comp_req = base_request(messages_for_compaction(scenario, first_response), "compaction",
                                "eval-session-20261012", "cold-prefill-128k-thread", [], 512)
        comp_req_path = out_dir / "compaction-request.json"
        comp_req_path.write_text(json.dumps(comp_req, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        status, comp_response, comp_s = post_json(f"http://{HOST}:{PORT}/v1/responses", comp_req)
        comp_out = out_dir / "compaction-response.json"
        comp_out.write_text(json.dumps(comp_response, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        summary_text = text_output(comp_response)
        lowered_summary = summary_text.lower()
        retrieved = {label: label in lowered_summary and value in summary_text for label, value in EXPECTED.items()}
        outcome["compaction"] = {"http_status": status, "wall_s": round(comp_s, 3),
                                 "request_sha256": sha256(comp_req_path), "response_sha256": sha256(comp_out),
                                 "status": comp_response.get("status"), "usage": comp_response.get("usage"),
                                 "text": summary_text, "retrieved_facts": retrieved,
                                 "error": comp_response.get("error")}
        outcome["classification"] = (
            "válida de calidad" if status == 200 and outcome["initial"]["http_status"] == 200 and
            first_response.get("status") == "completed" and comp_response.get("status") == "completed"
            else "incompleta"
        )
        if status >= 500 or outcome["initial"]["http_status"] >= 500:
            outcome["classification"] = "inválida por infraestructura" if status >= 500 or outcome["initial"]["http_status"] >= 500 else "incompleta"
        outcome["engine_requests"] = runtime_metrics(out_dir / "engine.log")
        outcome["gpu_after_requests"] = gpu_snapshot()
    except Exception as error:
        outcome["error"] = f"{type(error).__name__}: {error}"
        outcome["classification"] = "inválida por infraestructura"
    finally:
        outcome["server_stop"] = stop_server(proc)
        stop_event.set()
        watcher.join(timeout=12)
        server_log.close()
        outcome["finished_utc"] = utc_now()
        outcome["elapsed_s"] = round(time.perf_counter() - start, 3)
        outcome["engine_requests"] = runtime_metrics(out_dir / "engine.log")
        outcome["gpu_after_stop"] = gpu_snapshot()
        (out_dir / "result.json").write_text(json.dumps(outcome, indent=2, ensure_ascii=False) + "\n",
                                               encoding="utf-8")
        print(json.dumps({"event": "run_end", "run_id": run_id, "classification": outcome["classification"],
                          "elapsed_s": outcome["elapsed_s"], "requests": outcome["engine_requests"],
                          "error": outcome.get("error"), "gpu_after_stop": outcome["gpu_after_stop"]},
                         ensure_ascii=False), flush=True)
    return outcome


def main() -> int:
    scenario = load_scenario()
    orders = [(1, "A"), (1, "B"), (2, "B"), (2, "A"), (3, "A"), (3, "B")]
    results = []
    for index, (pair, arm) in enumerate(orders, 1):
        results.append(run_one(index, arm, pair, scenario))
        if index < len(orders):
            time.sleep(8)
    summary = {"task_id": "Q-20261009-STRATA-COLD-PREFILL-128K", "completed_utc": utc_now(),
               "protocol_order": [f"pair-{pair:02d}-{arm}" for pair, arm in orders], "runs": results}
    out = TASK / "receipts" / "comparison.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"event": "comparison_complete", "out": str(out), "valid_runs": sum(
        r["classification"] == "válida de calidad" for r in results)}, ensure_ascii=False), flush=True)
    return 0 if all(r["classification"] == "válida de calidad" for r in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
