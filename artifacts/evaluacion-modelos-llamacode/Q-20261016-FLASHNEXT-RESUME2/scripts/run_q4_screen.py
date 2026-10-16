#!/usr/bin/env python3
"""Run one Q4 context or vision screen with resource guards and owned cleanup."""
from __future__ import annotations
import datetime as dt
import json
import os
import pathlib
import signal
import socket
import subprocess
import sys
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parents[4]
TASK = pathlib.Path(__file__).resolve().parents[1]
SOURCE = pathlib.Path('/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source')
PYTHON = SOURCE / '.venv/bin/python'
OLD_SCREEN = ROOT / 'artifacts/evaluacion-modelos-llamacode/Q-20261015-IQ3XXS-REMAINING-SCREENS'
CONFIGS = {
    'context262k': ('context262k-q4.json', 262144, False),
    'vision': ('vision-q4.json', 131072, True),
}
PORT = 8350
GIB = 1024 ** 3
MIN_BEFORE_LOAD = 32 * GIB
MIN_DURING_RUN = 20 * GIB
MAX_SOME_AVG10 = 80.0
MAX_FULL_AVG10 = 60.0
STREAK_LIMIT = 15


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def state():
    mem = {}
    for line in pathlib.Path('/proc/meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        if key in {'MemAvailable', 'SwapTotal', 'SwapFree'}:
            mem[key] = int(value.strip().split()[0]) * 1024
    vm = {}
    for line in pathlib.Path('/proc/vmstat').read_text().splitlines():
        fields = line.split()
        if fields[0] in {'pswpin', 'pswpout', 'oom_kill'}:
            vm[fields[0]] = int(fields[1])
    psi = {}
    for line in pathlib.Path('/proc/pressure/memory').read_text().splitlines():
        fields = dict(item.split('=', 1) for item in line.split()[1:])
        psi[line.split()[0]] = {k: float(fields[k]) for k in ('avg10', 'avg60', 'avg300')}
    g = subprocess.run(['nvidia-smi', '--query-compute-apps=pid,name,used_memory',
                        '--format=csv,noheader'], capture_output=True, text=True, timeout=10)
    return {'atUtc': now(), 'mem': mem, 'vmstat': vm, 'psi': psi,
            'computeApps': [x.strip() for x in g.stdout.splitlines() if x.strip()],
            'gpuQueryError': None if g.returncode == 0 else g.stderr.strip()}


def port_free(port):
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(('127.0.0.1', port)) != 0


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def stop_group(proc, label):
    if proc is None or proc.poll() is not None:
        return
    for sig, timeout in ((signal.SIGINT, 45), (signal.SIGTERM, 15), (signal.SIGKILL, 5)):
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            break
        try:
            proc.wait(timeout=timeout)
            return
        except subprocess.TimeoutExpired:
            pass
    if proc.poll() is None:
        raise RuntimeError(f'could not stop task-owned {label} process group')


def start_errors(s, port):
    errors = []
    m = s['mem']
    if m.get('MemAvailable', 0) < MIN_BEFORE_LOAD:
        errors.append('MemAvailable below 32 GiB')
    if s['gpuQueryError']:
        errors.append('nvidia-smi compute-process query failed')
    if s['computeApps']:
        errors.append('CUDA compute process already active')
    if not port_free(port):
        errors.append(f'port {port} is busy')
    some = s['psi'].get('some', {}).get('avg10', 0)
    full = s['psi'].get('full', {}).get('avg10', 0)
    if some >= MAX_SOME_AVG10 or full >= MAX_FULL_AVG10:
        errors.append('memory PSI is already at runtime abort threshold')
    return errors


def monitor(proc, child_ref, path, stop, reasons, baseline_oom):
    low_mem = high_psi = 0
    with path.open('w', encoding='utf-8') as f:
        while proc.poll() is None and not stop.is_set():
            snap = state()
            f.write(json.dumps(snap) + '\n')
            f.flush()
            m = snap['mem']
            low_mem = low_mem + 1 if m.get('MemAvailable', 0) < MIN_DURING_RUN else 0
            some = snap['psi'].get('some', {}).get('avg10', 0)
            full = snap['psi'].get('full', {}).get('avg10', 0)
            high_psi = high_psi + 1 if some >= MAX_SOME_AVG10 or full >= MAX_FULL_AVG10 else 0
            reason = None
            if snap['vmstat'].get('oom_kill', 0) > baseline_oom:
                reason = 'system oom_kill counter increased'
            elif low_mem >= STREAK_LIMIT:
                reason = f'MemAvailable <20 GiB for {low_mem} samples'
            elif high_psi >= STREAK_LIMIT:
                reason = f'memory PSI remained high: some={some}, full={full}'
            if reason:
                reasons.append(reason)
                stop.set()
                for owned in (child_ref.get('proc'), proc):
                    if owned is not None and owned.poll() is None:
                        try:
                            os.killpg(owned.pid, signal.SIGTERM)
                        except ProcessLookupError:
                            pass
                break
            time.sleep(1)


def get_health(port):
    try:
        import urllib.request
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=1) as r:
            return json.loads(r.read())
    except Exception:
        return None


def child_command(mode, config, receipt_path):
    base = f'http://127.0.0.1:{PORT}/v1/chat/completions'
    if mode == 'context262k':
        data = json.loads(config.read_text(encoding='utf-8'))
        return [str(PYTHON), str(TASK / 'scripts/probe_q4_262k.py'),
                '--tokenizer-dir', data['tokenizer'],
                '--tokenizer-module', str(SOURCE / 'tools/strata_tokenizer.py'),
                '--config', str(config), '--endpoint', base, '--out', str(receipt_path)]
    fixture = OLD_SCREEN / 'fixtures/vision-holdout-v1'
    return [str(PYTHON), str(OLD_SCREEN / 'scripts/run_vision_smoke.py'),
            '--endpoint', base, '--profile', 'Qwen3.8 Flash-Next UD-Q4_K_XL / Strata 0.1.41',
            '--image', str(fixture / 'vision-holdout.png'),
            '--prompt', str(fixture / 'prompt.txt'),
            '--expected', str(fixture / 'expected.json'), '--out', str(receipt_path)]


def run(mode, attempt=1):
    if mode not in CONFIGS:
        raise SystemExit('usage: run_q4_screen.py {context262k|vision} [attempt]')
    config_name, expected_context, expected_images = CONFIGS[mode]
    config = TASK / 'receipts/configs' / config_name
    output = TASK / 'receipts' / f'{mode}-attempt-{attempt:02d}.json'
    record_path = TASK / 'receipts' / f'{mode}-attempt-{attempt:02d}-controller.json'
    monitor_path = TASK / 'receipts/logs' / f'{mode}-attempt-{attempt:02d}.resource-monitor.jsonl'
    engine_log = TASK / 'receipts/logs' / f'{mode}-attempt-{attempt:02d}.server-console.log'
    initial = state()
    preflight = {'taskId': TASK.name, 'mode': mode, 'attempt': attempt,
                 'atUtc': now(), 'state': initial, 'port': PORT,
                 'thresholds': {'MemAvailableGiB': 32,
                                'runtimeMemAvailableAbortGiB': 20,
                                'runtimePsiSomeAvg10Abort': MAX_SOME_AVG10,
                                'runtimePsiFullAvg10Abort': MAX_FULL_AVG10,
                                'runtimeAbortSamples': 15,
                                'swapFreeIsTelemetryOnly': True},
                 'errors': start_errors(initial, PORT)}
    baseline_oom = initial['vmstat'].get('oom_kill', 0)
    preflight['oomKillBaseline'] = baseline_oom
    write_json(TASK / 'receipts' / f'{mode}-attempt-{attempt:02d}-preflight.json', preflight)
    record = {'taskId': TASK.name, 'mode': mode, 'attempt': attempt,
              'configPath': str(config.resolve()), 'configSha256': __import__('hashlib').sha256(config.read_bytes()).hexdigest(),
              'preflight': preflight, 'engineCommand': [str(PYTHON), str(SOURCE/'serve/server.py'),
              '--engine','strata','--config',str(config),'--host','127.0.0.1','--port',str(PORT),'--gpu','0,1'],
              'engineLog': str(engine_log.resolve()), 'monitorLog': str(monitor_path.resolve()),
              'childReceipt': str(output.resolve()), 'status': 'blocked_preflight' if preflight['errors'] else 'starting'}
    if preflight['errors']:
        record['error'] = '; '.join(preflight['errors'])
        record['postflight'] = state()
        write_json(record_path, record)
        print(json.dumps({'mode': mode, 'status': record['status'], 'errors': preflight['errors']}))
        return 2
    env = os.environ.copy()
    env.update(json.loads(config.read_text(encoding='utf-8')).get('env', {}))
    engine_log.parent.mkdir(parents=True, exist_ok=True)
    monitor_path.parent.mkdir(parents=True, exist_ok=True)
    server_log = engine_log.open('w', encoding='utf-8')
    child_log = (TASK / 'receipts/logs' / f'{mode}-attempt-{attempt:02d}.child.log').open('w', encoding='utf-8')
    proc = child = None
    stop = threading.Event(); reasons = []; child_ref = {'proc': None}
    thread = None
    try:
        proc = subprocess.Popen(record['engineCommand'], cwd=SOURCE, env=env,
                                stdout=server_log, stderr=subprocess.STDOUT, start_new_session=True)
        record.update({'serverPid': proc.pid, 'startedAtUtc': now()})
        thread = threading.Thread(target=monitor, args=(proc, child_ref, monitor_path, stop, reasons, baseline_oom), daemon=True)
        thread.start()
        deadline = time.monotonic() + 900
        health = None
        while time.monotonic() < deadline and not stop.is_set():
            if proc.poll() is not None:
                raise RuntimeError(f'Server exited during load with {proc.returncode}')
            health = get_health(PORT)
            if health and health.get('status') == 'ok':
                if health.get('max_context') != expected_context or bool(health.get('images')) != expected_images:
                    raise RuntimeError(f'Health does not match frozen config: {health}')
                break
            time.sleep(1)
        if stop.is_set():
            raise RuntimeError('resource guard: ' + '; '.join(reasons))
        if not health or health.get('status') != 'ok':
            raise TimeoutError('API did not become ready in 900 seconds')
        record.update({'health': health, 'apiReadyAtUtc': now(), 'status': 'running'})
        write_json(record_path, record)
        command = child_command(mode, config, output)
        record['childCommand'] = command
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=child_log,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        child_ref['proc'] = child
        deadline = time.monotonic() + (1800 if mode == 'context262k' else 900)
        while time.monotonic() < deadline:
            if stop.is_set():
                raise RuntimeError('resource guard: ' + '; '.join(reasons))
            if child.poll() is not None:
                record['childExitCode'] = child.returncode
                record['status'] = 'completed' if child.returncode == 0 else 'child_nonzero'
                break
            if proc.poll() is not None:
                raise RuntimeError(f'Server exited during screen with {proc.returncode}')
            time.sleep(1)
        else:
            raise TimeoutError('screen exceeded configured timeout')
    except Exception as exc:
        record['error'] = f'{type(exc).__name__}: {exc}'
        record['status'] = 'aborted_guard' if stop.is_set() else 'failed'
    finally:
        stop.set()
        if thread is not None:
            thread.join(timeout=3)
        stop_group(child, 'screen child')
        stop_group(proc, 'Strata server')
        child_log.close(); server_log.close()
        record['postflight'] = state()
        record['serverStopped'] = proc is None or proc.poll() is not None
        record['portFreeAfterCleanup'] = port_free(PORT)
        record['abortReasons'] = reasons
        record['finishedAtUtc'] = now()
        if output.exists():
            try:
                child_result = json.loads(output.read_text(encoding='utf-8'))
                if mode == 'context262k':
                    record['quality'] = {k: child_result.get(k) for k in ('status','localTokenizerContentTokens','needleFractionOfContentTokens','retrievalExact','needleFound','usage','timings','elapsedSeconds','error')}
                else:
                    record['quality'] = {k: child_result.get(k) for k in ('status','exactMatch','exactMatchCount','exactMatchTotal','transportError','usage','finishReason')}
            except Exception as exc:
                record['qualityReadError'] = repr(exc)
        write_json(record_path, record)
    print(json.dumps({'mode': mode, 'status': record.get('status'), 'quality': record.get('quality'),
                      'serverStopped': record.get('serverStopped'), 'portFreeAfterCleanup': record.get('portFreeAfterCleanup'),
                      'error': record.get('error')}, ensure_ascii=False))
    return 0 if record.get('status') == 'completed' and record.get('portFreeAfterCleanup') else 1


if __name__ == '__main__':
    if len(sys.argv) not in (2,3):
        raise SystemExit('usage: run_q4_screen.py {context262k|vision} [attempt]')
    raise SystemExit(run(sys.argv[1], int(sys.argv[2]) if len(sys.argv) == 3 else 1))
