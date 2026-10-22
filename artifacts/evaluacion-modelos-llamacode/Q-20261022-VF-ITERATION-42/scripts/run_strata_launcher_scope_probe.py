#!/usr/bin/env python3
"""CPU-only integration canary for the Linux ASTRA/Strata launcher."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone


REPO = Path(__file__).resolve().parents[4]
LAUNCHER = REPO / "scripts" / "run-astra-strata.sh"
RECEIPT = Path(os.environ.get(
    "Q42_RECEIPT_PATH",
    str(Path(__file__).resolve().parents[1] / "receipts" / "c42-linux-launcher-scope-probe-attempt-05.json"),
))
UNIT_RE = re.compile(r"llamacode-eval-[A-Za-z0-9_.@-]+\.scope$")


def run(args: list[str], timeout: float = 10.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, timeout=timeout, check=False)


def read_start_line(process: subprocess.Popen[str], timeout: float = 20.0) -> str:
    assert process.stdout is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    try:
        if not selector.select(timeout):
            raise RuntimeError("el falso servidor no anunció su PID antes del timeout")
        line = process.stdout.readline()
        if not line:
            raise RuntimeError("el launcher terminó antes de iniciar el falso servidor")
        return line.rstrip("\n")
    finally:
        selector.close()


def inspect_scope(pid: int) -> dict[str, str]:
    lines = Path(f"/proc/{pid}/cgroup").read_text().splitlines()
    v2_line = next((line for line in lines if line.startswith("0::")), None)
    if v2_line is None:
        raise RuntimeError(f"PID {pid} no reporta cgroup v2: {lines}")
    control_group = v2_line.split("::", 1)[1]
    unit = control_group.rsplit("/", 1)[-1]
    if not control_group.startswith("/background.slice/") or not UNIT_RE.fullmatch(unit):
        raise RuntimeError(f"cgroup inesperado para PID {pid}: {control_group}")
    result = run([
        "sudo", "-n", "systemctl", "show", unit,
        "--property=ActiveState,ControlGroup,OOMPolicy,KillMode,ManagedOOMMemoryPressure,ManagedOOMSwap,MemoryHigh,MemoryMax,MemorySwapMax",
    ])
    if result.returncode:
        raise RuntimeError(f"systemctl show {unit} falló: {result.stderr}")
    values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    expected = {
        "ActiveState": "active",
        "ControlGroup": control_group,
        "OOMPolicy": "kill",
        "KillMode": "control-group",
        "ManagedOOMMemoryPressure": "kill",
        "ManagedOOMSwap": "kill",
        "MemoryHigh": "infinity",
        "MemoryMax": "infinity",
        "MemorySwapMax": "infinity",
    }
    mismatch = {key: (values.get(key), value) for key, value in expected.items() if values.get(key) != value}
    if mismatch:
        raise RuntimeError(f"propiedades de scope inesperadas: {mismatch}")
    score = Path(f"/proc/{pid}/oom_score_adj").read_text().strip()
    if score != "900":
        raise RuntimeError(f"oom_score_adj esperado 900 para PID {pid}, recibido {score}")
    return {**values, "Unit": unit, "OOMScoreAdj": score}


def wait_gone(pid: int, timeout: float = 8.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not Path(f"/proc/{pid}").exists():
            return True
        time.sleep(0.05)
    return not Path(f"/proc/{pid}").exists()


def make_fixture(base: Path) -> dict[str, str]:
    strata = base / "strata"
    fake_python = strata / ".venv" / "bin" / "python"
    server = strata / "serve" / "server.py"
    config = strata / "strata-iq3_s.json"
    fake_python.parent.mkdir(parents=True)
    server.parent.mkdir(parents=True)
    config.write_text("{}\n")
    server.write_text("# placeholder; fake runtime never imports this file\n")
    fake_python.write_text("""#!/usr/bin/env bash
set -eu
args="$*"
port=""
while (($#)); do
  if [[ "$1" == "--port" && $# -ge 2 ]]; then port="$2"; fi
  shift
done
printf 'FAKE_SERVER pid=%s port=%s cwd=%s env=%s args=%s\\n' "$$" "$port" "$PWD" "${Q42_CANARY_ENV:-unset}" "$args"
case "$port" in
  18342) sleep 2; exit 23 ;;
  18343) exec /bin/sleep 120 ;;
  *) exit 91 ;;
esac
""", encoding="utf-8")
    fake_python.chmod(0o755)
    env = os.environ.copy()
    env.update({
        "STRATA_ROOT": str(strata),
        "STRATA_PYTHON": str(fake_python),
        "STRATA_CONFIG": str(config),
        "STRATA_SCOPE_PYTHON": sys.executable,
        "Q42_CANARY_ENV": "q42-preserved",
    })
    return env


def run_case(port: str, receipt: dict) -> None:
    with tempfile.TemporaryDirectory(prefix=f"q42-strata-{port}-") as tmp:
        cwd = Path(tmp)
        env = make_fixture(cwd)
        env["ASTRA_STRATA_PORT"] = port
        process = subprocess.Popen(
            ["bash", str(LAUNCHER)], cwd=cwd, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        pid = None
        unit = None
        try:
            line = read_start_line(process)
            match = re.search(r"FAKE_SERVER pid=(\d+) port=(\d+) cwd=(\S+) env=(\S+) args=(.*)", line)
            if not match or match.group(2) != port or Path(match.group(3)) != cwd:
                raise RuntimeError(f"argv/cwd/port inesperados: {line!r}")
            if match.group(4) != "q42-preserved":
                raise RuntimeError(f"el entorno heredado no llegó al falso runtime: {line!r}")
            pid = int(match.group(1))
            for expected in ("--engine strata", "--config", f"--port {port}"):
                if expected not in line:
                    raise RuntimeError(f"argumento faltante {expected!r}: {line}")
            scope = inspect_scope(pid)
            unit = scope["Unit"]
            if port == "18342":
                remainder, _ = process.communicate(timeout=15)
                expected_exit = 23
                scope_active = "inactive-after-natural-exit"
            else:
                process.send_signal(signal.SIGTERM)
                state_samples = []
                deadline = time.monotonic() + 6.0
                while time.monotonic() < deadline and process.poll() is None:
                    state = run(["sudo", "-n", "systemctl", "show", unit, "--property=ActiveState", "--value"], timeout=2)
                    state_samples.append(state.stdout.strip() or state.stderr.strip())
                    time.sleep(0.2)
                if process.poll() is None:
                    external_stop = run(["sudo", "-n", "systemctl", "stop", unit], timeout=5)
                    state_samples.append(f"diagnostic exact-unit stop rc={external_stop.returncode}: {external_stop.stderr.strip()}")
                try:
                    remainder, _ = process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    remainder, _ = process.communicate(timeout=3)
                expected_exit = 128 + signal.SIGTERM
                active = run(["sudo", "-n", "systemctl", "is-active", unit])
                scope_active = {"samples": state_samples, "final": active.stdout.strip()}
                if scope_active["final"] == "active":
                    raise RuntimeError(f"scope {unit} siguió activo tras SIGTERM")
            if process.returncode != expected_exit:
                raise RuntimeError(f"exit esperado {expected_exit}; llegó {process.returncode}: {remainder}")
            if not wait_gone(pid):
                raise RuntimeError(f"el falso servidor PID {pid} sobrevivió al cierre")
            receipt[f"port_{port}"] = {
                "stdout_first_line": line,
                "stdout_remainder": remainder,
                "launcher_exit": process.returncode,
                "scope": scope,
                "child_gone": True,
                "scope_after_close": scope_active,
            }
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
            if pid is not None and Path(f"/proc/{pid}").exists() and unit:
                run(["sudo", "-n", "systemctl", "stop", unit])


def main() -> int:
    oomd = run(["systemctl", "is-active", "systemd-oomd.service"])
    sudo = run(["sudo", "-n", "true"])
    receipt = {
        "task": "Q-20261022-VF-ITERATION-42",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "fixture": "fake Python executable + placeholder server/config; CPU-only, no model/GPU",
        "preflight": {"platform": sys.platform, "systemd_oomd": oomd.stdout.strip(), "sudo_noninteractive": sudo.returncode == 0},
        "checks": [],
    }
    if sys.platform != "linux" or receipt["preflight"]["systemd_oomd"] != "active" or sudo.returncode:
        receipt["result"] = "ABORTED_BEFORE_LAUNCH"
        RECEIPT.parent.mkdir(parents=True, exist_ok=True)
        RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
        return 2
    try:
        run_case("18342", receipt)
        receipt["checks"].append("natural exit 23; stdout/argv/cwd; exact scope properties; oom_score_adj; cleanup")
        run_case("18343", receipt)
        receipt["checks"].append("SIGTERM returns 143 and stops exact scope plus child; controller remains alive")
        receipt["result"] = "PASS"
        result_code = 0
    except Exception as exc:
        receipt["result"] = "FAIL"
        receipt["error"] = f"{type(exc).__name__}: {exc}"
        result_code = 1
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return result_code


if __name__ == "__main__":
    raise SystemExit(main())
