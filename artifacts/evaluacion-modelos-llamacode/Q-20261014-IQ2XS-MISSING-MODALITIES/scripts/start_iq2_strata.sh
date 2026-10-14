#!/usr/bin/env bash
set -euo pipefail
ROOT="/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source"
TASK="/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode/artifacts/evaluacion-modelos-llamacode/Q-20261014-IQ2XS-MISSING-MODALITIES"
CONFIG="${EVAL_STRATA_CONFIG:-$TASK/configs/strata-iq2-text.json}"
cd "$ROOT"
exec "$ROOT/.venv/bin/python" "$ROOT/serve/server.py" \
  --engine strata --config "$CONFIG" --host 127.0.0.1 --port 8350
