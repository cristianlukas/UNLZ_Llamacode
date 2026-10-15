#!/usr/bin/env bash
set -euo pipefail
TASK_ENV='/media/cristian/Disco local/Models/evaluations/ekbasis-27b-int4/runtime'
MODEL_DIR='/media/cristian/Disco local/Models/evaluations/ekbasis-27b-int4/model'
export CUDA_VISIBLE_DEVICES=1 CUDA_DEVICE_ORDER=PCI_BUS_ID
export HF_HOME="$TASK_ENV/hf-home" HF_HUB_OFFLINE=1 HF_HUB_DISABLE_IMPLICIT_TOKEN=1
export VLLM_CACHE_ROOT="$TASK_ENV/vllm-cache" XDG_CACHE_HOME="$TASK_ENV/xdg-cache"
export TMPDIR='/tmp/ekbasis-q20261015'
exec "$TASK_ENV/venv/bin/python" "$MODEL_DIR/serve.py" --model "$MODEL_DIR" \
  --vllm-url http://127.0.0.1:18171 --host 127.0.0.1 --port 18172
