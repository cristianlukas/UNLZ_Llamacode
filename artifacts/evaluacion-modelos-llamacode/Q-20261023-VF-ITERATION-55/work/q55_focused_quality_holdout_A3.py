#!/usr/bin/env python3
"""Q55 A3: durable serial comparison on TC-70/74/84/92 only."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import re
import statistics
import sys

import q55_quality_holdout as core


TASK = core.TASK
ROOT = TASK / "focused-A3"
SCENARIOS = ["TC-70", "TC-74", "TC-84", "TC-92"]
SCENARIO_SET = set(SCENARIOS)
MAX_POINTS = 8

core.LOGS = ROOT / "logs"
core.RUNS = ROOT / "runs"
core.RECEIPTS = ROOT / "receipts"
core.PROGRESS = core.RUNS / "progress.json"
core.GUARDS = core.RECEIPTS / "resource-guards.jsonl"


def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def focused_command(arm: dict, port: int, seed: int, json_path: Path, report_dir: Path) -> list[str]:
    command = core.tool_eval_command(arm, port, seed, json_path, report_dir)
    index = command.index("--hardmode-only")
    command[index:index + 1] = ["--scenarios", *SCENARIOS]
    return command


def validate_focused_seed(json_path: Path, exit_code: int, seed: int) -> dict:
    if exit_code != 0:
        return {"valid": False, "reason": f"tool-eval-bench exit {exit_code}"}
    if not json_path.is_file():
        return {"valid": False, "reason": "faltó el JSON final del subset"}
    try:
        raw = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"valid": False, "reason": f"JSON inválido: {exc}"}
    scores = raw.get("scores") or {}
    scenarios = scores.get("scenario_results") or []
    ids = [item.get("scenario_id") for item in scenarios]
    if raw.get("status") not in {"completed", "complete", "success"}:
        return {"valid": False, "reason": f"status subset inesperado: {raw.get('status')!r}"}
    if raw.get("tool_eval_bench_version") != "2.8.0":
        return {"valid": False, "reason": "versión Tool-Eval distinta de 2.8.0"}
    if ids != SCENARIOS:
        return {"valid": False, "reason": f"IDs del subset no coinciden: {ids!r}"}
    if any(item.get("status") not in {"pass", "partial", "fail"} for item in scenarios):
        return {"valid": False, "reason": "hay escenario sin estado puntuable"}
    if any(item.get("error") for item in scenarios):
        return {"valid": False, "reason": "el subset registró error API/parser"}
    config = raw.get("config") or {}
    params = config.get("extra_params") or {}
    if config.get("seed") != seed or config.get("backend") != "llamacpp" or config.get("scenario_count") != len(SCENARIOS):
        return {"valid": False, "reason": "seed/backend/count no coincide con el preregistro A3"}
    if params.get("chat_template_kwargs") != core.EXPECTED_CHAT_KWARGS["chat_template_kwargs"]:
        return {"valid": False, "reason": "reasoning_effort no coincide"}
    if params.get("top_p") != 0.95 or params.get("top_k") != 20 or params.get("min_p") != 0.0:
        return {"valid": False, "reason": "sampling registrado no coincide"}
    points = sum(int(item.get("points", 0)) for item in scenarios)
    max_points = int(scores.get("max_points", 0))
    if points != int(scores.get("total_points", -1)) or max_points != MAX_POINTS:
        return {"valid": False, "reason": "auditoría de puntos del subset no coincide con 8 máximos"}
    score_percent = points * 100 / max_points
    raw_score = float(scores.get("final_score", -1))
    if abs(raw_score - score_percent) > 0.51 or abs(float(raw.get("final_score", -1)) - raw_score) > 0.01:
        return {"valid": False, "reason": "auditoría independiente del score del subset falló"}
    by_id = {item["scenario_id"]: item for item in scenarios}
    critical = {key: by_id[key]["status"] for key in ("TC-74", "TC-84", "TC-92")}
    warnings = raw.get("safety_warnings") or scores.get("safety_warnings") or []
    critical_warnings = [warning for warning in warnings if re.search(r"\bTC-(?:74|84|92)\b", str(warning))]
    api_errors = [
        item["scenario_id"] for item in scenarios
        if re.search(r"(?:HTTP\s+[45]\d\d|API request failed|response parse failed|invalid tool_calls payload)", item.get("raw_log") or "", re.I)
    ]
    if api_errors:
        return {"valid": False, "reason": "errores API/parser: " + ", ".join(api_errors)}
    return {
        "valid": True, "scope": "focused_screen_only", "score": round(score_percent, 3),
        "points": points, "max_points": max_points, "scenario_count": len(scenarios),
        "scenario_ids": ids, "scenario_status_counts": {
            state: sum(item.get("status") == state for item in scenarios) for state in ("pass", "partial", "fail")
        },
        "critical_scenarios": critical, "critical_all_pass": all(v == "pass" for v in critical.values()),
        "critical_safety_warnings": critical_warnings, "safety_warnings": warnings,
        "scenario_durations_seconds": {item["scenario_id"]: item.get("duration_seconds") for item in scenarios},
        "run_id": raw.get("run_id"), "json_sha256": core.sha256(json_path),
    }


def import_q54_baseline43(progress: dict) -> None:
    q54 = core.REPO / "artifacts/evaluacion-modelos-llamacode/Q-20261023-VF-ITERATION-54"
    source_json = q54 / "runs/baseline-seed43.json"
    receipt = json.loads((q54 / "receipts/baseline-seed43-result.json").read_text(encoding="utf-8"))
    prereg = json.loads((q54 / "receipts/preregistration.json").read_text(encoding="utf-8"))
    if receipt.get("task_id") != "Q-20261023-VF-ITERATION-54" or receipt.get("seed") != 43 or receipt.get("status") != "valid_seed":
        raise RuntimeError("Q54 baseline43 no es técnicamente válido")
    if prereg.get("baseline", {}).get("model_sha256") != "7e78da5d7e3ae28d178121f58646953305f3e5bd3cb46f4a75584e8b6c6fe169":
        raise RuntimeError("Q54 baseline43 usa otro GGUF")
    if prereg.get("baseline", {}).get("baseline_commit") != "39eab74a05d3e68ac822b6dc6cd78c90cb985c19" or prereg.get("baseline", {}).get("tool_eval_commit") != "0a1ba68c7709f429298bc92417a9e003f61de4e3":
        raise RuntimeError("Q54 baseline43 runtime/harness no coincide con Q55")
    if not source_json.is_file() or core.sha256(source_json) != receipt.get("json_sha256"):
        raise RuntimeError("SHA de Q54 baseline43 no coincide")
    full_validation = core.validate_seed(source_json, 0, 43)
    if not full_validation.get("valid") or full_validation.get("json_sha256") != receipt.get("json_sha256"):
        raise RuntimeError("revalidación completa de Q54 baseline43 falló")
    raw = json.loads(source_json.read_text(encoding="utf-8"))
    results = raw["scores"]["scenario_results"]
    selected = [item for item in results if item.get("scenario_id") in SCENARIO_SET]
    if [item.get("scenario_id") for item in selected] != SCENARIOS:
        raise RuntimeError("Q54 no contiene los cuatro escenarios A3 en orden")
    points = sum(int(item.get("points", 0)) for item in selected)
    by_id = {item["scenario_id"]: item for item in selected}
    warnings = raw.get("safety_warnings") or raw.get("scores", {}).get("safety_warnings") or []
    focused_warnings = [w for w in warnings if re.search(r"\bTC-(?:74|84|92)\b", str(w))]
    result = {
        "valid": True, "scope": "focused_screen_only", "arm": "baseline", "runtime": "llama.cpp MTP2",
        "seed": 43, "score": round(points * 100 / MAX_POINTS, 3), "points": points,
        "max_points": MAX_POINTS, "scenario_count": len(selected), "scenario_ids": SCENARIOS,
        "scenario_status_counts": {state: sum(x.get("status") == state for x in selected) for state in ("pass", "partial", "fail")},
        "critical_scenarios": {key: by_id[key]["status"] for key in ("TC-74", "TC-84", "TC-92")},
        "critical_all_pass": all(by_id[key]["status"] == "pass" for key in ("TC-74", "TC-84", "TC-92")),
        "critical_safety_warnings": focused_warnings, "safety_warnings": warnings,
        "scenario_durations_seconds": {item["scenario_id"]: item.get("duration_seconds") for item in selected},
        "json_path": str(source_json), "json_sha256": receipt["json_sha256"],
        "source_task_id": "Q-20261023-VF-ITERATION-54", "source_full_suite_valid": True,
        "reused_without_inference": True,
    }
    progress.setdefault("seeds", {}).setdefault("baseline", {})["43"] = result
    core.atomic_json(core.RECEIPTS / "baseline43-focused-projection.json", {
        "source_json_sha256": receipt["json_sha256"], "source_full_validation": full_validation,
        "scenario_ids": SCENARIOS, "points": points, "max_points": MAX_POINTS,
        "score_percent": result["score"], "critical_scenarios": result["critical_scenarios"],
        "reused_without_inference": True,
    })
    core.write_progress(progress, stage="Q54 baseline43 full result projected to A3 focused scenarios")


def require_preregistration_and_sheet_readback() -> dict:
    prereg_path = TASK / "receipts/preregistration-amendment-A3.json"
    sheet_receipt_path = ROOT / "receipts/google-sheet-sync-amendment-A3.json"
    if not prereg_path.is_file() or not sheet_receipt_path.is_file():
        raise RuntimeError("A3 requiere preregistro local y readback confirmado de Google Sheets")
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    sheet = json.loads(sheet_receipt_path.read_text(encoding="utf-8"))
    if prereg.get("amendment") != "A3" or prereg.get("status") != "ready_after_sheet_readback":
        raise RuntimeError("A3 no tiene estado de preregistro autorizado")
    if prereg.get("runner", {}).get("sha256") != core.sha256(Path(__file__)):
        raise RuntimeError("SHA del runner A3 no coincide con el preregistro")
    if not sheet.get("readback_verified"):
        raise RuntimeError("Google Sheets A3 todavía no tiene readback verificado")
    required = {
        "Evaluaciones LlamaCode!A285:J285",
        "Accionables!D8:N8",
        "IA local!A34:J34",
        "IA local!K34",
        "IA local!L34:O34",
    }
    if set(sheet.get("ranges_verified", [])) != required:
        raise RuntimeError("el recibo de Sheet no verifica los tres rangos A3")
    if (ROOT / "runs/progress.json").exists():
        raise RuntimeError("ya existe un checkpoint A3; no se sobreescribe ni reejecuta automáticamente")
    return {"preregistration": str(prereg_path), "sheet_readback_receipt": str(sheet_receipt_path)}


def run_focused() -> int:
    gates = require_preregistration_and_sheet_readback()
    for path in (core.LOGS, core.RUNS, core.RECEIPTS):
        path.mkdir(parents=True, exist_ok=True)
    cg = core.cgroup_dir()
    core.cgroup_properties(cg)
    core.lock_record()
    progress = {
        "task_id": "Q-20261023-VF-ITERATION-55", "amendment": "A3",
        "scope": "TC-70,TC-74,TC-84,TC-92 only; not a full Hard Mode score",
        "lock_token": core.TOKEN, "status": "running", "created_at_utc": utc(),
        "preregistration_gates": gates,
        "smokes": {}, "seeds": {}, "server_starts": [], "quality_servers": [],
        "tool_eval_processes": [], "seed_attempts": [], "cleanup": [], "invocation_history": [],
    }
    import_q54_baseline43(progress)
    core.import_q50_smokes(progress)
    for arm in core.ARMS:
        if progress["smokes"].get(arm["name"], {}).get("status") != "passed":
            raise RuntimeError(f"A3 requires previously audited Q50 smoke for {arm['name']}; no new smoke request")
    progress["invocation"] = 1
    progress["invocation_history"].append({"invocation": 1, "started_at_utc": utc(), "cgroup_path": str(cg), "cgroup": core.cgroup_properties(cg)})
    core.write_progress(progress, stage="A3 fresh preflight")
    pre = core.preflight("Q55 A3 focused start", cg)
    core.atomic_json(core.RECEIPTS / "preflight-A3.json", pre)

    for arm in core.ARMS:
        name = arm["name"]
        results = progress.setdefault("seeds", {}).setdefault(name, {})
        missing = [seed for seed in core.SEEDS if str(seed) not in results]
        server = log = None
        if not missing:
            continue
        try:
            server, log, port, start_record = core.start_server(arm, 1, cg, progress, "focused_quality")
            progress["quality_servers"].append(start_record | {"port": port})
            for seed in missing:
                core.guard(f"A3 {name} seed {seed} preflight", cg, server.pid, progress)
                output = core.RUNS / name / f"seed-{seed}.json"
                reports = core.RUNS / name / f"reports-seed-{seed}"
                work = TASK / "work" / f"a3-tooleval-{name}-seed-{seed}"
                output.parent.mkdir(parents=True, exist_ok=True)
                work.mkdir(parents=True, exist_ok=True)
                log_path = core.LOGS / f"{name}-seed-{seed}-tool-eval.log"
                command = focused_command(arm, port, seed, output, reports)
                progress["seed_attempts"].append({"arm": name, "seed": seed, "invocation": 1, "started_at_utc": utc(), "command": command, "json": str(output), "log": str(log_path), "status": "running", "scenario_ids": SCENARIOS})
                core.write_progress(progress, stage=f"A3 {name} seed {seed}: starting focused suite")
                try:
                    rc, timing = core.run_monitored(command, log_path, arm, seed, work, cg, server.pid, progress)
                except Exception as run_error:
                    attempt = progress["seed_attempts"][-1]
                    attempt.update(status="blocked_invalid_no_retry", completed_at_utc=utc(), failure=f"{type(run_error).__name__}: {run_error}")
                    failed_result = {
                        "valid": False, "scope": "focused_screen_only", "arm": name,
                        "runtime": arm["runtime"], "seed": seed,
                        "failure": f"{type(run_error).__name__}: {run_error}",
                        "json_path": str(output), "json_sha256": core.sha256(output) if output.is_file() else None,
                        "tool_eval_log": str(log_path), "scenario_ids": SCENARIOS,
                        "retry_allowed": False,
                    }
                    results[str(seed)] = failed_result
                    core.atomic_json(core.RECEIPTS / f"seed-{name}-{seed}.json", failed_result)
                    core.write_progress(progress, stage=f"A3 {name} seed {seed}: blocked; no automatic retry")
                    raise
                validation = validate_focused_seed(output, rc, seed)
                result = {
                    "valid": validation["valid"], "scope": "focused_screen_only", "arm": name,
                    "runtime": arm["runtime"], "seed": seed, "exit_code": rc,
                    "json_path": str(output), "json_sha256": core.sha256(output) if output.is_file() else None,
                    "tool_eval_log": str(log_path), "timing": timing, "validation": validation,
                }
                if validation["valid"]:
                    result.update({k: validation[k] for k in ("score", "points", "max_points", "scenario_count", "scenario_ids", "scenario_status_counts", "critical_scenarios", "critical_all_pass", "critical_safety_warnings", "safety_warnings", "scenario_durations_seconds", "run_id")})
                results[str(seed)] = result
                progress["seed_attempts"][-1].update(status="valid" if validation["valid"] else "invalid", completed_at_utc=utc(), exit_code=rc, validation=validation)
                core.atomic_json(core.RECEIPTS / f"seed-{name}-{seed}.json", result)
                core.write_progress(progress, stage=f"A3 {name} seed {seed}: {'valid' if validation['valid'] else 'invalid'}")
                if not validation["valid"]:
                    progress["status"] = "seed_invalid"
                    progress["failure"] = f"{name} seed {seed}: {validation['reason']}"
                    core.write_progress(progress, stage="A3 invalid seed; stop without retry")
                    return 2
            cleanup = core.stop_server(server, log, name, port)
            progress["cleanup"].append(cleanup)
            core.write_progress(progress, stage=f"A3 {name} focused cleanup confirmed")
        except Exception as exc:
            if server is not None and log is not None:
                try:
                    progress["cleanup"].append(core.stop_server(server, log, name, port))
                except Exception as cleanup_error:
                    progress.setdefault("cleanup_errors", []).append(str(cleanup_error))
            progress["status"] = "blocked"
            progress["failure"] = f"{name}: {type(exc).__name__}: {exc}"
            core.write_progress(progress, stage="A3 blocked; preserve checkpoint")
            raise

    summary = core.aggregate(progress)
    old_candidates = summary.get("decision", {}).pop("candidates", {})
    summary["scope"] = {"scenario_ids": SCENARIOS, "points_scale": f"0–{MAX_POINTS}", "full_suite_score": False, "tps_measured": False}
    summary["decision"]["focused_screen_comparisons"] = old_candidates
    summary["decision"]["adoption_eligible"] = {"openjet_d3": False, "openjet_d4": False}
    summary["decision"]["adoption_note"] = "A3 sólo compara un screening de cuatro escenarios; no basta para adopción ni para afirmar superioridad general. TC-92 tenant disclosure bloquea adopción sin excepción."
    core.atomic_json(core.RECEIPTS / "decision-audit-A3.json", summary)
    progress["status"] = "completed"
    progress["summary"] = summary
    progress["completed_at_utc"] = utc()
    core.write_progress(progress, stage="A3 all focused seeds complete")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0


def main() -> int:
    try:
        return run_focused()
    except Exception as exc:
        try:
            if core.PROGRESS.is_file():
                progress = json.loads(core.PROGRESS.read_text(encoding="utf-8"))
                if progress.get("status") == "running":
                    progress["status"] = "blocked"
                    progress["failure"] = f"{type(exc).__name__}: {exc}"
                    core.write_progress(progress, stage="A3 blocked; preserve checkpoint")
        except Exception:
            pass
        print(f"Q55 A3 BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
