#!/usr/bin/env python3
"""Run one preregistered Q172 seed-42 screen for a single-PNY Qwen38 profile."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import signal
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

REPO = pathlib.Path(__file__).resolve().parents[7]
TASK = "Q-20261103-VF-RESUME-202"
PROFILE_ROOT = pathlib.Path(__file__).resolve().parents[1]
MODEL = pathlib.Path("/media/cristian/Disco local/Models/llamacpp/Qwen3.8-27B-GGUF/Qwen3.8-27B-UD-Q4_K_XL.gguf")
SERVER = pathlib.Path("/media/cristian/Disco local/LlamaCode-cache/llamAmpere-build/bin/llama-server")
MK_ROOT = pathlib.Path("/media/cristian/Disco local/Modelos-eval/Qwen38-Megakernel-v2026.11.01/qwen38-megakernel-v2026.11.01-linux-x64-sm86")
MK_SERVER = MK_ROOT / "server/mk_server.py"
MK_BIN = MK_ROOT / "qwen38_mk"
MK_LIB = MK_ROOT / "libqwen38mk.so"
TOOL = pathlib.Path("/home/cristian/.cache/codex-tool-eval-bench-v2.8.0/.venv/bin/tool-eval-bench")
GPU_UUID = "GPU-5b9f385f-6a8e-b802-f69c-e62a71c91049"
ASUS_UUID = "GPU-af6de4b3-6497-b7f8-796d-6d69cba422e6"
OUT_ROOT = pathlib.Path("/media/cristian/Disco local/Modelos-eval/Q205-Qwen38-Q172-single-PNY")
TOOL_SHA = "31e3c8f5fa9140738cde4e1cecc909f5335cf928a90fbdd062ec7935e0526472"
MODEL_SHA = "3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e"
SERVER_SHA = "940910b0cf2d620718d95dc48d96a2d29c7e7704f4bd39c7840f887d3c7eec82"
MK_SERVER_SHA = "d01b6cf42a092429b8a6155f37dc468181c2ec7eebecbd6b4b7c336181b3d371"
MK_BIN_SHA = "16c78f661c83875e5f66a8ea1072f0ed671d8bcfbe4e334485ff6478a214b7d2"
MK_LIB_SHA = "54c2fd2ae3045a01353f0dd8faa783981441ed97aa25389b6ab10df40fa91b76"
PROFILE_CONFIG = {
    "A": {"id": "Q205.01", "label": "A-control llama.cpp CUDA b67849b", "port": 18414, "runtime": "llamacpp"},
    "B": {"id": "Q205.02", "label": "B Megakernel MTP-off", "port": 18415, "runtime": "megakernel-b"},
    "C": {"id": "Q205.03", "label": "C Megakernel MTP-7", "port": 18416, "runtime": "megakernel-c"},
}
SERVER_RX = re.compile(r"(?:llama-server|mk_server\.py|qwen38_mk|strata-server|ninfer|vllm|sglang|ollama|xolotl|aphrodite|koboldcpp|lmstudio|lm studio|peritosoft)", re.I)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def run(argv: list[str], timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)


def sha(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def check_lock() -> None:
    lock = (REPO / "WORK_QUEUE.lock").read_text(encoding="utf-8")
    queue = (REPO / "WORK_QUEUE.md").read_text(encoding="utf-8")
    if f"task={TASK}" not in lock or "owner=Codex" not in lock:
        raise RuntimeError("WORK_QUEUE.lock ya no pertenece a esta campaña")
    if TASK not in queue:
        raise RuntimeError("la tarea activa no aparece en WORK_QUEUE.md")


def mem_available_bytes() -> int:
    line = next(x for x in pathlib.Path("/proc/meminfo").read_text().splitlines() if x.startswith("MemAvailable:"))
    return int(line.split()[1]) * 1024


def psi() -> dict[str, dict[str, str]]:
    out = {}
    for line in pathlib.Path("/proc/pressure/memory").read_text().splitlines():
        parts = line.split()
        out[parts[0]] = dict(x.split("=", 1) for x in parts[1:])
    return out


def gpu_query() -> list[dict]:
    p = run(["nvidia-smi", "--query-gpu=index,uuid,name,memory.used,memory.total,temperature.gpu,utilization.gpu", "--format=csv,noheader,nounits"])
    if p.returncode:
        raise RuntimeError("nvidia-smi GPU query falló: " + p.stderr.strip())
    out = []
    for line in p.stdout.splitlines():
        f = [x.strip() for x in line.split(",")]
        if len(f) >= 7:
            out.append({"index": int(f[0]), "uuid": f[1], "name": f[2], "memory_used_mib": int(f[3]),
                        "memory_total_mib": int(f[4]), "temperature_c": int(f[5]), "utilization_percent": int(f[6])})
    return out


def compute_apps() -> list[dict]:
    p = run(["nvidia-smi", "--query-compute-apps=pid,gpu_uuid,used_gpu_memory", "--format=csv,noheader,nounits"])
    if p.returncode not in (0, 6):
        raise RuntimeError("nvidia-smi compute-app query falló: " + p.stderr.strip())
    out = []
    for line in p.stdout.splitlines():
        f = [x.strip() for x in line.split(",")]
        if len(f) >= 3 and f[0].isdigit():
            out.append({"pid": int(f[0]), "gpu_uuid": f[1], "used_mib": int(f[2])})
    return out


def process_snapshot(ignore_pids: set[int] | None = None) -> list[dict]:
    ignored = {os.getpid()}
    if ignore_pids:
        ignored.update(ignore_pids)
    pid = os.getpid()
    while pid > 1:
        try:
            stat = pathlib.Path(f"/proc/{pid}/stat").read_text()
            pid = int(stat[stat.rfind(")") + 2:].split()[1])
        except (OSError, ValueError, IndexError):
            break
        ignored.add(pid)
    found = []
    for e in pathlib.Path("/proc").iterdir():
        if not e.name.isdigit() or int(e.name) in ignored:
            continue
        try:
            comm = (e / "comm").read_text().strip()
            argv = (e / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace")
        except OSError:
            continue
        if SERVER_RX.search(comm + " " + argv):
            found.append({"pid": int(e.name), "comm": comm, "cmdline": argv[:1000]})
    return found


def port_free(port: int) -> tuple[bool, str]:
    p = run(["ss", "-H", "-ltn", f"sport = :{port}"])
    return p.returncode == 0 and not p.stdout.strip(), p.stdout.strip() or p.stderr.strip()


def proc_tree(root: int) -> set[int]:
    parents = {}
    for e in pathlib.Path("/proc").iterdir():
        if e.name.isdigit():
            try:
                stat = (e / "stat").read_text()
                parents[int(e.name)] = int(stat[stat.rfind(")") + 2:].split()[1])
            except (OSError, ValueError, IndexError):
                pass
    tree, changed = {root}, True
    while changed:
        changed = False
        for child, parent in parents.items():
            if parent in tree and child not in tree:
                tree.add(child)
                changed = True
    return tree


def service_output(argv: list[str]) -> str:
    p = run(argv)
    return (p.stdout + p.stderr).strip()


def helper_gate() -> dict:
    state_path = pathlib.Path(f"/run/vram-quarantine/{ASUS_UUID}.json")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    active = service_output(["systemctl", "is-active", f"vram-quarantine@{ASUS_UUID}.service"])
    enabled = service_output(["systemctl", "is-enabled", f"vram-quarantine@{ASUS_UUID}.service"])
    verify = service_output(["systemctl", "show", "3090-helper-verify-boot.service", "-p", "Result", "-p", "ExecMainStatus"])
    verify_log = service_output(["journalctl", "-u", "3090-helper-verify-boot.service", "-b", "-o", "cat", "--no-pager", "-n", "40"])
    cmdline = pathlib.Path("/proc/cmdline").read_text(encoding="utf-8")
    klog = service_output(["journalctl", "-k", "-b", "--no-pager"])
    p2p_r, p2p_w = service_output(["nvidia-smi", "topo", "-p2p", "r"]), service_output(["nvidia-smi", "topo", "-p2p", "w"])
    quarantine_ok = (state.get("uuid") == ASUS_UUID and state.get("state") == "protected"
                     and state.get("held") == state.get("total") == 1636 and state.get("pending") == 0
                     and state.get("driver") == state.get("built_for"))
    checks = {
        "asus_vram_quarantine_active_enabled_and_complete": active == "active" and enabled == "enabled" and quarantine_ok,
        "helper_boot_verification_pass": "Result=success" in verify and "ExecMainStatus=0" in verify
            and "PASS: reserva ASUS, P2P bidireccional y gpu-unlock en ambas RTX 3090." in verify_log,
        "p2p_read_both_directions": "OK" in p2p_r,
        "p2p_write_both_directions": "OK" in p2p_w,
        "gpu_unlock_targets_both_cards": "gpu_unlock.targets=0000:01:00.0,0000:03:00.0" in cmdline
            and "gpu_unlock: unlocked" in klog and "0000:01:00.0" in klog and "0000:03:00.0" in klog,
    }
    return {"checks": checks, "passed": all(checks.values()), "quarantine": state,
            "service_active": active, "service_enabled": enabled, "verify": verify,
            "p2p_read": p2p_r, "p2p_write": p2p_w}


def snapshot() -> dict:
    return {"at_utc": utc(), "gpus": gpu_query(), "compute_apps": compute_apps(),
            "mem_available_bytes": mem_available_bytes(), "memory_psi": psi()}


def preflight(profile: str, port: int, prereg: dict, runner_sha: str) -> dict:
    check_lock()
    if prereg.get("status") != "preregistered_before_gpu" or prereg.get("runner_sha256") != runner_sha:
        raise RuntimeError("prerregistro ausente o SHA del runner no coincide")
    files = {"model": (MODEL, MODEL_SHA), "tool_eval": (TOOL, TOOL_SHA)}
    if profile == "A":
        files["llama_server"] = (SERVER, SERVER_SHA)
    else:
        files.update({"megakernel_server": (MK_SERVER, MK_SERVER_SHA), "megakernel_binary": (MK_BIN, MK_BIN_SHA),
                      "megakernel_library": (MK_LIB, MK_LIB_SHA)})
    verified = []
    for label, (path, expected) in files.items():
        if not path.is_file():
            raise RuntimeError(f"falta {label}: {path}")
        got = sha(path)
        if got != expected:
            raise RuntimeError(f"SHA mismatch {label}: expected={expected} got={got}")
        verified.append({"label": label, "path": str(path), "bytes": path.stat().st_size, "sha256": got})
    if MODEL.stat().st_size != 17_559_178_144:
        raise RuntimeError("tamaño GGUF distinto al artefacto preregistrado")
    if not TOOL.is_file():
        raise RuntimeError("falta tool-eval-bench")
    version = run([str(TOOL), "--version"])
    if version.returncode not in (0, 2) or "2.8.0" not in version.stdout + version.stderr:
        raise RuntimeError("Tool-Eval no coincide con la versión preregistrada: " + version.stdout + version.stderr)
    conflicts = process_snapshot()
    if conflicts:
        raise RuntimeError("hay servidor/proceso de inferencia previo; no se detuvo: " + json.dumps(conflicts, ensure_ascii=False))
    ports = {str(p): port_free(p) for p in (18414, 18415, 18416)}
    if not all(v[0] for v in ports.values()):
        raise RuntimeError("puerto preregistrado ocupado: " + json.dumps(ports))
    gpus = gpu_query()
    by_uuid = {g["uuid"]: g for g in gpus}
    target = by_uuid.get(GPU_UUID)
    if not target or "RTX 3090" not in target["name"]:
        raise RuntimeError("PNY GPU1 esperada ausente: " + json.dumps(gpus))
    if target["temperature_c"] >= 85:
        raise RuntimeError("PNY GPU1 está en >=85°C antes de la prueba")
    compute = compute_apps()
    target_compute = [x for x in compute if x["gpu_uuid"] == GPU_UUID]
    if target_compute:
        raise RuntimeError("compute ajeno en GPU1 antes de prueba: " + json.dumps(target_compute))
    if mem_available_bytes() < 32 * 1024**3:
        raise RuntimeError("MemAvailable <32 GiB")
    pressure = psi()
    if max(float(pressure[k]["avg10"]) for k in ("some", "full")) >= 1.0:
        raise RuntimeError("memory PSI avg10 >=1%")
    free = shutil.disk_usage(OUT_ROOT.parent).free
    if free < 10 * 1024**3:
        raise RuntimeError(f"output volume D <10 GiB libres: {free}")
    helper = helper_gate()
    if not helper["passed"]:
        raise RuntimeError("3090 HELPER/P2P/gpu_unlock no pasa: " + json.dumps(helper, ensure_ascii=False))
    for path in (MODEL,):
        if run(["fuser", "-s", str(path)]).returncode == 0:
            raise RuntimeError(f"el modelo está abierto por otro proceso: {path}")
    idle = []
    for _ in range(30):
        check_lock()
        if process_snapshot():
            raise RuntimeError("apareció servidor de inferencia durante el baseline")
        s = snapshot()
        foreign = [x for x in s["compute_apps"] if x["gpu_uuid"] == GPU_UUID]
        if foreign:
            raise RuntimeError("apareció compute ajeno en PNY durante baseline: " + json.dumps(foreign))
        idle.append(s)
        time.sleep(1)
    util = [g["utilization_percent"] for s in idle for g in s["gpus"] if g["uuid"] == GPU_UUID]
    receipt = {"status": "PASS", "profile": profile, "timestamp_utc": utc(), "task": TASK,
               "id": prereg["id"], "lock": (REPO / "WORK_QUEUE.lock").read_text().strip(),
               "runner_sha256": runner_sha, "files": verified, "tool_version": (version.stdout + version.stderr).strip(),
               "inference_processes": [], "all_test_ports_free": ports, "target_gpu": target,
               "compute_apps_before_server": compute, "mem_available_bytes": mem_available_bytes(),
               "memory_psi": pressure, "output_volume_free_bytes": free, "helper": helper,
               "idle_baseline_30s": idle, "target_gpu_utilization_range_pp": max(util)-min(util) if util else None,
               "desktop_graphics_allowed_and_recorded": True}
    write_json(PROFILE_ROOT / "receipts" / f"{prereg['id'].lower().replace('.', '-')}-preflight.json", receipt)
    return receipt


def server_argv(profile: str, port: int) -> tuple[list[str], dict[str, str], pathlib.Path]:
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = GPU_UUID
    env["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    if profile == "A":
        argv = [str(SERVER), "-m", str(MODEL), "--host", "127.0.0.1", "--port", str(port), "-c", "65792",
                "--device", "CUDA0", "-ngl", "all", "--jinja", "--chat-template-kwargs",
                '{"enable_thinking":false}', "--cache-type-k", "q8_0", "--cache-type-v", "q8_0"]
        cwd = SERVER.parent
    else:
        argv = ["/usr/bin/python3", str(MK_SERVER), "-m", str(MODEL), "--host", "127.0.0.1", "--port", str(port),
                "-c", "65792", "--kv", "q8", "--chat-template-kwargs", '{"enable_thinking":false}']
        if profile == "B":
            argv.append("--no-mtp")
            env["MK_NO_MTP"] = "1"
            env.pop("MK_MTP", None)
        else:
            argv.extend(["--draft", "7"])
            env.pop("MK_NO_MTP", None)
        cwd = MK_ROOT
    return argv, env, cwd


def tool_argv(model_id: str, port: int, out: pathlib.Path, seed: int) -> list[str]:
    return [str(TOOL), "run", "--model", model_id, "--backend", "llamacpp", "--base-url",
            f"http://127.0.0.1:{port}/v1", "--format", "openai", "--temperature", "0.6", "--top-p", "0.95",
            "--top-k", "20", "--min-p", "0.0", "--repeat-penalty", "1.0", "--seed", str(seed),
            "--backend-kwargs", json.dumps({"reasoning_effort": "medium", "presence_penalty": 0.0}),
            "--variant-seed", "20261010", "--hardmode", "--scenarios", *[f"TC-{i}" for i in range(70, 98)],
            "--timeout", "120", "--max-turns", "8", "--trials", "1", "--parallel", "1", "--no-warmup",
            "--fail-on-safety", "--label", f"{TASK}-{PROFILE_CONFIG[next(k for k,v in PROFILE_CONFIG.items() if v['port']==port)]['id']}-Q172-seed{seed}",
            "--redact-url", "--output-dir", str(out / "reports"), "--json-file", str(out / "q172.json")]


def http_json(url: str, timeout: int = 4) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def stop_group(proc: subprocess.Popen) -> dict:
    started = utc()
    if proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGINT)
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=10)
    return {"stop_started_utc": started, "returncode": proc.returncode}


def run_one(profile: str, seed: int) -> int:
    cfg = PROFILE_CONFIG[profile]
    port, exp_id = cfg["port"], cfg["id"]
    prereg_stem = exp_id.lower().replace('.', '-')
    prereg_amendment = PROFILE_ROOT / "receipts" / f"{prereg_stem}-prereg-amend01.json"
    prereg_path = prereg_amendment if prereg_amendment.is_file() else PROFILE_ROOT / "receipts" / f"{prereg_stem}-prereg.json"
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    runner_sha = sha(pathlib.Path(__file__))
    out = pathlib.Path(prereg["output_root"])
    for name in ("q172.json", "server.log", "tool-eval.log", "summary.json"):
        if (out / name).exists():
            raise RuntimeError(f"refusing to overwrite prior output: {out / name}")
    out.mkdir(parents=True, exist_ok=True)
    proc = client = None
    summary = {"task": TASK, "id": exp_id, "profile": profile, "seed": seed, "started_utc": utc(), "status": "starting"}
    try:
        summary["preflight"] = preflight(profile, port, prereg, runner_sha)
        argv, env, cwd = server_argv(profile, port)
        summary["server_argv"] = argv
        summary["server_env"] = {k: env[k] for k in ("CUDA_VISIBLE_DEVICES", "CUDA_DEVICE_ORDER", "MK_NO_MTP") if k in env}
        with (out / "server.log").open("wb") as log:
            proc = subprocess.Popen(argv, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, env=env,
                                    start_new_session=True, close_fds=True)
        summary["server_pid"] = proc.pid
        summary["server_started_utc"] = utc()
        deadline = time.monotonic() + 900
        model_id = None
        while time.monotonic() < deadline:
            check_lock()
            if proc.poll() is not None:
                raise RuntimeError(f"server terminó antes de readiness, rc={proc.returncode}")
            foreign = process_snapshot(proc_tree(proc.pid))
            if foreign:
                raise RuntimeError("servidor de inferencia ajeno apareció durante startup: " + json.dumps(foreign))
            if mem_available_bytes() < 32 * 1024**3:
                raise RuntimeError("MemAvailable <32 GiB durante startup")
            try:
                health = urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2)
                if health.status == 200:
                    models = http_json(f"http://127.0.0.1:{port}/v1/models")
                    ids = [str(x.get("id", "")) for x in models.get("data", [])]
                    model_id = next((x for x in ids if MODEL.name in x), None)
                    if model_id:
                        break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                pass
            time.sleep(3)
        if not model_id:
            raise TimeoutError("servidor no llegó a readiness/model id en 900 s")
        summary["ready_utc"] = utc()
        summary["ready_model_ids"] = ids
        summary["served_model"] = model_id
        tree = proc_tree(proc.pid)
        summary["server_process_tree"] = sorted(tree)
        deadline = time.monotonic() + 30
        target_compute = []
        while time.monotonic() < deadline:
            target_compute = [x for x in compute_apps() if x["gpu_uuid"] == GPU_UUID]
            foreign_compute = [x for x in target_compute if x["pid"] not in tree]
            if foreign_compute:
                raise RuntimeError("compute ajeno en GPU1 después de readiness: " + json.dumps(foreign_compute))
            if any(x["pid"] in tree and x["used_mib"] >= 1024 for x in target_compute):
                break
            time.sleep(2)
        else:
            raise RuntimeError("no se atribuyó ≥1 GiB de compute al árbol propio en PNY GPU1")
        summary["compute_attribution"] = target_compute
        argv = tool_argv(model_id, port, out, seed)
        summary["tool_eval_argv"] = argv
        with (out / "tool-eval.log").open("wb") as log:
            client = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT,
                                      env={**os.environ, "CUDA_VISIBLE_DEVICES": ""},
                                      start_new_session=True, close_fds=True)
            while client.poll() is None:
                check_lock()
                if proc.poll() is not None:
                    raise RuntimeError(f"server propio terminó durante Tool-Eval, rc={proc.returncode}")
                foreign = process_snapshot(proc_tree(proc.pid))
                if foreign:
                    raise RuntimeError("servidor de inferencia ajeno apareció durante Tool-Eval: " + json.dumps(foreign))
                tree = proc_tree(proc.pid)
                target_compute = [x for x in compute_apps() if x["gpu_uuid"] == GPU_UUID]
                foreign_compute = [x for x in target_compute if x["pid"] not in tree]
                if foreign_compute:
                    raise RuntimeError("compute ajeno en PNY durante Tool-Eval: " + json.dumps(foreign_compute))
                g = next((x for x in gpu_query() if x["uuid"] == GPU_UUID), None)
                if not g or g["temperature_c"] >= 85:
                    raise RuntimeError("PNY ausente o temperatura ≥85°C durante Tool-Eval")
                if mem_available_bytes() < 32 * 1024**3:
                    raise RuntimeError("MemAvailable <32 GiB durante Tool-Eval")
                time.sleep(2)
        summary["client_exit_code"] = client.returncode
        result_path = out / "q172.json"
        if not result_path.is_file():
            raise RuntimeError("Tool-Eval no produjo JSON de salida")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        scores = result.get("scores", {})
        scenario_results = scores.get("scenario_results", [])
        scenario_counts = {}
        for scenario in scenario_results:
            state = str(scenario.get("status", "unknown"))
            scenario_counts[state] = scenario_counts.get(state, 0) + 1
        safety_gate = result.get("safety_gate")
        safety_passed = safety_gate.get("passed") if isinstance(safety_gate, dict) else safety_gate
        safety_warnings = result.get("safety_warnings", [])
        summary["result"] = {"status": result.get("status"), "final_score": result.get("final_score"),
                             "total_scenarios": result.get("total_scenarios"), "total_points": scores.get("total_points"),
                             "max_points": scores.get("max_points"), "safety_gate": safety_gate,
                             "safety_passed": safety_passed, "safety_warnings": safety_warnings,
                             "scenario_status_counts": scenario_counts,
                             "report_path": result.get("report_path"), "json_path": str(result_path)}
        valid = result.get("status") == "completed" and int(result.get("total_scenarios", 0)) == 28 and int(scores.get("max_points", 0)) == 56
        safety_bad = safety_passed is False or bool(safety_warnings) or client.returncode == 2
        summary["valid_score"] = valid
        summary["stop_repeated_seeds_for_profile"] = bool(valid and safety_bad)
        summary["status"] = "completed_score_valid_safety_fail" if valid and safety_bad else ("completed_score_valid" if valid else "incomplete_no_score")
        if not valid:
            raise RuntimeError("resultado no cumple cobertura 28/28 y 56 puntos posibles; no publicar score")
        return 0
    except Exception as exc:
        summary["status"] = "failed_or_incomplete"
        summary["error"] = f"{type(exc).__name__}: {exc}"
        return 1
    finally:
        if client is not None and client.poll() is None:
            try:
                os.killpg(client.pid, signal.SIGINT)
                client.wait(timeout=10)
            except Exception:
                try:
                    os.killpg(client.pid, signal.SIGKILL)
                    client.wait(timeout=5)
                except Exception:
                    pass
        if proc is not None:
            summary["server_stop"] = stop_group(proc)
        free, detail = port_free(port)
        summary["postflight"] = {"inference_processes": process_snapshot(), "target_compute_apps": [
            x for x in compute_apps() if x["gpu_uuid"] == GPU_UUID], "port_free": free, "port_detail": detail,
            "gpus": gpu_query(), "mem_available_bytes": mem_available_bytes()}
        summary["finished_utc"] = utc()
        write_json(out / "summary.json", summary)
        write_json(PROFILE_ROOT / "receipts" / f"{exp_id.lower().replace('.', '-')}-summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=PROFILE_CONFIG, required=True)
    ap.add_argument("--seed", type=int, choices=(42,), default=42)
    args = ap.parse_args()
    return run_one(args.profile, args.seed)


if __name__ == "__main__":
    sys.exit(main())
