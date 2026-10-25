#!/usr/bin/env python3
"""Verify a pinned evaluation runner/pressure guard before launching it.

This is an evaluation-harness safeguard. It does not monitor Codex or alter
LlamaCode product behavior. The only approved guard here is the AMD05 helper
that passed the Q117 CPU suite and Q118 ASTRA trace replay.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


APPROVED_GUARDS = {
    "b4d42302e7d405abd5c59df5aa86bb7de6ef3bb91aef487b49acbebd1d24270e":
        "q117_pressure_guard_attempt05",
}


class GuardSelectionError(ValueError):
    """Raised when a runner does not select the preregistered guard exactly."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _runner_imports(runner: Path, module_name: str) -> bool:
    try:
        tree = ast.parse(runner.read_text(encoding="utf-8"), filename=str(runner))
    except (OSError, SyntaxError) as exc:
        raise GuardSelectionError(f"runner cannot be parsed: {exc}") from exc
    return any(
        isinstance(node, ast.ImportFrom) and node.module == module_name
        for node in ast.walk(tree)
    )


def _starts_monitor_before_server(runner: Path) -> bool:
    tree = ast.parse(runner.read_text(encoding="utf-8"), filename=str(runner))
    main_function = next(
        (node for node in tree.body
         if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "main"),
        None,
    )
    if main_function is None:
        return False

    monitor_starts = []
    server_starts = []
    for node in ast.walk(main_function):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (isinstance(func, ast.Attribute) and func.attr == "start"
                and isinstance(func.value, ast.Name) and func.value.id == "monitor"):
            monitor_starts.append(node.lineno)
        if (isinstance(func, ast.Attribute) and func.attr == "Popen"
                and isinstance(func.value, ast.Name) and func.value.id == "subprocess"):
            server_starts.append(node.lineno)
    return bool(monitor_starts and server_starts and min(monitor_starts) < min(server_starts))


def _preimport_guard(guard: Path, module_name: str) -> str:
    """Import the exact guard file in this process before the runner can start."""
    guard_dir = str(guard.parent)
    if guard_dir not in sys.path:
        sys.path.insert(0, guard_dir)
    spec = importlib.util.spec_from_file_location(module_name, guard)
    if spec is None or spec.loader is None:
        raise GuardSelectionError("cannot create an import spec for the approved guard")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(module_name, None)
        raise GuardSelectionError(f"approved guard failed import preflight: {exc}") from exc
    loaded_from = Path(module.__file__).resolve()
    if loaded_from != guard.resolve():
        raise GuardSelectionError(
            f"guard import resolved to {loaded_from}, expected {guard.resolve()}"
        )
    return str(loaded_from)


def verify_selection(runner: Path, guard: Path, runner_sha256: str,
                     guard_sha256: str) -> dict:
    runner = runner.expanduser().resolve()
    guard = guard.expanduser().resolve()
    if not runner.is_file() or not guard.is_file():
        raise GuardSelectionError("runner and guard must both be existing files")
    if runner.parent != guard.parent:
        raise GuardSelectionError("runner and guard must share a directory for import identity")

    actual_runner_sha = sha256_file(runner)
    if actual_runner_sha != runner_sha256.lower():
        raise GuardSelectionError(
            f"runner SHA-256 mismatch: expected {runner_sha256}, got {actual_runner_sha}"
        )
    actual_guard_sha = sha256_file(guard)
    if actual_guard_sha != guard_sha256.lower():
        raise GuardSelectionError(
            f"guard SHA-256 mismatch: expected {guard_sha256}, got {actual_guard_sha}"
        )
    module_name = APPROVED_GUARDS.get(actual_guard_sha)
    if module_name is None or guard.stem != module_name:
        raise GuardSelectionError("guard hash/module is not on the approved candidate list")
    if not _runner_imports(runner, module_name):
        raise GuardSelectionError(f"runner does not import the pinned module {module_name}")
    if not _starts_monitor_before_server(runner):
        raise GuardSelectionError("runner must start its monitor before subprocess.Popen")

    imported_path = _preimport_guard(guard, module_name)
    return {
        "status": "PASS",
        "runner": str(runner),
        "runnerSha256": actual_runner_sha,
        "guard": str(guard),
        "guardSha256": actual_guard_sha,
        "guardModule": module_name,
        "preimportedFrom": imported_path,
        "monitorStartsBeforeServer": True,
    }


def run_guarded(runner: Path, guard: Path, runner_sha256: str,
                guard_sha256: str, runner_args: list[str] | None = None,
                verify_only: bool = False) -> int:
    report = verify_selection(runner, guard, runner_sha256, guard_sha256)
    print(json.dumps(report, indent=2, sort_keys=True), flush=True)
    if verify_only:
        return 0
    command = [sys.executable, str(runner.resolve()), *(runner_args or [])]
    return subprocess.run(command, cwd=str(runner.resolve().parent), check=False).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--guard", type=Path, required=True)
    parser.add_argument("--runner-sha256", required=True)
    parser.add_argument("--guard-sha256", required=True)
    parser.add_argument("--verify-only", action="store_true",
                        help="verify and import the guard without launching the runner")
    args, runner_args = parser.parse_known_args(argv)
    if runner_args[:1] == ["--"]:
        runner_args = runner_args[1:]
    try:
        return run_guarded(args.runner, args.guard, args.runner_sha256,
                           args.guard_sha256, runner_args, args.verify_only)
    except GuardSelectionError as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
