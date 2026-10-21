#!/usr/bin/env python3
"""Regrade persisted BCB8 candidates in isolated, networkless sandboxes."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import pathlib
import resource
import signal
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[4]
TASK_ROOT = pathlib.Path(__file__).resolve().parents[1]
RUN = REPO / "artifacts/evaluacion-modelos-llamacode/Q-20261019-STRATA-UDIQ4XS-REMAINING/receipts/runs/BCB8-attempt-2"
EVAL = RUN / "EVAL.json"
METADATA = RUN / "metadata.json"
EVAL_DATA = json.loads(EVAL.read_text())
METADATA_DATA = json.loads(METADATA.read_text())
WORKSPACE = pathlib.Path(EVAL_DATA["workspace"])
OUT = TASK_ROOT / "work"
OUT.mkdir(parents=True, exist_ok=True)

def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None

def limits() -> None:
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    cap = 4 * 1024**3
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))

def sandbox_command(workdir: pathlib.Path, script: pathlib.Path) -> list[str]:
    py = pathlib.Path(sys.executable).resolve()
    cmd = [
        "bwrap", "--die-with-parent", "--unshare-net", "--unshare-pid",
        "--unshare-ipc", "--unshare-uts", "--ro-bind", "/usr", "/usr",
    ]
    for path in ("/lib", "/lib64", "/etc"):
        if pathlib.Path(path).exists():
            cmd.extend(["--ro-bind-try", path, path])
    cmd.extend([
        "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp",
        "--dir", "/work", "--bind", str(workdir), "/work", "--chdir", "/work",
        "--setenv", "HOME", "/work/home", "--setenv", "TMPDIR", "/tmp",
        "--setenv", "PATH", "/usr/bin:/bin", "--setenv", "PYTHONNOUSERSITE", "1",
        "--setenv", "PYTHONDONTWRITEBYTECODE", "1", "--setenv", "MPLBACKEND", "Agg",
        str(py), "/work/" + script.name,
    ])
    return cmd

def run_one(task: dict, expected: dict) -> dict:
    task_id = task["id"].split("/")[-1]
    candidate = WORKSPACE / f"solution_BigCodeBench_{task_id}.py"
    item_dir = OUT / f"task-{task_id}"
    item_dir.mkdir(parents=True, exist_ok=True)
    row = {
        "task_id": task["id"],
        "recorded_passed": expected.get("passed"),
        "candidate_path": str(candidate),
        "candidate_exists": candidate.is_file(),
        "candidate_sha256": sha256(candidate) if candidate.is_file() else None,
        "timeout_seconds": 120,
    }
    if not candidate.is_file():
        row.update({"status": "missing_candidate", "regraded_passed": None})
        return row
    acceptance = task.get("acceptance", {})
    target = item_dir / "candidate.py"
    # Persisted solutions are complete modules (including the signature); the
    # acceptance preamble is only a prompt scaffold and must not be prepended.
    source = "\n".join([candidate.read_text(errors="replace"), acceptance.get("tests", "")])
    target.write_text(source)
    (item_dir / "home").mkdir(exist_ok=True)
    cmd = sandbox_command(item_dir, target)
    row["runner_sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
    started = time.monotonic()
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=True, preexec_fn=limits,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=120)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = process.communicate()
    elapsed = time.monotonic() - started
    (item_dir / "stdout.txt").write_text(stdout)
    (item_dir / "stderr.txt").write_text(stderr)
    row.update({
        "status": "timeout" if timed_out else ("pass" if process.returncode == 0 else "fail"),
        "regraded_passed": False if timed_out else process.returncode == 0,
        "exit_code": process.returncode,
        "elapsed_seconds": round(elapsed, 3),
        "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest(),
        "stdout_tail": stdout[-1200:],
        "stderr_tail": stderr[-1200:],
        "sandbox": "bubblewrap; network/pid/ipc/uts isolated; system read-only; only per-task directory writable",
    })
    return row

def main() -> int:
    canary_dir = OUT / "sandbox-canary"
    canary_dir.mkdir(exist_ok=True)
    (canary_dir / "home").mkdir(exist_ok=True)
    (canary_dir / "canary.py").write_text("print('BCB8_SANDBOX_READY')\n")
    try:
        canary = subprocess.run(
            sandbox_command(canary_dir, canary_dir / "canary.py"),
            check=False, capture_output=True, text=True, timeout=30, preexec_fn=limits,
        )
    except Exception as exc:
        print(json.dumps({"status": "sandbox_preflight_failed", "error": str(exc)}, indent=2))
        return 2
    if canary.returncode != 0 or "BCB8_SANDBOX_READY" not in canary.stdout:
        print(json.dumps({"status": "sandbox_preflight_failed", "returncode": canary.returncode, "stdout": canary.stdout, "stderr": canary.stderr}, indent=2))
        return 2
    recorded = {x["taskId"]: x for x in EVAL_DATA["acceptance"]}
    packages = ["numpy", "pandas", "matplotlib", "Pillow", "pytesseract", "openpyxl", "rsa", "pycryptodome"]
    results = []
    for task in METADATA_DATA["tasks"]:
        results.append(run_one(task, recorded[task["id"]]))
    summary = {
        "test_id": "Q-20261021-VF-ITERATION-23",
        "source_eval": str(EVAL),
        "source_eval_sha256": sha256(EVAL),
        "source_metadata_sha256": sha256(METADATA),
        "source_workspace": str(WORKSPACE),
        "python": sys.version,
        "python_executable": str(pathlib.Path(sys.executable).resolve()),
        "dependencies": {name: version(name) for name in packages},
        "sandbox_preflight": {"status": "pass", "stdout": canary.stdout.strip()},
        "overall_source_invalid": EVAL_DATA.get("invalid"),
        "overall_source_failed": EVAL_DATA.get("failed"),
        "overall_source_failure_kind": EVAL_DATA.get("failureKind"),
        "overall_source_score": [EVAL_DATA.get("finalScore"), EVAL_DATA.get("finalTotal")],
        "tasks": results,
        "decision": "Task-level offline regrade only; does not convert the timed-out/incomplete BCB8 run into a valid suite score or justify promotion.",
    }
    target = TASK_ROOT / "receipts" / "bcb8-saved-candidates-regrade-attempt02-result.json"
    target.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "result_receipt": str(target),
        "source_invalid": summary["overall_source_invalid"],
        "source_score": summary["overall_source_score"],
        "results": [{"task": x["task_id"], "recorded": x["recorded_passed"], "candidate": x["candidate_exists"], "regraded": x["regraded_passed"], "status": x["status"]} for x in results],
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
