#!/usr/bin/env python3
"""Run one isolated Strata Needle in a Haystack retrieval probe."""
import argparse
import hashlib
import json
import math
import os
import re
import signal
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path


GIB = 1024 ** 3


def json_get(url, timeout=3):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.load(response)


def system_memory():
    wanted = {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}
    values = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, rest = line.split(":", 1)
        if key in wanted:
            values[key] = int(rest.split()[0]) * 1024
    vmstat = {}
    for line in Path("/proc/vmstat").read_text().splitlines():
        key, value = line.split()
        if key in ("pswpin", "pswpout"):
            vmstat[key] = int(value)
    psi = {}
    for line in Path("/proc/pressure/memory").read_text().splitlines():
        fields = line.split()
        kind = fields[0]
        psi[kind] = {k: float(v) for k, v in (item.split("=") for item in fields[1:]) if k.startswith("avg")}
    return {"memory": values, "vmstat_pages": vmstat, "psi": psi}


def process_tree(root_pid):
    parents = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / "stat").read_text()
            tail = raw[raw.rfind(")") + 2:].split()
            parents[int(entry.name)] = int(tail[1])
        except (OSError, ValueError, IndexError):
            continue
    pids = {root_pid}
    changed = True
    while changed:
        changed = False
        for pid, parent in parents.items():
            if parent in pids and pid not in pids:
                pids.add(pid)
                changed = True
    processes = []
    for pid in sorted(pids):
        try:
            status = (Path("/proc") / str(pid) / "status").read_text()
            rss_kib = next(int(line.split()[1]) for line in status.splitlines() if line.startswith("VmRSS:"))
            cmd = (Path("/proc") / str(pid) / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
            processes.append({"pid": pid, "rss_bytes": rss_kib * 1024, "cmd": cmd[:300]})
        except (OSError, StopIteration, ValueError):
            continue
    return processes


def gpu_snapshot():
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        rows = []
        for line in result.stdout.splitlines():
            parts = [part.strip() for part in line.split(",")]
            if len(parts) == 5:
                rows.append({"index": int(parts[0]), "name": parts[1], "memory_used_mib": int(parts[2]),
                             "memory_total_mib": int(parts[3]), "utilization_percent": int(parts[4])})
        return rows
    except Exception as exc:
        return {"error": repr(exc)}


def signal_process_group(pgid, sig):
    try:
        os.killpg(pgid, sig)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def process_group_members(pgid):
    members = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            tail = (entry / "stat").read_text().rsplit(")", 1)[1].split()
            if int(tail[2]) == pgid:
                members.append(int(entry.name))
        except (OSError, ValueError, IndexError):
            continue
    return members


class Monitor:
    def __init__(self):
        self.root_pid = None
        self.rows = []
        self.stop_event = threading.Event()
        self.thread = None
        self.abort_reason = None
        self._pressure_samples = 0
        self._baseline_swapout = None

    def sample(self):
        row = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "monotonic": time.monotonic()}
        try:
            sysmem = system_memory()
            row.update(sysmem)
            if self._baseline_swapout is None:
                self._baseline_swapout = sysmem["vmstat_pages"]["pswpout"]
            if self.root_pid:
                procs = process_tree(self.root_pid)
                row["processes"] = procs
                row["process_tree_rss_bytes"] = sum(p["rss_bytes"] for p in procs)
            row["gpus"] = gpu_snapshot()
            self.rows.append(row)
            avail = sysmem["memory"].get("MemAvailable", 0)
            swapout = sysmem["vmstat_pages"].get("pswpout", 0) - self._baseline_swapout
            some = sysmem["psi"].get("some", {}).get("avg10", 0)
            full = sysmem["psi"].get("full", {}).get("avg10", 0)
            self._pressure_samples = self._pressure_samples + 1 if (some >= 80.0 or full >= 60.0) else 0
            if swapout > 1024:
                self.abort_reason = "swap-out exceeded 4 MiB during run"
            elif self._pressure_samples >= 15:
                self.abort_reason = "sustained memory PSI during run"
            elif avail < 20 * GIB:
                self.abort_reason = "MemAvailable fell below 20 GiB safety floor"
        except Exception as exc:
            self.rows.append({"utc": row["utc"], "monitor_error": repr(exc)})

    def start(self):
        self.sample()
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while not self.stop_event.wait(1.0):
            self.sample()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=3)
        self.sample()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--context", required=True, type=int)
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--fixture-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--server-root", required=True, type=Path)
    ap.add_argument("--python", required=True)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--max-tokens", type=int, default=768)
    ap.add_argument("--port", type=int, default=8350)
    args = ap.parse_args()

    args.config = args.config.resolve()
    args.fixture_dir = args.fixture_dir.resolve()
    args.out_dir = args.out_dir.resolve()
    args.server_root = args.server_root.resolve()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    config_bytes = args.config.read_bytes()
    config = json.loads(config_bytes)
    prompt_path = args.fixture_dir / "probe-prompt.txt"
    metadata = json.loads((args.fixture_dir / "probe-metadata.json").read_text())
    expected = json.loads((args.fixture_dir / "probe-expected.json").read_text())
    prompt_bytes = prompt_path.read_bytes()
    if hashlib.sha256(prompt_bytes).hexdigest() != metadata["promptSha256"]:
        raise RuntimeError("fixture prompt SHA-256 mismatch")

    command = [args.python, str(args.server_root / "serve/server.py"), "--engine", "strata",
               "--config", str(args.config), "--host", "127.0.0.1", "--port", str(args.port)]
    env = os.environ.copy()
    env["STRATA_ROOT"] = str(args.server_root)
    for key, value in config.get("env", {}).items():
        env[str(key)] = str(value)
    server_log = args.out_dir / "server.log"
    engine_log = Path(config["log"])
    deadline = time.monotonic() + args.timeout
    monitor = Monitor()
    started = time.monotonic()
    server = None
    health = None
    response_data = None
    request_bytes = None
    request_thread = None
    request_result = {}
    startup_error = None
    try:
        with server_log.open("wb") as log:
            monitor.start()
            server = subprocess.Popen(command, cwd=str(args.server_root), env=env, stdout=log,
                                      stderr=subprocess.STDOUT, start_new_session=True)
            monitor.root_pid = server.pid
            while time.monotonic() < deadline:
                if monitor.abort_reason:
                    startup_error = monitor.abort_reason
                    break
                if server.poll() is not None:
                    startup_error = f"Strata API exited during startup with code {server.returncode}"
                    break
                try:
                    health = json_get(f"http://127.0.0.1:{args.port}/health", timeout=3)
                    if health.get("status") == "ok":
                        break
                except Exception:
                    pass
                time.sleep(2)
            if not startup_error and (not health or health.get("status") != "ok"):
                startup_error = "Strata did not become healthy before the per-context deadline"
            if not startup_error and health.get("max_context") != args.context:
                startup_error = f"server context mismatch: expected {args.context}, got {health}"

            if not startup_error:
                payload = {
                    "model": health.get("model", "strata"),
                    "messages": [{"role": "user", "content": prompt_bytes.decode("utf-8")}],
                    "temperature": 0.0,
                    "top_p": 1.0,
                    "seed": 4242,
                    "top_k": 20,
                    "max_tokens": args.max_tokens,
                    "reasoning_effort": "none",
                    "chat_template_kwargs": {"enable_thinking": False},
                    "cache_prompt": False,
                    "stream": False,
                }
                request_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                (args.out_dir / "request.json").write_bytes(request_bytes)

                def send_request():
                    tick = time.monotonic()
                    request_result["started_monotonic"] = tick
                    request_result["started_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    req = urllib.request.Request(f"http://127.0.0.1:{args.port}/v1/chat/completions",
                                                 data=request_bytes, headers={"Content-Type": "application/json"},
                                                 method="POST")
                    try:
                        remaining = max(1, deadline - time.monotonic())
                        with urllib.request.urlopen(req, timeout=remaining) as response:
                            request_result["http_status"] = response.status
                            request_result["response"] = json.load(response)
                    except Exception as exc:
                        request_result["error"] = repr(exc)
                    request_result["elapsed_seconds"] = time.monotonic() - tick

                request_thread = threading.Thread(target=send_request, daemon=True)
                request_thread.start()
                while request_thread.is_alive() and time.monotonic() < deadline:
                    if monitor.abort_reason:
                        request_result["error"] = monitor.abort_reason
                        signal_process_group(server.pid, signal.SIGTERM)
                        break
                    request_thread.join(timeout=0.5)
                if request_thread.is_alive():
                    request_result["error"] = request_result.get("error", "per-context timeout")
                    signal_process_group(server.pid, signal.SIGTERM)
    except Exception as exc:
        startup_error = repr(exc)
    finally:
        hard_abort = bool(startup_error or monitor.abort_reason or request_result.get("error"))
        if server and hard_abort:
            signal_process_group(server.pid, signal.SIGTERM)
        elif server and server.poll() is None:
            server.terminate()
        if server:
            try:
                server.wait(timeout=60)
            except subprocess.TimeoutExpired:
                # The isolated session contains only this runner's server and its engine child.
                signal_process_group(server.pid, signal.SIGTERM)
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    signal_process_group(server.pid, signal.SIGKILL)
                    try:
                        server.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        pass
            if hard_abort:
                group_deadline = time.monotonic() + 10
                while process_group_members(server.pid) and time.monotonic() < group_deadline:
                    time.sleep(0.2)
                if process_group_members(server.pid):
                    signal_process_group(server.pid, signal.SIGKILL)
        monitor.stop()
    response_data = request_result.get("response")
    if response_data is not None:
        (args.out_dir / "response.json").write_text(json.dumps(response_data, ensure_ascii=False, indent=2) + "\n")
    rows = monitor.rows
    gpu_ids = sorted({gpu.get("index") for row in rows for gpu in row.get("gpus", []) if isinstance(gpu, dict) and "index" in gpu})
    gpu_summary = {}
    for idx in gpu_ids:
        values = [gpu["memory_used_mib"] for row in rows for gpu in row.get("gpus", [])
                  if isinstance(gpu, dict) and gpu.get("index") == idx]
        gpu_summary[str(idx)] = {"baseline_mib": values[0] if values else None,
                                 "peak_total_used_mib": max(values) if values else None,
                                 "peak_delta_mib": max(values) - values[0] if values else None}
    rss_values = [row.get("process_tree_rss_bytes", 0) for row in rows]
    avail_values = [row.get("memory", {}).get("MemAvailable", 0) for row in rows]
    swapin0 = rows[0].get("vmstat_pages", {}).get("pswpin", 0) if rows else 0
    swapout0 = rows[0].get("vmstat_pages", {}).get("pswpout", 0) if rows else 0
    swapin1 = rows[-1].get("vmstat_pages", {}).get("pswpin", 0) if rows else 0
    swapout1 = rows[-1].get("vmstat_pages", {}).get("pswpout", 0) if rows else 0
    timings = (response_data or {}).get("timings") or {}
    usage = (response_data or {}).get("usage") or {}
    prompt_tokens = usage.get("prompt_tokens")
    min_prompt_tokens = math.ceil(args.context * 0.95)
    err = request_result.get("error") or startup_error
    choices = (response_data or {}).get("choices") or []
    finish_reason = choices[0].get("finish_reason") if choices else None
    raw_content = str(((choices[0].get("message") or {}).get("content") or "")) if choices else ""
    parsed = None
    try:
        parsed = json.loads(raw_content.strip())
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw_content, re.S)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    exact_matches = {key: isinstance(parsed, dict) and parsed.get(key) == value
                     for key, value in expected.items()}
    correct = sum(exact_matches.values())
    if err or request_result.get("http_status") != 200:
        classification = "invalid infrastructure"
    elif not isinstance(prompt_tokens, int) or prompt_tokens < min_prompt_tokens or finish_reason != "stop":
        classification = "incomplete"
    else:
        classification = "valid quality"
    receipt = {
        "task": "Q-20261014-ISTA-NEEDLE-HAYSTACK",
        "suite": "context-retrieval-v1 / exact 10-fact retrieval",
        "profile": "ASTRA DEFAULT / ISTA IQ2_XS / Strata",
        "context_limit": args.context,
        "classification": classification,
        "quality_score": {"correct": correct, "total": len(expected), "percent": round(correct / max(1, len(expected)) * 100, 2)},
        "exact_matches": exact_matches,
        "expected": expected,
        "parsed_answer": parsed,
        "raw_answer": raw_content,
        "finish_reason": finish_reason,
        "fact_positions": metadata.get("factPositionsTextOnly"),
        "completed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "server_command": command,
        "server_exit_code": server.returncode if server else None,
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "prompt_sha256": metadata["promptSha256"],
        "prompt_text_tokens": metadata["tokenizerTextOnlyTokens"],
        "prompt_bytes": metadata["promptBytes"],
        "minimum_prompt_tokens_95pct": min_prompt_tokens,
        "health": health,
        "request_sha256": hashlib.sha256(request_bytes).hexdigest() if request_bytes else None,
        "request_sent": bool(request_result.get("started_utc")),
        "model_loaded": bool(health and health.get("loaded")),
        "request_max_tokens": args.max_tokens,
        "sampling": {"temperature": 0.0, "top_p": 1.0, "top_k": 20, "seed": 4242, "thinking": False, "cache_prompt": False},
        "request_started_utc": request_result.get("started_utc"),
        "request_elapsed_seconds": request_result.get("elapsed_seconds"),
        "transport_error": err,
        "http_status": request_result.get("http_status"),
        "response": response_data,
        "usage": usage,
        "timings": timings,
        "prefill_tokens_per_second": timings.get("prompt_per_second"),
        "decode_tokens_per_second": timings.get("predicted_per_second"),
        "ttft_engine_seconds": (timings.get("prompt_ms") / 1000.0) if isinstance(timings.get("prompt_ms"), (int, float)) else None,
        "peak_process_tree_rss_bytes": max(rss_values) if rss_values else None,
        "min_system_mem_available_bytes": min(avail_values) if avail_values else None,
        "gpu_memory": gpu_summary,
        "swap_delta_pages": {"pswpin": swapin1 - swapin0, "pswpout": swapout1 - swapout0},
        "monitor_abort_reason": monitor.abort_reason,
        "monitor_sample_count": len(rows),
        "monitor_samples": rows,
        "server_log": str(server_log),
        "engine_log": str(engine_log),
        "total_server_session_seconds": time.monotonic() - started,
    }
    (args.out_dir / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: receipt.get(k) for k in ["context_limit", "classification", "quality_score", "request_elapsed_seconds",
                  "prefill_tokens_per_second", "decode_tokens_per_second", "peak_process_tree_rss_bytes",
                  "min_system_mem_available_bytes", "gpu_memory", "swap_delta_pages", "transport_error"]}, indent=2))
    return 0 if classification == "valid quality" else 2


if __name__ == "__main__":
    raise SystemExit(main())
