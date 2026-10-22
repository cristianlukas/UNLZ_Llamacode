"""Launch Linux evaluation servers in a system-manager scope.

No memory or swap cap is applied. The scope is placed in background.slice,
marked as a systemd-oomd candidate, uses OOMPolicy=kill, and execs the target
with a high oom_score_adj so pressure handling can prefer the evaluation tree.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import uuid
from typing import Any, Mapping, Optional, Sequence


_EXEC_WRAPPER = Path(__file__).with_name("linux_eval_scope_exec.py")
_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ScopedProcess:
    """A Popen process plus the systemd scope that owns its process tree."""

    def __init__(self, process: subprocess.Popen, unit: str):
        self.process = process
        self.unit = unit

    def stop(self, timeout_seconds: float = 15.0) -> None:
        if self.process.poll() is None:
            result = subprocess.run(
                ["sudo", "-n", "systemctl", "stop", self.unit],
                text=True, capture_output=True, timeout=timeout_seconds,
            )
            if result.returncode and self.process.poll() is None:
                raise RuntimeError(
                    f"No se pudo detener el scope {self.unit}: {result.stderr[-1000:]}"
                )
            try:
                self.process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3.0)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=3.0)


def popen_in_background_scope(
    argv: Sequence[str], *, cwd: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
    env_overrides: Optional[Mapping[str, str]] = None,
    stdout: Any = None, stderr: Any = None, text: bool = False,
    start_new_session: bool = False,
) -> ScopedProcess:
    """Start argv in a system-manager scope and return its process/lifecycle handle.

    The caller must use :meth:`ScopedProcess.stop` when the server is stopped.
    ``sudo -n`` makes missing non-interactive privilege fail instead of hanging.
    """
    if sys.platform != "linux":
        raise RuntimeError("El aislamiento systemd sólo está disponible en Linux")
    if not argv or any(not isinstance(value, str) for value in argv):
        raise ValueError("argv debe contener al menos un argumento string")
    oomd = subprocess.run(
        ["sudo", "-n", "systemctl", "is-active", "--quiet", "systemd-oomd.service"],
        text=True, capture_output=True, timeout=10.0,
    )
    if oomd.returncode:
        raise RuntimeError(
            "systemd-oomd.service no está activo; se cancela el lanzamiento sin contención"
        )
    overrides = dict(env_overrides or {})
    for key, value in overrides.items():
        if not _ENV_NAME.fullmatch(key) or not isinstance(value, str) or "\0" in value:
            raise ValueError(f"Variable de entorno inválida: {key!r}")
    unit = f"llamacode-eval-{os.getpid()}-{uuid.uuid4().hex[:8]}.scope"
    command = [
        "sudo", "-n", "-E", "systemd-run", "--system", "--scope", "--quiet",
        f"--unit={unit.removesuffix('.scope')}", "--slice=background.slice",
        f"--uid={os.getuid()}", f"--gid={os.getgid()}",
        "--property=OOMPolicy=kill", "--property=KillMode=control-group",
        "--property=ManagedOOMMemoryPressure=kill", "--property=ManagedOOMSwap=kill",
        "--setenv=LLAMACODE_EVAL_OOM_SCORE_ADJ=900",
    ]
    command.extend(f"--setenv={key}={value}" for key, value in sorted(overrides.items()))
    command.extend(["--", sys.executable, str(_EXEC_WRAPPER), "--", *argv])
    process = subprocess.Popen(
        command, cwd=cwd, env=dict(env) if env is not None else None,
        stdout=stdout, stderr=stderr, text=text,
        start_new_session=start_new_session,
    )
    return ScopedProcess(process, unit)


def run_scoped_command(argv: Sequence[str]) -> int:
    """Run a foreground command in a protected scope and clean it on signals."""
    scoped = popen_in_background_scope(
        argv, cwd=os.getcwd(), env=os.environ.copy(), start_new_session=True,
    )
    previous_handlers = {}
    received_signals = []
    stop_completed = False

    def stop_on_signal(signum: int, _frame: Any) -> None:
        received_signals.append(signum)

    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous_handlers[signum] = signal.signal(signum, stop_on_signal)
        while True:
            try:
                return scoped.process.wait(timeout=0.2)
            except subprocess.TimeoutExpired:
                if received_signals:
                    signum = received_signals[0]
                    try:
                        scoped.stop()
                    except Exception as exc:
                        print(f"No se pudo detener el scope de evaluación: {exc}", file=sys.stderr)
                        return 1
                    stop_completed = True
                    return 128 + signum
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
        if scoped.process.poll() is None and not stop_completed:
            scoped.stop()


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 3 or args[0] != "--run" or args[1] != "--":
        print("Uso: linux_eval_scope.py --run -- COMANDO [ARG ...]", file=sys.stderr)
        return 2
    try:
        return run_scoped_command(args[2:])
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"No se inició el comando con contención: {exc}", file=sys.stderr)
        return 125


if __name__ == "__main__":
    raise SystemExit(main())
