#!/usr/bin/env python3
"""Run one TaskFlow or coding-smoke suite against the isolated SOL profile."""
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
RUNNER = TASK_ROOT / "scripts/run_taskflow.py"
PROFILE_ID = "c8d4f1a7-2b69-4e80-95c3-7a1d6f8b2045"
BASE = "http://127.0.0.1:8898"


def wait_health(proc, timeout_sec):
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", required=True)
    parser.add_argument("--temperature", required=True, type=float)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--label", required=True)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--max-wait", type=int, default=2100)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    safe_label = args.label.replace("/", "_").replace(" ", "_")
    app_log = TASK_ROOT / "receipts" / f"app-{safe_label}.log"
    runner_log = args.out.with_suffix(".runner.log")
    launcher_receipt = args.out.with_suffix(".launcher.json")
    env = os.environ.copy()
    env["LLAMACODE_EVAL_TEMPERATURE"] = str(args.temperature)
    env["LLAMACODE_EVAL_SEED"] = str(args.seed)
    started = time.time()
    app = None
    error = None
    runner_exit = None
    with app_log.open("w", encoding="utf-8") as app_out, \
            runner_log.open("w", encoding="utf-8") as runner_out:
        try:
            app = subprocess.Popen(["bash", str(APP_SCRIPT)], cwd=REPO_ROOT,
                                   env=env, stdout=app_out,
                                   stderr=subprocess.STDOUT)
            wait_health(app, 300)
            command = [
                sys.executable, str(RUNNER),
                "--profile", PROFILE_ID,
                "--suite", args.suite,
                "--label", args.label,
                "--timeout", str(args.timeout),
                "--max-wait", str(args.max_wait),
                "--base", BASE,
                "--out", str(args.out),
            ]
            completed = subprocess.run(command, cwd=REPO_ROOT, env=env,
                                       stdout=runner_out,
                                       stderr=subprocess.STDOUT,
                                       timeout=args.max_wait + 120,
                                       check=False)
            runner_exit = completed.returncode
            if runner_exit != 0:
                error = f"Suite runner exited with status {runner_exit}"
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
            rows = [row for row in raw.get("benchmarkResults", [])
                    if row.get("mode") == "custom"
                    and row.get("profileId") == PROFILE_ID]
            result = rows[-1] if rows else None
            if result and float(result.get("agentTemperature", -1)) != args.temperature:
                error = f"temperature mismatch: {result.get('agentTemperature')}"
            if result and int(result.get("agentSeed", -1)) != args.seed:
                error = f"seed mismatch: {result.get('agentSeed')}"
        except Exception as exc:
            error = f"invalid result JSON: {exc}"
    if result is None and error is None:
        error = "No custom result for SOL profile"

    launcher_receipt.write_text(json.dumps({
        "label": args.label,
        "suite_id": args.suite,
        "profile_id": PROFILE_ID,
        "temperature_requested": args.temperature,
        "seed_requested": args.seed,
        "timeout_sec": args.timeout,
        "max_wait_sec": args.max_wait,
        "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        "finished_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runner_exit_code": runner_exit,
        "error": error,
        "app_log": str(app_log),
        "runner_log": str(runner_log),
        "result_json": str(args.out),
        "effective_temperature": result.get("agentTemperature") if result else None,
        "effective_seed": result.get("agentSeed") if result else None,
        "final_score": [result.get("finalScore"), result.get("finalTotal")] if result else None,
        "first_pass_score": [result.get("firstAttemptScore"), result.get("firstAttemptTotal")] if result else None,
        "repair_attempts": result.get("repairAttempts") if result else None,
        "elapsed_sec": result.get("elapsedSec") if result else None,
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"suite": args.suite,
                      "temperature": args.temperature,
                      "seed": args.seed,
                      "runner_exit": runner_exit,
                      "error": error,
                      "result": str(args.out),
                      "receipt": str(launcher_receipt)}), flush=True)
    return 0 if error is None and runner_exit == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
