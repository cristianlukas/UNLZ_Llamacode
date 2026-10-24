#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode
COMPOSE_DIR="/media/cristian/HDD extra/Modelos-eval/Q85-HyperQwen/HyperQwen"
cd "$COMPOSE_DIR"
docker compose --profile single -f docker-compose.yml -f compose.q85.yaml config --format json | python3 -c '''import json,sys; d=json.load(sys.stdin); e=d["services"]["single"]["environment"]; safe={k:e.get(k) for k in ("GPU_UTIL","KV_MEM","GPU_COUNT","EXTRA_ARGS","MAX_LEN","MAX_SEQS")}; print("Q85_COMPOSE_ENV_READBACK", json.dumps(safe, sort_keys=True), flush=True); assert safe["GPU_UTIL"]=="0.91" and safe["KV_MEM"]=="3000000000" and safe["GPU_COUNT"]=="2" and safe["EXTRA_ARGS"]=="--tensor-parallel-size 2"'''
[[ "${Q85_CANARY_TOOL_MAX_TOKENS:-}" == "512" ]]
[[ "${Q85_CANARY_EXPLICIT_PATH_PROMPT:-}" == "true" ]]
exec /usr/bin/bash "$ROOT/artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-85/runner/run_q85_tp2_canary.sh"
