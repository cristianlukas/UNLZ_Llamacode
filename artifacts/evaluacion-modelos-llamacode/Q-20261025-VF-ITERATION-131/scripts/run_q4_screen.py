#!/usr/bin/env python3
"""Run one Q4 context or vision screen with resource guards and owned cleanup."""
from __future__ import annotations
import datetime as dt
import json
import os
import pathlib
import re
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
    'context262k': ('context262k-q4-q131.json', 262144, False),
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


def inference_processes():
    known = {'llama-server', 'ollama', 'vllm', 'text-generation-launcher',
             'llmster', 'lmstudio', 'strata', 'ninfer', 'koboldcpp',
             'local-ai', 'aphrodite'}
    patterns = (re.compile(r'(?:^|/)serve/server\.py(?:\s|$)', re.I),
                re.compile(r'vllm\.(?:entrypoints|serve)|sglang\.launch_server|text_generation_server', re.I),
                re.compile(r'ollama\s+serve|llama-server|peritosoft.*(?:server|serve)', re.I))
    found = []
    for entry in pathlib.Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            comm = (entry / 'comm').read_text().strip().lower()
            argv = (entry / 'cmdline').read_bytes().replace(b'\0', b' ').decode('utf-8', 'replace').strip()
            if comm in known or any(pattern.search(argv) for pattern in patterns):
                found.append({'pid': int(entry.name), 'comm': comm, 'argv': argv[:500]})
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
    try:
        docker = subprocess.run(['docker', 'ps', '--format', '{{.ID}}\t{{.Image}}\t{{.Names}}\t{{.Ports}}'],
                                capture_output=True, text=True, timeout=8)
        if docker.returncode == 0:
            for line in docker.stdout.splitlines():
                if re.search(r'vllm|llama|strata|ninfer|inference|ollama|kobold|sglang|peritosoft', line, re.I):
                    found.append({'container': line})
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    try:
        listeners = subprocess.run(['ss', '-lntp'], capture_output=True, text=True, timeout=8)
        inference_ports = {1234, 8350, 8352,
                           8354, 8363, 11434, 18111, 18112, 18119, 18789}
        for line in listeners.stdout.splitlines()[1:]:
            match = re.search(r':(\d+)\s', line)
            if match and int(match.group(1)) in inference_ports:
                found.append({'listener': line.strip()})
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return found


def stop_authorized_peritosoft(servers):
    stopped = []
    for item in servers:
        if 'peritosoft' not in json.dumps(item, ensure_ascii=False).lower():
            continue
        if 'pid' in item:
            pid = int(item['pid'])
            try:
                os.kill(pid, signal.SIGTERM)
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline and pathlib.Path(f'/proc/{pid}').exists():
                    time.sleep(0.2)
                if pathlib.Path(f'/proc/{pid}').exists():
                    os.kill(pid, signal.SIGKILL)
                stopped.append({'pid': pid, 'method': 'SIGTERM then SIGKILL if still present'})
            except ProcessLookupError:
                stopped.append({'pid': pid, 'method': 'already exited'})
        elif 'container' in item:
            container_id = item['container'].split('\t', 1)[0]
            result = subprocess.run(['docker', 'stop', container_id], capture_output=True,
                                     text=True, timeout=20)
            stopped.append({'container': container_id, 'returnCode': result.returncode,
                            'output': result.stdout.strip(), 'error': result.stderr.strip()})
    return stopped


def process_tree_rss(root_pids):
    if not root_pids:
        return None
    try:
        output = subprocess.run(['ps', '-eo', 'pid=,ppid=,rss='], capture_output=True,
                                text=True, timeout=5, check=True).stdout
        rows = {}
        for line in output.splitlines():
            fields = line.split()
            if len(fields) == 3:
                pid, ppid, rss = map(int, fields)
                rows[pid] = (ppid, rss)
        included = set(root_pids)
        while True:
            children = {pid for pid, (ppid, _) in rows.items() if ppid in included}
            new = included | children
            if new == included:
                break
            included = new
        return sum(rows[pid][1] * 1024 for pid in included if pid in rows)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def state(include_servers=False, root_pids=()):
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
    try:
        gpu = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.used,memory.total,utilization.gpu',
                              '--format=csv,noheader,nounits'], capture_output=True,
                             text=True, timeout=8)
        gpu_usage = gpu.stdout.strip().splitlines() if gpu.returncode == 0 else []
    except subprocess.TimeoutExpired:
        gpu_usage = []
    result = {'atUtc': now(), 'mem': mem, 'vmstat': vm, 'psi': psi,
              'computeApps': [x.strip() for x in g.stdout.splitlines() if x.strip()],
              'gpuUsage': gpu_usage, 'processTreeRssBytes': process_tree_rss(root_pids),
              'gpuQueryError': None if g.returncode == 0 else g.stderr.strip()}
    if include_servers:
        result['inferenceServers'] = inference_processes()
    return result


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
    if s.get('inferenceServers'):
        errors.append('inference server/container/listener active; refusing a second server')
    gpus = s.get('gpuUsage', [])
    if len(gpus) < 2 or not all('RTX 3090' in line for line in gpus[:2]):
        errors.append('expected two visible RTX 3090 GPUs')
    if not port_free(port):
        errors.append(f'port {port} is busy')
    some = s['psi'].get('some', {}).get('avg10', 0)
    full = s['psi'].get('full', {}).get('avg10', 0)
    if some >= MAX_SOME_AVG10 or full >= MAX_FULL_AVG10:
        errors.append('memory PSI is already at runtime abort threshold')
    return errors


def guard_transition(low_mem, high_psi, snap, baseline_oom):
    mem_available = snap.get('mem', {}).get('MemAvailable', 0)
    low_mem = low_mem + 1 if mem_available < MIN_DURING_RUN else 0
    some = snap.get('psi', {}).get('some', {}).get('avg10', 0)
    full = snap.get('psi', {}).get('full', {}).get('avg10', 0)
    # One combined streak is intentional: alternating severe some/full must not reset it.
    high_psi = high_psi + 1 if some >= MAX_SOME_AVG10 or full >= MAX_FULL_AVG10 else 0
    advisories = []
    if mem_available < 48 * GIB:
        advisories.append('MemAvailable below 48 GiB; advisory only')
    if some >= 50 or full >= 20:
        advisories.append('elevated global memory PSI; advisory only')
    reason = None
    if snap.get('vmstat', {}).get('oom_kill', 0) > baseline_oom:
        reason = 'system oom_kill counter increased'
    elif low_mem >= STREAK_LIMIT:
        reason = f'MemAvailable <20 GiB for {low_mem} samples'
    elif high_psi >= STREAK_LIMIT:
        reason = f'memory PSI remained high: some={some}, full={full}'
    return low_mem, high_psi, reason, advisories


def monitor(proc, child_ref, path, stop, reasons, baseline_oom):
    low_mem = high_psi = 0
    with path.open('w', encoding='utf-8') as f:
        while proc.poll() is None and not stop.is_set():
            roots = [proc.pid]
            if child_ref.get('proc') is not None:
                roots.append(child_ref['proc'].pid)
            snap = state(root_pids=roots)
            low_mem, high_psi, reason, advisories = guard_transition(
                low_mem, high_psi, snap, baseline_oom)
            snap['advisories'] = advisories
            f.write(json.dumps(snap) + '\n')
            f.flush()
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
        return [str(PYTHON), str(TASK / 'scripts/probe_q4_262k_ten_keys.py'),
                '--tokenizer-dir', data['tokenizer'],
                '--tokenizer-module', str(SOURCE / 'tools/strata_tokenizer.py'),
                '--config', str(config),
                '--fixture', str(TASK / 'receipts/fixtures/ten-keys-seed-4242.json'),
                '--endpoint', base, '--out', str(receipt_path)]
    raise ValueError(f'unsupported Q131 mode: {mode}')


def run(mode, attempt=1):
    if mode not in CONFIGS:
        raise SystemExit('usage: run_q4_screen.py {context262k|vision} [attempt]')
    config_name, expected_context, expected_images = CONFIGS[mode]
    config = TASK / 'receipts/configs' / config_name
    output = TASK / 'receipts' / f'{mode}-attempt-{attempt:02d}.json'
    record_path = TASK / 'receipts' / f'{mode}-attempt-{attempt:02d}-controller.json'
    monitor_path = TASK / 'receipts/logs' / f'{mode}-attempt-{attempt:02d}.resource-monitor.jsonl'
    engine_log = TASK / 'receipts/logs' / f'{mode}-attempt-{attempt:02d}.server-console.log'
    initial = state(include_servers=True)
    servers_before_stop = initial.get('inferenceServers', [])
    authorized_stops = stop_authorized_peritosoft(servers_before_stop)
    if authorized_stops:
        initial = state(include_servers=True)
    preflight = {'taskId': TASK.name, 'mode': mode, 'attempt': attempt,
                 'atUtc': now(), 'state': initial, 'port': PORT,
                 'inferenceServersBeforeAuthorizedStop': servers_before_stop,
                 'authorizedPeritoSoftStops': authorized_stops,
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
        record['postflight'] = state(include_servers=True)
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
        record['postflight'] = state(include_servers=True)
        record['serverStopped'] = proc is None or proc.poll() is not None
        record['portFreeAfterCleanup'] = port_free(PORT)
        record['abortReasons'] = reasons
        record['finishedAtUtc'] = now()
        if output.exists():
            try:
                child_result = json.loads(output.read_text(encoding='utf-8'))
                if mode == 'context262k':
                    record['quality'] = {k: child_result.get(k) for k in ('status','localTokenizerContentTokens','keyPositions','exactFields','expectedFields','exactKeySet','screenPass','usage','timings','elapsedSeconds','error')}
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
