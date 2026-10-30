#!/usr/bin/env python3
"""Q191 read-only 20-site browser A/B, after the local fixture gate."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time

import run_web_fixture_ab as core

BASE = Path(__file__).resolve().parents[1]
RUNS = BASE / 'runs'
NODE = core.NODE
LP = core.LP
CHROME = core.CHROME


def one(arm, replica):
    port = 18495 if arm == 'chrome' else 18496
    if not core.free_port(port):
        raise RuntimeError(f'foreign process owns port {port}')
    profile = tempfile.mkdtemp(prefix=f'q191-sites-{arm}-{replica}-')
    env = os.environ.copy()
    env['LIGHTPANDA_DISABLE_TELEMETRY'] = 'true'
    if arm == 'chrome':
        argv = [str(CHROME), '--headless=new', '--no-sandbox', '--disable-gpu',
                '--disable-background-networking', '--disable-sync', '--no-first-run',
                f'--user-data-dir={profile}', f'--remote-debugging-port={port}', 'about:blank']
    else:
        argv = [str(LP), 'serve', '--host', '127.0.0.1', '--port', str(port)]
    proc, log = core.start(argv, f'sites-{arm}-r{replica}', env)
    out = RUNS / f'sites-{arm}-r{replica}.json'
    result = {'arm': arm, 'replica': replica, 'pid': proc.pid, 'command': argv,
              'output': str(out)}
    samples = []
    sampling = True

    def sampler():
        while sampling:
            samples.append(core.rss_tree(proc.pid))
            time.sleep(0.1)

    thread = threading.Thread(target=sampler, daemon=True)
    thread.start()
    try:
        result['ready_seconds'] = core.ready(port, '/json/version', proc)
        start = time.monotonic()
        client = subprocess.run([str(NODE), str(BASE / 'scripts/web_sites_client.js'),
                                 f'http://127.0.0.1:{port}', str(out)], cwd=core.REPO,
                                capture_output=True, text=True, timeout=380)
        result['wall_seconds'] = time.monotonic() - start
        result['client_exit'] = client.returncode
        result['client_stderr'] = client.stderr[-1000:]
        result['client'] = json.loads(out.read_text()) if out.exists() else None
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        sampling = False
        thread.join(timeout=1)
        result['peak_rss_bytes'] = max(samples, default=0)
        result['rss_samples'] = len(samples)
        core.stop(proc, log)
        result['port_free_after'] = core.free_port(port)
        shutil.rmtree(profile, ignore_errors=True)
        (RUNS / f'sites-{arm}-r{replica}-receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    assert json.loads((core.REPO / 'WORK_QUEUE.lock').read_text())['token'] == 'q191-voice-web-cu-20261030'
    assert hashlib.sha256(LP.read_bytes()).hexdigest() == '73c6594300deeb8f20b30f96842655775ccc72f77af0a9085bbcae40b90759f1'
    fixture = RUNS / 'web-fixture-summary.json'
    assert fixture.is_file() and all((x.get('client') or {}).get('passed') for x in json.loads(fixture.read_text()))
    results = []
    for replica in (1, 2):
        for arm in (('chrome', 'lightpanda') if replica % 2 else ('lightpanda', 'chrome')):
            result = one(arm, replica)
            results.append(result)
            (RUNS / 'web-sites-progress.json').write_text(json.dumps(results, indent=2) + '\n')
            pages = (result.get('client') or {}).get('pages', [])
            print(arm, replica, f'{sum(x.get("passed", False) for x in pages)}/{len(pages)}',
                  round(result.get('wall_seconds', 0), 2), flush=True)
    (RUNS / 'web-sites-summary.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
