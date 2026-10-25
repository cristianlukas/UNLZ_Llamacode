#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
TASK_ID="Q-20261025-VF-ITERATION-117"
UNIT="llamacode-q117-supervisor-attempt03"
PYTHON="/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source/.venv/bin/python"

TOKEN="$("$PYTHON" - "$ROOT/WORK_QUEUE.lock" "$TASK_ID" <<'PY'
import json, pathlib, sys
lock = json.loads(pathlib.Path(sys.argv[1]).read_text())
task_id = lock.get("task_id", lock.get("taskId"))
if task_id != sys.argv[2] or not lock.get("token"):
    raise SystemExit(f"work queue lock ownership changed: {lock}")
print(lock["token"])
PY
)"

if sudo -n systemctl is-active --quiet "$UNIT.service"; then
  echo "$UNIT.service is already active" >&2
  exit 1
fi
if systemctl --user is-active --quiet "$UNIT.service"; then
  echo "legacy user-manager $UNIT.service is active; inspect before proceeding" >&2
  exit 1
fi

sudo -n systemd-run --system --no-block --collect --unit="$UNIT" --slice=background.slice \
  --uid="$(id -u)" --gid="$(id -g)" \
  --property=Type=exec --property=KillMode=control-group --property=OOMPolicy=kill \
  --property=OOMScoreAdjust=800 --property=MemoryHigh=1G --property=MemoryMax=2G \
  --property=MemorySwapMax=1G --property=ManagedOOMMemoryPressure=auto \
  --working-directory="$ROOT" \
  --setenv="HOME=$HOME" --setenv="USER=${USER:-cristian}" \
  --setenv="PATH=${PATH:-/usr/local/bin:/usr/bin:/bin}" \
  --setenv="LANG=${LANG:-C.UTF-8}" --setenv="LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-}" \
  --setenv="CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-}" \
  --setenv="LLAMACODE_QUEUE_LOCK_TOKEN=$TOKEN" --setenv="LLAMACODE_TASK_ID=$TASK_ID" \
  "$PYTHON" "$ROOT/artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-117/scripts/q117_supervisor_attempt03.py"

echo "Started $UNIT.service in system background.slice; progress: $ROOT/artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-117/receipts/progress-attempt03.json"
