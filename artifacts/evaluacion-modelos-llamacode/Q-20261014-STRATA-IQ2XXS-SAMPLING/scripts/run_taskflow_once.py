#!/usr/bin/env python3
"""Run one fixed TaskFlow ULTRA seed using the isolated evaluation binary."""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request


TASK_ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]
APP_SCRIPT = TASK_ROOT / "scripts/start-llamacode-headless.sh"
TASKFLOW_RUNNER = REPO_ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261014-R9700-TASKFLOW/scripts/run_taskflow.py"
BASE = "http://127.0.0.1:8898"


def wait_health(proc: subprocess.Popen, timeout_sec: int) -> None:
    deadline = time.monotonic() + timeout_sec
    last_error = "not tried"
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"LlamaCode exited early with status {proc.returncode}")
        try:
            with urllib.request.urlopen(BASE + "/health", timeout=3) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError) as exc:
            last_error = str(exc)
        time.sleep(2)
    raise TimeoutError(f"LlamaCode health endpoint did not become ready: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--temperature", required=True, type=float)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--max-wait", type=int, default=2100)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    label = f"Q-20261014 IQ2_XS TaskFlow sampling T{args.temperature:g} seed{args.seed}"
    app_log_path = TASK_ROOT / "receipts" / f"app-T{args.temperature:g}-seed{args.seed}.log"
    runner_log_path = args.out.with_suffix(".runner.log")
    launcher_receipt = args.out.with_suffix(".launcher.json")
    env = os.environ.copy()
    env["LLAMACODE_EVAL_TEMPERATURE"] = str(args.temperature)
    env["LLAMACODE_EVAL_SEED"] = str(args.seed)
    started = time.time()
    app_log_path.parent.mkdir(parents=True, exist_ok=True)
    runner_exit = None
    app = None
    error = None
    with app_log_path.open("w", encoding="utf-8") as app_log, runner_log_path.open("w", encoding="utf-8") as runner_log:
        try:
            app = subprocess.Popen(["bash", str(APP_SCRIPT)], cwd=REPO_ROOT,
                                   env=env, stdout=app_log, stderr=subprocess.STDOUT)
            wait_health(app, 300)
            command = [
                sys.executable, str(TASKFLOW_RUNNER),
                "--profile", "q14-iq2xs-sampling-taskflow",
                "--suite", "qwen38_taskflow_ultra_ast_vs_sol_20261006",
                "--label", label, "--timeout", str(args.timeout),
                "--max-wait", str(args.max_wait), "--base", BASE,
                "--out", str(args.out),
            ]
            completed = subprocess.run(command, cwd=REPO_ROOT, env=env,
                                       stdout=runner_log, stderr=subprocess.STDOUT,
                                       timeout=args.max_wait + 120, check=False)
            runner_exit = completed.returncode
            if runner_exit != 0:
                error = f"TaskFlow runner exited with status {runner_exit}"
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        finally:
            if app is not None and app.poll() is None:
                app.terminate()
                try:
                    app.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    app.kill()
                    app.wait(timeout=10)

    result = None
    if args.out.exists():
        try:
            raw = json.loads(args.out.read_text(encoding="utf-8"))
            rows = [r for r in raw.get("benchmarkResults", []) if r.get("mode") == "custom"]
            result = rows[-1] if rows else None
            if result:
                if float(result.get("agentTemperature", -1)) != args.temperature:
                    error = f"effective temperature mismatch: {result.get('agentTemperature')}"
                if int(result.get("agentSeed", -1)) != args.seed:
                    error = f"effective seed mismatch: {result.get('agentSeed')}"
        except Exception as exc:
            error = f"invalid result JSON: {exc}"

    if result is None and error is None:
        error = "TaskFlow result JSON has no custom benchmark result"
    launcher_receipt.write_text(json.dumps({
        "label": label,
        "temperature_requested": args.temperature,
        "seed_requested": args.seed,
        "timeout_sec": args.timeout,
        "max_wait_sec": args.max_wait,
        "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        "finished_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runner_exit_code": runner_exit,
        "error": error,
        "app_log": str(app_log_path),
        "runner_log": str(runner_log_path),
        "result_json": str(args.out),
        "effective_temperature": result.get("agentTemperature") if result else None,
        "effective_seed": result.get("agentSeed") if result else None,
        "final_score": [result.get("finalScore"), result.get("finalTotal")] if result else None,
        "first_pass_score": [result.get("firstAttemptScore"), result.get("firstAttemptTotal")] if result else None,
        "repair_attempts": result.get("repairAttempts") if result else None,
        "elapsed_sec": result.get("elapsedSec") if result else None,
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"temperature": args.temperature, "seed": args.seed,
                      "runner_exit": runner_exit, "error": error,
                      "result": str(args.out), "receipt": str(launcher_receipt)}), flush=True)
    return 0 if error is None and runner_exit == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
