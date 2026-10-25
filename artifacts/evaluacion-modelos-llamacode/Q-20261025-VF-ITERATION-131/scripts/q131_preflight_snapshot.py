#!/usr/bin/env python3
"""Read-only Q131 host/server preflight, isolated from shell command text."""
from __future__ import annotations
import importlib.util
import json
import subprocess
from pathlib import Path

TASK = Path(__file__).resolve().parents[1]
runner = TASK / 'scripts/run_q4_screen.py'
spec = importlib.util.spec_from_file_location('q131_runner', runner)
if spec is None or spec.loader is None:
    raise SystemExit('could not load Q131 runner')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
state = module.state(include_servers=True)
errors = module.start_errors(state, module.PORT)
receipt = {
    'taskId': TASK.name,
    'kind': 'read_only_prelaunch_snapshot',
    'atUtc': module.now(),
    'state': state,
    'startErrors': errors,
    'oomKillBaseline': state['vmstat'].get('oom_kill', 0),
    'authorizedPeritoSoftStopExecuted': False,
    'serverNotStarted': True,
    'gpuComputeStarted': False,
    'managerState': subprocess.run(
        ['systemctl', '--user', 'is-system-running'], capture_output=True, text=True
    ).stdout.strip(),
    'result': 'PASS' if not errors else 'BLOCKED',
}
out = TASK / 'receipts/preflight-review-clean.json'
out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({
    'result': receipt['result'],
    'memAvailableGiB': state['mem'].get('MemAvailable', 0) / 1024**3,
    'swapFreeGiB': state['mem'].get('SwapFree', 0) / 1024**3,
    'psi': state['psi'],
    'gpus': state['gpuUsage'],
    'computeApps': state['computeApps'],
    'inferenceServers': state.get('inferenceServers'),
    'errors': errors,
    'oom': state['vmstat'].get('oom_kill'),
}, ensure_ascii=False, indent=2))
raise SystemExit(0 if not errors else 2)
