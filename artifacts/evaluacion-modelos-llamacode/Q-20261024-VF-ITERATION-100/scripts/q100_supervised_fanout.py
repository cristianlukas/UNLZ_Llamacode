#!/usr/bin/env python3
"""Own and supervise the preregistered Q100 two-GPU agent fan-out screen."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from q100_tool_guard_state import clear_proxy_log, first_blocked_tool_call

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-100"
TOKEN = "fa90d45b-84a6-4679-9771-bad06cdb16a5"
PREREG = TASK / "receipts/q100-preregistration.json"
AMENDMENT = TASK / "receipts/q100-amendment-006.json"
CONFIG = TASK / "configs/astra-q100-parallel2-64k.json"
Q97_HELPER = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-97/scripts/q97_supervised_bcb.py"
Q97_ASSETS = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-97/receipts/q97-fingerprint-prelaunch.json"
Q99_RUNTIME_SHA256 = "770ecf303a4c6271654339c639392ecb455de3a999bf5d2e8dbc73c879103602"
STRATA_ROOT = Path("/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source")
STRATA_PYTHON = STRATA_ROOT / ".venv/bin/python"
STRATA_SERVER = STRATA_ROOT / "serve/server.py"
PROXY = TASK / "scripts/q100_tool_guard_proxy.py"
PROXY_TEST = TASK / "scripts/test_q100_tool_guard_proxy.py"
TOOL_GUARD_STATE = TASK / "scripts/q100_tool_guard_state.py"
TOOL_GUARD_STATE_TESTS = TASK / "scripts/test_q100_tool_guard_state.py"
TEST_SOURCE = ROOT / "tests/test_q100_subagent_probe.cpp"
TEST_BINARY = Path("/home/cristian/.cache/llamacode/build_tests_linux/test_q100_subagent_probe")
SERVER_PORT = 8363
PROXY_PORT = 8364

spec = importlib.util.spec_from_file_location("q97_memory_supervision", Q97_HELPER)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load pinned Q97 memory guard")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
guard.TASK = TASK
guard.STATE = TASK / "runs/state.json"
guard.SAMPLES = TASK / "runs/host-samples.jsonl"
guard.STOP = None
guard.OWNED = []


class GateStop(RuntimeError):
    pass


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_lock():
    lock = json.loads((ROOT / "WORK_QUEUE.lock").read_text())
    if lock.get("task_id") != "Q-20261024-VF-ITERATION-100" or lock.get("token") != TOKEN:
        raise GateStop("Q100 no longer owns WORK_QUEUE.lock")


def verify_small_inputs(expected):
    actual = {
        "testSource": sha256(TEST_SOURCE),
        "testBinary": sha256(TEST_BINARY),
        "serverConfig": sha256(CONFIG),
        "strataRuntime": sha256(STRATA_ROOT / "engine/strata"),
        "toolGuardProxy": sha256(PROXY),
        "toolGuardProxyTests": sha256(PROXY_TEST),
        "toolGuardState": sha256(TOOL_GUARD_STATE),
        "toolGuardStateTests": sha256(TOOL_GUARD_STATE_TESTS),
        "supervisor": sha256(Path(__file__)),
        "supervisorTests": sha256(TASK / "scripts/test_q100_supervisor.py"),
        "memoryGuard": sha256(Q97_HELPER),
    }
    mismatch = {key: {"expected": expected.get(key), "actual": value}
                for key, value in actual.items() if expected.get(key) != value}
    if mismatch:
        raise GateStop(f"Q100 pinned input fingerprint mismatch: {mismatch}")
    return actual


def verify_model_assets(oom_base):
    prior = json.loads(Q97_ASSETS.read_text())
    matched = {}
    for name, entry in prior["assets"].items():
        if name == "swift":
            continue
        path = Path(entry["path"])
        stat = path.stat()
        if stat.st_size != entry["bytes"]:
            raise GateStop(f"model asset size changed: {name}")
        proc = subprocess.Popen(["ionice", "-c", "3", "sha256sum", str(path)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                start_new_session=True)
        guard.OWNED.append(proc)
        try:
            while proc.poll() is None:
                verify_lock()
                guard.check_gates(f"fingerprint_{name}", oom_base)
                time.sleep(1)
            stdout, stderr = proc.communicate(timeout=5)
            if proc.returncode != 0:
                raise GateStop(f"asset hash failed for {name}: {stderr[-500:]}")
            actual = stdout.split()[0]
            if actual != entry["sha256Expected"]:
                raise GateStop(f"asset SHA-256 mismatch for {name}: {actual}")
            matched[name] = {"path": str(path), "bytes": stat.st_size, "sha256": actual,
                             "device": stat.st_dev, "inode": stat.st_ino, "mtimeNs": stat.st_mtime_ns}
        finally:
            if proc.poll() is None:
                guard.terminate_group(proc)
            guard.OWNED.remove(proc)
    return matched


def get_json(url):
    with urllib.request.urlopen(url, timeout=2) as response:
        if response.status != 200:
            raise GateStop(f"GET {url} returned {response.status}")
        return json.loads(response.read())


def wait_health(proc, url, stage, oom_base, timeout=1200):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        verify_lock()
        guard.check_gates(stage, oom_base)
        if proc.poll() is not None:
            raise GateStop(f"owned process exited before health (exit={proc.returncode})")
        if guard.health_ok(url):
            return
        time.sleep(1)
    raise GateStop(f"health timeout after {timeout}s: {url}")


def first_quality_failure(result_path: Path):
    if not result_path.exists():
        return None
    try:
        result = json.loads(result_path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    for run in result.get("runs", []):
        if run.get("started") and (run.get("error") or
                                    ("qualityPassed" in run and not run["qualityPassed"])):
            return {"seed": run.get("seed"), "policy": run.get("policy"),
                    "acceptedTasks": run.get("acceptedTasks"),
                    "taskCards": run.get("taskCards"), "error": run.get("error")}
    return None


def create_private_tmp_root():
    path = Path(tempfile.mkdtemp(
        prefix=f"private-tmp-q100-{os.getuid()}-", dir=str(TASK / "runs"))).resolve()
    if path == ROOT or ROOT not in path.parents:
        shutil.rmtree(path, ignore_errors=True)
        raise GateStop(f"Q100 test temporary root must stay inside this task folder: {path}")
    return path


def isolated_git_environment():
    env = os.environ.copy()
    env["GIT_CEILING_DIRECTORIES"] = str(ROOT.resolve())
    return env


def run_monitored(proc, stage, oom_base, owned_pids, proxy_records_path, result_path):
    while proc.poll() is None:
        verify_lock()
        blocked = first_blocked_tool_call(proxy_records_path)
        if blocked:
            raise GateStop(f"tool guard rejected unsupported model tool calls before dispatch: {blocked}")
        failed_run = first_quality_failure(result_path)
        if failed_run:
            raise GateStop(f"preregistered all-runs quality gate became unreachable; stopping after first failed run: {failed_run}")
        external = guard.external_inference_processes(owned_pids)
        if external:
            raise GateStop(f"another inference process appeared; left untouched: {external}")
        guard.check_gates(stage, oom_base)
        time.sleep(1)
    if proc.returncode != 0:
        raise GateStop(f"Q100 probe exited with {proc.returncode}")


def run():
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, guard.signal_handler)
    verify_lock()
    prereg = json.loads(PREREG.read_text())
    amendment = json.loads(AMENDMENT.read_text())
    expected = amendment["runtimeFingerprints"]
    state = {"taskId": prereg["taskId"], "experimentId": prereg["experimentId"],
             "status": "starting", "startedAtUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "memoryLimits": guard.cgroup_memory_limits(), "ownedProcesses": []}
    atomic_json(TASK / "runs/state.json", state)
    server = proxy = probe = None
    server_log = proxy_log = probe_log = None
    private_tmp = None
    private_tmp_cleanup_error = None
    failure = None
    try:
        if any(value != "max" for value in state["memoryLimits"].values()):
            raise GateStop(f"unexpected cgroup memory caps: {state['memoryLimits']}")
        inputs = verify_small_inputs(expected)
        external = guard.external_inference_processes()
        if external:
            raise GateStop(f"external inference process detected before launch; left untouched: {external}")
        for port in (SERVER_PORT, PROXY_PORT, 18789):
            if guard.listening(port):
                raise GateStop(f"port {port} already listening")
        gpus = guard.gpu_snapshot()
        oom_base = guard.oom_snapshot()
        baseline = guard.check_gates("baseline", oom_base, baseline=True)
        if baseline["memAvailableGiB"] < 32:
            raise GateStop("MemAvailable below the pre-registered 32 GiB hard stop")
        state.update({"status": "verifying_model_assets", "smallFingerprints": inputs,
                      "gpuBaseline": gpus, "baselineMemAvailableGiB": baseline["memAvailableGiB"],
                      "baselinePsi": baseline["memoryPsiAvg10Pct"]})
        atomic_json(TASK / "runs/state.json", state)
        assets = verify_model_assets(oom_base)
        verify_lock()
        external = guard.external_inference_processes()
        if external:
            raise GateStop(f"external inference process appeared before model start; left untouched: {external}")
        if guard.listening(SERVER_PORT) or guard.listening(PROXY_PORT):
            raise GateStop("Q100 port became occupied during asset verification")
        guard.check_gates("immediately_before_server_launch", oom_base)
        atomic_json(TASK / "receipts/q100-fingerprint-prelaunch.json", {
            "taskId": prereg["taskId"], "atUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "smallInputs": inputs, "modelAssets": assets, "gpuBaseline": gpus,
            "memAvailableBaselineGiB": baseline["memAvailableGiB"],
            "externalInferenceProcesses": [], "ports8363And8364Free": True,
            "filterPolicy": "parent task only; subagent read_file only; reject unexpected response tool names before LlamaCode dispatch"})

        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = "0,1"
        env["STRATA_PREFILL_CPU_SHARE"] = "0"
        command = [str(STRATA_PYTHON), str(STRATA_SERVER), "--engine", "strata", "--config", str(CONFIG),
                   "--host", "127.0.0.1", "--port", str(SERVER_PORT), "--gpu", "0,1"]
        server_log = (TASK / "runs/server.log").open("w")
        server = subprocess.Popen(command, cwd=STRATA_ROOT, env=env, stdout=server_log,
                                  stderr=subprocess.STDOUT, start_new_session=True)
        guard.OWNED.append(server)
        state.update({"status": "starting_dual_gpu_server", "serverCommand": command,
                      "serverPid": server.pid})
        atomic_json(TASK / "runs/state.json", state)
        wait_health(server, f"http://127.0.0.1:{SERVER_PORT}/health", "server_loading", oom_base)
        props = get_json(f"http://127.0.0.1:{SERVER_PORT}/props")
        slots = get_json(f"http://127.0.0.1:{SERVER_PORT}/slots")
        if props.get("total_slots") != 2 or not isinstance(slots, list) or len(slots) != 2:
            raise GateStop(f"ASTRA server is not confirmed at two slots: props={props}; slots={slots}")
        dual = guard.verify_dual_gpu_allocation(server.pid, gpus)
        if guard.external_inference_processes(guard.process_tree_pids(server.pid)):
            raise GateStop("unowned inference process appeared during ASTRA startup")
        state.update({"status": "server_ready_two_slots_dual_gpu", "totalSlots": 2,
                      "slots": slots, "dualGpuAllocation": dual})
        atomic_json(TASK / "runs/state.json", state)

        proxy_env = env.copy()
        proxy_env["Q100_UPSTREAM_PORT"] = str(SERVER_PORT)
        proxy_env["Q100_PROXY_PORT"] = str(PROXY_PORT)
        proxy_records_path = TASK / "runs/tool-guard-proxy.jsonl"
        clear_proxy_log(proxy_records_path)
        proxy_env["Q100_PROXY_LOG"] = str(proxy_records_path)
        proxy_log = (TASK / "runs/tool-guard-proxy.log").open("w")
        proxy = subprocess.Popen([sys.executable, str(PROXY)], cwd=ROOT, env=proxy_env,
                                 stdout=proxy_log, stderr=subprocess.STDOUT, start_new_session=True)
        guard.OWNED.append(proxy)
        wait_health(proxy, f"http://127.0.0.1:{PROXY_PORT}/health", "tool_guard_startup", oom_base, timeout=15)
        if guard.external_inference_processes(guard.process_tree_pids(server.pid) | guard.process_tree_pids(proxy.pid)):
            raise GateStop("unowned inference process appeared before Q100 test")

        result_path = TASK / "runs/live-probe-result.json"
        private_tmp = create_private_tmp_root()
        test_env = isolated_git_environment()
        test_env["LLAMACODE_Q100_SERVER_URL"] = f"http://127.0.0.1:{PROXY_PORT}"
        test_env["LLAMACODE_Q100_OUT"] = str(result_path)
        test_env["TMPDIR"] = str(private_tmp)
        test_env["TMP"] = str(private_tmp)
        test_env["TEMP"] = str(private_tmp)
        probe_log = (TASK / "runs/live-probe.log").open("w")
        probe = subprocess.Popen([str(TEST_BINARY), "realBackendSubagentFanoutProbe"], cwd=ROOT,
                                 env=test_env, stdout=probe_log, stderr=subprocess.STDOUT,
                                 start_new_session=True)
        guard.OWNED.append(probe)
        state.update({"status": "running_three_seed_agent_fanout", "probePid": probe.pid,
                      "probeCommand": [str(TEST_BINARY), "realBackendSubagentFanoutProbe"],
                      "proxyPid": proxy.pid, "serverPid": server.pid,
                      "testTemporaryRoot": str(private_tmp)})
        atomic_json(TASK / "runs/state.json", state)
        owned_pids = guard.process_tree_pids(server.pid) | guard.process_tree_pids(proxy.pid)
        run_monitored(probe, "agent_backend_fanout_live", oom_base, owned_pids,
                      proxy_records_path, result_path)
        guard.OWNED.remove(probe)
        probe = None
        if not result_path.exists():
            raise GateStop("live probe returned success without its result JSON")
        live_result = json.loads(result_path.read_text())
        proxy_records = [json.loads(line) for line in (TASK / "runs/tool-guard-proxy.jsonl").read_text().splitlines() if line.strip()]
        if any(row.get("blockedToolCall") for row in proxy_records):
            raise GateStop("tool guard blocked an unexpected model tool call; result is invalid, no call dispatched")
        proxy_counts = {role: sum(1 for row in proxy_records if row.get("role") == role)
                        for role in ("parent", "subagent")}
        if proxy_counts["parent"] == 0 or proxy_counts["subagent"] == 0:
            raise GateStop(f"proxy did not observe both model roles: {proxy_counts}")
        atomic_json(TASK / "receipts/q100-final-result.json", {
            "taskId": prereg["taskId"], "experimentId": prereg["experimentId"],
            "completedAtUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "liveProbe": live_result, "toolGuardRequestsByRole": proxy_counts,
            "blockedUnexpectedToolCalls": 0,
            "scope": "real ASTRA/Strata model and LlamaAgentBackend at 64K; no quality or memory conclusion at 1M; no production adoption"})
        state.update({"status": "probe_complete", "aggregate": live_result.get("aggregate"),
                      "toolGuardRequestsByRole": proxy_counts})
        atomic_json(TASK / "runs/state.json", state)
    except Exception as exc:
        failure = f"{type(exc).__name__}: {exc}"
        state.update({"status": "failed_or_aborted", "failure": failure})
        atomic_json(TASK / "runs/state.json", state)
    finally:
        for proc in (probe, proxy, server):
            if proc is not None:
                try:
                    guard.terminate_group(proc)
                finally:
                    if proc in guard.OWNED:
                        guard.OWNED.remove(proc)
        for log in (probe_log, proxy_log, server_log):
            if log:
                log.close()
        if private_tmp is not None and private_tmp.exists():
            try:
                shutil.rmtree(private_tmp)
            except OSError as exc:
                private_tmp_cleanup_error = f"{type(exc).__name__}: {exc}"

    cleanup = {"taskId": prereg["taskId"],
               "atUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "ownedServerStopped": server is None or server.poll() is not None,
               "ownedProxyStopped": proxy is None or proxy.poll() is not None,
               "port8363Free": not guard.listening(SERVER_PORT),
               "port8364Free": not guard.listening(PROXY_PORT),
               "externalInferenceProcesses": guard.external_inference_processes(),
               "privateTempRemoved": private_tmp is None or not private_tmp.exists(),
               "privateTempCleanupError": private_tmp_cleanup_error,
               "memoryPsiAvg10Pct": guard.psi_avg10(),
               "memAvailableGiB": round(guard.mem_available_gib(), 3),
               "oom": guard.oom_snapshot(), "gpus": guard.gpu_snapshot()}
    cleanup["pass"] = bool(cleanup["ownedServerStopped"] and cleanup["ownedProxyStopped"]
                           and cleanup["port8363Free"] and cleanup["port8364Free"]
                           and not cleanup["externalInferenceProcesses"]
                           and cleanup["privateTempRemoved"])
    if private_tmp_cleanup_error and not failure:
        failure = f"Q100 temporary-root cleanup failed: {private_tmp_cleanup_error}"
    atomic_json(TASK / "receipts/q100-cleanup-postflight.json", cleanup)
    state.update({"status": "failed" if failure or not cleanup["pass"] else "complete",
                  "failure": failure, "cleanup": cleanup,
                  "finishedAtUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    atomic_json(TASK / "runs/state.json", state)
    return 1 if failure or not cleanup["pass"] else 0


if __name__ == "__main__":
    raise SystemExit(run())
