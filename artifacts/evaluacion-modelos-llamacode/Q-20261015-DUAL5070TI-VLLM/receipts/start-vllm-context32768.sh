#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
task_dir="$(cd "$script_dir/.." && pwd)"
repo_root="$(cd "$task_dir/../../.." && pwd)"
secondary_root="/media/cristian/Disco local/Models/LlamaCodeEval/Q-20261015-DUAL5070TI-VLLM"
fork_root="$secondary_root/source/dual-gpus-vllm"
secondary_runtime="$secondary_root/runtime"

mkdir -p "$secondary_runtime"/{hf-cache,xdg-cache,triton-cache,torchinductor-cache,cuda-cache,tmp,vllm-cache}
mkdir -p "/media/cristian/Disco local/.llamacode-tmp"

export CUDA_VISIBLE_DEVICES=0,1
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUTE_DSL_ARCH=sm_86
export CUDA_HOME=/usr/local/cuda
export PP_PARTITION=32,32
export MAX_LEN=32768
export NUM_BLOCKS=110
export KV_CACHE_MEMORY_BYTES=4000000000
export BLOCK_SIZE=1664
export SPEC_TOKENS=7
export EAGLE_BLOCK_DROP=0
export DRAFT_ATTN=TRITON_ATTN
export GPU_UTIL=0.93
export MAX_NUM_SEQS=1
export MAX_BATCHED_TOKENS=128
export PORT=18888
export SERVED_NAME=qwen3.8-27b
export MODELS="$secondary_root/models"
export MODEL="$secondary_root/models/target"
export DRAFTER="$secondary_root/models/drafter"
export VLLM_BIN="$task_dir/runtime/venv/bin/vllm"
export SHIM="$fork_root/shim/smfix.so"
export TEMPLATE="$fork_root/chat-templates/sharp-v22.5.0.jinja"

export HF_HOME="$secondary_runtime/hf-cache"
export HUGGINGFACE_HUB_CACHE="$secondary_runtime/hf-cache/hub"
export XDG_CACHE_HOME="$secondary_runtime/xdg-cache"
export VLLM_CACHE_ROOT="$secondary_runtime/vllm-cache"
export TRITON_CACHE_DIR="$secondary_runtime/triton-cache"
export TORCHINDUCTOR_CACHE_DIR="$secondary_runtime/torchinductor-cache"
export CUDA_CACHE_PATH="$secondary_runtime/cuda-cache"
export CUTE_DSL_CACHE_DIR="$secondary_runtime/cuda-cache/cute"
export TMPDIR="/media/cristian/Disco local/.llamacode-tmp"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

exec "$fork_root/launchers/w8a16-localhost.sh"
