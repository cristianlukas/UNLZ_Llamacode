#!/bin/bash
# arm.sh NAME CUDA_DEVS PARALLEL CTX WORKERS [extra args...]
NAME=$1; DEVS=$2; PAR=$3; CTX=$4; WORKERS=$5; shift 5
P=$(dirname $0); BIN=/home/cristian/.local/share/LlamaCode/LlamaCode/linux-runtime/cuda-flashnext-2x3090
M="/media/cristian/Disco local/Models/llamacpp/Qwen3.8-27B-GGUF"
T=/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode/.claude/worktrees/ingi-charla/assets/chat-templates/qwen38-tools-fixed.jinja
PORT=18431
CUDA_VISIBLE_DEVICES=$DEVS LD_LIBRARY_PATH=$BIN $BIN/llama-server -m "$M/Qwen3.8-27B-UD-Q4_K_XL.gguf" --mmproj "$M/mmproj-BF16.gguf" \
  --host 127.0.0.1 --port $PORT -c $CTX -ngl 999 -b 2048 -ub 512 -t 8 -fa on --cache-type-k q4_0 --cache-type-v q4_0 \
  --temp 0.60 --top-p 0.95 --top-k 20 --min-p 0.0 --no-context-shift --metrics --no-warmup --jinja --chat-template-file "$T" \
  --cache-reuse 512 --parallel $PAR --reasoning off "$@" > $P/$NAME.server.log 2>&1 &
SP=$!
for i in $(seq 1 240); do curl -sf http://127.0.0.1:$PORT/health >/dev/null && break; kill -0 $SP 2>/dev/null || break; sleep 1; done
if ! curl -sf http://127.0.0.1:$PORT/health >/dev/null; then echo "$NAME: server no levantó"; tail -5 $P/$NAME.server.log; kill $SP 2>/dev/null; exit 1; fi
nvidia-smi --query-gpu=index,memory.used --format=csv,noheader > $P/$NAME.vram.txt
python3 $P/bench.py $PORT $WORKERS 4 $P/$NAME.json 2>&1 | tail -12
kill $SP; wait $SP 2>/dev/null; sleep 2
