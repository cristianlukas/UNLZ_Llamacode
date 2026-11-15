#!/usr/bin/env python3
"""Q209 Q173 ladder for Maya-XS with PNY-first, ASUS-second DS4_SPLIT=39,1."""
from __future__ import annotations

import argparse
import ctypes
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import signal
import socket
import statistics
import subprocess
import sys
import time
import urllib.request

REPO = pathlib.Path(__file__).resolve().parents[6]
PROFILE = pathlib.Path(__file__).resolve().parents[1]
RECEIPTS = PROFILE / "receipts"
LOCAL_RUNS = PROFILE / "runs"
LOCAL_LOGS = PROFILE / "logs"
PREREG = RECEIPTS / "preregistration.json"
TOKEN = "d9029f6b-c649-4291-b0be-f14d77dc737e"
TASK = "Q-20261103-VF-RESUME-202"
HOST = "127.0.0.1"
PORT = 18628
CTX = 262144
TG = 128
LADDER = {8192: 3, 32768: 1, 65536: 1, 131072: 1, 261888: 1}
HOST_FLOOR_BYTES = 16 * 1024**3
START_TIMEOUT = 1800
SAMPLE_SECONDS = 10

MAYA_ROOT = pathlib.Path("/media/cristian/HDD extra/LlamaCode-evals/Q189-project-maya-v1.1.37")
MAYA_RUN = MAYA_ROOT / "run-maya-ds4.sh"
MAYA_ENGINE = MAYA_ROOT / "build/maya-ds4"
CONFIG = PROFILE / "configs/maya-q173-262k-ds4split39.json"
MODEL_ROOT = pathlib.Path("/media/cristian/7CFE1E0FFE1DC1F6/LlamaCode-evals/Q189/Maya-XS")
MODEL_PREFIX = "DeepSeek-V4.1-Flash-1017-Maya-XS-IQ1_S-"
SHARD_HASHES = [
    "a0cb7966afd68bc35c46f78018d1fa1d2e4bcbe3c3baf39f60cd1733ed9ad7e5",
    "ba5afb43adfc667436ebcfbd82d25411fa2843ee7e1d877290611cd60f93cca1",
    "1482443bb4957c8d2f005ded365445f98558ff05c50674f9ee9a96ddabc122a4",
    "0d93315942c523d82f6dbc0a6e0e1751548e309f3963f96b82f92e8f9bc52e36",
    "39bbc8cde8b17604fed9a7ba7fc6bc9c5e72e34733657943ac049b4b9ca2d340",
]
TOKENIZER = pathlib.Path("/home/cristian/.cache/q173-tokenizers/deepseek-v41-flash-1017/tokenizer.json")
BENCHY = pathlib.Path("/home/cristian/.cache/q173-llama-benchy-0.4.0/bin/llama-benchy")
OUT = pathlib.Path("/media/cristian/Disco local/Modelos-eval/Q209-Maya-DS4SPLIT39-Q173")
BOOT_RECEIPT = REPO / "artifacts/evaluacion-modelos-llamacode/Q-20261029-VF-ITERATION-190/profiles/worker-boot-p2p-unlock/receipts/post-reboot-gates-p2p-smoke-20261031.json"
ASUS_UUID = "GPU-af6de4b3-6497-b7f8-796d-6d69cba422e6"
PNY_UUID = "GPU-5b9f385f-6a8e-b802-f69c-e62a71c91049"
SERVER_NAMES = {"llama-server", "dsx-server", "ninfer-serve", "vllm", "aphrodite-engine", "ollama", "maya-ds4", "strata", "koboldcpp", "lmstudio", "lm-studio"}
SERVER_MODULES = ("vllm.", "aphrodite", "exllama", "sglang.", "ninfer", "dsx.")


def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def write_json(path: pathlib.Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def sha(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run(argv: list[str], timeout: int = 30, check: bool = True) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(argv, text=True, capture_output=True, timeout=timeout)
    if check and p.returncode:
        raise RuntimeError(f"command failed ({p.returncode}): {argv!r}\n{p.stdout[-1200:]}\n{p.stderr[-1200:]}")
    return p


def check_lock() -> None:
    lock = json.loads((REPO / "WORK_QUEUE.lock").read_text(encoding="utf-8"))
    queue = (REPO / "WORK_QUEUE.md").read_text(encoding="utf-8")
    if lock.get("token") != TOKEN or lock.get("task") != TASK or TOKEN not in queue:
        raise RuntimeError("WORK_QUEUE.lock dejó de pertenecer al ciclo Q202; se aborta sin iniciar procesos")


def mem_state() -> dict:
    mem = pathlib.Path("/proc/meminfo").read_text().splitlines()
    avail = next(int(x.split()[1]) for x in mem if x.startswith("MemAvailable:")) * 1024
    pressure = {}
    for line in pathlib.Path("/proc/pressure/memory").read_text().splitlines():
        cols = line.split()
        pressure[cols[0]] = {k: float(v) for k, v in (field.split("=") for field in cols[1:])}
    vmstat = pathlib.Path("/proc/vmstat").read_text().splitlines()
    oom = int(next(x.split()[1] for x in vmstat if x.startswith("oom_kill ")))
    return {"mem_available_bytes": avail, "pressure": pressure, "oom_kill": oom}


def gpu_state() -> dict:
    q = run(["nvidia-smi", "--query-gpu=index,uuid,name,pci.bus_id,memory.used,memory.total,utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"])
    gpus = []
    for line in q.stdout.splitlines():
        v = [x.strip() for x in line.split(",")]
        if len(v) == 8:
            gpus.append({"index": int(v[0]), "uuid": v[1], "name": v[2], "pci": v[3], "memory_used_mib": int(v[4]), "memory_total_mib": int(v[5]), "utilization_percent": int(v[6]), "temperature_c": int(v[7])})
    apps = run(["nvidia-smi", "--query-compute-apps=pid,gpu_uuid,used_gpu_memory", "--format=csv,noheader,nounits"], check=False)
    compute = []
    for line in apps.stdout.splitlines():
        v = [x.strip() for x in line.split(",")]
        if len(v) == 3 and v[0].isdigit() and v[2].isdigit():
            compute.append({"pid": int(v[0]), "uuid": v[1], "used_mib": int(v[2])})
    return {"timestamp_utc": utc(), "gpus": gpus, "compute_apps": compute}


def proc_info(pid: int) -> dict | None:
    try:
        p = pathlib.Path(f"/proc/{pid}")
        status = (p / "status").read_text()
        ppid = int(next(x.split()[1] for x in status.splitlines() if x.startswith("PPid:")))
        comm = (p / "comm").read_text().strip()
        argv = (p / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
        exe = pathlib.Path(os.readlink(p / "exe")).name.lower()
        return {"pid": pid, "ppid": ppid, "comm": comm, "argv": argv, "exe": exe}
    except (OSError, ValueError, StopIteration):
        return None


def inference_processes(ignore: set[int] | None = None) -> list[dict]:
    ignore = ignore or set()
    found = []
    for p in pathlib.Path("/proc").iterdir():
        if not p.name.isdigit() or int(p.name) in ignore:
            continue
        x = proc_info(int(p.name))
        if not x:
            continue
        server = x["exe"] in SERVER_NAMES or x["comm"].lower() in SERVER_NAMES
        if x["exe"].startswith(("python", "pypy")):
            low = x["argv"].lower()
            server |= "maya.py" in low or any(m in low for m in SERVER_MODULES)
        if server:
            found.append(x)
    return found


def descendants(unit: str) -> set[int]:
    p = run(["systemctl", "--user", "show", unit, "-p", "MainPID", "--value"], check=False)
    try:
        main = int(p.stdout.strip())
    except ValueError:
        main = 0
    if not main:
        return set()
    allp = []
    for ent in pathlib.Path("/proc").iterdir():
        if ent.name.isdigit():
            x = proc_info(int(ent.name))
            if x:
                allp.append(x)
    kids: dict[int, list[int]] = {}
    for x in allp:
        kids.setdefault(x["ppid"], []).append(x["pid"])
    result, todo = {main}, [main]
    while todo:
        for child in kids.get(todo.pop(), []):
            if child not in result:
                result.add(child)
                todo.append(child)
    return result


def port_free() -> bool:
    with socket.socket() as s:
        return s.connect_ex((HOST, PORT)) != 0


def helper_gate() -> dict:
    systemd = run(["systemctl", "show", "3090-helper-verify-boot.service", "-p", "Result", "-p", "ExecMainStatus"])
    vram = run(["systemctl", "is-active", f"vram-quarantine@{ASUS_UUID}.service"])
    journal = run(["journalctl", "-u", "3090-helper-verify-boot.service", "-b", "-o", "cat", "--no-pager", "-n", "40"])
    modules = pathlib.Path("/proc/modules").read_text(encoding="utf-8")
    cmdline = pathlib.Path("/proc/cmdline").read_text(encoding="utf-8")
    p2pr = run(["nvidia-smi", "topo", "-p2p", "r"])
    p2pw = run(["nvidia-smi", "topo", "-p2p", "w"])
    boot = json.loads(BOOT_RECEIPT.read_text(encoding="utf-8"))
    checks = {
        "helper_verify_success": "Result=success" in systemd.stdout and "ExecMainStatus=0" in systemd.stdout,
        "helper_current_boot_pass": "PASS: reserva ASUS, P2P bidireccional y gpu-unlock en ambas RTX 3090." in journal.stdout,
        "asus_quarantine_full": boot.get("asusQuarantine", {}).get("held") == 1636 and boot.get("asusQuarantine", {}).get("total") == 1636 and boot.get("asusQuarantine", {}).get("pending") == 0,
        "asus_quarantine_service_active": vram.stdout.strip() == "active",
        "gpu_unlock_loaded": any(x.split() and x.split()[0] == "gpu_unlock" for x in modules.splitlines()),
        "gpu_unlock_both_cards": "gpu_unlock.targets=0000:01:00.0,0000:03:00.0" in cmdline,
        "p2p_read_bidirectional": p2pr.stdout.count("OK") >= 2,
        "p2p_write_bidirectional": p2pw.stdout.count("OK") >= 2,
    }
    if not all(checks.values()):
        raise RuntimeError("3090 HELPER/P2P/unlock preflight failed: " + json.dumps(checks, ensure_ascii=False))
    return {"status": "PASS", "checks": checks, "systemd": systemd.stdout.strip(), "vram": vram.stdout.strip(), "p2p_read": p2pr.stdout, "p2p_write": p2pw.stdout, "boot_receipt": boot, "gpus": gpu_state()}


def file_snapshot(path: pathlib.Path) -> dict:
    s = path.stat()
    return {"path": str(path), "resolved_path": str(path.resolve()), "bytes": s.st_size, "mtime_ns": s.st_mtime_ns, "inode": s.st_ino, "device": s.st_dev}


def prereg() -> dict:
    p = json.loads(PREREG.read_text(encoding="utf-8"))
    if p.get("lock_token") != TOKEN or p.get("task") != "Q209-MAYA-DS4SPLIT39-Q173":
        raise RuntimeError("Q209 preregistration does not match")
    if p.get("runner_sha256") != sha(pathlib.Path(__file__)):
        raise RuntimeError("Q209 runner SHA differs from preregistration")
    return p


def verify_assets(full: bool) -> dict:
    check_lock()
    p = prereg()
    shards = sorted(MODEL_ROOT.glob(MODEL_PREFIX + "*.gguf"))
    if len(shards) != 5:
        raise RuntimeError(f"expected 5 model shards; found {len(shards)}")
    files = []
    progress_path = RECEIPTS / "shard-hash-progress.json"
    write_json(progress_path, {"status": "IN_PROGRESS", "started_utc": utc(), "expected_shards": len(shards), "verified_shards": []})
    for i, path in enumerate(shards):
        item = file_snapshot(path)
        if full:
            observed = sha(path)
            if observed != SHARD_HASHES[i]:
                raise RuntimeError(f"shard {i+1} SHA mismatch: {observed}")
            item["sha256"] = observed
        else:
            item["sha256"] = SHARD_HASHES[i]
        files.append(item)
        write_json(progress_path, {"status": "IN_PROGRESS", "expected_shards": len(shards), "verified_shards": files, "updated_utc": utc()})
    fixed = [
        (MAYA_ENGINE, "b4d00bcb0dc1b6680158749941601e79f669af6b1ae5c2d28c5feaa0cc72df17"),
        (MAYA_RUN, "95087759f61e581888fadbb3e9f84128197a7d908628658ccb65e3298e82748b"),
        (TOKENIZER, "c90dfa01249db1be4245780a052ede752e1361c612ac6d08e2bdada7d599476b"),
        (BENCHY, "e8a892fe937d5ae1b6a43c31e8cb286ce4774f70396f62ab71008c9ddb0a01a1"),
        (CONFIG, p["runtime"]["config_sha256"]),
    ]
    support = []
    for path, expected in fixed:
        if not path.is_file():
            raise RuntimeError(f"missing pinned artifact: {path}")
        observed = sha(path)
        if observed != expected:
            raise RuntimeError(f"SHA mismatch for {path}: {observed} != {expected}")
        support.append({**file_snapshot(path), "sha256": observed})
    complete = {"status": "PASS", "full_shard_hashes_verified": full, "completed_utc": utc(), "model_shards": files, "supporting_files": support, "total_model_bytes": sum(x["bytes"] for x in files)}
    write_json(RECEIPTS / "asset-hash-verification.json", complete)
    write_json(progress_path, {**complete, "expected_shards": len(shards), "verified_shards": files})
    return complete


def live_gates(allow_own_unit: str | None = None) -> dict:
    check_lock()
    gates = helper_gate()
    if not port_free() and allow_own_unit is None:
        raise RuntimeError(f"port {PORT} occupied")
    own = descendants(allow_own_unit) if allow_own_unit else set()
    foreign = inference_processes(own)
    if foreign:
        raise RuntimeError("foreign inference server detected; untouched: " + json.dumps(foreign, ensure_ascii=False))
    mem = mem_state()
    if mem["mem_available_bytes"] < HOST_FLOOR_BYTES:
        raise RuntimeError("MemAvailable <16 GiB before a new context; no server launched")
    return {"timestamp_utc": utc(), "memory": mem, "gpus": gpu_state(), "helper_gate": gates, "foreign_inference_servers": foreign, "own_unit_pids": sorted(own), "port_free": port_free()}


def preflight() -> dict:
    assets = verify_assets(full=True)
    if not OUT.parent.is_dir():
        raise RuntimeError(f"output volume unavailable: {OUT.parent}")
    free = os.statvfs(OUT.parent).f_bavail * os.statvfs(OUT.parent).f_frsize
    if free < 1_000_000_000:
        raise RuntimeError(f"less than 1 GB free for receipts/results: {free}")
    gates = live_gates()
    gpus = {x["uuid"]: x for x in gates["gpus"]["gpus"]}
    if ASUS_UUID not in gpus or PNY_UUID not in gpus or "RTX 3090" not in gpus[ASUS_UUID]["name"] or "RTX 3090" not in gpus[PNY_UUID]["name"]:
        raise RuntimeError("physical ASUS/PNY GPU UUID mapping does not match preregistration")
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if config.get("gpu") != [1, 0] or config.get("env", {}).get("DS4_SPLIT") != "39,1":
        raise RuntimeError("model config is not PNY-first gpu=[1,0], DS4_SPLIT=39,1")
    receipt = {"schema": "llamacode.q209-maya-q173-preflight.v1", "status": "PASS", "timestamp_utc": utc(), "lock_token": TOKEN, "task": "Q209-MAYA-DS4SPLIT39-Q173", "runner_sha256": sha(pathlib.Path(__file__)), "assets": assets, "live_gates": gates, "profile_config": config, "output_free_bytes": free, "inference_servers": [], "profile_mutated": False}
    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "receipts/preflight.json", receipt)
    write_json(RECEIPTS / "preflight.json", receipt)
    return receipt


def check_cached_assets() -> dict:
    p = prereg()
    receipt = json.loads((RECEIPTS / "preflight.json").read_text(encoding="utf-8"))
    if receipt.get("status") != "PASS" or receipt.get("lock_token") != TOKEN:
        raise RuntimeError("full-hash preflight not PASS")
    if receipt.get("runner_sha256") != sha(pathlib.Path(__file__)):
        raise RuntimeError("runner changed after preflight")
    current = sorted(MODEL_ROOT.glob(MODEL_PREFIX + "*.gguf"))
    old = receipt["assets"]["model_shards"]
    if len(current) != len(old):
        raise RuntimeError("shard inventory changed")
    for path, snap in zip(current, old):
        if file_snapshot(path) != {k: snap[k] for k in ("path", "resolved_path", "bytes", "mtime_ns", "inode", "device")}:
            raise RuntimeError(f"shard identity changed after hashing: {path}")
    return p


def systemd_unit(pp: int) -> str:
    attempt = os.environ.get("Q209_ATTEMPT", "")
    if not re.fullmatch(r"a[0-9]{2}", attempt):
        raise RuntimeError("Q173 must run under a detached Q209 worker with Q209_ATTEMPT=aNN")
    return f"q209-maya-q173-pp{pp}-{attempt}"


def check_detached_worker() -> dict:
    unit = os.environ.get("Q209_WORKER_UNIT", "")
    attempt = os.environ.get("Q209_ATTEMPT", "")
    if not re.fullmatch(r"q209-maya-q173-pp[0-9]+-worker-a[0-9]{2}", unit):
        raise RuntimeError("Q173 controller is not running in the detached Q209 worker")
    if not re.fullmatch(r"a[0-9]{2}", attempt):
        raise RuntimeError("invalid Q209 attempt id")
    state = run(["systemctl", "--user", "show", unit, "-p", "ActiveState", "--value"], check=False).stdout.strip()
    description = run(["systemctl", "--user", "show", unit, "-p", "Description", "--value"], check=False).stdout.strip()
    if state not in ("activating", "active") or not description.startswith(f"Q209-WORKER|{TOKEN}|{unit}"):
        raise RuntimeError(f"detached worker identity/state check failed: {unit}: {state!r} {description!r}")
    return {"unit": unit, "attempt": attempt, "active_state": state, "description": description}


def api_models() -> dict | None:
    try:
        with urllib.request.urlopen(f"http://{HOST}:{PORT}/v1/models", timeout=5) as r:
            return json.loads(r.read()) if r.status == 200 else None
    except Exception:
        return None


def stop_unit(unit: str) -> dict:
    started = utc()
    result = run(["systemctl", "--user", "stop", unit], timeout=120, check=False)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and not port_free():
        time.sleep(0.5)
    remaining = inference_processes()
    receipt = {"unit": unit, "stop_started_utc": started, "finished_utc": utc(), "systemctl_rc": result.returncode, "stderr": result.stderr, "port_free": port_free(), "remaining_inference_servers": remaining, "memory": mem_state(), "gpus": gpu_state()}
    write_json(RECEIPTS / f"postflight-{unit}.json", receipt)
    write_json(OUT / f"receipts/postflight-{unit}.json", receipt)
    if result.returncode != 0 or not receipt["port_free"] or remaining:
        raise RuntimeError("owned server postflight failed: " + json.dumps(receipt, ensure_ascii=False))
    return receipt


def start_server(pp: int) -> tuple[str, dict]:
    check_cached_assets()
    before = live_gates()
    unit = systemd_unit(pp)
    if not port_free():
        raise RuntimeError("port occupied before startup")
    engine_description = f"Q209-MAYA-Q173|{TOKEN}|{unit}"
    cmd = ["systemd-run", "--user", f"--unit={unit}", f"--description={engine_description}", "--property=RuntimeMaxSec=3600s", "--property=MemoryMax=96G", "--property=MemorySwapMax=0", "--property=OOMPolicy=kill", "--property=KillMode=control-group", f"--property=WorkingDirectory={MAYA_ROOT}", "--setenv=CUDA_DEVICE_ORDER=PCI_BUS_ID", "--setenv=CUDA_VISIBLE_DEVICES=1,0", "--setenv=DS4_SPLIT=39,1", str(MAYA_RUN), "--config", str(CONFIG), "--port", str(PORT), "--plain"]
    launch = run(cmd, timeout=60, check=False)
    if launch.returncode:
        raise RuntimeError(f"systemd-run failed: {launch.stderr}")
    t0 = time.monotonic()
    samples = []
    low_count = 0
    while time.monotonic() - t0 < START_TIMEOUT:
        check_lock()
        ids = descendants(unit)
        foreign = inference_processes(ids)
        if foreign:
            stop_unit(unit)
            raise RuntimeError("foreign inference appeared during own startup; own service stopped: " + json.dumps(foreign, ensure_ascii=False))
        m = mem_state()
        low_count = low_count + 1 if m["mem_available_bytes"] < HOST_FLOOR_BYTES else 0
        if low_count >= 2:
            stop_unit(unit)
            raise RuntimeError("MemAvailable below 16 GiB twice; own service stopped")
        state = gpu_state()
        own_by_gpu = {u: [x["pid"] for x in state["compute_apps"] if x["uuid"] == u and x["pid"] in ids] for u in (PNY_UUID, ASUS_UUID)}
        models = api_models()
        active = run(["systemctl", "--user", "is-active", unit], check=False).stdout.strip()
        samples.append({"at_utc": utc(), "elapsed_seconds": round(time.monotonic()-t0, 2), "unit": active, "pids": sorted(ids), "own_compute_pids_by_physical_uuid": own_by_gpu, "memory": m, "gpus": state["gpus"]})
        ids_data = [x.get("id") for x in (models or {}).get("data", []) if isinstance(x, dict)]
        if "deepseek-v4.1-flash" in ids_data and all(own_by_gpu[u] for u in (PNY_UUID, ASUS_UUID)):
            ready = {"status": "PASS", "unit": unit, "port": PORT, "ready_seconds": round(time.monotonic()-t0, 3), "api_models": models, "compute_pid_by_uuid": own_by_gpu, "physical_order": [PNY_UUID, ASUS_UUID], "visible_devices": "1,0", "DS4_SPLIT": "39,1", "samples": samples, "preflight": before, "launch": cmd, "launch_stdout": launch.stdout, "launch_stderr": launch.stderr}
            write_json(RECEIPTS / f"startup-pp{pp}.json", ready)
            write_json(OUT / f"receipts/startup-pp{pp}.json", ready)
            return unit, ready
        if active in ("failed", "inactive"):
            logs = run(["journalctl", "--user", "-u", unit, "-n", "100", "--no-pager"], check=False).stdout
            write_json(RECEIPTS / f"startup-failure-pp{pp}.json", {"status": "FAIL", "unit": unit, "journal": logs, "samples": samples})
            raise RuntimeError(f"Maya unit stopped before API readiness; journal: {logs[-2000:]}")
        time.sleep(SAMPLE_SECONDS)
    stop_unit(unit)
    raise TimeoutError(f"Maya failed to become API-ready and allocate both GPUs within {START_TIMEOUT}s")


def effective_prefill(events_path: pathlib.Path, expected: int) -> dict:
    starts, first, ends = {}, {}, {}
    for line in events_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        rid = e.get("request_id")
        if rid is None:
            continue
        rid = int(rid)
        if e.get("type") == "request_start":
            starts[rid] = float(e["ts"])
        elif e.get("type") == "request_first_token":
            first[rid] = float(e["ttft_s"])
        elif e.get("type") == "request_end":
            ends[rid] = e
    if len(ends) != expected:
        raise RuntimeError(f"expected {expected} ended requests; got {len(ends)}")
    samples = []
    for rid, e in sorted(ends.items()):
        if rid not in starts or rid not in first or e.get("error"):
            raise RuntimeError(f"invalid prefill event for request {rid}: {e}")
        t = float(first[rid])
        n = int(e.get("prompt_tokens") or 0)
        if t <= 0 or n <= 0:
            raise RuntimeError(f"invalid prompt size/first-content TTFT for request {rid}")
        samples.append({"request_id": rid, "prompt_tokens": n, "first_content_elapsed_s": t, "effective_prefill_tps": n/t})
    vals = [x["effective_prefill_tps"] for x in samples]
    return {"method": "actual prompt_tokens / request start-to-first-content-token elapsed; includes client/network overhead", "n": len(vals), "samples": samples, "mean_tps": statistics.fmean(vals), "sample_stdev_tps": statistics.stdev(vals) if len(vals) > 1 else 0.0}


def monitor(unit: str) -> dict:
    check_lock()
    ids = descendants(unit)
    foreign = inference_processes(ids)
    if foreign:
        raise RuntimeError("foreign inference server appeared: " + json.dumps(foreign, ensure_ascii=False))
    state = gpu_state()
    by_gpu = {u: [x["pid"] for x in state["compute_apps"] if x["uuid"] == u and x["pid"] in ids] for u in (PNY_UUID, ASUS_UUID)}
    if not all(by_gpu[u] for u in (PNY_UUID, ASUS_UUID)):
        raise RuntimeError("Q209 server lost same-service compute allocation on ASUS or PNY: " + json.dumps(by_gpu))
    mem = mem_state()
    if mem["mem_available_bytes"] < HOST_FLOOR_BYTES:
        raise RuntimeError("MemAvailable <16 GiB")
    return {"timestamp_utc": utc(), "unit_pids": sorted(ids), "compute_by_physical_uuid": by_gpu, "memory": mem, "gpus": state["gpus"], "helper_gate": helper_gate()}


def run_context(pp: int, runs: int) -> dict:
    if pp not in LADDER or LADDER[pp] != runs:
        raise ValueError(f"not in preregistered ladder: pp={pp}, runs={runs}")
    worker = check_detached_worker()
    check_cached_assets()
    result_path = OUT / f"runs/q173-context-{pp}.json"
    events_path = OUT / f"runs/q173-context-{pp}-events.jsonl"
    log_path = OUT / f"logs/q173-context-{pp}.log"
    if any(x.exists() for x in (result_path, events_path, log_path)):
        raise FileExistsError(f"preserving existing attempt; output already exists for pp={pp}")
    OUT.mkdir(parents=True, exist_ok=True)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    unit = ""
    client = None
    samples = []
    start = utc()
    t0 = time.monotonic()
    try:
        unit, ready = start_server(pp)
        argv = [str(BENCHY), "--base-url", f"http://{HOST}:{PORT}/v1", "--model", "deepseek-v4.1-flash", "--tokenizer", str(TOKENIZER), "--pp", str(pp), "--tg", str(TG), "--exact-tg", "--depth", "0", "--concurrency", "1", "--runs", str(runs), "--latency-mode", "generation", "--no-cache", "--skip-coherence", "--no-adapt-prompt", "--extra-body", "temperature=0.6,top_p=0.95,top_k=20,min_p=0.0,repetition_penalty=1.0,presence_penalty=0.0,seed=42", "--format", "json", "--exit-on-first-fail", "--save-result", str(result_path), "--emit-progress", str(events_path)]
        write_json(OUT / f"runs/q173-context-{pp}.argv.json", {"argv": argv, "timestamp_utc": utc(), "lock_token": TOKEN, "runner_sha256": sha(pathlib.Path(__file__))})
        with log_path.open("w", encoding="utf-8") as log:
            env = {**os.environ, "CUDA_VISIBLE_DEVICES": ""}
            client = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True, close_fds=True)
            low_count = 0
            while client.poll() is None:
                sample = monitor(unit)
                samples.append(sample)
                low_count = low_count + 1 if sample["memory"]["mem_available_bytes"] < HOST_FLOOR_BYTES else 0
                if low_count >= 2:
                    raise RuntimeError("MemAvailable below 16 GiB twice")
                time.sleep(SAMPLE_SECONDS)
        if client.returncode != 0:
            raise RuntimeError(f"llama-benchy exit {client.returncode}; see {log_path}")
        data = json.loads(result_path.read_text(encoding="utf-8"))
        bench = data["benchmarks"][0]
        if int(bench.get("prompt_size", -1)) != pp or int(bench.get("response_size", -1)) != TG:
            raise RuntimeError(f"response sizes differ from preregistration: {bench}")
        prefill = effective_prefill(events_path, runs)
        result = {"schema": "llamacode.q209-maya-q173-context.v1", "status": "PASS", "task": "Q209-MAYA-DS4SPLIT39-Q173", "timestamp_utc": utc(), "lock_token": TOKEN, "detached_worker": worker, "profile": "Maya-XS IQ1_S · Project Maya v1.1.37 · PNY-first · DS4_SPLIT=39,1", "physical_gpus": [PNY_UUID, ASUS_UUID], "context_tokens": pp, "server_context": CTX, "generation_tokens": TG, "runs": runs, "prefill_effective_e2e": prefill, "benchy_prefill_tps_diagnostic_only": bench.get("pp_throughput"), "decode_tps": bench.get("tg_throughput"), "ttft_ms": bench.get("e2e_ttft"), "reported_prompt_tokens": bench.get("prompt_size"), "reported_output_tokens": bench.get("response_size"), "server_ready_seconds": ready["ready_seconds"], "server_ready_is_cold_or_hot": False, "quality_score": "N/D · Q173 only", "gpu_samples": samples, "argv": argv, "raw_result": str(result_path), "raw_events": str(events_path), "client_log": str(log_path), "finished_utc": utc()}
        write_json(RECEIPTS / f"q173-context-{pp}.json", result)
        write_json(LOCAL_RUNS / f"q173-context-{pp}.json", result)
        return result
    except Exception as e:
        failure = {"schema": "llamacode.q209-maya-q173-context.v1", "status": "FAIL_OR_INCOMPLETE", "task": "Q209-MAYA-DS4SPLIT39-Q173", "timestamp_utc": utc(), "lock_token": TOKEN, "context_tokens": pp, "runs": runs, "error": f"{type(e).__name__}: {e}", "raw_result_exists": result_path.exists(), "raw_events_exists": events_path.exists(), "client_log": str(log_path), "samples": samples}
        write_json(RECEIPTS / f"q173-context-{pp}-failure.json", failure)
        write_json(LOCAL_RUNS / f"q173-context-{pp}-failure.json", failure)
        raise
    finally:
        if client is not None and client.poll() is None:
            try:
                os.killpg(client.pid, signal.SIGTERM)
                client.wait(timeout=15)
            except Exception:
                try:
                    os.killpg(client.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        if unit:
            stop_unit(unit)


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("preflight")
    r = sub.add_parser("run")
    r.add_argument("--pp", required=True, type=int)
    r.add_argument("--runs", required=True, type=int)
    args = ap.parse_args()
    try:
        check_lock()
        if args.command == "preflight":
            print(json.dumps(preflight(), ensure_ascii=False, indent=2))
        else:
            check_detached_worker()
            print(json.dumps(run_context(args.pp, args.runs), ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
