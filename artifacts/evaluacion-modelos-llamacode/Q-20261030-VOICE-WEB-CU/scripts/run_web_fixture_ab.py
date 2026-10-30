#!/usr/bin/env python3
"""Preregistered Q191 local browser compatibility A/B; owns only its children."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time
import urllib.request

import psutil

BASE = Path(__file__).resolve().parents[1]
REPO = BASE.parents[2]
FIXTURE = REPO / 'artifacts/webbrain-evaluation-20261001/browser-fixture/site_server.py'
LP = BASE / 'runtime/lightpanda-x86_64-linux'
NODE = Path('/home/cristian/Documentos/ChatGPT/peritosoft/peritosoft-linux-build/toolchain/node-v20.9.0-linux-x64/bin/node')
CHROME = Path('/usr/bin/google-chrome')
RUNS = BASE / 'runs'
LOGS = BASE / 'logs'
RUNS.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(parents=True, exist_ok=True)


def free_port(port):
    with socket.socket() as s:
        return s.connect_ex(('127.0.0.1', port)) != 0


def start(argv, name, env=None):
    log = open(LOGS / f'{name}.log', 'wb')
    proc = subprocess.Popen(argv, cwd=REPO, stdout=log, stderr=subprocess.STDOUT,
                            start_new_session=True, env=env)
    return proc, log


def stop(proc, log):
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=5)
    log.close()


def ready(port, path, proc, timeout=20):
    started = time.monotonic()
    while time.monotonic() - started < timeout:
        if proc.poll() is not None:
            raise RuntimeError(f'process {proc.pid} exited {proc.returncode} before readiness')
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}', timeout=1) as resp:
                if resp.status == 200:
                    return time.monotonic() - started
        except Exception:
            time.sleep(0.1)
    raise TimeoutError(f'port {port} not ready')


def rss_tree(pid):
    try:
        parent = psutil.Process(pid)
        processes = [parent] + parent.children(recursive=True)
        return sum(p.memory_info().rss for p in processes if p.is_running())
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0


def one(arm, replica):
    port = 18495 if arm == 'chrome' else 18496
    if not free_port(port):
        raise RuntimeError(f'foreign process owns port {port}')
    profile = tempfile.mkdtemp(prefix=f'q191-{arm}-{replica}-')
    env = os.environ.copy()
    env['LIGHTPANDA_DISABLE_TELEMETRY'] = 'true'
    if arm == 'chrome':
        argv = [str(CHROME), '--headless=new', '--no-sandbox', '--disable-gpu',
                '--disable-background-networking', '--disable-sync', '--no-first-run',
                f'--user-data-dir={profile}', f'--remote-debugging-port={port}',
                'about:blank']
    else:
        argv = [str(LP), 'serve', '--host', '127.0.0.1', '--port', str(port)]
    proc, log = start(argv, f'{arm}-r{replica}', env)
    out = RUNS / f'{arm}-r{replica}.json'
    result = {'arm': arm, 'replica': replica, 'pid': proc.pid, 'command': argv,
              'browser_start': time.time(), 'output': str(out)}
    samples = []
    sampling = True

    def sampler():
        while sampling:
            samples.append(rss_tree(proc.pid))
            time.sleep(0.1)

    thread = threading.Thread(target=sampler, daemon=True)
    thread.start()
    try:
        result['ready_seconds'] = ready(port, '/json/version', proc)
        client = subprocess.run([str(NODE), str(BASE / 'scripts/web_fixture_client.js'),
                                 f'http://127.0.0.1:{port}', str(out)], cwd=REPO,
                                capture_output=True, text=True, timeout=150)
        result['client_exit'] = client.returncode
        result['client_stderr'] = client.stderr[-1000:]
        result['client_stdout'] = client.stdout[-1000:]
        result['client'] = json.loads(out.read_text()) if out.exists() else None
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        sampling = False
        thread.join(timeout=1)
        result['peak_rss_bytes'] = max(samples, default=0)
        result['rss_samples'] = len(samples)
        stop(proc, log)
        result['port_free_after'] = free_port(port)
        shutil.rmtree(profile, ignore_errors=True)
        (RUNS / f'{arm}-r{replica}-receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    lock = json.loads((REPO / 'WORK_QUEUE.lock').read_text())
    assert lock['token'] == 'q191-voice-web-cu-20261030'
    assert hashlib.sha256(LP.read_bytes()).hexdigest() == '73c6594300deeb8f20b30f96842655775ccc72f77af0a9085bbcae40b90759f1'
    assert NODE.is_file() and CHROME.is_file() and FIXTURE.is_file()
    assert free_port(8777), 'foreign fixture server on port 8777'
    fixture, fixture_log = start(['python3', str(FIXTURE)], 'fixture')
    results = []
    try:
        ready(8777, '/northstar', fixture)
        for replica in (1, 2, 3):
            for arm in (('chrome', 'lightpanda') if replica % 2 else ('lightpanda', 'chrome')):
                result = one(arm, replica)
                results.append(result)
                (RUNS / 'web-fixture-progress.json').write_text(json.dumps(results, indent=2) + '\n')
                print(arm, replica, result.get('client_exit'),
                      [x.get('passed') for x in (result.get('client') or {}).get('sites', [])], flush=True)
    finally:
        stop(fixture, fixture_log)
    (RUNS / 'web-fixture-summary.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
