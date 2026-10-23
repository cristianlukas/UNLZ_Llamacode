#!/usr/bin/env python3
"""Run one preregistered full Hard Mode baseline seed for Q54."""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path
import shutil
import signal
import sys
import traceback


TASK_ID = "Q-20261023-VF-ITERATION-54"
TOKEN = "fec51815-42c8-4efa-94e4-c76a616a7087"
TASK = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[4]
Q50_RUNNER = REPO / "artifacts/evaluacion-modelos-llamacode/Q-20261022-VF-ITERATION-50/work/q50_quality_holdout.py"
spec = importlib.util.spec_from_file_location("q50_q54_baseline", Q50_RUNNER)
if spec is None or spec.loader is None:
    raise RuntimeError(f"No se pudo cargar el runner Q50 validado: {Q50_RUNNER}")
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)

q.TASK = TASK
q.TOKEN = TOKEN
q.PROGRESS = TASK / "runs/progress.json"
q.GUARDS = TASK / "receipts/resource-guards.jsonl"
q.RUNS = TASK / "runs"
q.LOGS = TASK / "logs"
q.RECEIPTS = TASK / "receipts"
q.EXPECTED_CHAT_KWARGS = {"chat_template_kwargs": {"reasoning_effort": "medium"}}


def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def lock_record() -> dict:
    path = REPO / "WORK_QUEUE.lock"
    if not path.is_file():
        raise RuntimeError("WORK_QUEUE.lock no existe; Q54 no inicia")
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("token") != TOKEN or record.get("task_id") != TASK_ID:
        raise RuntimeError("WORK_QUEUE.lock dejó de pertenecer a Q54")
    return record


q.lock_record = lock_record


def on_signal(signum, _frame):
    raise InterruptedError(f"Q54 recibió señal {signum}; detener sólo su proceso/servicio")


def main() -> int:
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    for path in (TASK / "runs", TASK / "logs", TASK / "receipts", TASK / "work"):
        path.mkdir(parents=True, exist_ok=True)
    if q.PROGRESS.exists():
        raise RuntimeError("Q54 ya tiene checkpoint; no repetir automáticamente")

    arm = q.ARMS[0]
    progress = {
        "task_id": TASK_ID,
        "amendment": "baseline-seed-43-full-hardmode",
        "lock_token": TOKEN,
        "status": "running",
        "configuration": {
            "arm": "baseline", "runtime": "llama.cpp MTP2", "seed": 43,
            "scenario_count": 28, "reasoning_effort": "medium",
            "model_sha256": "7e78da5d7e3ae28d178121f58646953305f3e5bd3cb46f4a75584e8b6c6fe169",
            "context_size": 16384, "variant_seed": 20261010,
            "sampling": {"temperature": 0.6, "top_p": 0.95, "top_k": 20, "min_p": 0.0, "repeat_penalty": 1.0},
            "scenario_ids": [f"TC-{n}" for n in range(70, 98)],
        },
        "created_at_utc": utc(),
        "server_start": None,
        "suite_attempt": None,
        "cleanup": [],
    }
    server = log = port = None
    try:
        lock_record()
        disk_task = shutil.disk_usage(TASK).free
        disk_model = shutil.disk_usage(q.MODEL.parent).free
        if disk_task < 1 * 1024**3:
            raise RuntimeError(f"espacio libre en carpeta de resultados <1 GiB: {disk_task}")
        if disk_model < 20 * 1024**3:
            raise RuntimeError(f"espacio libre en HDD extra <20 GiB: {disk_model}")
        cg = q.cgroup_dir()
        q.cgroup_properties(cg)
        pre = q.preflight("Q54 baseline seed43 fresh preflight", cg)
        pre["disk_free_task_bytes"] = disk_task
        pre["disk_free_model_volume_bytes"] = disk_model
        q.atomic_json(q.RECEIPTS / "preflight.json", pre)
        progress["preflight"] = pre
        q.write_progress(progress, stage="fresh preflight passed")
        print(f"Q54 PREFLIGHT PASS cgroup={cg} GPU0={pre['gpu0']['name']} free={pre['gpu0']['memory_free_mib']}MiB", flush=True)

        server, log, port, start_record = q.start_server(arm, 1, cg, progress, "seed43")
        progress["server_start"] = start_record | {"port": port}
        q.write_progress(progress, stage="baseline seed43 server ready")

        output = TASK / "runs/baseline-seed43.json"
        report_dir = TASK / "reports/baseline-seed43"
        work = TASK / "work/tool-eval-baseline-seed43"
        work.mkdir(parents=True, exist_ok=True)
        command = q.tool_eval_command(arm, port, 43, output, report_dir)
        for i, value in enumerate(command[:-1]):
            if value == "--label":
                command[i + 1] = "Q54-baseline-seed-43"
                break
        log_path = TASK / "logs/baseline-seed43-tool-eval.log"
        progress["suite_attempt"] = {
            "started_at_utc": utc(), "command": command,
            "json_path": str(output), "log_path": str(log_path), "status": "running",
        }
        q.write_progress(progress, stage="baseline seed43 full Hard Mode suite running")
        rc, timing = q.run_monitored(command, log_path, arm, 43, work, cg, server.pid, progress)
        validation = q.validate_seed(output, rc, 43)
        raw = json.loads(output.read_text(encoding="utf-8")) if output.is_file() else {}
        scenarios = ((raw.get("scores") or {}).get("scenario_results") or [])
        failures = [
            {k: item.get(k) for k in ("scenario_id", "status", "failure_kind", "summary") if k in item}
            for item in scenarios if item.get("status") != "pass" or item.get("error")
        ]
        result = {
            "task_id": TASK_ID, "lock_token": TOKEN,
            "status": "valid_seed" if validation.get("valid") else "seed_invalid",
            "seed": 43, "arm": "baseline", "runtime": arm["runtime"],
            "tool_eval_exit_code": rc, "timing": timing,
            "validation": validation,
            "score": validation.get("score"), "critical_scenarios": validation.get("critical_scenarios"),
            "critical_all_pass": validation.get("critical_all_pass"),
            "scenario_status_counts": validation.get("scenario_status_counts"),
            "scenario_failures_or_partials": failures,
            "json_path": str(output), "json_sha256": q.sha256(output) if output.is_file() else None,
            "log_path": str(log_path), "log_sha256": q.sha256(log_path) if log_path.is_file() else None,
            "preflight": pre,
            "interpretation": "A valid baseline seed is a prerequisite only; no OpenJet comparison or adoption claim is made in Q54.",
        }
        progress["suite_attempt"].update(status=result["status"], completed_at_utc=utc(), exit_code=rc, validation=validation)
        progress["result"] = result
        progress["status"] = result["status"]
        progress["completed_at_utc"] = utc()
        q.atomic_json(q.RECEIPTS / "baseline-seed43-result.json", result)
        q.write_progress(progress, stage=f"baseline seed43 {result['status']}; cleanup pending")
        cleanup = q.stop_server(server, log, "baseline", port)
        server = log = port = None
        progress["cleanup"].append(cleanup)
        progress["cleanup_confirmed"] = True
        q.write_progress(progress, stage=f"baseline seed43 {result['status']}; cleanup confirmed")
        result["cleanup"] = cleanup
        result["cleanup_confirmed"] = True
        result["completed_at_utc"] = progress["completed_at_utc"]
        q.atomic_json(q.RECEIPTS / "baseline-seed43-result.json", result)
        print(json.dumps({"status": result["status"], "score": result["score"], "critical": result["critical_scenarios"], "failure_count": len(failures), "cleanup": cleanup}, ensure_ascii=False), flush=True)
        return 0 if validation.get("valid") else 2
    except Exception as exc:
        if server is not None and log is not None and port is not None:
            try:
                cleanup = q.stop_server(server, log, "baseline", port)
                progress["cleanup"].append(cleanup)
                server = log = port = None
            except Exception as cleanup_exc:
                progress.setdefault("cleanup_errors", []).append(str(cleanup_exc))
        progress["status"] = "blocked"
        progress["failure"] = f"{type(exc).__name__}: {exc}"
        progress["traceback"] = traceback.format_exc(limit=12)
        progress["completed_at_utc"] = utc()
        q.write_progress(progress, stage="Q54 blocked; preserve evidence")
        q.atomic_json(q.RECEIPTS / "baseline-seed43-result.json", progress)
        print(f"Q54 BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
