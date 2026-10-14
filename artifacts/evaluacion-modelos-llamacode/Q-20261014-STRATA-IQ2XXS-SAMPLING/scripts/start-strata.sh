#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT="/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode/artifacts/evaluacion-modelos-llamacode/Q-20261014-STRATA-IQ2XXS-SAMPLING"
STRATA_ROOT="/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source"
exec "$STRATA_ROOT/.venv/bin/python" "$STRATA_ROOT/serve/server.py" --engine strata --config "$TASK_ROOT/configs/iq2xs-strata-1m.json" --host 127.0.0.1 --port 8352
