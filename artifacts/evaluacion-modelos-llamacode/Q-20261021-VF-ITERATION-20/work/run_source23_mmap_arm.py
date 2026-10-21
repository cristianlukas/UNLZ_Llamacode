#!/usr/bin/env python3
"""Isolated adapter for the preregistered S23 mmap-experts screen."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pathlib
import sys

TASK = pathlib.Path(__file__).resolve().parents[1]
REPO = pathlib.Path(__file__).resolve().parents[4]
ORIGINAL = REPO / "artifacts/evaluacion-modelos-llamacode/Q-20261021-VF-ITERATION-20/work/source23-run-arm.py"
LOCK_ID = "Q-20261021-VF-ITERATION-20"
PORT = 8355
MEMORY_HIGH_BYTES = 64 * 1024**3
MEMORY_MAX_BYTES = 72 * 1024**3


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--arm", choices=("stock", "fp8"), required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--attempt", type=int, default=1)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def lock_matches(token: str) -> bool:
    try:
        data = json.loads((REPO / "WORK_QUEUE.lock").read_text(encoding="utf-8"))
    except Exception:
        return False
    return data.get("task_id") == LOCK_ID and data.get("token") == token


def current_scope_memory_limits() -> tuple[int, int] | None:
    try:
        line = next(x for x in pathlib.Path("/proc/self/cgroup").read_text().splitlines()
                    if x.startswith("0::"))
        relative = line.split("::", 1)[1].lstrip("/")
        base = pathlib.Path("/sys/fs/cgroup") / relative
        return int((base / "memory.high").read_text()), int((base / "memory.max").read_text())
    except Exception:
        return None


def output_paths(arm: str, seed: int, attempt: int) -> dict[str, pathlib.Path]:
    suffix = "" if attempt == 1 else f"-attempt-{attempt:02d}"
    return {
        "config": TASK / f"work/source23/configs/{arm}.json",
        "result": TASK / f"work/source23/results/{arm}-seed-{seed}{suffix}.json",
        "receipt": TASK / f"receipts/source-23-{arm}-seed-{seed}{suffix}-execution.json",
        "server_log": TASK / f"work/source23/server-{arm}-seed-{seed}{suffix}.log",
    }


def main() -> int:
    args = parse_args()
    if args.seed <= 0 or args.attempt <= 0:
        raise SystemExit("seed and attempt must be positive")
    token = os.environ.get("LCA_WORK_QUEUE_LOCK_TOKEN", "")
    if not lock_matches(token):
        raise SystemExit("Q20 lock ownership mismatch")
    paths = output_paths(args.arm, args.seed, args.attempt)
    if not paths["config"].is_file():
        raise SystemExit(f"config missing: {paths['config']}")
    if any(paths[key].exists() for key in ("result", "receipt", "server_log")):
        raise SystemExit("refusing to overwrite an existing Q20 result, receipt, or server log")
    config = json.loads(paths["config"].read_text(encoding="utf-8"))
    if "--mmap-experts" not in config.get("args", []):
        raise SystemExit("config does not include the preregistered mmap-experts flag")
    if args.dry_run:
        print(json.dumps({
            "status": "dry_run_pass",
            "taskId": LOCK_ID,
            "arm": args.arm,
            "seed": args.seed,
            "port": PORT,
            "config": str(paths["config"]),
            "result": str(paths["result"]),
            "receipt": str(paths["receipt"]),
            "serverLog": str(paths["server_log"]),
            "mmapExperts": True,
            "expectedMemoryHighBytes": MEMORY_HIGH_BYTES,
            "expectedMemoryMaxBytes": MEMORY_MAX_BYTES,
            "scopeCheck": "deferred-to-real-run",
            "lockOwned": True,
            "outputsUnused": True,
            "gpuStarted": False,
        }, ensure_ascii=False))
        return 0
    if current_scope_memory_limits() != (MEMORY_HIGH_BYTES, MEMORY_MAX_BYTES):
        raise SystemExit("refusing to start: transient scope memory.high/max do not match the preregistered 64/72 GiB limits")
    spec = importlib.util.spec_from_file_location("source23_original_runner", ORIGINAL)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load original S23 runner: {ORIGINAL}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.TASK = TASK
    module.PORT = PORT
    module.LOCK_TOKEN = token
    sys.argv = [str(ORIGINAL), "--arm", args.arm, "--seed", str(args.seed), "--attempt", str(args.attempt)]
    return int(module.main())


if __name__ == "__main__":
    raise SystemExit(main())
