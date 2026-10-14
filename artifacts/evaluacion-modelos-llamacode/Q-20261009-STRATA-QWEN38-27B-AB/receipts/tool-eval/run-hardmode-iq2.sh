#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "$0")" && pwd)"
RUNNER="/home/cristian/.cache/codex-tool-eval-bench-v2.8.0/.venv/bin/tool-eval-bench"
BASE_URL="http://127.0.0.1:8351/v1"
MODEL="qwen3.8-flash-next-iq2_xs"
HEALTH_URL="http://127.0.0.1:8351/health"

for seed in 42 43 44; do
    if ! curl -fsS --max-time 3 "$HEALTH_URL" > "$ROOT/health-before-seed-${seed}.json"; then
        printf '%s seed=%s status=not-started reason=endpoint-unhealthy\n' \
            "$(date -u +%FT%TZ)" "$seed" | tee -a "$ROOT/status.txt"
        break
    fi

    started="$(date -u +%FT%TZ)"
    started_epoch="$(date +%s)"
    report_dir="$ROOT/reports/seed-${seed}"
    json_file="$ROOT/iq2-hardmode-seed-${seed}.json"
    log_file="$ROOT/runner-seed-${seed}.log"
    mkdir -p "$report_dir"

    "$RUNNER" run \
        --hardmode-only \
        --base-url "$BASE_URL" \
        --model "$MODEL" \
        --backend strata \
        --temperature 0.6 \
        --top-p 0.95 \
        --top-k 20 \
        --min-p 0 \
        --repeat-penalty 1 \
        --seed "$seed" \
        --variant-seed 20261010 \
        --timeout 120 \
        --max-turns 8 \
        --parallel 1 \
        --backend-kwargs '{"reasoning_effort":"medium"}' \
        --label "IQ2_XS-Strata-HardMode-seed-${seed}" \
        --json-file "$json_file" \
        --output-dir "$report_dir" \
        --no-live > "$log_file" 2>&1
    rc=$?

    ended="$(date -u +%FT%TZ)"
    elapsed="$(( $(date +%s) - started_epoch ))"
    printf '%s seed=%s started=%s ended=%s elapsed_sec=%s exit=%s json=%s log=%s\n' \
        "$(date -u +%FT%TZ)" "$seed" "$started" "$ended" "$elapsed" "$rc" \
        "$json_file" "$log_file" | tee -a "$ROOT/status.txt"

    if ! curl -fsS --max-time 3 "$HEALTH_URL" > "$ROOT/health-after-seed-${seed}.json"; then
        printf '%s seed=%s status=stopped-after-unhealthy-endpoint\n' \
            "$(date -u +%FT%TZ)" "$seed" | tee -a "$ROOT/status.txt"
        break
    fi
done
