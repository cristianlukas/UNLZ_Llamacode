#!/usr/bin/env python3
"""Run the pinned Q138 reverse-engineering profile comparison in isolation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261026-VF-ITERATION-138"
RECEIPT = TASK / "receipts/amendment-01-runtime-and-prompt-correction.json"
TOKEN = "q138-re-fixture-bda789bf8eb8993f45f6bdc7"
LOCK_TASK = "Q138 legal reverse-engineering fixture for pending Qwen27B/Ghidra actionable"
GIB = 1024 ** 3
PORTS = (18138, 18139)
SERVER_MARKERS = ("llama-server", "serve/server.py", "ollama serve", "vllm", "sglang", "aphrodite", "ninfer")


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_sha(path: Path) -> tuple[str, int, int]:
    rows = []
    for item in sorted(path.rglob("*")):
        if item.is_file():
            rows.append((item.relative_to(path).as_posix(), item.stat().st_size, sha_file(item)))
    raw = json.dumps(rows, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest(), len(rows), sum(row[1] for row in rows)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with temp.open("r+b") as stream:
        os.fsync(stream.fileno())
    temp.replace(path)


def append_jsonl(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def check_lock() -> dict:
    lock = json.loads((ROOT / "WORK_QUEUE.lock").read_text(encoding="utf-8"))
    if lock.get("task") != LOCK_TASK or lock.get("token") != TOKEN:
        raise RuntimeError("Q138 no longer owns WORK_QUEUE.lock")
    return lock


def meminfo() -> dict[str, int]:
    wanted = {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}
    result = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, _, value = line.partition(":")
        if key in wanted:
            result[key] = int(value.split()[0]) * 1024
    if result.keys() < wanted:
        raise RuntimeError("required host RAM/swap telemetry missing")
    return result


def psi() -> dict[str, dict[str, float]]:
    result = {}
    for line in Path("/proc/pressure/memory").read_text().splitlines():
        fields = line.split()
        if fields and fields[0] in ("some", "full"):
            result[fields[0]] = {k: float(v) for k, v in
                                 (x.split("=", 1) for x in fields[1:] if "=" in x) if k.startswith("avg")}
    if set(result) != {"some", "full"} or any("avg10" not in row for row in result.values()):
        raise RuntimeError("global memory PSI some/full avg10 unavailable")
    return result


def gpu_rows() -> list[dict]:
    proc = subprocess.run(
        ["nvidia-smi", "--query-gpu=index,name,temperature.gpu,memory.used,memory.total,utilization.gpu",
         "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10, check=True)
    rows = []
    for line in proc.stdout.splitlines():
        fields = [x.strip() for x in line.split(",")]
        if len(fields) != 6:
            raise RuntimeError("unexpected nvidia-smi row")
        rows.append({"index": int(fields[0]), "name": fields[1], "temperatureC": int(fields[2]),
                     "memoryUsedMiB": int(fields[3]), "memoryTotalMiB": int(fields[4]),
                     "utilizationPct": int(fields[5]), "memoryFreeMiB": int(fields[4]) - int(fields[3])})
    return rows


def proc_commands() -> list[dict]:
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            cmd = entry.joinpath("cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
            comm = entry.joinpath("comm").read_text().strip()
        except OSError:
            continue
        low = (comm + " " + cmd).lower()
        if any(marker in low for marker in SERVER_MARKERS):
            found.append({"pid": int(entry.name), "comm": comm, "cmd": cmd[:400]})
    return found


def container_servers() -> list[dict]:
    if not shutil_which("docker"):
        return []
    proc = subprocess.run(["docker", "ps", "--format", "{{.ID}}\t{{.Image}}\t{{.Names}}\t{{.Ports}}"],
                          capture_output=True, text=True, timeout=15)
    if proc.returncode:
        raise RuntimeError("cannot inspect running containers for inference servers")
    rows = []
    for line in proc.stdout.splitlines():
        fields = line.split("\t")
        signature = " ".join(fields[1:]).lower()
        if any(marker in signature for marker in ("llama", "strata", "ollama", "vllm", "sglang", "ninfer", "aphrodite")):
            rows.append({"id": fields[0], "image": fields[1], "name": fields[2], "ports": fields[3] if len(fields) > 3 else ""})
    return rows


def shutil_which(name: str) -> str | None:
    from shutil import which
    return which(name)


def listeners(ports: tuple[int, ...] = PORTS) -> dict[int, str]:
    result = {}
    for port in ports:
        proc = subprocess.run(["ss", "-H", "-ltnp", f"sport = :{port}"],
                              capture_output=True, text=True, timeout=10)
        if proc.returncode:
            raise RuntimeError("cannot inspect TCP listeners")
        if proc.stdout.strip():
            result[port] = proc.stdout.strip()
    return result


def cgroup_path() -> Path:
    rel = next((line.split("::", 1)[1] for line in Path("/proc/self/cgroup").read_text().splitlines()
                if line.startswith("0::")), None)
    if rel is None:
        raise RuntimeError("unified cgroup v2 path unavailable")
    path = Path("/sys/fs/cgroup") / rel.lstrip("/")
    if not path.is_dir():
        raise RuntimeError("worker cgroup directory unavailable")
    return path


def verify_uncapped_cgroup() -> dict:
    path = cgroup_path()
    observed = []
    current = path
    while current != Path("/sys/fs/cgroup") and current.is_relative_to("/sys/fs/cgroup"):
        values = {}
        for field in ("memory.max", "memory.high", "memory.swap.max"):
            file = current / field
            if file.exists():
                values[field] = file.read_text().strip()
        observed.append({"path": str(current), "limits": values})
        if any(value != "max" for value in values.values()):
            raise RuntimeError(f"finite worker/inherited memory cap detected: {observed[-1]}")
        current = current.parent
    if not any("background.slice" in row["path"] for row in observed):
        raise RuntimeError("worker is not isolated in background.slice")
    return {"workerCgroup": str(path), "ancestorLimits": observed, "noFiniteMemoryOrSwapCaps": True}


def check_port(port: int) -> None:
    proc = subprocess.run(["ss", "-H", "-ltn", f"sport = :{port}"],
                          capture_output=True, text=True, timeout=10)
    if proc.returncode or proc.stdout.strip():
        raise RuntimeError(f"port {port} is not free: {proc.stdout.strip()}")


def strict_score(content: str, expected: str) -> bool:
    return content.strip() == expected


def assembled_prompt(question: dict, source: str) -> tuple[list[dict], str]:
    system = ("You are analyzing a decompiled C program from a synthetic binary authored for this test. "
              "Use only the supplied decompilation. Return exactly one option letter, A, B, C, or D. "
              "Do not include explanation, punctuation, or any other text.")
    user = "Ghidra decompilation follows:\n\n" + source + "\n\nQuestion:\n" + question["prompt"]
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    fingerprint = hashlib.sha256(json.dumps(messages, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    return messages, fingerprint


def verify_fixture() -> tuple[str, list[dict]]:
    source_path = TASK / "fixtures/ghidra-decompilation.c"
    source = source_path.read_text(encoding="utf-8")
    if sha_file(source_path) != "fd64ae63b1e0add2a1f842e349a6cfc54a8f3b841e69a1a34bd9af190337cadd":
        raise RuntimeError("Ghidra decompilation hash mismatch")
    question_path = TASK / "fixtures/questions.json"
    questions = json.loads(question_path.read_text(encoding="utf-8"))["questions"]
    if sha_file(question_path) != "ba2bc6b96cf20aa04334927efe2bd113e8385379ed1f495ec6b813c785b61cfe":
        raise RuntimeError("Q138 question set hash mismatch")
    if len(questions) != 12:
        raise RuntimeError("Q138 question count changed")
    for q in questions:
        messages, _ = assembled_prompt(q, source)
        if source not in messages[1]["content"] or q["prompt"] not in messages[1]["content"]:
            raise RuntimeError("contextual prompt assembly failed")
        if strict_score(q["answer"], q["answer"]) is not True:
            raise RuntimeError("exact scorer self-check failed")
        if strict_score(q["answer"] + ".", q["answer"]) is True:
            raise RuntimeError("exact scorer accepted non-exact answer")
    oracle = subprocess.run([sys.executable, str(TASK / "fixtures/validate_questions.py")],
                            capture_output=True, text=True, timeout=10)
    if oracle.returncode:
        raise RuntimeError("fixture oracle validation failed: " + oracle.stdout + oracle.stderr)
    return source, questions


def verify_artifacts() -> dict:
    profile_prereg = json.loads(RECEIPT.read_text(encoding="utf-8"))
    attempt06_receipt = TASK / "receipts/amendment-06-startup-timeout-preregistration.json"
    attempt05_receipt = TASK / "receipts/amendment-05-astra-config-log-parent.json"
    attempt04_receipt = TASK / "receipts/amendment-04-runner-prereg-name-fix.json"
    attempt02_receipt = TASK / "receipts/amendment-02-attempt02-log-directory-fix.json"
    pin_receipt = next((p for p in (attempt06_receipt, attempt05_receipt, attempt04_receipt, attempt02_receipt) if p.exists()), None)
    pin_prereg = json.loads(pin_receipt.read_text(encoding="utf-8")) if pin_receipt else profile_prereg
    control, candidate = profile_prereg["profiles"]
    checks = {}
    for pin_key in ("runner", "staticVerifier"):
        pin = pin_prereg.get(pin_key, profile_prereg.get(pin_key, {}))
        pinned_path = ROOT / pin.get("path", "")
        if not pinned_path.is_file() or sha_file(pinned_path) != pin.get("sha256"):
            raise RuntimeError(f"pinned Q138 {pin_key} missing or hash mismatch")
    for profile in (control, candidate):
        engine = Path(profile["enginePath"])
        if not engine.is_file() or sha_file(engine) != profile["engineSha256"]:
            raise RuntimeError("pinned inference engine missing or hash mismatch: " + str(engine))
    if sha_file(Path(control["serverPath"])) != control["serverSha256"]:
        raise RuntimeError("pinned Strata server.py hash mismatch")
    for model, expected in zip(control["modelPaths"], control["modelSha256"]):
        if sha_file(Path(model)) != expected:
            raise RuntimeError("ASTRA model shard hash mismatch: " + model)
    pack_sha, pack_files, pack_bytes = tree_sha(Path(control["strataPack"]))
    if pack_sha != control["strataPackManifestSha256"]:
        raise RuntimeError("ASTRA pack manifest hash mismatch")
    expert = Path(control["expertProfile"])
    if sha_file(expert) != control["expertProfileSha256"]:
        raise RuntimeError("Strata expert-profile hash mismatch")
    mtp_sha, mtp_files, mtp_bytes = tree_sha(Path(control["mtp"]["path"]))
    if mtp_sha != control["mtp"]["manifestSha256"]:
        raise RuntimeError("ASTRA MTP manifest hash mismatch")
    if sha_file(Path(candidate["modelPath"])) != candidate["modelSha256"]:
        raise RuntimeError("Qwen Q4 model hash mismatch")
    if sha_file(ROOT / candidate["chatTemplatePath"]) != candidate["chatTemplateSha256"]:
        raise RuntimeError("Qwen chat-template hash mismatch")
    config = Path(control["resolvedConfigPath"])
    if not config.is_absolute():
        config = ROOT / config
    if sha_file(config) != control["resolvedConfigSha256"]:
        raise RuntimeError("dedicated ASTRA profile config hash mismatch")
    q127 = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-127"
    guard_files = {
        q127 / "scripts/q117_pressure_guard_attempt05.py": profile_prereg["guard"]["sha256"],
        q127 / "guard_sources/q108_guard_core.py": profile_prereg["guard"]["coreSha256"],
        q127 / "guard_sources/q116_composite_psi.py": profile_prereg["guard"]["psiHelperSha256"],
    }
    for path, expected in guard_files.items():
        if sha_file(path) != expected:
            raise RuntimeError("pinned AMD05 guard dependency hash mismatch: " + str(path))
    checks.update({"astraPack": {"sha256": pack_sha, "files": pack_files, "bytes": pack_bytes},
                   "astraMtp": {"sha256": mtp_sha, "files": mtp_files, "bytes": mtp_bytes},
                   "allModelRuntimeAndPromptPinsMatched": True})
    return checks


def detect_external_servers() -> dict:
    processes = proc_commands()
    containers = container_servers()
    if processes or containers:
        raise RuntimeError("an inference server is already active; no model was started")
    return {"processes": processes, "containers": containers}


def systemd_help_check() -> dict:
    qwen = json.loads(RECEIPT.read_text(encoding="utf-8"))["profiles"][1]
    help_result = subprocess.run([qwen["enginePath"], "--help"], capture_output=True,
                                 text=True, timeout=25)
    help_text = help_result.stdout + help_result.stderr
    needed = ("--temp", "--top-p", "--top-k", "--min-p", "--repeat-penalty", "--presence-penalty", "--n-predict")
    missing = [item for item in needed if item not in help_text]
    if help_result.returncode or missing:
        raise RuntimeError("llama.cpp CLI option preflight failed: " + repr(missing))
    return {"llamaHelpExit": help_result.returncode, "requiredSamplerFlagsPresent": not missing}


def preflight(require_service: bool = True) -> dict:
    check_lock()
    source, questions = verify_fixture()
    artifact_pins = verify_artifacts()
    runtime_help = systemd_help_check()
    external = detect_external_servers()
    occupied = listeners()
    if occupied:
        raise RuntimeError("Q138 server port already has a listener: " + repr(occupied))
    mem = meminfo()
    pressure = psi()
    gpus = gpu_rows()
    if len(gpus) != 2 or [row["index"] for row in gpus] != [0, 1]:
        raise RuntimeError("Q138 requires both RTX 3090 devices")
    if any(row["temperatureC"] >= 80 or row["memoryFreeMiB"] < 20 * 1024 for row in gpus):
        raise RuntimeError("GPU temperature/free-VRAM preflight did not pass")
    if mem["MemAvailable"] < 88 * GIB or mem["SwapFree"] < GIB:
        raise RuntimeError("host RAM/swap preflight did not pass")
    if max(pressure["some"]["avg10"], pressure["full"]["avg10"]) >= 20.0:
        raise RuntimeError("host memory PSI is already elevated")
    cg = verify_uncapped_cgroup()
    rel = cg["workerCgroup"]
    if require_service and "llamacode-q138-profile-ab.service" not in rel:
        raise RuntimeError("campaign runner is not inside its detached Q138 systemd unit")
    result = {"atUtc": utc(), "gatePassed": True, "taskId": "Q-20261026-VF-ITERATION-138",
              "lockToken": TOKEN, "fixtureQuestionCount": len(questions),
              "decompilationSha256": "fd64ae63b1e0add2a1f842e349a6cfc54a8f3b841e69a1a34bd9af190337cadd",
              "sourceCharacters": len(source), "artifactPins": artifact_pins, "runtimeHelp": runtime_help,
              "externalInferenceServers": external, "taskPorts": {str(k): "free" for k in PORTS},
              "meminfo": mem, "memoryPsi": pressure, "gpus": gpus, "workerIsolation": cg,
              "noHostMemoryOrSwapCaps": True, "guiProcessesTerminated": False}
    write_json(TASK / "receipts/preflight-final.json", result)
    return result


def cgroup_snapshot(path: Path) -> dict:
    events = {}
    for line in (path / "memory.events").read_text().splitlines():
        key, value = line.split()
        events[key] = int(value)
    psi_rows = {}
    for line in (path / "memory.pressure").read_text().splitlines():
        fields = line.split()
        if fields and fields[0] in ("some", "full"):
            metrics = dict(x.split("=", 1) for x in fields[1:] if "=" in x)
            psi_rows[fields[0]] = {"avg10": float(metrics["avg10"])}
    return {"memory_current_bytes": int((path / "memory.current").read_text()),
            "memory_peak_bytes": int((path / "memory.peak").read_text()),
            "memory_swap_current_bytes": int((path / "memory.swap.current").read_text()),
            "memory_events": events, "psi": psi_rows}


class Monitor:
    def __init__(self, path: Path):
        sys.path.insert(0, str(ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-127/scripts"))
        import q117_pressure_guard_attempt05 as guard
        self.guard = guard
        self.path = path
        self.cgroup = cgroup_path()
        self.host_baseline = self.guard.read_sample()
        self.worker_baseline = cgroup_snapshot(self.cgroup)
        self.counters = self.guard.initial_counts()
        self.stop_event = threading.Event()
        self.abort_reason = None
        self.proc = None
        self.rows = 0
        self.thread = threading.Thread(target=self._run, name="q138-amd05-monitor", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def set_proc(self, proc) -> None:
        self.proc = proc

    def _stop_owned_server(self, reason: str) -> None:
        proc = self.proc
        if proc is None:
            return
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        except OSError:
            return

    def _run(self) -> None:
        while not self.stop_event.wait(1.0):
            stamp = {"atUtc": utc()}
            try:
                host = self.guard.read_sample()
                reason, self.counters, warning = self.guard.evaluate(
                    host, self.host_baseline["oomKill"], self.counters)
                worker = cgroup_snapshot(self.cgroup)
                worker_reason, worker_psi, swap_delta = self.guard.evaluate_worker_cgroup(
                    worker, self.worker_baseline["memory_events"],
                    self.worker_baseline["memory_swap_current_bytes"])
                gpus = gpu_rows()
                if any(row["temperatureC"] >= 85 for row in gpus):
                    reason = reason or "RTX 3090 reached 85 C"
                stamp.update({"host": host, "hostWarning": warning, "worker": worker,
                              "workerPsiDiagnostic": worker_psi, "workerSwapDeltaBytes": swap_delta,
                              "gpus": gpus, "warning": warning})
                self.rows += 1
                append_jsonl(self.path, stamp)
                reason = reason or worker_reason
                if reason:
                    self.abort_reason = reason
                    self._stop_owned_server(reason)
                    return
            except BaseException as exc:
                self.abort_reason = "telemetry failure: " + type(exc).__name__ + ": " + str(exc)
                stamp["error"] = self.abort_reason
                try:
                    append_jsonl(self.path, stamp)
                finally:
                    self._stop_owned_server(self.abort_reason)
                return

    def close(self) -> None:
        self.stop_event.set()
        if self.thread.ident is not None:
            self.thread.join(timeout=5)


def ensure_astra_engine_log_parent(profile: dict) -> Path:
    config_path = Path(profile["resolvedConfigPath"])
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if not config.get("log"):
        raise RuntimeError("pinned ASTRA config has no engine log path")
    engine_log = Path(config["log"])
    if not engine_log.is_absolute():
        engine_log = Path(profile["cwd"]) / engine_log
    engine_log = engine_log.resolve()
    if TASK.resolve() not in engine_log.parents:
        raise RuntimeError("configured ASTRA engine log escaped the Q138 task directory")
    engine_log.parent.mkdir(parents=True, exist_ok=True)
    return engine_log


def server_process(profile: dict, log_path: Path):
    env = os.environ.copy()
    env.update(profile["environment"])
    env["CUDA_VISIBLE_DEVICES"] = "0,1"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    output = log_path.open("w", encoding="utf-8")
    if profile["name"].startswith("ASTRA"):
        ensure_astra_engine_log_parent(profile)
        return subprocess.Popen(profile["serverCommand"], cwd=profile["cwd"], env=env,
                                stdout=output, stderr=subprocess.STDOUT, text=True,
                                start_new_session=True), output
    args = profile["serverArgs"]
    command = [profile["enginePath"], *args]
    return subprocess.Popen(command, cwd=str(ROOT), env=env, stdout=output,
                            stderr=subprocess.STDOUT, text=True, start_new_session=True), output


def wait_ready(proc, profile: dict, log_path: Path, timeout: int = 1800) -> tuple[str, float]:
    port = profile["port"]
    start = time.monotonic()
    deadline = start + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            tail = log_path.read_text(errors="replace")[-3000:] if log_path.exists() else ""
            raise RuntimeError(f"inference server exited during startup ({proc.returncode}): {tail}")
        try:
            with urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=3) as response:
                data = json.loads(response.read().decode())
                ids = [row.get("id") for row in data.get("data", [])]
                if response.status == 200 and ids:
                    return ids[0], time.monotonic() - start
        except Exception:
            pass
        time.sleep(0.5)
    tail = log_path.read_text(errors="replace")[-5000:] if log_path.exists() else "<server log missing>"
    raise TimeoutError(f"server did not become healthy on 127.0.0.1:{port} within {timeout}s; log tail:\n{tail}")


def stop_server(proc, log_path: Path, output) -> dict:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=10)
    if not output.closed:
        output.flush()
        output.close()
    time.sleep(1)
    try:
        os.killpg(proc.pid, 0)
        group_alive = True
    except ProcessLookupError:
        group_alive = False
    if group_alive:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        time.sleep(0.5)
        try:
            os.killpg(proc.pid, 0)
            group_alive = True
        except ProcessLookupError:
            group_alive = False
    ports = listeners()
    own_port = next((p for p in PORTS if ports.get(p)), None)
    return {"pid": proc.pid, "exitCode": proc.returncode, "processGroupAlive": group_alive,
            "listenersAfterStop": ports, "clean": not group_alive and own_port is None}


def post_chat(port: int, model_id: str, messages: list[dict], seed: int) -> dict:
    body = {"model": model_id, "messages": messages, "max_tokens": 1024,
            "temperature": 0.6, "top_p": 0.95, "top_k": 20, "min_p": 0.0,
            "repeat_penalty": 1.0, "presence_penalty": 0.0,
            "seed": seed, "cache_prompt": False, "stream": False}
    request = Request(f"http://127.0.0.1:{port}/v1/chat/completions",
                      data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
    started = time.monotonic()
    try:
        with urlopen(request, timeout=240) as response:
            raw = response.read().decode("utf-8", errors="replace")
            status = response.status
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        status = exc.code
    except (URLError, TimeoutError, socket.timeout) as exc:
        return {"httpStatus": None, "transportError": type(exc).__name__ + ": " + str(exc),
                "requestWallSeconds": time.monotonic() - started}
    elapsed = time.monotonic() - started
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"httpStatus": status, "transportError": "non-JSON API response", "rawResponse": raw[:3000],
                "requestWallSeconds": elapsed}
    choices = data.get("choices", [])
    message = choices[0].get("message", {}) if choices else {}
    content = message.get("content") or ""
    usage = data.get("usage", {})
    timings = data.get("timings", {})
    return {"httpStatus": status, "transportError": None, "rawResponse": data,
            "content": content, "finishReason": choices[0].get("finish_reason") if choices else None,
            "usage": usage, "timings": timings, "requestWallSeconds": elapsed}


def run_campaign(attempt_name: str) -> int:
    if attempt_name != "attempt05":
        raise RuntimeError("Q138 accepts only the preregistered attempt05 campaign")
    attempt = TASK / "runs" / attempt_name
    progress_path = TASK / "receipts" / f"campaign-{attempt_name}-progress.json"
    final_path = TASK / "receipts" / f"campaign-{attempt_name}-final.json"
    rows_path = attempt / "responses.jsonl"
    logs = attempt / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    status = "FAILED"
    error = None
    monitor = None
    completed = 0
    profile_results = []
    server_started = False
    try:
        check_lock()
        prior = json.loads(progress_path.read_text()) if progress_path.exists() else None
        if prior or final_path.exists() or rows_path.exists():
            raise RuntimeError("Q138 campaign already has progress; automatic retry is disabled")
        gates = preflight(require_service=True)
        write_json(TASK / "receipts/preflight-attempt05.json", gates)
        write_json(progress_path, {"taskId": "Q-20261026-VF-ITERATION-138", "status": "preflight_passed",
                                   "atUtc": utc(), "completedRequests": 0, "expectedRequests": 72,
                                   "preflightReceipt": "receipts/preflight-attempt05.json"})
        source, questions = verify_fixture()
        amendment = json.loads(RECEIPT.read_text(encoding="utf-8"))
        profiles = amendment["profiles"]
        monitor = Monitor(attempt / "resource-monitor.jsonl")
        monitor.start()
        for profile in profiles:
            check_lock()
            if monitor.abort_reason:
                raise RuntimeError("AMD05 aborted before profile start: " + monitor.abort_reason)
            external = detect_external_servers()
            if external["processes"] or external["containers"]:
                raise RuntimeError("external inference server appeared between profile blocks")
            port = profile["port"]
            check_port(port)
            log_path = logs / ("astra-strata.log" if profile["name"].startswith("ASTRA") else "qwen-llama-server.log")
            before = {"meminfo": meminfo(), "gpus": gpu_rows(), "atUtc": utc()}
            proc, output = server_process(profile, log_path)
            server_started = True
            monitor.set_proc(proc)
            try:
                model_id, startup_seconds = wait_ready(proc, profile, log_path)
                for seed in (4242, 5051, 6061):
                    seed_rows = []
                    for question in questions:
                        if monitor.abort_reason:
                            raise RuntimeError("AMD05 stopped the profile: " + monitor.abort_reason)
                        messages, prompt_sha = assembled_prompt(question, source)
                        response = post_chat(port, model_id, messages, seed)
                        answer = question["answer"]
                        content = response.get("content", "")
                        row = {"profile": profile["name"], "questionId": question["id"], "seed": seed,
                               "promptSha256": prompt_sha, "expected": answer,
                               "response": response, "exactMatch": strict_score(content, answer),
                               "atUtc": utc()}
                        append_jsonl(rows_path, row)
                        completed += 1
                        seed_rows.append(row)
                        write_json(progress_path, {"taskId": "Q-20261026-VF-ITERATION-138",
                                                   "status": "running", "atUtc": utc(),
                                                   "completedRequests": completed, "expectedRequests": 72,
                                                   "activeProfile": profile["name"], "activeSeed": seed,
                                                   "activeQuestion": question["id"], "amd05Abort": monitor.abort_reason})
                        if response.get("httpStatus") != 200 or response.get("transportError"):
                            raise RuntimeError(f"invalid HTTP response for {profile['name']} {question['id']} seed {seed}")
                    correct = sum(row["exactMatch"] for row in seed_rows)
                    write_json(attempt / ("astra" if profile["name"].startswith("ASTRA") else "qwen") /
                               f"seed-{seed}-summary.json", {"profile": profile["name"], "seed": seed,
                               "correct": correct, "total": len(seed_rows), "accuracy": correct / len(seed_rows)})
                stop = stop_server(proc, log_path, output)
                server_started = False
                monitor.set_proc(None)
                if not stop["clean"]:
                    raise RuntimeError("profile process or TCP listener remained after cleanup")
                profile_results.append({"profile": profile["name"], "modelId": model_id,
                                        "startupSeconds": startup_seconds, "before": before, "stop": stop})
                write_json(progress_path, {"taskId": "Q-20261026-VF-ITERATION-138", "status": "profile_complete",
                                           "atUtc": utc(), "completedRequests": completed,
                                           "expectedRequests": 72, "lastProfile": profile["name"],
                                           "profileResults": profile_results, "amd05Samples": monitor.rows})
            except BaseException:
                stop = stop_server(proc, log_path, output)
                server_started = False
                monitor.set_proc(None)
                raise
        if completed != 72:
            raise RuntimeError(f"campaign ended with {completed}/72 responses")
        status = "PASS"
    except BaseException as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        if monitor is not None:
            monitor.close()
        if server_started:
            error = error or {"type": "CleanupError", "message": "owned inference server still marked active"}
            status = "FAILED"
        final = {"taskId": "Q-20261026-VF-ITERATION-138", "status": status, "error": error,
                 "completedRequests": completed, "expectedRequests": 72,
                 "profileResults": profile_results,
                 "monitor": {"samples": monitor.rows if monitor else 0,
                             "abortReason": monitor.abort_reason if monitor else None},
                 "noHostMemoryOrSwapCaps": True, "noGUIProcessesTerminated": True,
                 "noProductionProfilesChanged": True,
                 "preflightReceipt": "receipts/preflight-attempt05.json", "atUtc": utc()}
        write_json(final_path, final)
        write_json(progress_path, {"taskId": "Q-20261026-VF-ITERATION-138", "attempt": attempt_name, "status": status,
                                   "atUtc": utc(), "completedRequests": completed,
                                   "expectedRequests": 72, "finalReceipt": f"receipts/campaign-{attempt_name}-final.json",
                                   "error": error})
    return 0 if status == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--attempt", choices=("attempt05",), default="attempt05")
    args = parser.parse_args()
    if args.preflight_only == args.run:
        parser.error("choose exactly one of --preflight-only or --run")
    if args.preflight_only:
        result = preflight(require_service=False)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    return run_campaign(args.attempt)


if __name__ == "__main__":
    raise SystemExit(main())
