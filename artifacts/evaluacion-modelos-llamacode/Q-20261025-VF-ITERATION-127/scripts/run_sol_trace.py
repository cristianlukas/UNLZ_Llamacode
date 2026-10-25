#!/usr/bin/env python3
"""One monitored SOL prompt-copy smoke; owned Q127 container only."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen

TASK_ID = "Q-20261025-VF-ITERATION-127"
LOCK_TOKEN = "7a80fae3-371f-4758-9aea-62e211b6d709"
ROOT = Path(__file__).resolve().parents[4]
TASK_ROOT = Path(__file__).resolve().parents[1]
RUN = TASK_ROOT / "attempt01"
RECEIPTS = RUN / "receipts"
LOGS = RUN / "logs"
RUNS = RUN / "runs"
sys_path = str(TASK_ROOT / "guard_sources")
import sys
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)
from q117_pressure_guard_attempt05 import evaluate, initial_counts  # noqa: E402

COMPOSE = Path("/home/cristian/.cache/llamacode/club-3090-src/models/qwen3.8-27b/vllm/compose/dual/autoround-int4/mtp.yml")
COMPOSE_OVERRIDE = COMPOSE.parent / "vram-quarantine.override.yml"
ISOLATION = TASK_ROOT / "work/sol-isolated.compose.yml"
MODEL_DIR = Path("/media/cristian/Disco local/Models/llamacpp/club-3090/qwen3.8-27b-autoround-int4")
COMPOSE_SHA = "2df4e44e1e1b268da80690a0812ac1b60768d60b643096ce8473110f88b7b76a"
OVERRIDE_SHA = "e547197d1b283e5c8b684d35e1b348bb91bbba3a327183a14b0d4a6083c36a50"
SOL_FILES = [
    ("model-00001-of-00007.safetensors", "83c0adb0f1141142a25c5f7937a09272fef2baee7d6b07afe60a076feffe3b66"),
    ("model-00002-of-00007.safetensors", "6c86c3917cd228d5699cb1435d9216e2baf281582ba4282a98638163605be7ec"),
    ("model-00003-of-00007.safetensors", "bfb9613b3f6ba3d0c5b3efa74f92cc14ec5c9266b341a79bf6b45247a5857770"),
    ("model-00004-of-00007.safetensors", "8e9fbd476aa3055c3c0a886298f9beb93c5275c748c533835746f6648f6dae55"),
    ("model-00005-of-00007.safetensors", "f0cd639621eb26410d96b8c073344ae008f646572a9c4713326ff43d406cf276"),
    ("model-00006-of-00007.safetensors", "55a14ee79d3e5a65a8731d89426f4df477e8bdc7daa7976d41254d8afb9432f0"),
    ("model-00007-of-00007.safetensors", "6866cf8adcccc4cc6a00e74bc025f1a774fb52103b70f2674d0288272951a733"),
]
PROJECT = "q127-sol-memory"
CONTAINER = "q127-sol-memory"
PORT = 18117
BASE_URL = f"http://127.0.0.1:{PORT}/v1"
MODEL_ID = "qwen3.8-27b"
GPU_QUERY = ["nvidia-smi", "--query-gpu=index,temperature.gpu,memory.used,memory.total,utilization.gpu", "--format=csv,noheader,nounits"]
SERVER_WORDS = ("llama-server", "vllm", "ollama serve", "sglang", "aphrodite", "ninfer")
GIB = 1024 ** 3
SWAP_ABORT_BYTES = 4 * 1024 * 1024


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def append_jsonl(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(data, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def check_lock() -> None:
    lock = json.loads((ROOT / "WORK_QUEUE.lock").read_text(encoding="utf-8"))
    if lock.get("task_id") != TASK_ID or lock.get("token") != LOCK_TOKEN:
        raise RuntimeError("Q127 no longer owns WORK_QUEUE.lock")


def meminfo() -> dict[str, int]:
    values = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, _, rest = line.partition(":")
        if key in {"MemTotal", "MemAvailable", "SwapFree"}:
            values[key] = int(rest.strip().split()[0]) * 1024
    if not {"MemTotal", "MemAvailable", "SwapFree"}.issubset(values):
        raise RuntimeError("required /proc/meminfo fields missing")
    return values


def psi_memory() -> dict[str, float]:
    result = {}
    for line in Path("/proc/pressure/memory").read_text().splitlines():
        fields = line.split()
        if not fields or fields[0] not in {"some", "full"}:
            continue
        metrics = dict(item.split("=", 1) for item in fields[1:] if "=" in item)
        result[fields[0]] = float(metrics["avg10"])
    if set(result) != {"some", "full"}:
        raise RuntimeError("global memory PSI some/full missing")
    return result


def oom_kill_count() -> int:
    for line in Path("/proc/vmstat").read_text().splitlines():
        if line.startswith("oom_kill "):
            return int(line.split()[1])
    raise RuntimeError("/proc/vmstat oom_kill missing")


def gpu_rows() -> list[dict]:
    proc = subprocess.run(GPU_QUERY, capture_output=True, text=True, timeout=10, check=True)
    rows = []
    for line in proc.stdout.splitlines():
        fields = [part.strip() for part in line.split(",")]
        if len(fields) != 5:
            raise RuntimeError("unexpected nvidia-smi telemetry row")
        rows.append({"index": int(fields[0]), "temperatureC": int(fields[1]),
                     "memoryUsedMiB": int(fields[2]), "memoryTotalMiB": int(fields[3]),
                     "utilizationPct": int(fields[4])})
    return rows


def docker_rows() -> list[dict]:
    proc = subprocess.run(["docker", "ps", "--format", "{{json .}}"], capture_output=True,
                          text=True, timeout=10, check=True)
    return [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]


def q127_project_rows() -> list[dict]:
    proc = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"label=com.docker.compose.project={PROJECT}",
         "--format", "{{json .}}"],
        capture_output=True, text=True, timeout=10, check=True)
    return [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]


def server_processes(owned_pids: set[int] | None = None) -> list[dict]:
    proc = subprocess.run(["ps", "-eo", "pid=,comm=,args="], capture_output=True,
                          text=True, timeout=10, check=True)
    found = []
    for line in proc.stdout.splitlines():
        fields = line.strip().split(None, 2)
        if len(fields) < 2:
            continue
        pid, comm = int(fields[0]), fields[1]
        args = fields[2] if len(fields) > 2 else ""
        low = f"{comm} {args}".lower()
        if pid == os.getpid() or (owned_pids and pid in owned_pids) or "q127-sol-memory" in low:
            continue
        if any(word in low for word in SERVER_WORDS):
            found.append({"pid": pid, "comm": comm})
    return found


def port_free() -> None:
    proc = subprocess.run(["ss", "-H", "-ltn", f"sport = :{PORT}"],
                          capture_output=True, text=True, timeout=10)
    if proc.returncode:
        raise RuntimeError("cannot verify whether the Q127 TCP port has a listener")
    if proc.stdout.strip():
        raise OSError(f"TCP port {PORT} still has a listening socket")


def env_for_compose() -> dict[str, str]:
    env = os.environ.copy()
    env.update({
        "BIND_HOST": "127.0.0.1", "PORT": str(PORT), "ESTATE_CONTAINER": CONTAINER,
        "MODEL_DIR": str(MODEL_DIR.parent), "TP": "2", "MAX_MODEL_LEN": "262144",
        "GPU_MEMORY_UTILIZATION": "0.90", "MAX_NUM_SEQS": "8", "MAX_NUM_BATCHED_TOKENS": "8192",
        "SPEC_N": "4", "W4A8": "1", "ENABLE_THINKING": "true", "TEMP": "0.6",
        "TOP_P": "0.95", "TOP_K": "20", "MIN_P": "0.0", "PRESENCE_PENALTY": "0.0",
    })
    return env


def compose_cmd(*args: str) -> list[str]:
    return ["docker", "compose", "--project-directory", str(COMPOSE.parent), "-p", PROJECT,
            "-f", str(COMPOSE), "-f", str(COMPOSE_OVERRIDE), "-f", str(ISOLATION), *args]


def preflight() -> dict:
    check_lock()
    for path, expected in ((COMPOSE, COMPOSE_SHA), (COMPOSE_OVERRIDE, OVERRIDE_SHA)):
        if not path.is_file() or sha(path) != expected:
            raise RuntimeError(f"pinned SOL compose artifact mismatch: {path}")
    if not ISOLATION.is_file():
        raise RuntimeError("Q127 isolated compose overlay missing")
    if not Path("/proc/pressure/memory").is_file():
        raise RuntimeError("host memory PSI unavailable")
    model_hashes = {}
    for name, expected in SOL_FILES:
        path = MODEL_DIR / name
        if not path.is_file():
            raise RuntimeError(f"SOL shard missing: {name}")
        actual = sha(path)
        if actual != expected:
            raise RuntimeError(f"SOL shard hash mismatch: {name}")
        model_hashes[name] = actual
    mem = meminfo()
    psi = psi_memory()
    gpus = gpu_rows()
    servers = server_processes()
    existing_project_containers = q127_project_rows()
    containers = []
    for item in docker_rows():
        name = item.get("Names", "")
        signature = " ".join((name, item.get("Image", ""), item.get("Ports", ""))).lower()
        if any(word in signature for word in SERVER_WORDS):
            containers.append({"name": name, "image": item.get("Image", "")})
    disk_free = shutil.disk_usage("/var/lib/docker").free
    port_free()
    if servers or containers:
        raise RuntimeError("inference server already active; Q127 did not start")
    if existing_project_containers:
        raise RuntimeError("Q127 compose project already has a container; refusing to reuse it")
    if len(gpus) != 2 or [row["index"] for row in gpus] != [0, 1]:
        raise RuntimeError("SOL TP=2 requires both physical RTX 3090 devices visible")
    if mem["MemAvailable"] < 80 * GIB or mem["SwapFree"] < GIB:
        raise RuntimeError("host memory/swap preflight below preregistered floor")
    if max(row["temperatureC"] for row in gpus) >= 80:
        raise RuntimeError("GPU temperature preflight >=80C")
    if disk_free < 8 * GIB:
        raise RuntimeError("Docker root filesystem has <8 GiB free")
    compose_check = subprocess.run(compose_cmd("config", "-q"), env=env_for_compose(),
                                   capture_output=True, text=True, timeout=30)
    if compose_check.returncode:
        raise RuntimeError("isolated compose config validation failed")
    state = {"atUtc": utc(), "host": mem, "psi": psi, "gpus": gpus,
             "activeInferenceProcesses": servers, "activeInferenceContainers": containers,
             "dockerFreeBytes": disk_free, "solModelShardHashes": model_hashes,
             "composeBaseSha256": COMPOSE_SHA, "composeOverrideSha256": OVERRIDE_SHA,
             "isolationOverlaySha256": sha(ISOLATION), "gatePassed": True}
    write_json(RECEIPTS / "preflight.json", state)
    return state


def container_cgroup() -> tuple[int | None, Path | None]:
    proc = subprocess.run(["docker", "inspect", "--format", "{{.State.Pid}}", CONTAINER],
                          capture_output=True, text=True, timeout=10)
    if proc.returncode or not proc.stdout.strip() or proc.stdout.strip() == "0":
        return None, None
    pid = int(proc.stdout.strip())
    for line in Path(f"/proc/{pid}/cgroup").read_text().splitlines():
        if line.startswith("0::"):
            return pid, Path("/sys/fs/cgroup") / line.split("::", 1)[1].lstrip("/")
    return pid, None


def read_kv_file(path: Path) -> dict[str, int]:
    result = {}
    if not path.is_file():
        return result
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[1].isdigit():
            result[fields[0]] = int(fields[1])
    return result


def cgroup_snapshot() -> dict:
    pid, cg = container_cgroup()
    if not cg:
        return {"containerPid": pid, "available": False}
    required = (cg / "memory.current", cg / "memory.peak", cg / "memory.swap.current", cg / "memory.events")
    if not all(path.is_file() for path in required):
        return {"containerPid": pid, "available": False,
                "reason": "required cgroup memory telemetry file missing"}
    current = int((cg / "memory.current").read_text())
    peak = int((cg / "memory.peak").read_text())
    swap = int((cg / "memory.swap.current").read_text())
    events = read_kv_file(cg / "memory.events")
    if not {"oom", "oom_kill"}.issubset(events):
        return {"containerPid": pid, "available": False,
                "reason": "required cgroup OOM counters missing"}
    rss_bytes = 0
    pids = set()
    for path in cg.rglob("cgroup.procs"):
        try:
            pids.update(int(x) for x in path.read_text().splitlines() if x.isdigit())
        except OSError:
            pass
    for child_pid in pids:
        try:
            for line in Path(f"/proc/{child_pid}/status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    rss_bytes += int(line.split()[1]) * 1024
                    break
        except (OSError, ValueError):
            pass
    return {"containerPid": pid, "available": True, "memoryCurrentBytes": current,
            "memoryPeakBytes": peak, "memorySwapCurrentBytes": swap,
            "memoryEvents": events, "processTreeRssBytes": rss_bytes,
            "processIds": sorted(pids)}


def make_prompt() -> list[dict]:
    vocab = ("amber", "bicycle", "carbon", "cedar", "cobalt", "compass", "copper", "crystal", "garden", "harbor", "island", "lantern", "maple", "meadow", "museum", "orbit", "orange", "parcel", "planet", "quartz", "silver", "station", "velvet", "violet", "window", "yellow")
    target, rep = 24576, 1
    nonce = f"q32-prompt_copy-{target}-{rep}-a2"
    rng = random.Random(4000 + target + rep)
    chars = int(target * 5.5)
    phrase = " ".join(rng.sample(vocab, 9))
    unit = (phrase + " | ") * 4
    data = (unit * max(1, chars // len(unit)))[:chars]
    task = "Copy the reference text sequence repeatedly, separated by one space. Output only copied text; continue until the response reaches its output limit."
    system = f"You are in a local performance test. Request identifier: {nonce}. Follow the user's task exactly."
    user = f"Trial {nonce}. Reference records follow:\n{data}\n{task}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def request_sol(messages: list[dict]) -> dict:
    body = {"model": MODEL_ID, "messages": messages, "max_tokens": 256}
    req = Request(BASE_URL + "/chat/completions", data=json.dumps(body).encode(),
                  headers={"Content-Type": "application/json"}, method="POST")
    started = time.monotonic()
    with urlopen(req, timeout=900) as response:
        payload = json.loads(response.read().decode())
        status = response.status
    usage = payload.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    if status != 200 or not isinstance(prompt_tokens, int) or not isinstance(completion_tokens, int):
        raise RuntimeError("SOL response lacks HTTP 200 or token usage")
    if not 20000 <= prompt_tokens <= 30000:
        raise RuntimeError(f"actual prompt tokens outside preregistered [20000,30000]: {prompt_tokens}")
    return {"httpStatus": status, "promptTokens": prompt_tokens,
            "completionTokens": completion_tokens,
            "finishReason": payload.get("choices", [{}])[0].get("finish_reason"),
            "e2eSeconds": time.monotonic() - started,
            "responseId": payload.get("id"),
            "promptSha256": hashlib.sha256("\n".join(m["content"] for m in messages).encode()).hexdigest()}


class Monitor(threading.Thread):
    def __init__(self) -> None:
        super().__init__(name="q127-amd05-monitor", daemon=True)
        self.stop_event = threading.Event()
        self.abort_reason: str | None = None
        self.rows: list[dict] = []
        self.counts = initial_counts()
        self.baseline_oom = oom_kill_count()
        self.baseline_cgroup_oom: dict[str, int] | None = None
        self.baseline_swap: int | None = None

    def abort_owned_container(self, reason: str) -> None:
        if self.abort_reason is not None:
            return
        self.abort_reason = reason
        subprocess.run(["docker", "stop", "--time", "10", CONTAINER],
                       capture_output=True, text=True, timeout=20)

    def run(self) -> None:
        while not self.stop_event.wait(1.0):
            try:
                mem = meminfo()
                psi = psi_memory()
                gpus = gpu_rows()
                cgroup = cgroup_snapshot()
                oom = oom_kill_count()
                gate_sample = {"memAvailableGiB": mem["MemAvailable"] / GIB,
                               "memoryPsiAvg10Pct": psi, "oomKill": oom}
                reason, self.counts, warning = evaluate(gate_sample, self.baseline_oom, self.counts)
                row = {"atUtc": utc(), "memAvailableBytes": mem["MemAvailable"],
                       "swapFreeBytes": mem["SwapFree"], "psi": psi, "oomKill": oom,
                       "gpus": gpus, "cgroup": cgroup, "warning": warning,
                       "amd05StopReason": reason}
                append_jsonl(RUNS / "memory-trace.jsonl", row)
                self.rows.append(row)
                events = cgroup.get("memoryEvents", {})
                swap_now = cgroup.get("memorySwapCurrentBytes")
                if cgroup.get("available"):
                    if self.baseline_cgroup_oom is None:
                        self.baseline_cgroup_oom = events
                        self.baseline_swap = swap_now
                        if any(events.get(key, 0) > 0 for key in ("oom", "oom_kill")):
                            self.abort_owned_container("new Q127 container began with a nonzero cgroup OOM counter")
                        if swap_now is not None and swap_now > SWAP_ABORT_BYTES:
                            self.abort_owned_container("new Q127 container began with >4 MiB cgroup swap")
                    else:
                        if any(events.get(key, 0) > self.baseline_cgroup_oom.get(key, 0) for key in ("oom", "oom_kill")):
                            self.abort_owned_container("worker cgroup OOM event increased")
                        if (swap_now is not None and self.baseline_swap is not None
                                and swap_now - self.baseline_swap > SWAP_ABORT_BYTES):
                            self.abort_owned_container("worker cgroup swap increased by >4 MiB")
                elif cgroup.get("containerPid") is not None or self.baseline_cgroup_oom is not None:
                    self.abort_owned_container("worker cgroup disappeared or telemetry became unavailable")
                if len(self.rows) % 5 == 0:
                    other_processes = server_processes(set(cgroup.get("processIds", [])))
                    other_containers = []
                    for item in docker_rows():
                        name = item.get("Names", "")
                        signature = " ".join((name, item.get("Image", ""), item.get("Ports", ""))).lower()
                        if name != CONTAINER and any(word in signature for word in SERVER_WORDS):
                            other_containers.append(name)
                    if other_processes or other_containers:
                        self.abort_owned_container("foreign inference server appeared during Q127")
                if reason:
                    self.abort_owned_container(reason)
            except Exception as exc:
                append_jsonl(RUNS / "monitor-errors.jsonl", {"atUtc": utc(), "errorType": type(exc).__name__})
                self.abort_owned_container("required memory/GPU telemetry unavailable")
            if self.abort_reason:
                return

    def close(self) -> None:
        self.stop_event.set()
        self.join(timeout=5)

    def summary(self) -> dict:
        if not self.rows:
            return {"sampleCount": 0, "abortReason": self.abort_reason}
        return {
            "sampleCount": len(self.rows),
            "minMemAvailableGiB": min(x["memAvailableBytes"] for x in self.rows) / GIB,
            "maxHostPsiSomeAvg10Pct": max(x["psi"]["some"] for x in self.rows),
            "maxHostPsiFullAvg10Pct": max(x["psi"]["full"] for x in self.rows),
            "maxProcessTreeRssGiB": max((x["cgroup"].get("processTreeRssBytes") or 0) for x in self.rows) / GIB,
            "maxCgroupMemoryGiB": max((x["cgroup"].get("memoryPeakBytes") or x["cgroup"].get("memoryCurrentBytes") or 0) for x in self.rows) / GIB,
            "maxCgroupSwapMiB": max((x["cgroup"].get("memorySwapCurrentBytes") or 0) for x in self.rows) / (1024 ** 2),
            "maxGpuMemoryUsedMiBByIndex": {str(index): max((gpu["memoryUsedMiB"] for row in self.rows for gpu in row["gpus"] if gpu["index"] == index), default=0) for index in (0, 1)},
            "maxGpuTemperatureC": max(gpu["temperatureC"] for row in self.rows for gpu in row["gpus"]),
            "oomKillStart": self.baseline_oom,
            "oomKillEnd": self.rows[-1]["oomKill"],
            "warnings": sum(bool(x["warning"]) for x in self.rows),
            "abortReason": self.abort_reason,
        }


def capture_logs() -> None:
    proc = subprocess.run(["docker", "logs", "--tail", "2000", CONTAINER],
                          capture_output=True, text=True, timeout=15)
    raw = re.sub(r"(?i)(hf_[A-Za-z0-9]{16,}|Bearer\s+[^\s\"']+)", "[REDACTED]",
                 proc.stdout + proc.stderr)[-200000:]
    path = LOGS / "sol-engine-before-cleanup.log"
    path.write_text(raw, encoding="utf-8")
    write_json(RECEIPTS / "docker-log-capture.json", {"returncode": proc.returncode,
               "bytesSaved": len(raw), "sha256": hashlib.sha256(raw.encode()).hexdigest()})


def main() -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    RECEIPTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(parents=True, exist_ok=True)
    status = "FAILED"
    error = None
    monitor = None
    server_started = False
    try:
        preflight()
        env = env_for_compose()
        monitor = Monitor()
        monitor.start()
        # Q121 verifies this monitor.start() precedes the only server-start subprocess.
        start = subprocess.Popen(compose_cmd("up", "-d", "--remove-orphans"), env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                 start_new_session=True)
        server_started = True
        stdout, stderr = start.communicate(timeout=180)
        write_json(RECEIPTS / "compose-start.json", {"returncode": start.returncode,
                   "stdoutSha256": hashlib.sha256(stdout.encode()).hexdigest(),
                   "stderrSha256": hashlib.sha256(stderr.encode()).hexdigest(),
                   "project": PROJECT, "container": CONTAINER})
        if start.returncode:
            raise RuntimeError("Q127 isolated Compose start failed")
        deadline = time.monotonic() + 900
        ready = False
        while time.monotonic() < deadline:
            if monitor.abort_reason:
                raise RuntimeError("AMD05 aborted during SOL startup: " + monitor.abort_reason)
            try:
                with urlopen(BASE_URL + "/models", timeout=3) as response:
                    models = json.loads(response.read().decode()).get("data", [])
                    if response.status == 200 and any(item.get("id") == MODEL_ID for item in models):
                        ready = True
                        break
            except Exception:
                pass
            time.sleep(5)
        if not ready:
            raise TimeoutError("SOL did not reach /v1/models within 900 seconds; no retry")
        write_json(RECEIPTS / "server-ready.json", {"atUtc": utc(), "modelId": MODEL_ID})
        request_result = request_sol(make_prompt())
        if monitor.abort_reason:
            raise RuntimeError("AMD05 stopped the SOL worker: " + monitor.abort_reason)
        status = "PASS"
        write_json(RECEIPTS / "sol-request.json", request_result)
    except BaseException as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
        if server_started:
            try:
                capture_logs()
            except Exception as log_exc:
                error["logCaptureError"] = type(log_exc).__name__
    finally:
        if monitor is not None:
            monitor.close()
        if server_started:
            down = subprocess.run(compose_cmd("down", "--remove-orphans", "--timeout", "15"),
                                  env=env_for_compose(), capture_output=True, text=True, timeout=90)
            write_json(RECEIPTS / "compose-stop.json", {"returncode": down.returncode,
                       "stdoutSha256": hashlib.sha256(down.stdout.encode()).hexdigest(),
                       "stderrSha256": hashlib.sha256(down.stderr.encode()).hexdigest()})
            remaining = [item.get("Names", "") for item in docker_rows() if item.get("Names") == CONTAINER]
            if down.returncode or remaining:
                status = "FAILED"
                error = error or {"type": "CleanupError", "message": "Q127 container remained after compose down"}
            else:
                try:
                    port_free()
                except OSError:
                    status = "FAILED"
                    error = error or {"type": "CleanupError", "message": "Q127 loopback port remained occupied"}
            server_started = False
        summary = monitor.summary() if monitor else {"sampleCount": 0}
        final = {"taskId": TASK_ID, "status": status, "error": error,
                 "monitor": summary, "atUtc": utc(),
                 "noProductionProfileChanged": True, "otherGpuProcessesKilled": False}
        write_json(RECEIPTS / "final-summary.json", final)
        append_jsonl(RUNS / "completion.jsonl", final)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
