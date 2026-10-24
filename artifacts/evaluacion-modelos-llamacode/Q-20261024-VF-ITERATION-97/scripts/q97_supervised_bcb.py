#!/usr/bin/env python3
"""Run the preregistered Q97 screen inside its transient systemd user unit."""
from __future__ import annotations

import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-97"
PREREG = TASK / "receipts/q97-preregistration.json"
FIXTURE = ROOT / "artifacts/bigcodebench-hard-ubuntu-8.json"
RUNNER = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-89/scripts/q89_run_bcb.py"
ASTRA_CFG = TASK / "configs/astra-q97-short-context.json"
STATE = TASK / "runs/state.json"
SAMPLES = TASK / "runs/host-samples.jsonl"
STOP = None
OWNED = []


class GateStop(RuntimeError):
    pass


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def mem_available_gib() -> float:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / 1024 / 1024
    raise RuntimeError("MemAvailable missing")


def psi_avg10():
    values = {}
    for line in Path("/proc/pressure/memory").read_text().splitlines():
        fields = line.split()
        if fields and fields[0] in ("some", "full"):
            values[fields[0]] = float(next(x.split("=", 1)[1] for x in fields if x.startswith("avg10=")))
    if set(values) != {"some", "full"}:
        raise RuntimeError("memory PSI some/full unavailable")
    return values


def service_cgroup_memory_psi_avg10():
    """Read memory PSI scoped to this transient unit; diagnostic only in Q97."""
    for line in Path("/proc/self/cgroup").read_text().splitlines():
        if line.startswith("0::"):
            path = Path("/sys/fs/cgroup") / line[3:].lstrip("/") / "memory.pressure"
            if not path.exists():
                return None
            values = {}
            for row in path.read_text().splitlines():
                fields = row.split()
                if fields and fields[0] in ("some", "full"):
                    values[fields[0]] = float(next(x.split("=", 1)[1] for x in fields if x.startswith("avg10=")))
            return values if set(values) == {"some", "full"} else None
    return None


def oom_snapshot():
    vm = {}
    for line in Path("/proc/vmstat").read_text().splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[0] in ("oom_kill",):
            vm[fields[0]] = int(fields[1])
    cg = {}
    for line in Path("/proc/self/cgroup").read_text().splitlines():
        if line.startswith("0::"):
            cgpath = Path("/sys/fs/cgroup") / line[3:].lstrip("/") / "memory.events"
            if cgpath.exists():
                cg = {k: int(v) for k, v in (row.split() for row in cgpath.read_text().splitlines())}
            break
    return {"global": vm, "cgroup": cg}


def gpu_snapshot():
    res = subprocess.run(
        ["nvidia-smi", "--query-gpu=index,name,uuid,memory.total,memory.used", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, timeout=10, check=True,
    )
    rows = []
    for line in res.stdout.splitlines():
        cols = [x.strip() for x in line.split(",")]
        if len(cols) >= 5:
            rows.append({"index": int(cols[0]), "name": cols[1], "uuid": cols[2],
                         "totalMiB": int(cols[3]), "usedMiB": int(cols[4])})
    if len(rows) != 2 or [r["index"] for r in rows] != [0, 1] or any("RTX 3090" not in r["name"] for r in rows):
        raise GateStop(f"expected exactly GPU0/GPU1 RTX 3090; got {rows}")
    return rows


def record_sample(stage, oom_base):
    psi = psi_avg10()
    cgroup_psi = service_cgroup_memory_psi_avg10()
    oom = oom_snapshot()
    row = {"atUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "stage": stage,
           "memAvailableGiB": round(mem_available_gib(), 3), "memoryPsiAvg10Pct": psi,
           "serviceCgroupMemoryPsiAvg10Pct": cgroup_psi,
           "oom": oom, "gpus": gpu_snapshot()}
    counts, warning, psi_stop = pressure_gate_transition(psi, record_sample.psi_counts)
    record_sample.psi_counts = counts
    row["memoryPsiWarning"] = warning
    SAMPLES.parent.mkdir(parents=True, exist_ok=True)
    with SAMPLES.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    if row["memAvailableGiB"] < 32:
        raise GateStop("MemAvailable fell below 32 GiB")
    if psi_stop:
        raise GateStop(psi_stop)
    if oom["global"].get("oom_kill", 0) > oom_base["global"].get("oom_kill", 0):
        raise GateStop("global oom_kill counter increased")
    for key in ("oom", "oom_kill"):
        if oom["cgroup"].get(key, 0) > oom_base["cgroup"].get(key, 0):
            raise GateStop(f"service cgroup memory.events {key} counter increased")
    return row


def pressure_gate_transition(psi, previous):
    """Moderate PSI warns; only severe, historically calibrated PSI stops."""
    thresholds = {
        "warning_full20": ("full", 20.0),
        "warning_some70": ("some", 70.0),
        "severe_full60": ("full", 60.0),
        "severe_some80": ("some", 80.0),
    }
    counts = {}
    for key, (stall, limit) in thresholds.items():
        counts[key] = previous.get(key, 0) + 1 if psi[stall] >= limit else 0
    warning = counts["warning_full20"] >= 30 or counts["warning_some70"] >= 30
    stop = None
    if counts["severe_full60"] >= 15:
        stop = "global memory PSI full avg10 >=60% for 15 consecutive samples"
    elif counts["severe_some80"] >= 15:
        stop = "global memory PSI some avg10 >=80% for 15 consecutive samples"
    return counts, warning, stop


record_sample.psi_counts = {"warning_full20": 0, "warning_some70": 0, "severe_full60": 0, "severe_some80": 0}


def cgroup_memory_limits():
    for line in Path("/proc/self/cgroup").read_text().splitlines():
        if line.startswith("0::"):
            base = Path("/sys/fs/cgroup") / line[3:].lstrip("/")
            return {name: (base / name).read_text().strip() for name in ("memory.max", "memory.high", "memory.swap.max")
                    if (base / name).exists()}
    return {}


def check_small_fingerprints(prereg):
    expected = {
        str(FIXTURE): "11279cde14113fc8527f141c53e14cb5ccf0dba65749081a4f914408e391c268",
        str(RUNNER): "0760f48da5f1804d8605960b7ff913308182f911a35a906313b864a9cff9bf7f",
        str(ASTRA_CFG): prereg["comparison"]["control"]["testConfigSha256"],
        prereg["comparison"]["control"]["runtime"]: "770ecf303a4c6271654339c639392ecb455de3a999bf5d2e8dbc73c879103602",
        prereg["comparison"]["candidate"]["runtime"]: "fe8a7d6073d3e3a276193fcaec162cbf280d2572ad2016c9100fd924be19c6ed",
    }
    actual = {path: sha256(Path(path)) for path in expected}
    mismatch = {p: {"expected": v, "actual": actual[p]} for p, v in expected.items() if actual[p] != v}
    if mismatch:
        raise GateStop(f"small-file fingerprint mismatch: {mismatch}")
    return actual


def check_model_files(prereg):
    paths = [
        ("swift", prereg["comparison"]["candidate"]["model"], prereg["comparison"]["candidate"]["bytes"], prereg["comparison"]["candidate"]["sha256"]),
        ("astra-shard-1", "/media/cristian/Disco local/Models/FlashNext-IQ2XS-ISTA-Strata-eval-20261012/IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf", 39225954592, "92cee27ae5bbadcd732416a0f7a7f0acc092399dbbe8f5a5efa707c2ec0a49d7"),
        ("astra-shard-2", "/media/cristian/Disco local/Models/FlashNext-IQ2XS-ISTA-Strata-eval-20261012/IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00002-of-00002.gguf", 28800138432, "316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113"),
        ("astra-pack", "/media/cristian/Disco local/Models/FlashNext-IQ2XS-ISTA-Strata-eval-20261012/strata-data/packs/iq2_xs/dense.bin", 1538035200, "d2af3d8331e5c7a1985d1d589747230f9d56719a6d33c7cddc9ee6b81cde6b13"),
        ("astra-expert-profile", "/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source/data/expert-profile.bin", 0, "8f59b4aa8873209dff11c11e37bcda9529a1335b724a1afeea37bf6388975baf"),
        ("mtp-dense", "/media/cristian/Disco local/Models/FlashNext-IQ3XXS-ISTA-Strata-eval-20261009/strata-data/mtp/rt/dense.bin", 0, "c724dc0b0822ada5d2977bf5bde821605feabaa64ea2e0045b67ca656329070a"),
        ("mtp-dense-txt", "/media/cristian/Disco local/Models/FlashNext-IQ3XXS-ISTA-Strata-eval-20261009/strata-data/mtp/rt/dense.txt", 0, "991456cf4eb266eb8a888c349e548d11bc640f5dbd9149439aa9786af0f732fd"),
        ("mtp-draft-vocab", "/media/cristian/Disco local/Models/FlashNext-IQ3XXS-ISTA-Strata-eval-20261009/strata-data/mtp/rt/draft_vocab.bin", 0, "b1e1d3a7a9e4bf862dcd5923ce661fb59bbd07907e594df5cf86a62ac235cb91"),
        ("mtp-experts", "/media/cristian/Disco local/Models/FlashNext-IQ3XXS-ISTA-Strata-eval-20261009/strata-data/mtp/rt/experts.bin", 0, "09398406be61f1f54c93861f449e48b8df0bfccbc9ec9b2b7636775a6ea9244f"),
    ]
    out = {}
    for name, path, size, expected_sha in paths:
        st = Path(path).stat()
        if size and st.st_size != size:
            raise GateStop(f"model asset size mismatch: {name} expected {size}, got {st.st_size}")
        out[name] = {"path": path, "bytes": st.st_size, "device": st.st_dev, "inode": st.st_ino,
                     "mtimeNs": st.st_mtime_ns, "sha256Expected": expected_sha}
    return out


def verify_large_fingerprints(prereg, oom_base):
    """Hash pinned model artifacts under the transient service's low I/O priority."""
    snapshot = check_model_files(prereg)
    verified = {}
    for name, entry in snapshot.items():
        proc = subprocess.Popen(["sha256sum", entry["path"]], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, start_new_session=True)
        OWNED.append(proc)
        try:
            while proc.poll() is None:
                check_gates(f"fingerprint_{name}", oom_base)
                time.sleep(1)
            stdout, stderr = proc.communicate(timeout=3)
            if proc.returncode != 0:
                raise GateStop(f"sha256sum failed for {name}: {stderr[-500:]}")
            actual = stdout.split()[0]
            if actual != entry["sha256Expected"]:
                raise GateStop(f"SHA-256 mismatch for {name}: expected {entry['sha256Expected']}, got {actual}")
            verified[name] = {**entry, "sha256": actual}
        finally:
            if proc.poll() is None:
                terminate_group(proc)
            OWNED.remove(proc)
    return verified


def listening(port):
    with socket.socket() as s:
        s.settimeout(0.25)
        return s.connect_ex(("127.0.0.1", port)) == 0


def external_inference_processes(owned_pids=frozenset()):
    result = subprocess.run(["ps", "-eo", "pid=,args="], capture_output=True, text=True, check=True)
    patterns = ("llama-server", "vllm serve", "ollama serve", "mlx_lm.server", "sglang.launch_server")
    found = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2:
            continue
        pid, args = int(parts[0]), parts[1]
        if pid in owned_pids or pid == os.getpid():
            continue
        if any(p in args for p in patterns) or ("serve/server.py" in args and "--engine strata" in args):
            found.append({"pid": pid, "command": args[:500]})
    return found


def process_tree_pids(root_pid):
    rows = subprocess.run(["ps", "-eo", "pid=,ppid="], capture_output=True, text=True, check=True).stdout.splitlines()
    children = {}
    for line in rows:
        p, parent = (int(x) for x in line.split())
        children.setdefault(parent, []).append(p)
    found = {root_pid}
    todo = [root_pid]
    while todo:
        for child in children.get(todo.pop(), []):
            if child not in found:
                found.add(child); todo.append(child)
    return found


def compute_app_uuids():
    p = subprocess.run(["nvidia-smi", "--query-compute-apps=gpu_uuid,pid,used_gpu_memory", "--format=csv,noheader,nounits"],
                       capture_output=True, text=True, timeout=10, check=True)
    rows = []
    for line in p.stdout.splitlines():
        cols = [x.strip() for x in line.split(",")]
        if len(cols) >= 2:
            try:
                rows.append({"uuid": cols[0], "pid": int(cols[1]), "usedMiB": int(cols[2]) if len(cols) > 2 and cols[2].isdigit() else None})
            except ValueError:
                continue
    return rows


def verify_dual_gpu_allocation(server_pid, gpus_before):
    owned = process_tree_pids(server_pid)
    apps = compute_app_uuids()
    gpus = gpu_snapshot()
    by_index = {g["index"]: g for g in gpus}
    before = {g["index"]: g["usedMiB"] for g in gpus_before}
    deltas = {i: by_index[i]["usedMiB"] - before[i] for i in (0, 1)}
    app_pids = {g["uuid"]: sorted({a["pid"] for a in apps if a["uuid"] == g["uuid"]}) for g in gpus}
    owned_on = {g["index"]: bool(owned.intersection(app_pids[g["uuid"]])) for g in gpus}
    if not all(owned_on.values()) or not all(deltas[i] >= 512 for i in (0, 1)):
        raise GateStop(f"dual GPU allocation not confirmed by owned compute process on both GPUs; pids={owned_on}, memoryDeltaMiB={deltas}, owned={sorted(owned)}")
    return {"ownedComputeProcessOnBothGpus": owned_on, "memoryDeltaMiB": deltas,
            "computeApps": apps, "ownedPids": sorted(owned)}


def terminate_group(proc):
    if proc is None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=5)


def health_ok(url):
    try:
        with urllib.request.urlopen(url, timeout=1) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def signal_handler(signum, _frame):
    global STOP
    STOP = f"received signal {signum}"


def write_state(state, **updates):
    state.update(updates)
    atomic_json(STATE, state)


def check_gates(stage, oom_base, baseline=False):
    row = record_sample(stage, oom_base)
    if baseline and (row["memoryPsiAvg10Pct"]["some"] >= 5 or row["memoryPsiAvg10Pct"]["full"] >= 5):
        raise GateStop("baseline memory PSI some/full avg10 is not below 5%")
    return row


def wait_health(proc, url, stage, oom_base, timeout_sec=1200):
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if STOP:
            raise GateStop(STOP)
        check_gates(stage, oom_base)
        if proc.poll() is not None:
            raise GateStop(f"server exited before health (exit={proc.returncode})")
        if health_ok(url):
            return
        time.sleep(1)
    raise GateStop("server health timeout (1200 s)")


def run_runner(proc, stage, oom_base):
    while proc.poll() is None:
        if STOP:
            raise GateStop(STOP)
        check_gates(stage, oom_base)
        time.sleep(1)
    if proc.returncode != 0:
        raise GateStop(f"fixed BCB runner exited {proc.returncode}")


def run():
    global OWNED
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, signal_handler)
    prereg = json.loads(PREREG.read_text())
    state = {"taskId": prereg["taskId"], "experimentId": prereg["experimentId"], "status": "starting",
             "startedAtUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "arms": [],
             "memoryLimits": cgroup_memory_limits()}
    write_state(state)
    if any(v != "max" for v in state["memoryLimits"].values()):
        raise GateStop(f"unexpected cgroup memory limit(s): {state['memoryLimits']}")
    hashes = check_small_fingerprints(prereg)
    gpus = gpu_snapshot()
    oom_base = oom_snapshot()
    baseline = check_gates("baseline", oom_base, baseline=True)
    if baseline["memAvailableGiB"] < 32:
        raise GateStop("baseline MemAvailable below 32 GiB")
    if external_inference_processes():
        raise GateStop(f"external inference process detected: {external_inference_processes()}")
    for port in (8363, 18789):
        if listening(port):
            raise GateStop(f"candidate port {port} is already listening")
    write_state(state, status="verifying_model_fingerprints", fingerprints=hashes,
                gpuBaseline=gpus, memAvailableBaselineGiB=baseline["memAvailableGiB"],
                memoryPsiBaseline=baseline["memoryPsiAvg10Pct"], memoryLimits=state["memoryLimits"])
    assets = verify_large_fingerprints(prereg, oom_base)
    write_state(state, status="preflight_pass", fingerprints=hashes, modelAssetFingerprints=assets,
                gpuBaseline=gpus, memAvailableBaselineGiB=baseline["memAvailableGiB"],
                memoryPsiBaseline=baseline["memoryPsiAvg10Pct"], memoryLimits=state["memoryLimits"])

    python = "/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source/.venv/bin/python"
    strata_root = "/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source"
    strata_server = f"{strata_root}/serve/server.py"
    swift_runtime = prereg["comparison"]["candidate"]["runtime"]
    swift_model = prereg["comparison"]["candidate"]["model"]
    arms = [
        {"arm": "astra", "port": 8363, "model": "q97-astra-flash-next-iq2_xs",
         "url": "http://127.0.0.1:8363/v1/chat/completions",
         "command": [python, strata_server, "--engine", "strata", "--config", str(ASTRA_CFG), "--host", "127.0.0.1", "--port", "8363", "--gpu", "0,1"],
         "cwd": strata_root},
        {"arm": "swift", "port": 18789, "model": "q97-swift-qwen38-27b",
         "url": "http://127.0.0.1:18789/v1/chat/completions",
         "command": [swift_runtime, "--model", swift_model, "--host", "127.0.0.1", "--port", "18789", "--ctx-size", "8192",
                     "--gpu-layers", "999", "--split-mode", "tensor", "--tensor-split", "1,1", "--cache-type-k", "q8_0",
                     "--cache-type-v", "q8_0", "--parallel", "1", "--seed", "4242", "--temp", "0.6", "--top-p", "0.95",
                     "--top-k", "20", "--min-p", "0", "--repeat-penalty", "1", "--presence-penalty", "0", "--reasoning", "on",
                     "--reasoning-budget", "2048", "--chat-template-kwargs", "{\"enable_thinking\":true}", "--no-webui"],
         "cwd": str(Path(swift_runtime).parent)},
    ]
    failure = None
    try:
        for index, arm in enumerate(arms):
            if STOP:
                raise GateStop(STOP)
            current_gpus = gpu_snapshot()
            check_gates(f"{arm['arm']}_baseline", oom_base, baseline=True)
            if external_inference_processes():
                raise GateStop("external inference process detected before arm start")
            if listening(arm["port"]):
                raise GateStop(f"port {arm['port']} unexpectedly occupied before arm")
            arm_dir = TASK / "runs" / arm["arm"]
            arm_dir.mkdir(parents=True, exist_ok=True)
            server_log = (arm_dir / "server.log").open("w")
            env = os.environ.copy()
            env["CUDA_VISIBLE_DEVICES"] = "0,1"
            env["STRATA_PREFILL_CPU_SHARE"] = "0"
            state_row = {"arm": arm["arm"], "status": "starting", "port": arm["port"], "gpuIndices": [0, 1],
                         "startedAtUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            state["arms"].append(state_row)
            write_state(state, status="running_arm", currentArm=arm["arm"])
            server = subprocess.Popen(arm["command"], cwd=arm["cwd"], env=env, stdout=server_log,
                                      stderr=subprocess.STDOUT, start_new_session=True)
            OWNED.append(server)
            try:
                wait_health(server, f"http://127.0.0.1:{arm['port']}/health", f"{arm['arm']}_loading", oom_base)
                dual = verify_dual_gpu_allocation(server.pid, current_gpus)
                state_row["dualGpuAllocation"] = dual
                state_row["status"] = "healthy_dual_gpu"
                write_state(state)
                out = arm_dir / "bcb8-result.json"
                runner_log = (arm_dir / "runner.log").open("w")
                runner_cmd = [sys.executable, str(RUNNER), "--url", arm["url"], "--arm", arm["arm"], "--seed", "4242",
                              "--model", arm["model"], "--out", str(out), "--budget", "2048", "--max-tokens", "6144"]
                runner = subprocess.Popen(runner_cmd, cwd=ROOT, env=env, stdout=runner_log, stderr=subprocess.STDOUT,
                                          start_new_session=True)
                OWNED.append(runner)
                state_row["runnerStartedAtUtc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                write_state(state)
                run_runner(runner, f"{arm['arm']}_requests", oom_base)
                runner_log.close()
                OWNED.remove(runner)
                result = json.loads(out.read_text())
                state_row["result"] = {k: result.get(k) for k in ("runs", "transportOk", "passed", "sandboxErrors", "noFinalContent")}
                state_row["status"] = "complete"
                state_row["finishedAtUtc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                write_state(state)
            finally:
                terminate_group(server)
                server_log.close()
                OWNED.remove(server)
            for _ in range(20):
                if not listening(arm["port"]):
                    break
                time.sleep(0.5)
            if listening(arm["port"]):
                raise GateStop(f"port {arm['port']} did not release after owned server shutdown")
            if external_inference_processes():
                raise GateStop("inference process remains after arm cleanup")
            state_row["cleanup"] = "server stopped; port free; no inference server process detected"
            write_state(state)
        state["status"] = "complete"
        state["completedAtUtc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    except Exception as exc:
        failure = f"{type(exc).__name__}: {exc}"
        for proc in list(OWNED):
            terminate_group(proc)
        state["status"] = "aborted_or_failed"
        state["failure"] = failure
        state["completedAtUtc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    finally:
        write_state(state, failure=failure)
    return 1 if failure else 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except Exception as exc:
        atomic_json(STATE, {"taskId": "Q-20261024-VF-ITERATION-97", "status": "failed_before_arm",
                            "failure": f"{type(exc).__name__}: {exc}",
                            "atUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        raise
