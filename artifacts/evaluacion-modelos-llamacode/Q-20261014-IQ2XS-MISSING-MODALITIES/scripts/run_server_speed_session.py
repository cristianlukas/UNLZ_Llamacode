#!/usr/bin/env python3
"""Start one isolated LlamaCode daemon and run its native Server Speed v1 receipt."""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261014-IQ2XS-MISSING-MODALITIES"
START = TASK / "scripts/start_private_x11_session.sh"
SPEED = TASK / "scripts/run_server_speed.py"
PROFILES = {"iq2": "q14-iq2xs-cu", "q4": "q14-dense-q4-cu"}


def get_json(url: str, timeout: float = 3.0):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read())


def prop(base: str, name: str):
    from urllib.parse import quote
    return get_json(f"{base}/prop?name={quote(name)}")["value"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=sorted(PROFILES), required=True)
    ap.add_argument("--display", default=":97")
    ap.add_argument("--control-port", type=int, default=8898)
    ap.add_argument("--endpoint-port", type=int, default=8350)
    ap.add_argument("--passes", type=int, default=2)
    ap.add_argument("--timeout", type=int, default=1600)
    args = ap.parse_args()

    base = f"http://127.0.0.1:{args.control_port}"
    endpoint = f"http://127.0.0.1:{args.endpoint_port}/v1/models"
    try:
        get_json(base + "/health", 1)
        raise SystemExit(f"control port {args.control_port} is already occupied")
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        pass
    get_json(endpoint, 5)

    session = f"serverspeed-{args.profile}"
    state_root = TASK / "runtime/sessions" / session
    log_dir = TASK / "receipts/sessions" / session
    log_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({
        "DISPLAY": args.display,
        "EVAL_DISPLAY": args.display,
        "EVAL_ISOLATION_ID": session,
        "EVAL_RUN_ID": session,
        "LLAMACODE_CONTROL_PORT": str(args.control_port),
        "QT_QPA_PLATFORM": "xcb",
    })
    env.pop("XAUTHORITY", None)
    log = (log_dir / "daemon.log").open("w", encoding="utf-8")
    daemon = subprocess.Popen(
        ["dbus-run-session", "--", "bash", str(START)], cwd=ROOT, env=env,
        stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
    )
    code = 1
    try:
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if daemon.poll() is not None:
                raise RuntimeError(f"LlamaCode daemon exited {daemon.returncode}; see {log_dir/'daemon.log'}")
            try:
                if get_json(base + "/health", 2).get("ok") and not prop(base, "startupBusy"):
                    break
            except (OSError, urllib.error.URLError, TimeoutError, KeyError):
                pass
            time.sleep(1)
        else:
            raise TimeoutError(f"LlamaCode ControlApi did not become ready; see {log_dir/'daemon.log'}")

        out = TASK / "receipts" / "server-speed" / args.profile
        command = [
            "python3", str(SPEED), "--endpoint", base,
            "--profile", PROFILES[args.profile], "--runtime-data", str(state_root / "data"),
            "--out", str(out), "--passes", str(args.passes), "--warmup", "1",
            "--max-prefill-tokens", "65536", "--timeout", str(args.timeout),
        ]
        run = subprocess.run(command, cwd=ROOT, env=env)
        code = run.returncode
    finally:
        if daemon.poll() is None:
            try:
                os.killpg(daemon.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                daemon.wait(timeout=15)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(daemon.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                daemon.wait(timeout=5)
        log.close()
    print(json.dumps({"profile": args.profile, "returnCode": code,
                      "receipt": str(TASK / "receipts/server-speed" / args.profile),
                      "daemonLog": str(log_dir / "daemon.log")}, ensure_ascii=False), flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
