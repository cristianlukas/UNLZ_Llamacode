#!/usr/bin/bash
set -Eeuo pipefail
mkdir -p "$HOME/logs" "$HOME/.local/share" "$HOME/.config" "$HOME/.cache"
/usr/bin/python3 - <<'PYCFG'
import json
from pathlib import Path
cfg=json.loads(Path('/opt/q181/astra-config.json').read_text())
assert cfg.get('log') == '/run/q181/home/logs/astra-strata.log', cfg.get('log')
assert cfg.get('gpu') == [0, 1], cfg.get('gpu')
assert cfg.get('model_name') == 'qwen3.8-flash-next-iq2_xs', cfg.get('model_name')
assert cfg.get('args', [])[cfg.get('args', []).index('--max-context') + 1] == '1048576'
print('Q181 config guard: PASS', flush=True)
PYCFG
strata_pid=""; app_pid=""
stop_child() {
    local pid="$1"; [[ -n "$pid" ]] || return 0
    if kill -0 "$pid" 2>/dev/null; then
        kill -INT "$pid" 2>/dev/null || true
        for _ in {1..30}; do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
        kill -TERM "$pid" 2>/dev/null || true
        wait "$pid" 2>/dev/null || true
    fi
}
cleanup() { stop_child "$app_pid"; stop_child "$strata_pid"; }
trap cleanup EXIT INT TERM
/opt/q181/probe_cuda_dual_device >"$HOME/logs/cuda-probe.log" 2>&1
/opt/strata/.venv/bin/python /opt/strata/serve/server.py \
    --engine strata --config /opt/q181/astra-config.json \
    --host 127.0.0.1 --port 18473 >"$HOME/logs/astra-server.log" 2>&1 &
strata_pid=$!
ready=0
for _ in {1..240}; do
    if ! kill -0 "$strata_pid" 2>/dev/null; then wait "$strata_pid" || true; break; fi
    if /usr/bin/python3 - <<'PYREADY'
import json, urllib.request
try:
    with urllib.request.urlopen('http://127.0.0.1:18473/health', timeout=3) as r:
        health=json.loads(r.read())
    with urllib.request.urlopen('http://127.0.0.1:18473/v1/models', timeout=3) as r:
        models=json.loads(r.read())
    expected='qwen3.8-flash-next-iq2_xs'
    ok=(health.get('status') == 'ok' and health.get('loaded') is True
        and health.get('model') == expected
        and any(m.get('id') == expected for m in models.get('data', [])))
    raise SystemExit(0 if ok else 1)
except Exception:
    raise SystemExit(1)
PYREADY
    then ready=1; break; fi
    sleep 5
done
if [[ "$ready" != 1 ]]; then
    echo 'Q181 ASTRA Strata readiness failed within 1200 s, before any benchmark request' >&2
    tail -200 "$HOME/logs/astra-server.log" >&2 || true
    exit 70
fi
/opt/llamacode/LlamaCode --headless --agent-daemon >"$HOME/logs/llamacode.log" 2>&1 &
app_pid=$!
/usr/bin/python3 /opt/q181/run_q181_coding_holdout.py
