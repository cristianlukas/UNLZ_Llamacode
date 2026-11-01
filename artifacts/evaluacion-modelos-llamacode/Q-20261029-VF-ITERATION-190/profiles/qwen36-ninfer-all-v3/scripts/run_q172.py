#!/usr/bin/env python3
"""Run one preregistered Q190 Q172 seed against the owned NInfer-all server."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import signal
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[6]
PROFILE = pathlib.Path(__file__).resolve().parents[1]
RUNS = PROFILE / "runs"
RECEIPTS = PROFILE / "receipts"
TOOL = pathlib.Path("/home/cristian/.cache/codex-tool-eval-bench-v2.8.0/.venv/bin/tool-eval-bench")
TOOL_SHA = "31e3c8f5fa9140738cde4e1cecc909f5335cf928a90fbdd062ec7935e0526472"
HOST = "127.0.0.1"
PORT = 18493
LOCK_TOKEN = "d4618d1c-b63c-4d9c-b523-bd4b7d0eb4a0"
WORKER = "Q-20261029-VF-ITERATION-190"
TASK = "Q190-profile-qwen36-ninfer-all-v3-q173-q172"
MODEL_ID = "qwen3.6-35b-a3b"
SCENARIOS = [f"TC-{n}" for n in range(70, 98)]
CHECKER_PATH = PROFILE / "scripts/run_q173.py"
SPEC = importlib.util.spec_from_file_location("q190_q173_checks", CHECKER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("No se pudo cargar el preflight Q173")
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_write(path: pathlib.Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def server_pid() -> int:
    owned = json.loads((RUNS / "owned-server.json").read_text(encoding="utf-8"))
    pid = int(owned["pid"])
    try:
        argv = [x.decode(errors="replace") for x in pathlib.Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0") if x]
    except OSError as exc:
        raise RuntimeError(f"PID server propio ya no existe: {pid}") from exc
    if not argv or pathlib.Path(argv[0]).name != "ninfer-serve":
        raise RuntimeError(f"PID de Q190 ya no corresponde a ninfer-serve: {pid}")
    return pid


def preflight() -> dict:
    CHECKER.check_lock()
    pid = server_pid()
    gates = CHECKER.assert_infrastructure(pid)
    with urllib.request.urlopen(f"http://{HOST}:{PORT}/health", timeout=5) as response:
        if response.status != 200:
            raise RuntimeError(f"/health status {response.status}")
    model_list = CHECKER.read_json(f"http://{HOST}:{PORT}/v1/models")
    ids = [x.get("id") for x in model_list.get("data", [])]
    if MODEL_ID not in ids:
        raise RuntimeError(f"El servidor no expone el modelo preregistrado: {ids}")
    state = gates["gpu"]
    for index in (0, 1):
        if not any(x["pid"] == pid and x["used_mib"] >= 1024 for x in state["compute"][index]):
            raise RuntimeError(f"El PID Q190 no reserva >=1GiB en GPU{index}")
    return {"timestamp_utc": utc(), "server_pid": pid, "model_id": MODEL_ID, "gates": gates}


def command(seed: int, run_dir: pathlib.Path) -> list[str]:
    return [
        str(TOOL), "run", "--model", MODEL_ID, "--backend", "ninfer",
        "--base-url", f"http://{HOST}:{PORT}/v1", "--format", "openai",
        "--temperature", "0.6", "--top-p", "0.95", "--top-k", "20", "--min-p", "0.0",
        "--repeat-penalty", "1.0", "--seed", str(seed),
        "--backend-kwargs", json.dumps({"reasoning_effort": "medium", "presence_penalty": 0.0}, separators=(",", ":")),
        "--variant-seed", "20261010", "--hardmode", "--scenarios", *SCENARIOS,
        "--timeout", "120", "--max-turns", "8", "--trials", "1", "--parallel", "1",
        "--no-warmup", "--fail-on-safety", "--no-live", "--redact-url",
        "--label", f"Q190-Qwen36-NInfer-all-Q172-seed{seed}",
        "--output-dir", str(run_dir / "reports"), "--json-file", str(run_dir / "result.json"),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, choices=(42, 43, 44), required=True)
    args = parser.parse_args()
    CHECKER.check_lock()
    if not TOOL.is_file() or sha256(TOOL) != TOOL_SHA:
        raise RuntimeError("SHA de tool-eval-bench 2.8.0 no coincide con el preregistro")
    run_dir = RUNS / f"q172-seed-{args.seed}"
    result_path = run_dir / "result.json"
    log_path = run_dir / "tool-eval.log"
    receipt_path = RECEIPTS / f"q172-seed-{args.seed}-execution.json"
    if result_path.exists() or receipt_path.exists():
        raise RuntimeError(f"Seed {args.seed} ya tiene artefactos; no repetir automáticamente")
    run_dir.mkdir(parents=True, exist_ok=True)
    before = preflight()
    argv = command(args.seed, run_dir)
    start_utc = utc()
    start = time.monotonic()
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": ""}
    failure = None
    with log_path.open("wb") as log:
        proc = subprocess.Popen(argv, cwd=run_dir, stdout=log, stderr=subprocess.STDOUT,
                                env=env, start_new_session=True, close_fds=True)
        while proc.poll() is None:
            try:
                preflight()
            except Exception as exc:
                failure = f"infraestructura dejó de pasar durante Q172: {type(exc).__name__}: {exc}"
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    proc.wait(timeout=5)
                break
            time.sleep(10)
        rc = proc.returncode
    after = preflight() if failure is None else None
    payload = json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else None
    total = payload.get("total_scenarios") if isinstance(payload, dict) else None
    complete = total == 28 and failure is None
    record = {
        "task_id": TASK,
        "stage": "q172-hardmode",
        "seed": args.seed,
        "status": "complete" if complete else "incomplete",
        "started_utc": start_utc,
        "finished_utc": utc(),
        "elapsed_seconds": round(time.monotonic() - start, 3),
        "return_code": rc,
        "harness_json": str(result_path),
        "log": str(log_path),
        "total_scenarios": total,
        "expected_scenarios": 28,
        "final_score": payload.get("final_score") if isinstance(payload, dict) else None,
        "weighted_score": payload.get("weighted_score") if isinstance(payload, dict) else None,
        "rating": payload.get("rating") if isinstance(payload, dict) else None,
        "run_status": payload.get("status") if isinstance(payload, dict) else None,
        "safety_gate": payload.get("safety_gate") if isinstance(payload, dict) else None,
        "safety_warnings": payload.get("safety_warnings") if isinstance(payload, dict) else None,
        "report_path": payload.get("report_path") if isinstance(payload, dict) else None,
        "infrastructure_failure": failure,
        "start_preflight": before,
        "finish_preflight": after,
        "argv": argv,
        "tool_eval_sha256": TOOL_SHA,
        "lock_token": LOCK_TOKEN,
    }
    atomic_write(receipt_path, record)
    print(json.dumps(record, ensure_ascii=False))
    return 0 if complete else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        raise
