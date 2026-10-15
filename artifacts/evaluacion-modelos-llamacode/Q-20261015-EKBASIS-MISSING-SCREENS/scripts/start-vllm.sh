#!/usr/bin/env bash
set -euo pipefail
TASK_ENV='/media/cristian/Disco local/Models/evaluations/ekbasis-27b-int4/runtime'
MODEL_DIR='/media/cristian/Disco local/Models/evaluations/ekbasis-27b-int4/model'
export CUDA_VISIBLE_DEVICES=1 CUDA_DEVICE_ORDER=PCI_BUS_ID
export HF_HOME="$TASK_ENV/hf-home" HF_HUB_OFFLINE=1 HF_HUB_DISABLE_IMPLICIT_TOKEN=1
export VLLM_CACHE_ROOT="$TASK_ENV/vllm-cache" XDG_CACHE_HOME="$TASK_ENV/xdg-cache"
export TORCH_EXTENSIONS_DIR="$TASK_ENV/torch-extensions" TRITON_CACHE_DIR="$TASK_ENV/triton-cache"
export TMPDIR='/tmp/ekbasis-q20261015'
mkdir -p "$TMPDIR"
exec "$TASK_ENV/venv/bin/vllm" serve "$MODEL_DIR" \
  --host 127.0.0.1 --port 18171 --served-model-name decider --dtype bfloat16 \
  --gpu-memory-utilization 0.95 --max-model-len 4096 \
  --enable-prefix-caching --mamba-cache-mode align \
  --logprobs-mode processed_logprobs --max-logprobs 600 --max-num-seqs 1
