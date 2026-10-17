#!/usr/bin/env python3
"""Run one isolated, real LlamaCode desktop-agent session for the Muse A/B."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261016-MUSE-CU-HOLDOUT"
START = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261013-MUSE-CU-E2E/scripts/start_private_x11_session.sh"
OVERLAY = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261009-MUSE-AGENT-EVAL/prompt/muse-safe-transfer-v1.txt"
OVERLAY = OVERLAY.resolve()
APP = pathlib.Path("/media/cristian/Disco local/LlamaCode-cache/build_linux/LlamaCode")
ISOLATED_PROFILE_ID = "31ff813d-6bf5-4400-8f82-69af4fcc64bc"
LAUNCHES = {
    "astra": "iq3s-lch1-20261009",
    "q4": "q4-udq4kxl-lch1-20261010",
}
MODEL_MARKERS = {
    "astra": ("astra", "iq3_s"),
    "q4": ("unsloth", "q4_k_xl"),
}

CASES = [
    {
        "id": "CU-ES-CALC",
        "expected_visible": "1411",
        "prompt": (
            "Usá sólo las herramientas de escritorio. Abre `gnome-calculator`, "
            "calcula `83*17=` en una sola entrada, deja el resultado actual visible "
            "y compruébalo con los controles de la ventana. No abras terminal, "
            "archivos ni red."
        ),
    },
    {
        "id": "CU-EN-EDITOR",
        "expected_visible": "MUSE CU HOLDOUT: keyboard input verified.",
        "prompt": (
            "Use only desktop tools. Open `gnome-text-editor` as a new blank "
            "document and type this exact line: `MUSE CU HOLDOUT: keyboard input "
            "verified.` Leave it unsaved. Verify it using the available desktop "
            "controls; if the UI does not expose the document text, say so instead "
            "of claiming you read it. Do not use shell, files, or network tools."
        ),
    },
    {
        "id": "CU-ES-MULTIAPP",
        "expected_visible": "1829",
        "prompt": (
            "En la Calculadora ya abierta, calcula `59*31=` y confirma el valor "
            "actual del visor mediante los controles. Después, en el Editor de "
            "texto ya abierto, reemplaza la línea anterior con `Resultado "
            "verificado: 1829` y deja el documento sin guardar. Confirma el estado "
            "con una observación disponible y no afirmes que verificaste algo que "
            "la interfaz no te mostró. No uses terminal, archivos ni red."
        ),
    },
]


def request_json(url: str, body: dict | None = None, timeout: float = 10) -> dict:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read())


def prop(base: str, name: str):
    return request_json(f"{base}/prop?name={urllib.parse.quote(name)}")["value"]


def invoke(base: str, method: str, args: list, target: str = "") -> dict:
    url = f"{base}/invoke"
    if target:
        url += "?target=" + urllib.parse.quote(target, safe="")
    return request_json(url, {"method": method, "args": args}, timeout=30)


def setprop(base: str, name: str, value) -> dict:
    return request_json(f"{base}/setprop", {"name": name, "value": value})


def wait_control(base: str, deadline: float, predicate, label: str):
    last = None
    while time.monotonic() < deadline:
        try:
            last = predicate()
            if last:
                return last
        except (OSError, urllib.error.URLError, TimeoutError, KeyError, ValueError):
            pass
        time.sleep(1)
    raise TimeoutError(f"timeout esperando {label}; último estado={last!r}")


def process_env(pid: int) -> dict[str, str]:
    raw = pathlib.Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
    return {k.decode(): v.decode(errors="replace") for item in raw if b"=" in item
            for k, v in [item.split(b"=", 1)]}


def stop_private_display(display: str, excluded: set[int] | None = None) -> list[int]:
    excluded = excluded or set()
    signalled = []
    for entry in pathlib.Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid in excluded:
            continue
        try:
            env = process_env(pid)
            cmd = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            if env.get("DISPLAY") == display and any(k in cmd for k in (
                "gnome-calculator", "gnome-text-editor", "firefox", "google-chrome",
                "LlamaCode --agent-daemon", "Xvfb " + display, "minimal_ewmh_wm.py",
            )):
                os.kill(pid, signal.SIGTERM)
                signalled.append(pid)
        except (OSError, ProcessLookupError, PermissionError):
            continue
    return signalled


def capture(stage: str, run_dir: pathlib.Path, env: dict[str, str]) -> dict:
    image = run_dir / f"{stage}.png"
    xwd = run_dir / f"{stage}.xwd"
    p = subprocess.run(["xwd", "-root", "-silent", "-out", str(xwd)], env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=15)
    if p.returncode != 0:
        raise RuntimeError(f"xwd failed: {p.stdout}")
    p = subprocess.run(["convert", str(xwd), str(image)], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True, timeout=30)
    xwd.unlink(missing_ok=True)
    if p.returncode != 0:
        raise RuntimeError(f"ImageMagick convert failed: {p.stdout}")
    p = subprocess.run(["tesseract", str(image), "stdout", "--psm", "6"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True, env=env, timeout=45)
    ocr_path = run_dir / f"{stage}.ocr.txt"
    ocr_path.write_text(p.stdout)
    wins = subprocess.run(["wmctrl", "-lpG"], env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, timeout=10)
    per_window = {}
    for line in wins.stdout.splitlines():
        fields = line.split(maxsplit=7)
        if len(fields) != 8:
            continue
        window_id = fields[0]
        window_xwd = run_dir / f"{stage}-{window_id}.xwd"
        window_png = run_dir / f"{stage}-{window_id}.png"
        get_window = subprocess.run(
            ["xwd", "-id", window_id, "-silent", "-out", str(window_xwd)],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=15,
        )
        if get_window.returncode != 0:
            continue
        convert_window = subprocess.run(
            ["convert", str(window_xwd), str(window_png)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30,
        )
        window_xwd.unlink(missing_ok=True)
        if convert_window.returncode != 0:
            continue
        window_ocr = subprocess.run(
            ["tesseract", str(window_png), "stdout", "--psm", "6"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env=env, timeout=45,
        )
        per_window[window_id] = {
            "title": fields[7],
            "png": str(window_png),
            "ocr_text": window_ocr.stdout,
            "ocr_exit": window_ocr.returncode,
        }
    return {
        "png": str(image),
        "ocr": str(ocr_path),
        "ocr_text": p.stdout,
        "window_ocr": per_window,
        "windows": wins.stdout,
        "ocr_exit": p.returncode,
    }


def wait_turn(base: str, before_count: int, timeout_sec: int) -> tuple[list, float]:
    start = time.monotonic()
    deadline = start + timeout_sec
    stable = 0
    final_messages = []
    last_signature = None
    while time.monotonic() < deadline:
        messages = prop(base, "agentMessages")
        streaming_index = int(prop(base, "agentStreamingIndex"))
        delta = messages[before_count:] if isinstance(messages, list) else []
        stale_control_failures = sum(
            1 for message in delta
            if isinstance(message, dict)
            and "snapshot quedó obsoleto" in str(message.get("output", "")).casefold()
        )
        if stale_control_failures >= 5:
            raise RuntimeError(
                f"bucle de recuperación AT-SPI: {stale_control_failures} acciones sobre "
                "snapshots obsoletos en un mismo turno"
            )
        last_assistant = next((m for m in reversed(delta)
                               if isinstance(m, dict)
                               and m.get("role") == "assistant"), None)
        finished = (last_assistant is not None
                    and not bool(last_assistant.get("typing", False))
                    and streaming_index < 0)
        signature = json.dumps(delta, ensure_ascii=False, sort_keys=True) if finished else None
        if finished and signature == last_signature:
            stable += 1
            final_messages = delta
            if stable >= 2:
                return final_messages, time.monotonic() - start
        elif finished:
            stable = 0
            last_signature = signature
            final_messages = delta
        else:
            stable = 0
            last_signature = None
        time.sleep(1)
    raise TimeoutError(
        f"turno excedió {timeout_sec}s; streamingIndex={prop(base, 'agentStreamingIndex')}; "
        f"messages={json.dumps(prop(base, 'agentMessages'), ensure_ascii=False)[-3000:]}"
    )


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).casefold()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=sorted(LAUNCHES), required=True)
    parser.add_argument("--arm", choices=("base", "muse_overlay"), required=True)
    parser.add_argument("--rep", type=int, choices=(1, 2, 3, 4), required=True)
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--port", type=int, default=8898)
    parser.add_argument("--display", default=":97")
    args = parser.parse_args()

    if not APP.is_file() or not START.is_file():
        raise SystemExit("LlamaCode build o script de X11 aislado no disponible")
    base = f"http://127.0.0.1:{args.port}"
    run_id = f"{args.profile}-{args.arm}-r{args.rep}"
    if args.attempt > 1:
        run_id += f"-try{args.attempt}"
    run_dir = TASK / "receipts" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    if args.rep == 1:
        screen, lang, theme = "1440x900x24", "es_AR.utf8", ""
    elif args.rep == 2:
        screen, lang, theme = "1280x800x24", "C.UTF-8", "Adwaita:dark"
    elif args.rep == 3:
        screen, lang, theme = "1024x768x24", "es_AR.utf8", ""
    else:
        screen, lang, theme = "1366x768x24", "es_AR.utf8", "Adwaita:dark"
    overlay_text = OVERLAY.read_text() if args.arm == "muse_overlay" else ""
    env = os.environ.copy()
    env.pop("XAUTHORITY", None)
    env.update({
        "DISPLAY": args.display,
        "EVAL_DISPLAY": args.display,
        "EVAL_SCREEN": screen,
        "EVAL_LANG": lang,
        "EVAL_GTK_THEME": theme,
        "EVAL_ISOLATION_ID": run_id,
        "EVAL_RUN_ID": run_id,
        "LLAMACODE_CONTROL_PORT": str(args.port),
        "QT_QPA_PLATFORM": "xcb",
    })
    try:
        request_json(base + "/health", timeout=1)
        raise SystemExit(f"el puerto {args.port} ya está ocupado; no se reutiliza otro daemon")
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        pass

    started_local = dt.datetime.now().astimezone().isoformat()
    daemon_log = (TASK / "receipts" / "sessions" / run_id / "runner-daemon.log")
    daemon_log.parent.mkdir(parents=True, exist_ok=True)
    log_file = daemon_log.open("w")
    daemon = subprocess.Popen(["dbus-run-session", "--", str(START)], cwd=ROOT,
                              env=env, stdout=log_file, stderr=subprocess.STDOUT,
                              start_new_session=True, text=True)
    result = {
        "run_id": run_id,
        "profile": args.profile,
        "launch_id": LAUNCHES[args.profile],
        "agent_profile_id": ISOLATED_PROFILE_ID,
        "arm": args.arm,
        "replicate": args.rep,
        "attempt": args.attempt,
        "sampling": {"temperature": 0.6, "top_p": 0.95, "top_k": 20,
                     "min_p": 0.0, "repeat_penalty": 1.0,
                     "presence_penalty": 0.0, "reasoning_effort": "medium"},
        "screen": screen,
        "lang": lang,
        "gtk_theme": theme or "system default (Adwaita light observed in preflight)",
        "started_at_local": started_local,
        "overlay_sha256": hashlib.sha256(overlay_text.encode()).hexdigest() if overlay_text else None,
        "tasks": [],
        "daemon_log": str(daemon_log),
    }
    current_case = None
    current_before_messages = 0
    try:
        wait_control(base, time.monotonic() + 120,
                     lambda: request_json(base + "/health").get("ok"), "ControlApi health")
        wait_control(base, time.monotonic() + 120,
                     lambda: not prop(base, "startupBusy"), "arranque headless")
        model_list = wait_control(
            "http://127.0.0.1:8350/v1/models", time.monotonic() + 900,
            lambda: request_json("http://127.0.0.1:8350/v1/models", timeout=15),
            "endpoint externo Strata listo",
        )
        advertised = json.dumps(model_list, ensure_ascii=False).casefold()
        if not all(marker in advertised for marker in MODEL_MARKERS[args.profile]):
            raise RuntimeError(
                f"El endpoint no anuncia el modelo esperado para {args.profile}: {model_list!r}"
            )
        result["endpoint_models"] = model_list
        set_profile = setprop(base, "activeAgentProfileId", ISOLATED_PROFILE_ID)
        set_prompt = setprop(base, "agentSystemPrompt", overlay_text)
        result["profile_setprop"] = set_profile
        result["prompt_setprop"] = {"ok": set_prompt.get("ok"), "chars": len(overlay_text)}
        spec = invoke(base, "agentProfileSpec", [ISOLATED_PROFILE_ID], "profileManager")["result"]
        enabled = spec["tools"]["include"]
        if any(not name.startswith("desktop_") for name in enabled) or spec["tools"]["mcpTools"]:
            raise RuntimeError("perfil de prueba no está limitado a herramientas desktop_*")
        result["effective_profile"] = {"id": ISOLATED_PROFILE_ID, "tools": enabled,
                                       "approval": spec["permissions"]["approvalMode"],
                                       "mcp": spec["tools"]["mcpTools"]}
        invoke(base, "startServerAndAgent", [LAUNCHES[args.profile]])
        wait_control(base, time.monotonic() + 180,
                     lambda: bool(prop(base, "serverRunning"))
                             and bool(prop(base, "serverReady"))
                             and bool(prop(base, "agentRunning"))
                             and not bool(prop(base, "agentStarting")),
                     "inicio del agente")
        if not prop(base, "agentRunning"):
            raise RuntimeError("Agente no quedó activo; log=" + str(prop(base, "agentLog"))[-4000:])
        result["agent_started"] = True
        initial_messages = prop(base, "agentMessages")
        result["initial_message_count"] = len(initial_messages) if isinstance(initial_messages, list) else None

        for index, case in enumerate(CASES, start=1):
            before = prop(base, "agentMessages")
            before_count = len(before) if isinstance(before, list) else 0
            current_case = case
            current_before_messages = before_count
            t0 = time.monotonic()
            invoke(base, "sendToAgent", [case["prompt"]])
            # This runner owns a private Xvfb display, so it can resolve the
            # product's foreground/background choice explicitly for that
            # isolated desktop. The real desktop is never exposed to the test.
            choice_deadline = time.monotonic() + 15
            while time.monotonic() < choice_deadline:
                pending_choice = prop(base, "agentComputerUseRequest")
                if pending_choice:
                    invoke(base, "answerComputerUseChoice", ["foreground"])
                    break
                current_messages = prop(base, "agentMessages")
                if (prop(base, "agentStreamingIndex") >= 0
                        or (isinstance(current_messages, list) and len(current_messages) > before_count)):
                    break
                time.sleep(0.2)
            delta, elapsed = wait_turn(base, before_count, 300)
            receipt = capture(f"stage{index}-{case['id']}", run_dir, env)
            expected = normalize(case["expected_visible"])
            observed = normalize(receipt["ocr_text"])
            all_window_text = normalize("\n".join(
                item["ocr_text"] for item in receipt["window_ocr"].values()))
            receipt["expected_visible"] = case["expected_visible"]
            receipt["root_ocr_contains_expected"] = expected in observed
            receipt["window_ocr_contains_expected"] = expected in all_window_text
            receipt["ocr_contains_expected"] = (expected in observed
                                                or expected in all_window_text)
            receipt["messages_delta"] = delta
            receipt["elapsed_seconds"] = round(elapsed, 3)
            receipt["agent_log"] = prop(base, "agentLog")
            receipt["prompt"] = case["prompt"]
            receipt["task_id"] = case["id"]
            result["tasks"].append(receipt)
            print(json.dumps({"run_id": run_id, "task": case["id"],
                              "seconds": receipt["elapsed_seconds"],
                              "ocr_contains_expected": receipt["ocr_contains_expected"],
                              "windows": receipt["windows"]}, ensure_ascii=False), flush=True)

        result["finished_at_local"] = dt.datetime.now().astimezone().isoformat()
        result["agent_log_final"] = prop(base, "agentLog")
        result["messages_final"] = prop(base, "agentMessages")
        result["successes"] = sum(bool(t["ocr_contains_expected"]) for t in result["tasks"])
        result["task_count"] = len(result["tasks"])
        result["total_agent_seconds"] = round(sum(t["elapsed_seconds"] for t in result["tasks"]), 3)
        return_code = 0
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["agent_log_error"] = None
        try:
            result["agent_log_error"] = prop(base, "agentLog")
        except Exception:
            pass
        if current_case is not None:
            try:
                messages = prop(base, "agentMessages")
                result["partial_task"] = {
                    "task_id": current_case["id"],
                    "prompt": current_case["prompt"],
                    "messages_delta": messages[current_before_messages:]
                        if isinstance(messages, list) else messages,
                }
                result["partial_capture"] = capture(
                    f"partial-{current_case['id']}", run_dir, env
                )
            except Exception as capture_exc:
                result["partial_capture_error"] = (
                    f"{type(capture_exc).__name__}: {capture_exc}"
                )
        result["finished_at_local"] = dt.datetime.now().astimezone().isoformat()
        return_code = 1
    finally:
        try:
            if daemon.poll() is None:
                try:
                    invoke(base, "stopAgent", [])
                except Exception:
                    pass
                try:
                    setprop(base, "agentSystemPrompt", "")
                except Exception:
                    pass
                try:
                    os.killpg(daemon.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    daemon.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(daemon.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    daemon.wait(timeout=5)
        finally:
            leftovers = stop_private_display(args.display)
            result["cleanup_signalled_pids"] = leftovers
            log_file.close()
            (run_dir / "run.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"run_id": run_id, "return_code": return_code,
                      "error": result.get("error"), "successes": result.get("successes"),
                      "tasks": len(result.get("tasks", [])),
                      "total_agent_seconds": result.get("total_agent_seconds")}, ensure_ascii=False),
          flush=True)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
