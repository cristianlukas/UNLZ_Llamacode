#!/usr/bin/env bash
set -Eeuo pipefail
ROOT='/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode'
OUT="$ROOT/artifacts/evaluacion-modelos-llamacode/Q-20261116-Q240-PREFIX-CACHE-AB"
MODEL='/media/cristian/Disco local/Models/llamacpp/Qwen3.8-27B-GGUF/Qwen3.8-27B-UD-Q4_K_XL.gguf'
SERVER='/home/cristian/.cache/llamacode-evaluations/Q210-tandem-sm86-20261115/llama.cpp/build/bin/llama-server'
PORT=18780
PID=''
cleanup() {
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then kill -TERM "$PID" 2>/dev/null || true; fi
  if [[ -n "$PID" ]]; then wait "$PID" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM
printf 'worker_started_utc=%s\n' "$(date -u +%FT%TZ)" | tee "$OUT/receipts/worker.log"
[[ "$(sha256sum "$MODEL" | awk '{print $1}')" == '3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e' ]]
[[ "$(sha256sum "$SERVER" | awk '{print $1}')" == '31de89f011944d9f88d7f8fd188df04d6d1c93db5faad1a697820ad36c0eae96' ]]
"$SERVER" --model "$MODEL" --host 127.0.0.1 --port "$PORT" --ctx-size 8320 --parallel 1 --device CUDA0,CUDA1 --split-mode layer --tensor-split 1,1 --gpu-layers all --fit off --flash-attn on --cache-type-k q8_0 --cache-type-v q8_0 --batch-size 512 --ubatch-size 64 --no-context-shift --metrics --no-warmup --jinja --chat-template-kwargs '{"enable_thinking":false}' --reasoning off --predict 4096 --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.0 --repeat-penalty 1.0 --presence-penalty 0.0 > "$OUT/runs/server.log" 2>&1 &
PID=$!
printf 'server_pid=%s\n' "$PID" | tee -a "$OUT/receipts/worker.log"
READY=0
for _ in $(seq 1 180); do
  if curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null; then READY=1; break; fi
  if ! kill -0 "$PID" 2>/dev/null; then echo 'server_exited_before_ready' | tee -a "$OUT/receipts/worker.log"; exit 3; fi
  sleep 2
done
[[ "$READY" == 1 ]]
printf 'api_ready_utc=%s\n' "$(date -u +%FT%TZ)" | tee -a "$OUT/receipts/worker.log"
cd "$ROOT"
python3 tools/benchmark_prefix_loop.py --url "http://127.0.0.1:$PORT/v1/chat/completions" --model 'Qwen3.8-27B-UD-Q4_K_XL.gguf' --turns 6 --passes 3 --timeout 120 --out "$OUT/runs/q240-prefix-cache-result.json" | tee "$OUT/runs/client.log"
printf 'client_exit=0\nworker_finished_utc=%s\n' "$(date -u +%FT%TZ)" | tee -a "$OUT/receipts/worker.log"
