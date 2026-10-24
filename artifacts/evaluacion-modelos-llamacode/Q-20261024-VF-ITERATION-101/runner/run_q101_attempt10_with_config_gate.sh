#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode
COMPOSE_DIR="/media/cristian/HDD extra/Modelos-eval/Q85-HyperQwen/HyperQwen"
cd "$COMPOSE_DIR"
docker compose --profile single -f docker-compose.yml -f compose.q85.yaml config --format json | python3 -c "import json,sys; d=json.load(sys.stdin); s=d['services']['single']; e=s['environment']; safe={k:e.get(k) for k in ('GPU_UTIL','KV_MEM','GPU_COUNT','EXTRA_ARGS','MAX_LEN','MAX_SEQS','SPEC','DFLASH_TOKENS')}; print('Q101_COMPOSE_ENV_READBACK',json.dumps(safe,sort_keys=True),flush=True); assert safe['GPU_UTIL']=='0.91' and safe['KV_MEM']=='3000000000' and safe['GPU_COUNT']=='2' and safe['EXTRA_ARGS']=='--tensor-parallel-size 2' and safe['MAX_LEN']=='65536' and safe['SPEC']=='dflash2'; assert s['image']=='ghcr.io/syv-ai/hyperqwen@sha256:0acd4b9625473e51c9bab56406c30814bc0d0d7e0a38deb408c62664b5a77669'"
[[ "${Q101_CANARY_READ_MAX_TOKENS:-}" == "512" ]]
[[ "${Q101_CANARY_WRITE_MAX_TOKENS:-}" == "1024" ]]
[[ "${Q101_CANARY_TOOL_CHOICE_MODE:-}" == "named" ]]
[[ "${Q101_CANARY_ENABLE_THINKING:-}" == "false" ]]
[[ "${Q101_CANARY_FIXTURE_PATH_ENUM:-}" == "true" ]]
[[ "${Q101_CANARY_EXPLICIT_PATH_PROMPT:-}" == "true" ]]
exec /usr/bin/bash "$ROOT/artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-101/runner/run_q101_tp2_canary.sh"
