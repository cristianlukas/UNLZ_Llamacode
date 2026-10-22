#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
TASK_ID="Q-20261022-VF-ITERATION-35"
TOKEN="20f0de1a-7953-4c05-95f8-f6a5b73fac26"
UNIT="llamacode-q35-supervisor"
PYTHON="/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source/.venv/bin/python"
PYTHONPATH_VALUE="/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source/tools"

"$PYTHON" - "$ROOT/WORK_QUEUE.lock" "$TOKEN" "$TASK_ID" <<'PY'
import json, pathlib, sys
lock = json.loads(pathlib.Path(sys.argv[1]).read_text())
if lock.get("token") != sys.argv[2] or lock.get("task_id") != sys.argv[3]:
    raise SystemExit(f"work queue lock ownership changed: {lock}")
PY

if systemctl --user is-active --quiet "$UNIT.service"; then
    echo "$UNIT.service is already active" >&2
    exit 1
fi

systemd-run --user --no-block --collect --unit="$UNIT" --slice=background.slice \
  --property=Type=exec \
  --property=KillMode=control-group \
  --property=OOMPolicy=stop \
  --property=ManagedOOMMemoryPressure=auto \
  --working-directory="$ROOT" \
  --setenv="HOME=$HOME" \
  --setenv="USER=${USER:-cristian}" \
  --setenv="PATH=${PATH:-/usr/local/bin:/usr/bin:/bin}" \
  --setenv="LANG=${LANG:-C.UTF-8}" \
  --setenv="LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-}" \
  --setenv="CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-}" \
  --setenv="PYTHONPATH=$PYTHONPATH_VALUE" \
  --setenv="STRATA_ROOT=/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source" \
  "$PYTHON" "$ROOT/artifacts/evaluacion-modelos-llamacode/$TASK_ID/scripts/run_all_context_holdout.py"

echo "Started $UNIT.service in background.slice; progress: $ROOT/artifacts/evaluacion-modelos-llamacode/$TASK_ID/receipts/progress.json"
