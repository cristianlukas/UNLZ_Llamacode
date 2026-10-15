#!/usr/bin/env bash
set -euo pipefail
COMPOSE_DIR="/home/cristian/.cache/llamacode/club-3090-src/models/qwen3.8-27b/vllm/compose/dual/autoround-int4"
cd "$COMPOSE_DIR"
export ESTATE_CONTAINER="llamacode-sol-eval-20261015"
export PORT="8113"
export BIND_HOST="127.0.0.1"
exec docker compose --project-name llamacode-sol-eval-20261015 \
  -f mtp.yml -f vram-quarantine.override.yml down
