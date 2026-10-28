#!/usr/bin/env bash
set -euo pipefail
MODEL='/media/cristian/Disco local/Modelos-eval/Q-20261027-VF-ITERATION-172/Bonsai2-Prism-PQ2_0/models/Ternary-Bonsai-2-27B-PQ2_0.gguf'
BIN='/media/cristian/Disco local/Modelos-eval/Q-20261027-VF-ITERATION-172/Bonsai2-Prism-PQ2_0/runtime/llama-prism-b10826-c9c34bc/llama-bench'
ROOT='artifacts/evaluacion-modelos-llamacode/Q-20261028-VF-ITERATION-173'
OUT="$ROOT/runs/prism-a17"
LOG="$ROOT/logs/prism-a17"
BENCH_PID=''
MON_PID=''
cleanup() {
  if [[ -n "$BENCH_PID" ]] && kill -0 "$BENCH_PID" 2>/dev/null; then kill -TERM "$BENCH_PID" 2>/dev/null || true; fi
  if [[ -n "$MON_PID" ]] && kill -0 "$MON_PID" 2>/dev/null; then kill "$MON_PID" 2>/dev/null || true; fi
}
trap cleanup INT TERM HUP
run_level() {
  local label="$1" prompt="$2" reps="$3" rc=0
  printf '%s start prompt=%s repetitions=%s
' "$(date -u +%FT%TZ)" "$prompt" "$reps" | tee -a "$LOG/progress.log"
  "$BIN" --model "$MODEL" --device CUDA0/CUDA1 --split-mode layer --tensor-split 1/1 --n-gpu-layers 99 --flash-attn on --batch-size 2048 --ubatch-size 512 --threads 16 -pg "$prompt,128" --repetitions "$reps" --no-warmup --progress --output json > "$OUT/$label.json" 2> "$LOG/$label.log" &
  BENCH_PID=$!
  (
    low=0
    gpu_bad=0
    started=$(date +%s)
    while kill -0 "$BENCH_PID" 2>/dev/null; do
      ts=$(date -u +%FT%TZ)
      mem=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)
      psi=$(awk '/^some / {for (i=1;i<=NF;i++) if ($i ~ /^avg10=/) {split($i,a,"="); print a[2]}}' /proc/pressure/memory)
      gpu=$(nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv,noheader 2>/dev/null | tr '
' '|')
      g0=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | sed -n '1p' | tr -cd '0-9')
      g1=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | sed -n '2p' | tr -cd '0-9')
      elapsed=$(( $(date +%s) - started ))
      printf '%s memavailable_kib=%s psi_some_avg10=%s gpu=%s
' "$ts" "$mem" "$psi" "$gpu" >> "$LOG/$label-resources.log"
      if (( elapsed >= 45 )) && { [[ ! "$g0" =~ ^[0-9]+$ ]] || [[ ! "$g1" =~ ^[0-9]+$ ]] || (( g0 < 1000 || g1 < 1000 )); }; then
        gpu_bad=$((gpu_bad+1))
      else
        gpu_bad=0
      fi
      if (( gpu_bad >= 2 )); then
        printf '%s stop: dual-GPU allocation gate failed; GPU0=%s MiB GPU1=%s MiB; terminating only PID %s
' "$ts" "$g0" "$g1" "$BENCH_PID" >> "$LOG/$label-resources.log"
        kill -TERM "$BENCH_PID" 2>/dev/null || true
        exit 0
      fi
      if [[ "$mem" =~ ^[0-9]+$ ]] && (( mem < 33554432 )); then low=$((low+1)); else low=0; fi
      if (( low >= 4 )); then
        printf '%s stop: MemAvailable below 32 GiB for four 15s samples; terminating only PID %s
' "$ts" "$BENCH_PID" >> "$LOG/$label-resources.log"
        kill -TERM "$BENCH_PID" 2>/dev/null || true
        exit 0
      fi
      sleep 15
    done
  ) &
  MON_PID=$!
  if wait "$BENCH_PID"; then rc=0; else rc=$?; fi
  BENCH_PID=''
  kill "$MON_PID" 2>/dev/null || true
  wait "$MON_PID" 2>/dev/null || true
  MON_PID=''
  printf '%s finish prompt=%s exit=%s
' "$(date -u +%FT%TZ)" "$prompt" "$rc" | tee -a "$LOG/progress.log"
  return "$rc"
}
run_level 8k 8192 3
run_level 32k 32768 1
run_level 64k 65536 1
run_level 128k 131072 1
run_level 256k 261888 1
