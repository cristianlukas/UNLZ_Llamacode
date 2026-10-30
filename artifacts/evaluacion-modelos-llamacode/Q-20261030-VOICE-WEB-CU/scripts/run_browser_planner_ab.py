#!/usr/bin/env python3
"""Q191 deterministic local-LLM planner A/B over Chrome and Lightpanda CDP."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import tempfile
import time
import urllib.request

BASE = Path(__file__).resolve().parents[1]
REPO = BASE.parents[2]
FIXTURE = REPO / 'artifacts/webbrain-evaluation-20261001/browser-fixture/site_server.py'
MODEL = Path('/media/cristian/Disco local/Models/llamacpp/Qwen3.5-4B/Qwen3.5-4B-Q4_K_M.gguf')
SERVER = Path('/media/cristian/Disco local/Modelos-eval/Q-20261028-VF-ITERATION-180/llama-build-cu128/bin/llama-server')
LP = BASE / 'runtime/lightpanda-x86_64-linux'
CHROME = Path('/usr/bin/google-chrome')
NODE = Path('/home/cristian/Documentos/ChatGPT/peritosoft/peritosoft-linux-build/toolchain/node-v20.9.0-linux-x64/bin/node')
CLIENT = BASE / 'scripts/run_browser_planner_cdp.js'
RUNS, LOGS = BASE / 'runs', BASE / 'logs'
RUNS.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)

EXPECTED = {
    MODEL: '3874209241c9a397e2f62cd3f70f80fd2dfbf0dfccb6838416bdb48a714e8630',
    SERVER: '0f25065d4c5e304000b38c6e1d288b483aac0a1c8936f3bfdc130b5d44d15ae5',
    LP: '73c6594300deeb8f20b30f96842655775ccc72f77af0a9085bbcae40b90759f1',
}
PORTS = (8777, 18493, 18495, 18496)


def free_port(port):
    with socket.socket() as s:
        return s.connect_ex(('127.0.0.1', port)) != 0


def start(argv, name, env=None, nice=False):
    log = open(LOGS / f'{name}.log', 'wb')
    if nice:
        argv = ['nice', '-n', '12', *argv]
    proc = subprocess.Popen(argv, cwd=REPO, stdout=log, stderr=subprocess.STDOUT,
                            start_new_session=True, env=env)
    return proc, log


def stop(proc, log):
    if proc is None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=5)
    log.close()


def ready(url, proc, timeout=120):
    started = time.monotonic()
    while time.monotonic() - started < timeout:
        if proc.poll() is not None:
            raise RuntimeError(f'process {proc.pid} exited {proc.returncode} before readiness')
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return time.monotonic() - started
        except Exception:
            time.sleep(0.25)
    raise TimeoutError(f'{url} not ready after {timeout}s')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def run_browser(arm, rep, server_proc):
    cdp_port = 18495 if arm == 'chrome' else 18496
    if not free_port(cdp_port):
        raise RuntimeError(f'foreign process owns CDP port {cdp_port}')
    profile = tempfile.mkdtemp(prefix=f'q191-plan-{arm}-{rep}-')
    env = os.environ.copy()
    env['LIGHTPANDA_DISABLE_TELEMETRY'] = 'true'
    if arm == 'chrome':
        argv = [str(CHROME), '--headless=new', '--no-sandbox', '--disable-gpu',
                '--disable-background-networking', '--disable-sync', '--no-first-run',
                f'--user-data-dir={profile}', f'--remote-debugging-port={cdp_port}',
                '--remote-debugging-address=127.0.0.1', 'about:blank']
    else:
        argv = [str(LP), 'serve', '--host', '127.0.0.1', '--port', str(cdp_port)]
    proc, log = start(argv, f'planner-{arm}-r{rep}', env)
    row = {'arm': arm, 'replica': rep, 'pid': proc.pid, 'browser_argv': argv}
    out = RUNS / f'planner-{arm}-r{rep}.json'
    try:
        row['browser_ready_seconds'] = ready(f'http://127.0.0.1:{cdp_port}/json/version', proc, 30)
        run_env = env.copy()
        run_env['Q191_CDP'] = f'http://127.0.0.1:{cdp_port}'
        run_env['LLAMACODE_QA_MODEL_URL'] = 'http://127.0.0.1:18493/v1/chat/completions'
        run_env['LLAMACODE_QA_MODEL'] = 'qwen3.5-4b-q4_k_m-cpu'
        run_env['LLAMACODE_QA_SERVER_BUILD'] = 'llama.cpp 0.8.0-dev commit 2e0d86b; CPU-only'
        run_env['LLAMACODE_QA_RESULT'] = str(out)
        t0 = time.monotonic()
        result = subprocess.run([str(NODE), str(CLIENT)], cwd=REPO, env=run_env,
                                capture_output=True, text=True, timeout=600)
        row['planner_wall_seconds'] = time.monotonic() - t0
        row['planner_exit'] = result.returncode
        row['planner_stdout_tail'] = result.stdout[-1500:]
        row['planner_stderr_tail'] = result.stderr[-1000:]
        row['planner_result'] = json.loads(out.read_text()) if out.is_file() else None
    except Exception as exc:
        row['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        stop(proc, log)
        row['browser_port_free_after'] = free_port(cdp_port)
        row['model_server_alive_after_arm'] = server_proc.poll() is None
        shutil.rmtree(profile, ignore_errors=True)
        (RUNS / f'planner-{arm}-r{rep}-receipt.json').write_text(json.dumps(row, indent=2) + '\n')
    return row


def main():
    lock = json.loads((REPO / 'WORK_QUEUE.lock').read_text())
    assert lock.get('token') == 'q191-voice-web-cu-20261030', 'Q191 lock not owned'
    for path, expected in EXPECTED.items():
        actual = sha(path)
        assert actual == expected, f'fingerprint mismatch {path}: {actual}'
    assert FIXTURE.is_file() and NODE.is_file() and CHROME.is_file()
    assert all(free_port(p) for p in PORTS), 'one or more preregistered ports are occupied'
    assert 'RTX 3090' in subprocess.check_output(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'], text=True)

    model_args = [str(SERVER), '--model', str(MODEL), '--host', '127.0.0.1', '--port', '18493',
                  '--ctx-size', '8192', '--n-gpu-layers', '0', '--threads', '2', '--threads-batch', '2',
                  '--parallel', '1', '--batch-size', '512', '--ubatch-size', '128', '--flash-attn', 'off',
                  '--jinja', '--reasoning-effort', 'medium', '--temp', '0.2', '--top-p', '0.95',
                  '--top-k', '20', '--min-p', '0.0', '--repeat-penalty', '1.0', '--presence-penalty', '0.0']
    fixture, fixture_log = start(['python3', str(FIXTURE)], 'planner-fixture')
    model, model_log = None, None
    summary = {'benchmark': 'Q191 browser planner A/B', 'model': str(MODEL),
               'model_sha256': EXPECTED[MODEL], 'server': str(SERVER),
               'server_sha256': EXPECTED[SERVER], 'server_args': model_args,
               'no_gpu': True, 'sampling': {'temperature': 0.2, 'top_p': 0.95, 'top_k': 20,
                                             'seed': 191, 'max_tokens': 256},
               'replica_order': [['chrome', 1], ['lightpanda', 1],
                                 ['lightpanda', 2], ['chrome', 2]], 'arms': []}
    try:
        summary['fixture_ready_seconds'] = ready('http://127.0.0.1:8777/northstar', fixture, 10)
        model, model_log = start(model_args, 'planner-model-cpu', nice=True)
        summary['model_ready_seconds'] = ready('http://127.0.0.1:18493/health', model, 180)
        for arm, rep in summary['replica_order']:
            result = run_browser(arm, rep, model)
            summary['arms'].append(result)
            (RUNS / 'planner-progress.json').write_text(json.dumps(summary, indent=2) + '\n')
            print(arm, rep, result.get('planner_exit'),
                  (result.get('planner_result') or {}).get('completedSites'), flush=True)
    finally:
        stop(model, model_log)
        stop(fixture, fixture_log)
        summary['model_port_free_after'] = free_port(18493)
        summary['fixture_port_free_after'] = free_port(8777)
        summary['closed_at'] = time.time()
        (RUNS / 'planner-summary.json').write_text(json.dumps(summary, indent=2) + '\n')


if __name__ == '__main__':
    main()
