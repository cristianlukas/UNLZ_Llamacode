#!/usr/bin/env bash
set -euo pipefail

task_dir="$(cd "$(dirname "$0")/.." && pwd -P)"
model_dir="/media/cristian/Disco local/Models/llamacpp/club-3090/qwen3.8-27b-autoround-int4"
container_name="llamacode-anyjev-eval-20261015"

if docker inspect "$container_name" >/dev/null 2>&1; then
  echo "Refusing to replace existing container: $container_name" >&2
  exit 2
fi
if ss -ltn | awk '$4 ~ /:8117$/ {found=1} END {exit !found}'; then
  echo "Refusing to bind occupied port 8117" >&2
  exit 3
fi

docker run -d \
  --name "$container_name" \
  --gpus all \
  --ipc=host \
  --network host \
  --tmpfs /tmp:rw,exec,nosuid,nodev,size=8g \
  -e HF_HOME=/tmp/hf-anyjev \
  -e HF_HUB_OFFLINE=1 \
  -e TRANSFORMERS_OFFLINE=1 \
  -e VLLM_CACHE_ROOT=/tmp/vllm-anyjev \
  -e TORCHINDUCTOR_CACHE_DIR=/tmp/torchinductor-anyjev \
  -e TRITON_CACHE_DIR=/tmp/triton-anyjev \
  -v "$model_dir:/model:ro" \
  -v "$task_dir:/task:rw" \
  --entrypoint /usr/local/bin/vllm \
  vllm/vllm-openai:v0.27.1 \
  serve /model \
  --served-model-name qwen3.8-27b \
  --quantization auto_round \
  --dtype bfloat16 \
  --tensor-parallel-size 2 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.80 \
  --max-num-seqs 1 \
  --max-num-batched-tokens 4096 \
  --trust-remote-code \
  --enable-prefix-caching \
  --enable-chunked-prefill \
  --mamba-cache-mode align \
  --prefix-match-unit 16 \
  --kv-cache-dtype fp8_e4m3 \
  --disable-custom-all-reduce \
  --no-async-scheduling \
  --max-logprobs 20 \
  --host 127.0.0.1 \
  --port 8117
