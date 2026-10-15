#!/usr/bin/env bash
set -euo pipefail
COMPOSE_DIR="/home/cristian/.cache/llamacode/club-3090-src/models/qwen3.8-27b/vllm/compose/dual/autoround-int4"
cd "$COMPOSE_DIR"
export ESTATE_CONTAINER="llamacode-sol-eval-20261015"
export PORT="8113"
export BIND_HOST="127.0.0.1"
export ENABLE_THINKING="true"
export TEMP="1.0"
export TOP_P="0.95"
export TOP_K="20"
export MIN_P="0.0"
export PRESENCE_PENALTY="0.0"
export SPEC_N="4"
exec docker compose --project-name llamacode-sol-eval-20261015 \
  -f mtp.yml -f vram-quarantine.override.yml up -d --pull never
