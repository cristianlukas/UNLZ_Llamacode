#!/usr/bin/env python3
"""Measure Q176 warm-page-cache launch to readiness for the exact Q174 Bonsai profile."""
from __future__ import annotations

import json
import os
import pathlib
import signal
import socket
import subprocess
import time
import urllib.request
from datetime import datetime, timezone

REPO = pathlib.Path(__file__).resolve().parents[4]
ART = pathlib.Path(__file__).resolve().parents[1]
BIN = pathlib.Path("/tmp/q174-d/ninfer-build-short/apps/ninfer-serve")
MODEL = pathlib.Path("/tmp/q174-d/model/Ternary-Bonsai-2-27B-ninfer-v3.ninfer")
LOG = ART / "logs/bonsai-ninfer-hot-start.log"
OUT = ART / "receipts/bonsai-ninfer-hot-start.json"
HOST, PORT = "127.0.0.1", 18574
LOCK_TOKEN = "2242863e-c78e-4fa9-9649-c1d1541f3919"
SHA_MODEL = "cdc4810b0ff17c40d0f62cf214b6e0bcd08346e9eb05ca53371507037793c14a"
SHA_BIN = "09145c529015ac7d27ce63214138625927c70c1e89e4291594d74be59bd5f895"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def atomic_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)


def lock_check():
    lock = json.loads((REPO / "WORK_QUEUE.lock").read_text())
    if lock.get("token") != LOCK_TOKEN:
        raise RuntimeError("umbrella WORK_QUEUE.lock changed; stop")


def servers():
    found = []
    for ent in pathlib.Path("/proc").iterdir():
        if not ent.name.isdigit() or int(ent.name) == os.getpid():
            continue
        try:
            comm = (ent / "comm").read_text().strip().lower()
            cmd = (ent / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            continue
        if comm in {"llama-server", "ninfer-serve", "ollama", "vllm", "aphrodite-engine"}:
            found.append({"pid": int(ent.name), "comm": comm, "cmdline": cmd[:350]})
    return found


def gpu():
    p = subprocess.run(["nvidia-smi", "--query-gpu=index,memory.used,memory.total,utilization.gpu",
                        "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5, check=True)
    out = {}
    for line in p.stdout.splitlines():
        i, used, total, util = [x.strip() for x in line.split(",")]
        out[int(i)] = {"used_mib": int(used), "total_mib": int(total), "util_percent": int(util)}
    return out


def mem_available_kib():
    return next(int(x.split()[1]) for x in pathlib.Path("/proc/meminfo").read_text().splitlines()
                if x.startswith("MemAvailable:"))


def port_free():
    s = socket.socket()
    try:
        return s.connect_ex((HOST, PORT)) != 0
    finally:
        s.close()


def stop(proc):
    if proc.poll() is None:
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait(timeout=5)


def main():
    lock_check()
    if servers():
        raise RuntimeError(f"another inference server is active: {servers()}")
    if not port_free():
        raise RuntimeError(f"port {PORT} is occupied")
    if not MODEL.is_file() or not BIN.is_file():
        raise RuntimeError("fixed model or runtime path missing")
    base_gpu = gpu()
    if mem_available_kib() < 32 * 1024 * 1024:
        raise RuntimeError("less than 32 GiB available before launch")
    argv = [str(BIN), str(MODEL), "--max-context", "262144", "--kv-capacity", "262144",
            "--kv-dtype", "rk8v4", "--gdn-state-fp16", "--spec", "dflash2",
            "--draft-tokens", "5", "--no-prefix-reuse", "--max-concurrency", "1",
            "--devices", "0,1", "--host", HOST, "--port", str(PORT)]
    rec = {"task_id":"Q176-Bonsai-NInfer-hot-init", "registered_profile":"Q174 exact pinned model/runtime/flags",
           "started_utc":now(), "model_sha256":SHA_MODEL, "binary_sha256":SHA_BIN,
           "argv":argv, "gpu_topology":"2× RTX 3090; NInfer pipeline stage on each GPU",
           "cache_condition":"immediately follows Q174 context ladder; model pages were just read; no global page-cache flush; cache warmth is inferred from sequence, not directly instrumented",
           "cold_vs_hot_definition":"new clean server process, same model absent from VRAM at launch, page cache expected warm",
           "baseline_gpu":base_gpu, "mem_available_before_kib":mem_available_kib(),
           "inference_request_sent":False, "readiness":"pending"}
    proc = None
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("w", encoding="utf-8") as f:
            begin = time.monotonic()
            proc = subprocess.Popen(argv, stdout=f, stderr=subprocess.STDOUT, start_new_session=True,
                cwd="/tmp/q174-d/ninfer-src", env={**os.environ,"CUDA_VISIBLE_DEVICES":"0,1","TMPDIR":"/tmp/q174-d/tmp"})
            rec["pid"] = proc.pid
            deadline = time.monotonic() + 600
            health = None
            while time.monotonic() < deadline and proc.poll() is None:
                lock_check()
                try:
                    with urllib.request.urlopen(f"http://{HOST}:{PORT}/health", timeout=3) as r:
                        if r.status == 200:
                            health = json.loads(r.read())
                            if health.get("status") == "ok":
                                break
                except Exception:
                    pass
                time.sleep(1)
            if not health or proc.poll() is not None:
                raise RuntimeError("server did not reach healthy readiness within 600 seconds")
            rec["readiness"] = "healthy"
            rec["health_body"] = health
            rec["ready_utc"] = now()
            rec["launch_to_readiness_seconds"] = round(time.monotonic() - begin, 3)
            rec["gpu_at_readiness"] = gpu()
            rec["gpu_dual_gate"] = all(rec["gpu_at_readiness"].get(i,{}).get("used_mib",0)-base_gpu[i]["used_mib"]>1024 for i in (0,1))
            if not rec["gpu_dual_gate"]:
                raise RuntimeError("both 3090s did not gain >1GiB model/runtime allocation")
            rec["log"] = str(LOG)
            rec["status"] = "complete"
    except Exception as e:
        rec["status"] = "failed"
        rec["error"] = f"{type(e).__name__}: {e}"
        raise
    finally:
        if proc is not None:
            stop(proc)
            rec["server_exit_code"] = proc.returncode
            rec["port_free_after_cleanup"] = port_free()
            rec["gpu_after_cleanup"] = gpu()
            rec["mem_available_after_kib"] = mem_available_kib()
        rec["finished_utc"] = now()
        atomic_json(OUT, rec)


if __name__ == "__main__":
    main()
