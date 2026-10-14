#!/usr/bin/env bash
set -euo pipefail
BIN="/home/cristian/.cache/llamacode-local-agent-eval-20261009/llama.cpp/build/bin/llama-server"
MODEL="/media/cristian/Disco local/Models/llamacpp/Qwen3.8-27B-GGUF-Q4_K_M/Qwen3.8-27B-Q4_K_M.gguf"
ARGS=(
  --model "$MODEL"
  --alias qwen3.8-27b-q4-k-m
  --host 127.0.0.1 --port 8350
  --ctx-size 131072 --parallel 1
  --n-gpu-layers 999 --split-mode layer --tensor-split 1,1
  --cache-type-k q8_0 --cache-type-v q8_0
  --batch-size 512 --ubatch-size 128
  --flash-attn on --jinja
  --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.0
  --repeat-penalty 1.0 --presence-penalty 0.0
)
if [[ -n "${EVAL_MMPROJ:-}" ]]; then
  ARGS+=(--mmproj "$EVAL_MMPROJ")
fi
exec "$BIN" "${ARGS[@]}"
