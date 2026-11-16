#!/usr/bin/env python3
"""Detached, bounded Q232 Q172 seed-42 screen; does not depend on Codex."""
from __future__ import annotations
import hashlib, importlib.util, json, os, pathlib, signal, socket, subprocess, sys, time, urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[6]
PROFILE = pathlib.Path(__file__).resolve().parents[1]
RUNS, RECEIPTS, LOGS = PROFILE / "runs", PROFILE / "receipts", PROFILE / "logs"
SOURCE = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261103-VF-RESUME-202/profiles/qwen36-ninfer-all-v3-dflash5-5t/scripts/run_q173.py"
SPEC = importlib.util.spec_from_file_location("q229_runner", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("No se pudo cargar el verificador de infraestructura Q229")
Q229 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(Q229)

MODEL = pathlib.Path(Q229.MODEL)
SERVER = pathlib.Path(Q229.SERVER)
TOOL = pathlib.Path("/home/cristian/.cache/codex-tool-eval-bench-v2.8.0/.venv/bin/tool-eval-bench")
TOOL_SHA = "31e3c8f5fa9140738cde4e1cecc909f5335cf928a90fbdd062ec7935e0526472"
MODEL_SHA = "3e33297645dc33557751be1a3c407a74ed7c00f34909b5d4e8cfdce91b3dbe84"
SERVER_SHA = "7d839bb832f79605363f7a5fbe31944123b7cb54c0d980c1e3686865f163fdb1"
HOST, PORT, MODEL_ID = "127.0.0.1", 18645, "qwen3.6-35b-a3b"
UNIT_TASK = "Q232-QWEN36-DFLASH5-Q172-SEED42-EXTRA-FAST-SCREEN"

def utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()

def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)

def read_json(url, timeout=8):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())

def pid_alive(pid):
    return pathlib.Path(f"/proc/{pid}").exists()

def run():
    RUNS.mkdir(parents=True, exist_ok=True); RECEIPTS.mkdir(parents=True, exist_ok=True); LOGS.mkdir(parents=True, exist_ok=True)
    result_path = RUNS / "tool-eval-seed42.json"
    if result_path.exists() or (RUNS / "owned-server.json").exists():
        raise RuntimeError("Q232 outputs/PID file already exist; refusing to overwrite")
    Q229.check_lock()
    if sha(TOOL) != TOOL_SHA or sha(SERVER) != SERVER_SHA:
        raise RuntimeError("SHA del harness o servidor no coincide con el preregistro")
    stat = MODEL.stat()
    if stat.st_size != 22790484480 or stat.st_mtime_ns != Q229.MODEL_MTIME_NS or stat.st_ino != Q229.MODEL_INODE:
        raise RuntimeError("La identidad local del modelo cambió respecto del Q229 verificado")
    if not Q229.port_free():
        raise RuntimeError("Puerto 18645 ocupado antes de iniciar")
    gates = Q229.assert_infrastructure()
    atomic(RECEIPTS / "preflight.json", {"test_id": UNIT_TASK, "status": "PASS", "time_utc": utc(), "gates": gates,
           "artifact": {"path": str(MODEL), "bytes": stat.st_size, "sha256_pinned": MODEL_SHA, "identity_match": True},
           "runtime_sha256": SERVER_SHA, "tool_eval_sha256": TOOL_SHA, "port_free": True})
    argv = Q229.server_argv()
    server_log = (LOGS / "server.log").open("wb")
    server = subprocess.Popen(argv, cwd=PROFILE, stdin=subprocess.DEVNULL, stdout=server_log, stderr=subprocess.STDOUT,
                              env={**os.environ, "CUDA_VISIBLE_DEVICES": "0,1"}, start_new_session=True, close_fds=True)
    atomic(RUNS / "owned-server.json", {"pid": server.pid, "pgid": server.pid, "argv": argv, "started_utc": utc(), "task_id": UNIT_TASK})
    tool = None
    failure = None
    try:
        deadline = time.monotonic() + 1800
        while time.monotonic() < deadline:
            if server.poll() is not None:
                raise RuntimeError(f"ninfer-serve terminó antes de readiness: rc={server.returncode}")
            Q229.assert_infrastructure(server.pid)
            try:
                with urllib.request.urlopen(f"http://{HOST}:{PORT}/health", timeout=8) as health:
                    ready = health.status == 200
                if ready:
                    models = read_json(f"http://{HOST}:{PORT}/v1/models")
                    ids = [x.get("id") for x in models.get("data", [])]
                    if MODEL_ID not in ids:
                        raise RuntimeError(f"Modelo servido inesperado: {ids}")
                    break
            except Exception:
                time.sleep(3)
        else:
            raise TimeoutError("NInfer no alcanzó readiness en 1800 s")
        gpu_attribution = Q229.gpu_state()
        for i in (0, 1):
            if not any(p["pid"] == server.pid and p["used_mib"] >= 1024 for p in gpu_attribution["compute"][i]):
                raise RuntimeError(f"El PID del servidor no quedó atribuido a GPU{i}")
        start_utc = utc(); start = time.monotonic()
        run_dir = RUNS / "seed42"
        run_dir.mkdir(parents=True, exist_ok=False)
        cmd = [str(TOOL), "run", "--model", MODEL_ID, "--backend", "ninfer", "--base-url", f"http://{HOST}:{PORT}/v1", "--format", "openai",
               "--temperature", "0.6", "--top-p", "0.95", "--top-k", "20", "--min-p", "0.0", "--repeat-penalty", "1.0", "--seed", "42",
               "--backend-kwargs", '{"reasoning_effort":"medium","presence_penalty":0.0}', "--variant-seed", "20261010", "--hardmode", "--scenarios",
               *[f"TC-{n}" for n in range(70, 98)], "--timeout", "120", "--max-turns", "8", "--trials", "1", "--parallel", "1",
               "--no-warmup", "--fail-on-safety", "--no-live", "--redact-url", "--label", "Q232-Qwen36-DFlash5-Q172-seed42",
               "--output-dir", str(run_dir / "reports"), "--json-file", str(result_path)]
        log_path = LOGS / "tool-eval.log"
        with log_path.open("wb") as log:
            tool = subprocess.Popen(cmd, cwd=run_dir, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                    env={**os.environ, "CUDA_VISIBLE_DEVICES": ""}, start_new_session=True, close_fds=True)
            while tool.poll() is None:
                if server.poll() is not None:
                    failure = f"Servidor terminó durante Q172: rc={server.returncode}"
                    os.killpg(tool.pid, signal.SIGTERM); tool.wait(timeout=15); break
                Q229.assert_infrastructure(server.pid)
                time.sleep(10)
        payload = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else None
        events = payload.get("total_scenarios") if isinstance(payload, dict) else None
        rec = {"test_id": UNIT_TASK, "status": "complete" if events == 28 and not failure else "partial_or_failed",
               "started_utc": start_utc, "finished_utc": utc(), "elapsed_seconds": round(time.monotonic()-start, 3),
               "return_code": tool.returncode if tool else None, "total_scenarios": events, "expected_scenarios": 28,
               "final_score": payload.get("final_score") if payload else None, "weighted_score": payload.get("weighted_score") if payload else None,
               "safety_gate": payload.get("safety_gate") if payload else None, "safety_warnings": payload.get("safety_warnings") if payload else None,
               "failure": failure, "artifact_sha256": MODEL_SHA, "runtime_sha256": SERVER_SHA, "tool_eval_sha256": TOOL_SHA,
               "server_pid": server.pid, "gpu_attribution": gpu_attribution, "argv": cmd, "harness_log": str(log_path), "result_json": str(result_path)}
        atomic(RECEIPTS / "result.json", rec)
    except Exception as exc:
        failure_record = {"test_id": UNIT_TASK, "status": "worker_failed", "timestamp_utc": utc(),
                          "error": f"{type(exc).__name__}: {exc}", "result_json_exists": result_path.exists(),
                          "server_pid": server.pid if server else None}
        atomic(RECEIPTS / "worker-failure.json", failure_record)
        raise
    finally:
        if tool and tool.poll() is None:
            os.killpg(tool.pid, signal.SIGTERM)
            try: tool.wait(timeout=10)
            except subprocess.TimeoutExpired: os.killpg(tool.pid, signal.SIGKILL); tool.wait(timeout=5)
        if pid_alive(server.pid):
            try: os.killpg(server.pid, signal.SIGINT)
            except ProcessLookupError: pass
            try: server.wait(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(server.pid, signal.SIGTERM)
                try: server.wait(timeout=10)
                except subprocess.TimeoutExpired: os.killpg(server.pid, signal.SIGKILL); server.wait(timeout=5)
        server_log.close()
        (RUNS / "owned-server.json").unlink(missing_ok=True)
        post = {"timestamp_utc": utc(), "server_exit": server.returncode, "port_free": Q229.port_free(), "inference_processes": Q229.inference_processes(),
                "compute_apps": Q229.gpu_state()["compute"]}
        atomic(RECEIPTS / "postflight.json", post)
        if not post["port_free"] or post["inference_processes"] or any(post["compute_apps"].values()):
            raise RuntimeError("Postflight dejó procesos/puerto/compute residuales: " + json.dumps(post))

if __name__ == "__main__":
    run()
