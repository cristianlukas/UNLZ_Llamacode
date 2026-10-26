#!/usr/bin/env python3
"""Run Q154 Tool-Eval cells serially on the two pinned Strata profiles."""
from __future__ import annotations

import hashlib
import argparse
import json
import os
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_throughput_arm as common  # noqa: E402

TASK = common.TASK
REPO = TASK.parents[2]
ROOT_BASE = TASK / "runs" / "tool-eval"
ATTEMPT_LABEL = "01"
ROOT = ROOT_BASE / f"campaign-{ATTEMPT_LABEL}"
RECEIPTS = TASK / "receipts"
TOOL_EVAL_ROOT = Path("/home/cristian/.cache/codex-tool-eval-bench-v2.8.0")
TOOL_EVAL = TOOL_EVAL_ROOT / ".venv/bin/tool-eval-bench"
TOOL_EVAL_COMMIT = "0a1ba68c7709f429298bc92417a9e003f61de4e3"
PORT = 8350
BASE_URL = f"http://127.0.0.1:{PORT}"
SCENARIO_IDS = [f"TC-{n}" for n in range(70, 98)]
SCHEDULE = ((42, "control"), (42, "candidate"), (43, "candidate"),
            (43, "control"), (44, "control"), (44, "candidate"))
SAFETY_ID = re.compile(r"\bTC-\d+\b")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def model_config(arm: str) -> tuple[Path, dict]:
    config_path = TASK / "configs" / ("astra-rco-iq2xs-32k.json" if arm == "control" else "huihui-v2-32k.json")
    return config_path, json.loads(config_path.read_text(encoding="utf-8"))


def assert_port_free() -> None:
    with socket.socket() as sock:
        sock.settimeout(0.3)
        if sock.connect_ex(("127.0.0.1", PORT)) == 0:
            raise RuntimeError(f"127.0.0.1:{PORT} already has a listener")


def model_rows() -> dict:
    with urllib.request.urlopen(BASE_URL + "/v1/models", timeout=5) as response:
        return json.loads(response.read())


def profile_engine_pids(cfg: dict) -> list[int]:
    """Identify the exact detached engine child owned by this profile."""
    expected = {}
    for flag in ("--pack", "--native", "--ple-gguf", "--expert-profile"):
        try:
            expected[flag] = cfg["args"][cfg["args"].index(flag) + 1]
        except (ValueError, IndexError) as exc:
            raise RuntimeError(f"profile is missing {flag}") from exc
    engine_path = str(Path(cfg["exe"]).resolve())
    pids = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            argv = [x.decode(errors="replace") for x in (entry / "cmdline").read_bytes().split(b"\0") if x]
            if not argv or str(Path(argv[0]).resolve()) != engine_path or "--serve" not in argv:
                continue
            if all(flag in argv and argv[argv.index(flag) + 1] == value for flag, value in expected.items()):
                pids.append(int(entry.name))
        except (OSError, ValueError, IndexError, ProcessLookupError):
            continue
    return pids


def assert_no_external_servers(owned_pgid: int | None = None, owned_pids: set[int] | None = None) -> list[dict]:
    """Refuse unexpected servers, while allowing this runner's process group."""
    owned_pids = owned_pids or set()
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            args = [x.decode(errors="replace") for x in (entry / "cmdline").read_bytes().split(b"\0") if x]
            if not args:
                continue
            joined = " ".join(args).casefold()
            executable = Path(args[0]).name.casefold()
            relevant = ("peritosoft" in joined or "perito-soft" in joined or executable == "llama-server"
                        or (executable == "strata" and (" serve " in f" {joined} "
                            or "/runtime/components/engine/" in joined)))
            if not relevant or pid in owned_pids:
                continue
            stat = (entry / "stat").read_text()
            close = stat.rfind(")")
            fields = stat[close + 2:].split()
            pgrp = int(fields[2])  # /proc/PID/stat field 5, after pid/comm.
            if owned_pgid is not None and pgrp == owned_pgid:
                continue
            found.append({"pid": pid, "pgrp": pgrp, "argv": args[:12]})
        except (OSError, ValueError, IndexError, ProcessLookupError):
            continue
    return found


def preflight() -> dict:
    common.lock_check()
    if not TOOL_EVAL.is_file():
        raise RuntimeError(f"Tool-Eval binary is missing: {TOOL_EVAL}")
    version = subprocess.run([str(TOOL_EVAL), "--version"], cwd=str(TOOL_EVAL_ROOT),
                             capture_output=True, text=True, timeout=30, check=True)
    commit = subprocess.run(["git", "-C", str(TOOL_EVAL_ROOT), "rev-parse", "HEAD"],
                            capture_output=True, text=True, timeout=30, check=True).stdout.strip()
    if "2.8.0" not in version.stdout + version.stderr or commit != TOOL_EVAL_COMMIT:
        raise RuntimeError(f"Tool-Eval pin mismatch: {version.stdout!r}, {commit}")
    external = assert_no_external_servers()
    if external:
        raise RuntimeError("external inference/PeritoSoft server present: " + json.dumps(external))
    assert_port_free()
    gpus = common.gpu_rows()
    if len(gpus) != 2 or any("3090" not in row["name"] for row in gpus):
        raise RuntimeError("expected dual RTX 3090 preflight failed: " + json.dumps(gpus))
    if any(row["temperature_c"] is not None and row["temperature_c"] >= 85 for row in gpus):
        raise RuntimeError("a GPU is already at the 85 C stop threshold")
    configs = {}
    for arm in ("control", "candidate"):
        path, cfg = model_config(arm)
        if not Path(cfg["exe"]).is_file():
            raise RuntimeError(f"engine missing for {arm}: {cfg['exe']}")
        for key in ("--pack", "--native", "--ple-gguf", "--expert-profile"):
            try:
                value = cfg["args"][cfg["args"].index(key) + 1]
            except (ValueError, IndexError) as exc:
                raise RuntimeError(f"missing {key} for {arm}") from exc
            if not Path(value).exists():
                raise RuntimeError(f"missing {key} target for {arm}: {value}")
        if cfg["gpu"] != [0, 1] or cfg["port"] != PORT or cfg["sampling"] != {
            "temperature": 0.6, "top_p": 0.95, "top_k": 20, "min_p": 0.0,
            "repetition_penalty": 1.0, "presence_penalty": 0.0,
        }:
            raise RuntimeError(f"profile drift for {arm}: {cfg}")
        configs[arm] = {"path": str(path), "sha256": sha256(path), "model_name": cfg["model_name"],
                        "exe": cfg["exe"], "exe_sha256": sha256(Path(cfg["exe"])),
                        "pack": cfg["args"][cfg["args"].index("--pack") + 1],
                        "native": cfg["args"][cfg["args"].index("--native") + 1],
                        "ple_gguf": cfg["args"][cfg["args"].index("--ple-gguf") + 1],
                        "expert_profile": cfg["args"][cfg["args"].index("--expert-profile") + 1],
                        "gpu": cfg["gpu"], "context": 32768, "sampling": cfg["sampling"]}
    free_disk = __import__("shutil").disk_usage(TASK).free
    return {"recorded_utc": common.utc_now(), "lock_token": common.LOCK_TOKEN,
            "tool_eval_version": (version.stdout + version.stderr).strip(), "tool_eval_commit": commit,
            "external_inference_servers": external, "port_free": True, "gpus": gpus,
            "memory": common.memory_snapshot(), "free_disk_bytes": free_disk, "profiles": configs}


def launch_server(arm: str, seed: int, cell: Path):
    common.lock_check()
    existing = assert_no_external_servers()
    if existing:
        raise RuntimeError("external server appeared before model load: " + json.dumps(existing))
    assert_port_free()
    config_path, cfg = model_config(arm)
    plan = subprocess.run([str(common.STRATA), "serve", "--profile", str(config_path),
                           "--host", "127.0.0.1", "--port", str(PORT), "--offline", "--plan", "--output", "json"],
                          cwd=str(common.STRATA.parent.parent), capture_output=True, text=True, timeout=45)
    write_json(cell / "offline-plan.json", {"exit_code": plan.returncode, "stdout": plan.stdout, "stderr": plan.stderr})
    if plan.returncode != 0 or "--gpu" not in plan.stdout or "0,1" not in plan.stdout:
        raise RuntimeError("offline plan failed or did not select both GPUs")
    before_gpu = common.gpu_rows()
    before_mem = common.memory_snapshot()
    private = Path(tempfile.mkdtemp(prefix=f"q154-tool-eval-{arm}-{seed}-"))
    os.chmod(private, 0o700)
    ready = private / "ready.json"
    config_path, _ = model_config(arm)
    log_path = cell / "server.log"
    env = os.environ.copy()
    env["STRATA_PREFILL_CPU_SHARE"] = "0"
    with log_path.open("wb") as log:
        proc = subprocess.Popen([str(common.STRATA), "serve", "--profile", str(config_path),
                                 "--host", "127.0.0.1", "--port", str(PORT), "--offline",
                                 "--ready-file", str(ready), "--shutdown-timeout", "90"],
                                cwd=str(common.STRATA.parent.parent), env=env, stdout=log,
                                stderr=subprocess.STDOUT, start_new_session=True)
    guard = common.Guard(cell, proc, common.oom_count(before_mem))
    guard.start()
    started = time.monotonic()
    try:
        while time.monotonic() - started < 1200:
            common.lock_check()
            if proc.poll() is not None:
                raise RuntimeError(f"Strata exited before ready: {proc.returncode}")
            if guard.abort_reason:
                raise RuntimeError(guard.abort_reason)
            try:
                ready_data = json.loads(ready.read_text(encoding="utf-8"))
                models = model_rows()
                break
            except (OSError, urllib.error.URLError, json.JSONDecodeError):
                time.sleep(3)
        else:
            raise TimeoutError("owned Strata ready file did not appear within 20 minutes")
        loaded_gpu = common.gpu_rows()
        delta = [loaded["memory_used_mib"] - before["memory_used_mib"]
                 for before, loaded in zip(before_gpu, loaded_gpu)]
        if len(delta) != 2 or min(delta) < 1024:
            raise RuntimeError(f"dual-GPU allocation <1 GiB/card: {delta}")
        model_ids = [entry.get("id") for entry in models.get("data", [])]
        if cfg["model_name"] not in model_ids:
            raise RuntimeError(f"/v1/models omitted the pinned alias {cfg['model_name']}: {model_ids}")
        engine_pids = profile_engine_pids(cfg)
        if not engine_pids:
            raise RuntimeError("could not associate the detached engine with this exact profile")
        write_json(cell / "server-ready.json", {"recorded_utc": common.utc_now(), "pid": proc.pid,
                   "load_s": round(time.monotonic() - started, 3), "ready": ready_data, "models": models,
                   "gpu_before": before_gpu, "gpu_loaded": loaded_gpu, "gpu_delta_mib": delta,
                   "memory_before": before_mem, "owned_engine_pids": engine_pids})
        print(json.dumps({"event": "READY", "arm": arm, "seed": seed, "load_s": round(time.monotonic()-started, 3),
                          "gpu_delta_mib": delta, "owned_engine_pids": engine_pids}, separators=(",", ":")), flush=True)
        return proc, guard, ready, set(engine_pids)
    except BaseException:
        try:
            os.killpg(proc.pid, signal.SIGINT)
            proc.wait(timeout=100)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=15)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        guard.close()
        raise


def safety_ids(result: dict) -> set[str]:
    values = result.get("safety_warnings", [])
    if isinstance(result.get("safety_gate"), dict):
        values = list(values) + list(result["safety_gate"].get("warnings", []))
    return {match.group(0) for value in values if (match := SAFETY_ID.search(str(value)))}


def validate_result(path: Path, exit_code: int) -> dict:
    if not path.is_file():
        raise RuntimeError(f"Tool-Eval did not write result JSON (exit {exit_code})")
    result = json.loads(path.read_text(encoding="utf-8"))
    if result.get("tool_eval_bench_version") != "2.8.0":
        raise RuntimeError("Tool-Eval result version mismatch")
    rows = result.get("scores", {}).get("scenario_results", [])
    ids = [row.get("scenario_id") for row in rows]
    if len(rows) != 28 or sorted(ids) != SCENARIO_IDS:
        raise RuntimeError(f"expected exact TC-70..TC-97 set; received {ids}")
    if exit_code not in (0, 2):
        raise RuntimeError(f"Tool-Eval exited {exit_code}; preserve partial JSON and stop without retry")
    return result


def run_cell(seed: int, arm: str) -> dict:
    global CELL_STARTED
    CELL_STARTED = time.monotonic()
    common.lock_check()
    cell = ROOT / f"seed-{seed}-{arm}"
    cell.mkdir(parents=True, exist_ok=False)
    (cell / "data").mkdir()
    (cell / "reports").mkdir()
    config_path, cfg = model_config(arm)
    preflight = {"recorded_utc": common.utc_now(), "arm": arm, "seed": seed,
                 "lock_token": common.LOCK_TOKEN, "external_servers": assert_no_external_servers(),
                 "gpus": common.gpu_rows(), "memory": common.memory_snapshot(),
                 "port_free": True, "config": str(config_path), "config_sha256": sha256(config_path)}
    if preflight["external_servers"]:
        raise RuntimeError("external inference server active before cell")
    assert_port_free()
    write_json(cell / "preflight.json", preflight)
    proc = None
    guard = None
    eval_proc = None
    ready = None
    failure = None
    try:
        proc, guard, ready, owned_engine_pids = launch_server(arm, seed, cell)
        result_path = cell / "result.json"
        cmd = [str(TOOL_EVAL), "run", "--backend", "strata", "--format", "openai",
               "--base-url", BASE_URL + "/v1", "--model", cfg["model_name"],
               "--temperature", "0.6", "--top-p", "0.95", "--top-k", "20", "--min-p", "0",
               "--repeat-penalty", "1", "--seed", str(seed), "--variant-seed", "20261010",
               "--hardmode-only", "--timeout", "120", "--max-turns", "8", "--parallel", "1",
               "--context-size", "32768", "--backend-kwargs", '{"reasoning_effort":"medium"}',
               "--label", f"Q154-{arm}-seed-{seed}", "--fail-on-safety", "--json-file", str(result_path),
               "--output-dir", str(cell / "reports"), "--no-live"]
        env = os.environ.copy()
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            env.pop(key, None)
        env["NO_PROXY"] = "127.0.0.1,localhost"
        write_json(cell / "tool-eval-command.json", {"argv": cmd, "cwd": str(cell), "isolated_db": str(cell / "data/benchmarks.sqlite"),
                   "scenario_ids": SCENARIO_IDS, "safety_gate_exit_2_is_valid_if_json_complete": True})
        log_path = cell / "tool-eval.log"
        with log_path.open("wb") as log:
            eval_proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env,
                                         cwd=str(cell), start_new_session=True)
            next_sample = 0.0
            while eval_proc.poll() is None:
                common.lock_check()
                external = assert_no_external_servers(owned_pgid=proc.pid, owned_pids=owned_engine_pids)
                if external:
                    raise RuntimeError("unexpected inference server appeared: " + json.dumps(external))
                if proc.poll() is not None:
                    raise RuntimeError(f"owned Strata exited during Tool-Eval: {proc.returncode}")
                if guard.abort_reason:
                    raise RuntimeError(guard.abort_reason)
                if time.monotonic() >= next_sample:
                    with (cell / "progress.jsonl").open("a", encoding="utf-8") as stream:
                        stream.write(json.dumps({"recorded_utc": common.utc_now(), "tool_eval_pid": eval_proc.pid,
                            "server_pid": proc.pid, "elapsed_s": round(time.monotonic() - CELL_STARTED, 2),
                            "gpu": common.gpu_rows(), "memory": common.memory_snapshot()}, separators=(",", ":")) + "\n")
                    next_sample = time.monotonic() + 10
                time.sleep(2)
            exit_code = int(eval_proc.returncode or 0)
        result = validate_result(result_path, exit_code)
        warnings = sorted(safety_ids(result))
        output = {"recorded_utc": common.utc_now(), "seed": seed, "arm": arm,
                  "tool_eval_exit_code": exit_code, "result_path": str(result_path),
                  "result_sha256": sha256(result_path), "final_score": result.get("final_score"),
                  "scenario_count": result.get("total_scenarios"), "safety_warning_ids": warnings,
                  "safety_gate": result.get("safety_gate"), "run_id": result.get("run_id"),
                  "status": result.get("status"), "model_name": cfg["model_name"],
                  "config_sha256": sha256(config_path)}
        write_json(cell / "cell-result.json", output)
        print(json.dumps({"event": "CELL_COMPLETE", "arm": arm, "seed": seed,
                          "score": output["final_score"], "safety_warning_ids": warnings,
                          "tool_eval_exit_code": exit_code}, separators=(",", ":")), flush=True)
        return output
    except BaseException as exc:
        failure = f"{type(exc).__name__}: {exc}"
        write_json(cell / "cell-failure.json", {"recorded_utc": common.utc_now(), "arm": arm,
                    "seed": seed, "failure": failure, "partial_result_exists": (cell / "result.json").exists()})
        raise
    finally:
        if eval_proc is not None and eval_proc.poll() is None:
            try:
                os.killpg(eval_proc.pid, signal.SIGINT)
                eval_proc.wait(timeout=30)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(eval_proc.pid, signal.SIGTERM)
                    eval_proc.wait(timeout=10)
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    pass
        if proc is not None:
            cleanup = {}
            try:
                os.killpg(proc.pid, signal.SIGINT)
                proc.wait(timeout=100)
                cleanup["sigint_exit_code"] = proc.returncode
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                    proc.wait(timeout=15)
                    cleanup["sigterm_exit_code"] = proc.returncode
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait(timeout=10)
                        cleanup["sigkill_exit_code"] = proc.returncode
                    except ProcessLookupError:
                        cleanup["already_exited"] = True
            if guard is not None:
                guard.close()
            time.sleep(2)
            try:
                assert_port_free()
                cleanup["port_free"] = True
            except RuntimeError:
                cleanup["port_free"] = False
            cleanup.update({"remaining_inference_processes": assert_no_external_servers(),
                            "gpu_after": common.gpu_rows(), "memory_after": common.memory_snapshot(),
                            "ready_file_removed": ready is None or not ready.exists(), "failure": failure})
            write_json(cell / "cleanup.json", {"recorded_utc": common.utc_now(), **cleanup})
            if cleanup["remaining_inference_processes"] or not cleanup["port_free"]:
                raise RuntimeError("cleanup gate failed; do not start the next cell")


CELL_STARTED = time.monotonic()


def check_safety_pair(seed: int) -> dict | None:
    control_path = ROOT / f"seed-{seed}-control" / "cell-result.json"
    candidate_path = ROOT / f"seed-{seed}-candidate" / "cell-result.json"
    if not control_path.is_file() or not candidate_path.is_file():
        return None
    control = json.loads(control_path.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    new = sorted(set(candidate["safety_warning_ids"]) - set(control["safety_warning_ids"]))
    pair = {"seed": seed, "control_warnings": control["safety_warning_ids"],
            "candidate_warnings": candidate["safety_warning_ids"], "candidate_new_warning_ids": new,
            "passed": not new}
    write_json(RECEIPTS / f"tool-eval-attempt-{ATTEMPT_LABEL}-safety-pair-seed-{seed}.json", pair)
    return pair


def campaign_preflight() -> None:
    if ROOT.exists():
        raise RuntimeError(f"refusing to overwrite campaign output: {ROOT}")
    ROOT.mkdir(parents=True, exist_ok=False)
    (RECEIPTS / "tool-eval-progress").mkdir(exist_ok=True)
    pf = preflight()
    write_json(RECEIPTS / f"tool-eval-attempt-{ATTEMPT_LABEL}-preflight.json", pf)
    schedule = [{"sequence_index": i, "seed": seed, "arm": arm}
                for i, (seed, arm) in enumerate(SCHEDULE, 1)]
    write_json(RECEIPTS / f"tool-eval-attempt-{ATTEMPT_LABEL}-schedule.json", {"recorded_utc": common.utc_now(), "cells": schedule})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--attempt", default="01", choices=("01", "02", "03"), help="isolated campaign attempt")
    ap.add_argument("--resume", action="store_true", help="continue only after complete cells; never rerun a partial cell")
    args = ap.parse_args()
    global ATTEMPT_LABEL, ROOT
    ATTEMPT_LABEL = args.attempt
    ROOT = ROOT_BASE / f"campaign-{ATTEMPT_LABEL}"
    if args.resume:
        if not ROOT.is_dir():
            raise RuntimeError("no Q154 Tool-Eval campaign directory to resume")
        for child in ROOT.iterdir():
            if child.is_dir() and child.name.startswith("seed-") and not (child / "cell-result.json").is_file():
                raise RuntimeError(f"partial cell {child.name}; preserving evidence and refusing automatic retry")
        resumed = preflight()
        write_json(RECEIPTS / f"tool-eval-attempt-{ATTEMPT_LABEL}-resume-{int(time.time())}.json", resumed)
    else:
        campaign_preflight()
    completed = []
    pairs = []
    try:
        for i, (seed, arm) in enumerate(SCHEDULE, 1):
            if not (ROOT / f"seed-{seed}-{arm}").exists():
                print(json.dumps({"event": "CELL_START", "sequence_index": i, "total": len(SCHEDULE),
                                  "seed": seed, "arm": arm, "recorded_utc": common.utc_now()}, separators=(",", ":")), flush=True)
                cell = run_cell(seed, arm)
            else:
                cell = json.loads((ROOT / f"seed-{seed}-{arm}" / "cell-result.json").read_text())
            completed.append(cell)
            write_json(RECEIPTS / f"tool-eval-attempt-{ATTEMPT_LABEL}-progress.json", {"recorded_utc": common.utc_now(), "completed": completed})
            pair = check_safety_pair(seed)
            if pair is not None and not any(item["seed"] == seed for item in pairs):
                pairs.append(pair)
                if not pair["passed"]:
                    write_json(RECEIPTS / f"tool-eval-attempt-{ATTEMPT_LABEL}-safety-stop.json", {"recorded_utc": common.utc_now(),
                        "stop_after_seed": seed, "reason": "candidate added safety warning(s) absent from paired control",
                        "new_warning_ids": pair["candidate_new_warning_ids"], "completed_cells": completed,
                        "remaining_cells_skipped": [{"seed": s, "arm": a} for s, a in SCHEDULE[i:]]})
                    print(json.dumps({"event": "SAFETY_STOP", "seed": seed,
                                      "new_warning_ids": pair["candidate_new_warning_ids"]}, separators=(",", ":")), flush=True)
                    break
        summary = {"recorded_utc": common.utc_now(), "status": "complete" if len(completed) == len(SCHEDULE) else "stopped_on_safety",
                   "completed_cells": completed, "paired_safety_checks": pairs,
                   "remaining_cells": [{"seed": s, "arm": a} for s, a in SCHEDULE[len(completed):]]}
        write_json(RECEIPTS / f"tool-eval-attempt-{ATTEMPT_LABEL}-final.json", summary)
        print(json.dumps({"event": "CAMPAIGN_COMPLETE", "status": summary["status"],
                          "completed_cells": len(completed), "safety_pairs": len(pairs)}, separators=(",", ":")), flush=True)
        return 0
    except BaseException as exc:
        write_json(RECEIPTS / f"tool-eval-attempt-{ATTEMPT_LABEL}-failure.json", {"recorded_utc": common.utc_now(),
                    "failure": f"{type(exc).__name__}: {exc}", "completed_cells": completed})
        raise


if __name__ == "__main__":
    raise SystemExit(main())
