#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode

exec systemd-run --user --wait --collect --unit=q101-hyperqwen-attempt-10.service \
  --property=AppArmorProfile=chatgpt \
  --property=KillMode=control-group \
  --property=RuntimeMaxSec=1800 \
  --property=TimeoutStopSec=45 \
  --property=Nice=10 \
  --property=CPUWeight=20 \
  --property=IOWeight=25 \
  --property=IOSchedulingClass=best-effort \
  --property=IOSchedulingPriority=7 \
  --property=MemoryMax=infinity \
  --property=MemoryHigh=infinity \
  --property=MemorySwapMax=infinity \
  --setenv=GPU_UTIL=0.91 \
  --setenv=KV_MEM=3000000000 \
  --setenv=GPU_COUNT=2 \
  '--setenv=EXTRA_ARGS=--tensor-parallel-size 2' \
  --setenv=Q101_CANARY_READ_MAX_TOKENS=512 \
  --setenv=Q101_CANARY_WRITE_MAX_TOKENS=1024 \
  --setenv=Q101_CANARY_TOOL_CHOICE_MODE=named \
  --setenv=Q101_CANARY_ENABLE_THINKING=false \
  --setenv=Q101_CANARY_FIXTURE_PATH_ENUM=true \
  --setenv=Q101_CANARY_EXPLICIT_PATH_PROMPT=true \
  /usr/bin/bash "$ROOT/artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-101/runner/run_q101_attempt10_with_config_gate.sh"
