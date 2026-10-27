#!/usr/bin/env python3
"""Start one isolated profile, run the preregistered BCB screen, and clean it up."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[4]
TASK = Path(__file__).resolve().parents[1]
Q127 = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-127/scripts/run_sol_trace.py"
Q85_RECEIPT = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-85/receipts/base-model-hash-verification.json"
Q85_ROOT = Path("/media/cristian/HDD extra/Modelos-eval/Q85-HyperQwen/HyperQwen")
Q85_MODELS = Path("/media/cristian/HDD extra/Modelos-eval/Q85-HyperQwen/models")
TASK_STORAGE = Path("/media/cristian/HDD extra/Modelos-eval/Q-20261027-VF-ITERATION-167")
HYPER_MODELS = TASK_STORAGE / "models"
HYPER_MODEL = HYPER_MODELS / "Qwen3.8-27B-W4A16-AutoRound"
HYPER_DRAFTER = HYPER_MODELS / "Qwen3.8-27B-DFlash2-W4A16/model.safetensors"
HYPER_DRAFTER_SHA = "ec26996e6a0745ab5edb857117220ce1e219ad524f71e6e149b703804947d8e7"
HYPER_COPY_MANIFEST = TASK / "receipts/hyperqwen/private-copy-manifest.json"
HYPER_IMAGE = "ghcr.io/syv-ai/hyperqwen@sha256:0acd4b9625473e51c9bab56406c30814bc0d0d7e0a38deb408c62664b5a77669"
SOL_COMPOSE = Path("/home/cristian/.cache/llamacode/club-3090-src/models/qwen3.8-27b/vllm/compose/dual/autoround-int4/mtp.yml")
SOL_OVERRIDE = SOL_COMPOSE.parent / "vram-quarantine.override.yml"
SOL_MODEL_DIR = Path("/media/cristian/Disco local/Models/llamacpp/club-3090/qwen3.8-27b-autoround-int4")
PORT = 18167
LOCK_TASK = "Q146 resume justified VF-20261019-01 tests"
LOCK_TOKEN = "2242863e-c78e-4fa9-9649-c1d1541f3919"
EXPECTED_FIXTURE_SHA = "11279cde14113fc8527f141c53e14cb5ccf0dba65749081a4f914408e391c268"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def run(args: list[str], *, env: dict[str, str] | None = None, timeout: int = 60,
        check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env)
    if check and result.returncode:
        raise RuntimeError(f"command failed ({Path(args[0]).name}, exit {result.returncode})")
    return result


def stop_owned_process_group(process: subprocess.Popen | None, timeout: int = 15) -> None:
    """Stop only a child process group created by this Q167 runner."""
    if process is None or process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=10)


def load_monitor_module():
    # Q127's monitor imports q117_pressure_guard_attempt05 from its own
    # scripts directory. Loading it by file path does not add that directory
    # to sys.path, so make the dependency location explicit before execution.
    script_dir = str(Q127.parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("q127_monitor_source", Q127)
    if spec is None or spec.loader is None:
        raise RuntimeError("Q127 monitor source cannot be imported")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_lock() -> None:
    with (ROOT / "WORK_QUEUE.lock").open(encoding="utf-8") as stream:
        lock = json.load(stream)
    if lock.get("task") != LOCK_TASK or lock.get("token") != LOCK_TOKEN:
        raise RuntimeError("umbrella evaluation lock ownership changed")


def verify_model_files(model_dir: Path, checks: list[tuple[str, str]]) -> list[dict]:
    rows = []
    for name, expected in checks:
        path = model_dir / name
        if not path.is_file():
            raise RuntimeError(f"required model shard missing: {name}")
        actual = sha(path)
        if actual != expected:
            raise RuntimeError(f"model shard checksum mismatch: {name}")
        rows.append({"file": name, "sha256": actual, "sizeBytes": path.stat().st_size})
    return rows


def candidate_processes() -> list[dict]:
    proc = run(["ps", "-eo", "pid=,comm=,args="], timeout=10)
    terms = re.compile(r"(llama-server|vllm|ollama\s+serve|sglang|aphrodite|ninfer|strata|peritosoft)", re.I)
    found = []
    self_pid = os.getpid()
    own = set(OWN_PIDS)
    for line in proc.stdout.splitlines():
        fields = line.strip().split(None, 2)
        if len(fields) < 2:
            continue
        pid = int(fields[0])
        if pid == self_pid or pid in own:
            continue
        command = fields[2] if len(fields) > 2 else ""
        if "run_profile.py" in command or "run_bcb_text.py" in command:
            continue
        if "q167-grader-" in command:
            continue
        if terms.search(fields[1] + " " + command):
            found.append({"pid": pid, "comm": fields[1]})
    return found


OWN_PIDS: set[int] = set()


def compose_command(arm: str, project: str, *args: str) -> tuple[list[str], dict[str, str]]:
    env = os.environ.copy()
    if arm == "sol":
        env.update({
            "BIND_HOST": "127.0.0.1", "PORT": str(PORT), "ESTATE_CONTAINER": "q167-sol-screen",
            "MODEL_DIR": str(SOL_MODEL_DIR.parent), "TP": "2", "MAX_MODEL_LEN": "262144",
            "GPU_MEMORY_UTILIZATION": "0.90", "MAX_NUM_SEQS": "8", "MAX_NUM_BATCHED_TOKENS": "8192",
            "SPEC_N": "4", "W4A8": "1", "ENABLE_THINKING": "true", "REASONING_EFFORT": "medium", "TEMP": "0.6",
            "TOP_P": "0.95", "TOP_K": "20", "MIN_P": "0.0", "PRESENCE_PENALTY": "0.0",
            "CLUB3090_RESTART": "no", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        })
        command = ["docker", "compose", "--project-directory", str(SOL_COMPOSE.parent), "-p", project,
                   "-f", str(SOL_COMPOSE), "-f", str(SOL_OVERRIDE),
                   "-f", str(TASK / "work/sol-isolated.compose.yml"), *args]
    else:
        env.update({
            "BIND": "127.0.0.1", "PORT": str(PORT), "GPU_COUNT": "2", "GPU_UTIL": "0.91",
            "KV_MEM": "3000000000", "EXTRA_ARGS": "--tensor-parallel-size 2",
            "MAX_LEN": "65536", "MAX_SEQS": "8", "SPEC": "dflash2", "PREFIX_CACHE": "1",
            "DFLASH_TOKENS": "7", "FAST_VARIANT": "0", "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1", "MODELS_DIR": str(HYPER_MODELS),
        })
        command = ["docker", "compose", "--project-directory", str(Q85_ROOT), "--profile", "single", "-p", project,
                   "-f", str(Q85_ROOT / "docker-compose.yml"), "-f", str(Q85_ROOT / "compose.q85.yaml"),
                   "-f", str(TASK / "work/hyperqwen-isolated.compose.yaml"), *args]
    return command, env


def compose_readback(arm: str, project: str, env: dict[str, str]) -> dict:
    if arm == "hyperqwen":
        directory = str(Q85_ROOT)
        base = ["docker", "compose", "--project-directory", str(Q85_ROOT), "--profile", "single", "-p", project,
                "-f", str(Q85_ROOT / "docker-compose.yml"), "-f", str(Q85_ROOT / "compose.q85.yaml"),
                "-f", str(TASK / "work/hyperqwen-isolated.compose.yaml")]
        service = "single"
        expected = {"GPU_COUNT": "2", "GPU_UTIL": "0.91", "KV_MEM": "3000000000",
                    "EXTRA_ARGS": "--tensor-parallel-size 2", "MAX_LEN": "65536", "MAX_SEQS": "8",
                    "SPEC": "dflash2", "DFLASH_TOKENS": "7", "FAST_VARIANT": "0",
                    "PORT": "18167", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
                    "PREPARE": "0", "VERIFY": "1", "DFLASH2": "1"}
    else:
        directory = str(SOL_COMPOSE.parent)
        base = ["docker", "compose", "--project-directory", directory, "-p", project,
                "-f", str(SOL_COMPOSE), "-f", str(SOL_OVERRIDE),
                "-f", str(TASK / "work/sol-isolated.compose.yml")]
        service = "vllm-qwen38-27b-dual-fast"
        expected = {"SPEC_N": "4", "W4A8": "1", "ENABLE_THINKING": "true",
                    "TEMP": "0.6", "TOP_P": "0.95", "TOP_K": "20", "MIN_P": "0.0",
                    "PRESENCE_PENALTY": "0.0", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
    proc = run(base + ["config", "--format", "json"], env=env, timeout=45)
    config = json.loads(proc.stdout)
    container = config["services"][service].get("container_name")
    ports = config["services"][service].get("ports", [])
    environment = config["services"][service].get("environment", {})
    if isinstance(environment, list):
        environment = dict(item.split("=", 1) if "=" in item else (item, "") for item in environment)
    selected = {key: str(environment.get(key, "")) for key in expected}
    mismatches = {key: {"actual": selected[key], "expected": expected[key]}
                  for key in expected if selected[key] != expected[key]}
    command = config["services"][service].get("command", [])
    if isinstance(command, str):
        command = command.split()
    if arm == "sol":
        if config["services"][service].get("image") != "vllm/vllm-openai@sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967":
            mismatches["image"] = {"actual": config["services"][service].get("image"), "expected": "pinned vLLM v0.27.1 digest"}
        command_expected = {
            "--tensor-parallel-size": "2", "--max-model-len": "262144",
            "--gpu-memory-utilization": "0.90", "--max-num-seqs": "8",
            "--max-num-batched-tokens": "8192", "--port": "8000",
        }
        for flag, value in command_expected.items():
            if flag not in command or command[command.index(flag) + 1] != value:
                mismatches[flag] = {"actual": command[command.index(flag) + 1] if flag in command and command.index(flag) + 1 < len(command) else None,
                                    "expected": value}
        try:
            kwargs = json.loads(command[command.index("--default-chat-template-kwargs") + 1])
        except (ValueError, IndexError, json.JSONDecodeError):
            kwargs = None
        if kwargs != {"enable_thinking": True, "reasoning_effort": "medium"}:
            mismatches["--default-chat-template-kwargs"] = {"actual": kwargs,
                                                            "expected": {"enable_thinking": True, "reasoning_effort": "medium"}}
        volume_by_target = {row.get("target"): row for row in config["services"][service].get("volumes", [])}
        expected_mounts = {
            "/root/.cache/huggingface": (str(SOL_MODEL_DIR.parent), True),
            "/root/.cache/vllm/torch_compile_cache": ("/media/cristian/HDD extra/Modelos-eval/Q-20261027-VF-ITERATION-167/cache/torch_compile", False),
            "/root/.triton/cache": ("/media/cristian/HDD extra/Modelos-eval/Q-20261027-VF-ITERATION-167/cache/triton", False),
        }
        for target, (source, read_only) in expected_mounts.items():
            actual = volume_by_target.get(target, {})
            if actual.get("source") != source or bool(actual.get("read_only", False)) != read_only:
                mismatches[f"volume:{target}"] = {"actualSource": actual.get("source"),
                                                    "actualReadOnly": bool(actual.get("read_only", False)),
                                                    "expectedSource": source, "expectedReadOnly": read_only}
    else:
        volume_by_target = {row.get("target"): row for row in config["services"][service].get("volumes", [])}
        expected_mounts = {
            "/app/models": (str(HYPER_MODELS), True),
            "/cache": (str(TASK_STORAGE / "cache/hyperqwen"), False),
            "/tmp": (str(TASK_STORAGE / "tmp/hyperqwen"), False),
        }
        for target, (source, read_only) in expected_mounts.items():
            actual = volume_by_target.get(target, {})
            if actual.get("source") != source or bool(actual.get("read_only", False)) != read_only:
                mismatches[f"volume:{target}"] = {"actualSource": actual.get("source"),
                                                    "actualReadOnly": bool(actual.get("read_only", False)),
                                                    "expectedSource": source, "expectedReadOnly": read_only}
        prepare = config["services"].get("prepare", {})
        if prepare.get("container_name") != "q167-hyperqwen-prepare":
            mismatches["prepare:container_name"] = {"actual": prepare.get("container_name"),
                                                        "expected": "q167-hyperqwen-prepare"}
        prepare_command = prepare.get("command", [])
        if isinstance(prepare_command, str):
            prepare_command = prepare_command.split()
        if prepare_command != ["prepare"]:
            mismatches["prepare:command"] = {"actual": prepare_command, "expected": ["prepare"]}
        prepare_environment = prepare.get("environment", {})
        if isinstance(prepare_environment, list):
            prepare_environment = dict(item.split("=", 1) if "=" in item else (item, "")
                                       for item in prepare_environment)
        prepare_expected = {"DFLASH2": "1", "FAST_VARIANT": "0",
                            "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
        prepare_selected = {key: str(prepare_environment.get(key, "")) for key in prepare_expected}
        for key, expected_value in prepare_expected.items():
            if prepare_selected[key] != expected_value:
                mismatches[f"prepare:environment:{key}"] = {"actual": prepare_selected[key],
                                                              "expected": expected_value}
        prepare_volumes = {row.get("target"): row for row in prepare.get("volumes", [])}
        for target, source in (("/app/models", str(HYPER_MODELS)),
                               ("/cache", str(TASK_STORAGE / "cache/hyperqwen")),
                               ("/tmp", str(TASK_STORAGE / "tmp/hyperqwen"))):
            actual = prepare_volumes.get(target, {})
            if actual.get("source") != source or bool(actual.get("read_only", False)):
                mismatches[f"prepare:volume:{target}"] = {
                    "actualSource": actual.get("source"), "actualReadOnly": bool(actual.get("read_only", False)),
                    "expectedSource": source, "expectedReadOnly": False}
        if prepare.get("deploy", {}).get("resources", {}).get("reservations", {}).get("devices"):
            mismatches["prepare:gpuReservation"] = {"actual": "GPU reservation present", "expected": "none"}
        if prepare.get("image") != HYPER_IMAGE:
            mismatches["prepare:image"] = {"actual": prepare.get("image"), "expected": HYPER_IMAGE}
        prepare_readback = {"service": "prepare", "container": prepare.get("container_name"),
                            "command": prepare_command, "image": prepare.get("image"),
                            "selectedEnvironment": prepare_selected,
                            "volumes": prepare.get("volumes", []),
                            "gpuReservation": prepare.get("deploy", {}).get("resources", {}).get("reservations", {}).get("devices", [])}
    if mismatches:
        raise RuntimeError("resolved Compose parameters differ from preregistration: " + json.dumps(mismatches))
    if container != ("q167-sol-screen" if arm == "sol" else "q167-hyperqwen-screen"):
        raise RuntimeError("resolved container name differs from preregistration")
    if not any(str(item.get("published")) == str(PORT) and str(item.get("host_ip")) == "127.0.0.1" for item in ports):
        raise RuntimeError("resolved Compose port is not loopback-bound on Q167's port")
    result = {"service": service, "container": container, "port": ports,
            "selectedEnvironment": selected, "command": command,
            "volumes": config["services"][service].get("volumes", []),
            "image": config["services"][service].get("image")}
    if arm == "hyperqwen":
        result["prepareService"] = prepare_readback
    return result


def verify_disk_and_host() -> dict:
    disk = {path: shutil.disk_usage(path).free for path in ("/", "/var/lib/docker", "/media/cristian/HDD extra")}
    minimums = {"/": 8 * 1024**3, "/var/lib/docker": 8 * 1024**3,
                "/media/cristian/HDD extra": 40 * 1024**3}
    for path, floor in minimums.items():
        if disk[path] < floor:
            raise RuntimeError(f"storage floor failed for {path}")
    q = run(["nvidia-smi", "--query-gpu=index,name,temperature.gpu,memory.used,memory.total,utilization.gpu",
             "--format=csv,noheader,nounits"], timeout=10)
    gpus = []
    for line in q.stdout.splitlines():
        fields = [x.strip() for x in line.split(",")]
        if len(fields) != 6:
            raise RuntimeError("unexpected nvidia-smi row")
        gpus.append({"index": int(fields[0]), "name": fields[1], "temperatureC": int(fields[2]),
                     "memoryUsedMiB": int(fields[3]), "memoryTotalMiB": int(fields[4]),
                     "utilizationPct": int(fields[5])})
    if len(gpus) != 2 or any("3090" not in row["name"] or row["temperatureC"] >= 80 for row in gpus):
        raise RuntimeError("two cool RTX 3090 devices are required")
    if sum(1 for row in gpus if row["memoryTotalMiB"] >= 23000 and
           row["memoryTotalMiB"] - row["memoryUsedMiB"] >= 22900) != 2:
        raise RuntimeError("both 24 GB GPUs need at least 22,900 MiB free")
    mem = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, _, rest = line.partition(":")
        if key in ("MemAvailable", "SwapFree"):
            mem[key] = int(rest.split()[0]) * 1024
    if mem.get("MemAvailable", 0) < 80 * 1024**3 or mem.get("SwapFree", 0) < 1024**3:
        raise RuntimeError("host RAM/swap preflight below preregistered floor")
    return {"diskFreeBytes": disk, "gpus": gpus, "hostMemory": mem}


def no_foreign_servers(arm: str, project: str) -> None:
    if candidate_processes():
        raise RuntimeError("foreign inference server or PeritoSoft process found; leaving it untouched")
    proc = run(["docker", "ps", "--format", "{{json .}}"], timeout=15)
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        name = row.get("Names", "")
        signature = " ".join((name, row.get("Image", ""), row.get("Ports", ""))).lower()
        if project in signature:
            raise RuntimeError("Q167 container/project already exists; refusing to reuse it")
        if re.search(r"(llama-server|vllm|ollama|sglang|aphrodite|ninfer|strata|peritosoft)", signature):
            raise RuntimeError("foreign inference container found; leaving it untouched")
    listeners = run(["ss", "-H", "-ltn", f"sport = :{PORT}"], timeout=10)
    if listeners.stdout.strip():
        raise RuntimeError("Q167 TCP port already has a listener")


def log_capture(container: str, env_file: Path | None, logs_dir: Path) -> dict:
    proc = subprocess.run(["docker", "logs", "--tail", "1500", container],
                          capture_output=True, timeout=20)
    text = (proc.stdout + proc.stderr).decode("utf-8", errors="replace")
    text = re.sub(r"(?i)(hf_[A-Za-z0-9]{16,}|Bearer\s+[^\s\"']+)", "[REDACTED]", text)
    if env_file and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("VLLM_API_KEY="):
                secret = line.split("=", 1)[1].strip().strip("\"'")
                if secret:
                    text = text.replace(secret, "[REDACTED]")
    text = text[-200000:]
    logs_dir.mkdir(parents=True, exist_ok=True)
    path = logs_dir / "engine-before-cleanup.log"
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)
    return {"returnCode": proc.returncode, "bytes": len(text.encode()),
            "sha256": hashlib.sha256(text.encode()).hexdigest(), "path": str(path.relative_to(ROOT))}


def main() -> int:
    def handle_stop(signum, _frame):
        raise InterruptedError(f"Q167 received signal {signum}; cleaning only Q167 processes")

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=("sol", "hyperqwen"), required=True)
    args = parser.parse_args()
    arm = args.arm
    project = "q167-sol-screen" if arm == "sol" else "q167-hyperqwen-screen"
    container = project
    arm_dir = TASK / "runs" / arm
    receipt_dir = TASK / "receipts" / arm
    logs_dir = TASK / "logs" / arm
    arm_dir.mkdir(parents=True, exist_ok=True)
    receipt_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    monitor = load_monitor_module()
    monitor.CONTAINER = container
    monitor.PROJECT = project
    monitor.PORT = PORT
    monitor.RUNS = arm_dir
    monitor.RECEIPTS = receipt_dir
    monitor.LOGS = logs_dir
    original_server_processes = monitor.server_processes
    original_docker_rows = monitor.docker_rows

    def server_processes(owned_pids: set[int] | None = None) -> list[dict]:
        return [row for row in candidate_processes()
                if not owned_pids or row["pid"] not in owned_pids]

    def docker_rows() -> list[dict]:
        return [row for row in original_docker_rows()
                if not str(row.get("Names", "")).startswith("q167-grader-")]

    monitor.server_processes = server_processes
    monitor.docker_rows = docker_rows
    compose, env = compose_command(arm, project)
    q85_model_checks = []
    if arm == "hyperqwen":
        for row in json.loads(Q85_RECEIPT.read_text(encoding="utf-8"))["fileChecks"]:
            q85_model_checks.append((row["path"], row["sha256"]))
    model_id = "qwen3.8-27b"
    url = f"http://127.0.0.1:{PORT}/v1/chat/completions"
    started = False
    guard = None
    compose_process = None
    bench = None
    summary = {"taskId": "Q-20261027-VF-ITERATION-167", "arm": arm, "status": "FAILED"}
    try:
        verify_lock()
        (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        (ROOT / "README.md").read_text(encoding="utf-8")
        (ROOT / "WORK_QUEUE.md").read_text(encoding="utf-8")
        preflight = verify_disk_and_host()
        no_foreign_servers(arm, project)
        task_storage = Path("/media/cristian/HDD extra/Modelos-eval/Q-20261027-VF-ITERATION-167")
        for relative in ("cache/torch_compile", "cache/triton", "cache/hyperqwen", "tmp/hyperqwen"):
            path = task_storage / relative
            path.mkdir(parents=True, exist_ok=True)
            path.chmod(0o700)
        if arm == "sol":
            checks = [
                    ("model-00001-of-00007.safetensors", "83c0adb0f1141142a25c5f7937a09272fef2baee7d6b07afe60a076feffe3b66"),
                    ("model-00002-of-00007.safetensors", "6c86c3917cd228d5699cb1435d9216e2baf281582ba4282a98638163605be7ec"),
                    ("model-00003-of-00007.safetensors", "bfb9613b3f6ba3d0c5b3efa74f92cc14ec5c9266b341a79bf6b45247a5857770"),
                    ("model-00004-of-00007.safetensors", "8e9fbd476aa3055c3c0a886298f9beb93c5275c748c533835746f6648f6dae55"),
                    ("model-00005-of-00007.safetensors", "f0cd639621eb26410d96b8c073344ae008f646572a9c4713326ff43d406cf276"),
                    ("model-00006-of-00007.safetensors", "55a14ee79d3e5a65a8731d89426f4df477e8bdc7daa7976d41254d8afb9432f0"),
                    ("model-00007-of-00007.safetensors", "6866cf8adcccc4cc6a00e74bc025f1a774fb52103b70f2674d0288272951a733"),
            ]
            model_hashes = verify_model_files(SOL_MODEL_DIR, checks)
            for path, expected in ((SOL_COMPOSE, "2df4e44e1e1b268da80690a0812ac1b60768d60b643096ce8473110f88b7b76a"),
                                   (SOL_OVERRIDE, "e547197d1b283e5c8b684d35e1b348bb91bbba3a327183a14b0d4a6083c36a50")):
                if sha(path) != expected:
                    raise RuntimeError("SOL compose fingerprint differs from Q34")
        else:
            copy_manifest = json.loads(HYPER_COPY_MANIFEST.read_text(encoding="utf-8"))
            if copy_manifest.get("status") != "VERIFIED_PRIVATE_COPY":
                raise RuntimeError("HyperQwen private copy manifest is not verified")
            expected_files = {row["path"] for row in copy_manifest["files"]}
            runtime_files = {row["path"] for row in copy_manifest.get("runtimeFiles", [])}
            actual_files = {path.relative_to(HYPER_MODELS).as_posix()
                            for path in HYPER_MODELS.rglob("*") if path.is_file()}
            if actual_files != expected_files | runtime_files:
                raise RuntimeError("HyperQwen private copy file set differs from its manifest")
            for row in copy_manifest.get("runtimeFiles", []):
                path = HYPER_MODELS / row["path"]
                if (not path.is_file() or path.stat().st_size != row["sizeBytes"]
                        or sha(path) != row["sha256"]):
                    raise RuntimeError("HyperQwen runtime file differs from its manifest")
            model_hashes = verify_model_files(HYPER_MODELS, [
                (row["path"], row["sha256"]) for row in copy_manifest["files"]
            ])
            if HYPER_MODELS == Q85_MODELS or str(Q85_MODELS) in str(HYPER_MODELS):
                raise RuntimeError("HyperQwen private model root aliases the shared Q85 tree")
            if sha(HYPER_DRAFTER) != HYPER_DRAFTER_SHA:
                raise RuntimeError("HyperQwen DFlash2 checksum mismatch")
            image = run(["docker", "image", "inspect", HYPER_IMAGE, "--format", "{{.Id}}"], timeout=20)
            if not image.stdout.strip():
                raise RuntimeError("pinned HyperQwen image is absent")
        resolved = compose_readback(arm, project, env)
        write_json(receipt_dir / "host-preflight.json", preflight)
        write_json(receipt_dir / "compose-readback.json", resolved)

        guard = monitor.Monitor()
        guard.start()
        compose_process = subprocess.Popen(compose + ["up", "-d", "--no-build", "--pull", "never",
                                                       "--remove-orphans", "single"] if arm == "hyperqwen"
                                          else compose + ["up", "-d", "--no-build", "--pull", "never", "--remove-orphans"],
                                          env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                          start_new_session=True)
        OWN_PIDS.add(compose_process.pid)
        started = True
        start_deadline = time.monotonic() + 2400
        while True:
            try:
                stdout, stderr = compose_process.communicate(timeout=min(5, max(1, start_deadline - time.monotonic())))
                break
            except subprocess.TimeoutExpired:
                if guard.abort_reason:
                    raise RuntimeError("memory/GPU monitor stopped the owned server during Compose startup")
                if time.monotonic() >= start_deadline:
                    raise TimeoutError("Q167 Compose startup exceeded forty minutes")
        write_json(receipt_dir / "compose-start.json", {"returnCode": compose_process.returncode,
                   "stdoutSha256": hashlib.sha256(stdout.encode()).hexdigest(),
                   "stderrSha256": hashlib.sha256(stderr.encode()).hexdigest()})
        if compose_process.returncode:
            raise RuntimeError("Q167 Compose start failed")
        deadline = time.monotonic() + 1800
        ready = False
        health_url = f"http://127.0.0.1:{PORT}/health"
        while time.monotonic() < deadline:
            if guard.abort_reason:
                raise RuntimeError("memory/GPU monitor stopped the owned server")
            try:
                with urlopen(health_url, timeout=3) as response:
                    if response.status == 200:
                        ready = True
                        break
            except Exception:
                pass
            state = run(["docker", "inspect", "--format", "{{.State.Status}}", container], timeout=10, check=False)
            status = state.stdout.strip() if state.returncode == 0 else ""
            if status in {"exited", "dead", "removing"}:
                raise RuntimeError("owned inference container exited before health")
            time.sleep(5)
        if not ready:
            raise TimeoutError("owned inference profile did not reach health within 30 minutes")
        write_json(receipt_dir / "server-ready.json", {"atUtc": time.time(), "health": "HTTP 200"})
        runner = TASK / "scripts/run_bcb_text.py"
        outfile = arm_dir / "bcb8-result.json"
        cmd = [sys.executable, str(runner), "--arm", arm, "--url", url, "--model", model_id,
               "--seed", "4242", "--out", str(outfile)]
        if arm == "hyperqwen":
            cmd += ["--api-key-file", str(Q85_ROOT / ".env"), "--reverse"]
        bench = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, env=os.environ.copy(), start_new_session=True)
        OWN_PIDS.add(bench.pid)
        bench_deadline = time.monotonic() + 3 * 60 * 60
        while True:
            try:
                bench_stdout, _ = bench.communicate(timeout=min(5, max(1, bench_deadline - time.monotonic())))
                break
            except subprocess.TimeoutExpired:
                if guard.abort_reason:
                    raise RuntimeError("memory/GPU monitor stopped the owned server during BCB screen")
                if time.monotonic() >= bench_deadline:
                    raise TimeoutError("Q167 BCB screen exceeded three hours")
        (logs_dir / "runner.stdout.log").write_text(bench_stdout or "", encoding="utf-8")
        print((bench_stdout or "").rstrip(), flush=True)
        rc = bench.returncode
        write_json(receipt_dir / "runner-exit.json", {"returnCode": rc, "output": str(outfile.relative_to(ROOT))})
        if guard.abort_reason:
            raise RuntimeError("memory/GPU monitor stopped the owned server during BCB screen")
        if not outfile.is_file():
            raise RuntimeError("BCB runner did not write its sanitized result")
        result = json.loads(outfile.read_text(encoding="utf-8"))
        summary.update({"status": "SCREENED" if rc == 0 else "SCREEN_INVALID",
                        "metrics": {key: result.get(key) for key in ("runs", "transportOk", "passed", "sandboxErrors", "emptyFinals")},
                        "profile": resolved, "modelHashes": model_hashes})
    except BaseException as exc:
        summary["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        stop_owned_process_group(bench)
        # The server's cgroup is expected to disappear when this arm is torn down.
        # Stop sampling first on ordinary completion; retain any real abort reason.
        if guard is not None and guard.abort_reason is None:
            guard.close()
        stop_owned_process_group(compose_process)
        if bench is not None:
            try:
                output, _ = bench.communicate(timeout=10)
                (logs_dir / "runner.stdout.log").write_text(output or "", encoding="utf-8")
            except Exception:
                pass
        if started:
            try:
                log_receipt = log_capture(container, Q85_ROOT / ".env" if arm == "hyperqwen" else None, logs_dir)
                write_json(receipt_dir / "docker-log-capture.json", log_receipt)
            except Exception as exc:
                write_json(receipt_dir / "docker-log-capture.json", {"errorType": type(exc).__name__})
            down_command, down_env = compose_command(arm, project)
            down = subprocess.run(down_command + ["down", "--remove-orphans", "--volumes", "--timeout", "30"],
                                  env=down_env, capture_output=True, text=True, timeout=120)
            write_json(receipt_dir / "compose-stop.json", {"returnCode": down.returncode,
                       "stdoutSha256": hashlib.sha256(down.stdout.encode()).hexdigest(),
                       "stderrSha256": hashlib.sha256(down.stderr.encode()).hexdigest()})
            if down.returncode:
                summary["status"] = "FAILED_CLEANUP"
            remaining = run(["docker", "ps", "-a", "--filter", f"label=com.docker.compose.project={project}",
                             "--format", "{{.Names}}"], timeout=20, check=False)
            listener = run(["ss", "-H", "-ltn", f"sport = :{PORT}"], timeout=10, check=False)
            summary["cleanup"] = {"composeDownReturnCode": down.returncode,
                                  "remainingProjectContainers": remaining.stdout.splitlines(),
                                  "portListeners": listener.stdout.splitlines()}
            if remaining.stdout.strip() or listener.stdout.strip():
                summary["status"] = "FAILED_CLEANUP"
        if guard is not None:
            guard.close()
        monitor_summary = guard.summary() if guard is not None else {"sampleCount": 0}
        summary["monitor"] = monitor_summary
        summary["monitorAbortReason"] = guard.abort_reason if guard is not None else None
        summary["atUtc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        summary["noProductionProfileChanged"] = True
        summary["otherGpuProcessesKilled"] = False
        try:
            summary["postflightGpus"] = verify_disk_and_host()["gpus"]
        except Exception as exc:
            summary["postflightError"] = type(exc).__name__
        write_json(receipt_dir / "final-summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0 if summary.get("status") == "SCREENED" and not summary.get("monitorAbortReason") else 1


if __name__ == "__main__":
    raise SystemExit(main())
