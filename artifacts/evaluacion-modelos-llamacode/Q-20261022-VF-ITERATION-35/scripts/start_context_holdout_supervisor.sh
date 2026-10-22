#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
TASK_ID="Q-20261022-VF-ITERATION-35"
LOCK_TASK_ID="Q-20261022-VF-ITERATION-37"
UNIT="llamacode-q35-supervisor"
PYTHON="/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source/.venv/bin/python"
PYTHONPATH_VALUE="/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source/tools"

TOKEN="$("$PYTHON" - "$ROOT/WORK_QUEUE.lock" "$LOCK_TASK_ID" <<'PY'
import json, pathlib, sys
lock = json.loads(pathlib.Path(sys.argv[1]).read_text())
if lock.get("task_id") != sys.argv[2] or not lock.get("token"):
    raise SystemExit(f"work queue lock ownership changed: {lock}")
print(lock["token"])
PY
)"

if sudo -n systemctl is-active --quiet "$UNIT.service"; then
    echo "$UNIT.service is already active" >&2
    exit 1
fi
if systemctl --user is-active --quiet "$UNIT.service"; then
    echo "legacy user-manager $UNIT.service is active; stop and reconcile it before migration" >&2
    exit 1
fi

sudo -n systemd-run --system --no-block --collect --unit="$UNIT" --slice=background.slice \
  --uid="$(id -u)" --gid="$(id -g)" \
  --property=Type=exec \
  --property=KillMode=control-group \
  --property=MemoryHigh=1G \
  --property=MemoryMax=2G \
  --property=MemorySwapMax=1G \
  --property=OOMScoreAdjust=800 \
  --property=OOMPolicy=kill \
  --property=ManagedOOMMemoryPressure=auto \
  --working-directory="$ROOT" \
  --setenv="HOME=$HOME" \
  --setenv="USER=${USER:-cristian}" \
  --setenv="PATH=${PATH:-/usr/local/bin:/usr/bin:/bin}" \
  --setenv="LANG=${LANG:-C.UTF-8}" \
  --setenv="LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-}" \
  --setenv="CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-}" \
  --setenv="PYTHONPATH=$PYTHONPATH_VALUE" \
  --setenv="LLAMACODE_QUEUE_LOCK_TOKEN=$TOKEN" \
  --setenv="LLAMACODE_TASK_ID=$LOCK_TASK_ID" \
  --setenv="STRATA_ROOT=/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source" \
  "$PYTHON" "$ROOT/artifacts/evaluacion-modelos-llamacode/$TASK_ID/scripts/run_all_context_holdout.py"

echo "Started $UNIT.service in background.slice; progress: $ROOT/artifacts/evaluacion-modelos-llamacode/$TASK_ID/receipts/progress.json"
