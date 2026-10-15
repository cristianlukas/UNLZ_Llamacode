#!/usr/bin/env python3
"""Execute the registered 9-run TaskFlow matrix and 3 coding smokes in order."""
import json
import pathlib
import subprocess
import sys
import time


TASK_ROOT = pathlib.Path(__file__).resolve().parents[1]
RUN_ONCE = TASK_ROOT / "scripts/run_once.py"
RECEIPTS = TASK_ROOT / "receipts"
TASKFLOW = "qwen38_taskflow_ultra_ast_vs_sol_20261006"
SMOKE = "llamacode_local_coding_smoke"


def run(suite, temperature, seed, label, output):
    command = [
        sys.executable, str(RUN_ONCE),
        "--suite", suite,
        "--temperature", str(temperature),
        "--seed", str(seed),
        "--label", label,
        "--out", str(output),
    ]
    print(json.dumps({"event": "run_start", "label": label,
                      "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}),
          flush=True)
    completed = subprocess.run(command, cwd=TASK_ROOT, check=False)
    print(json.dumps({"event": "run_end", "label": label,
                      "return_code": completed.returncode,
                      "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}),
          flush=True)
    return completed.returncode


def main():
    RECEIPTS.mkdir(parents=True, exist_ok=True)
    for temperature in (0.1, 0.6, 1.0):
        for seed in (4242, 4243, 4244):
            label = f"SOL TaskFlow T{temperature:g} seed{seed}"
            output = RECEIPTS / f"taskflow-T{temperature:g}-seed{seed}.json"
            if run(TASKFLOW, temperature, seed, label, output):
                print("Stopping after first incomplete/invalid TaskFlow run.", flush=True)
                return 1
    for temperature in (0.1, 0.6, 1.0):
        label = f"SOL coding smoke T{temperature:g} seed4242"
        output = RECEIPTS / f"smoke-T{temperature:g}-seed4242.json"
        if run(SMOKE, temperature, 4242, label, output):
            print("Stopping after first incomplete/invalid coding-smoke run.", flush=True)
            return 1
    print("All 12 registered runs completed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
