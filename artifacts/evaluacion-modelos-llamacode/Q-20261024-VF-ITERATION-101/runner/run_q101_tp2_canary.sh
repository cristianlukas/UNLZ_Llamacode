#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode
COMPOSE_DIR="/media/cristian/HDD extra/Modelos-eval/Q85-HyperQwen/HyperQwen"
cd "$ROOT"

# Re-read the repository workflow and verify this task still owns the lock
# immediately before the candidate server gets both GPUs.
cat AGENTS.md README.md WORK_QUEUE.md WORK_QUEUE.lock >/dev/null
python3 - <<'PY'
import json, os, re, subprocess, sys

root = "/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode"
with open(os.path.join(root, "WORK_QUEUE.lock"), encoding="utf-8") as f:
    lock = json.load(f)
if lock.get("task_id") != "Q-20261024-VF-ITERATION-101" or lock.get("token") != "f5f2021d-5cbf-4ae2-a0c9-878f53871914":
    raise SystemExit("Q101 lock mismatch")
for path, minimum in [("/", 8 * 1024**3), ("/var/lib/containerd", 18 * 1024**3), ("/media/cristian/HDD extra", 20 * 1024**3)]:
    output = subprocess.run(["df", "-B1", "--output=avail", path], check=True, capture_output=True, text=True).stdout
    free = int(output.splitlines()[-1])
    print("FREE_BYTES", path, free, flush=True)
    if free < minimum:
        raise SystemExit("storage floor failed: " + path)
names = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], check=True, capture_output=True, text=True).stdout
listeners = subprocess.run(["ss", "-ltnp"], check=True, capture_output=True, text=True).stdout
pattern = re.compile(r"(llama-server|vllm.*(serve|api)|strata.*(serve|server)|hyperqwen.*(single|server)|peritosoft.*(serve|server))", re.I)
processes = []
for pid in os.listdir("/proc"):
    if not pid.isdigit() or pid == str(os.getpid()):
        continue
    try:
        cmd = open("/proc/" + pid + "/cmdline", "rb").read().replace(b"\0", b" ").decode(errors="ignore")
    except OSError:
        continue
    if pattern.search(cmd) and "run_q85_tp2_canary" not in cmd:
        processes.append(pid)
if any(pattern.search(name) for name in names.splitlines()) or processes:
    raise SystemExit("an inference server is already active; leaving it untouched")
if any(":18142" in line for line in listeners.splitlines()):
    raise SystemExit("candidate port 18142 is already listening; leaving it untouched")
print("NO_INFERENCE_SERVER", flush=True)
PY

cd "$COMPOSE_DIR"
compose() {
    docker compose --profile single -f docker-compose.yml -f compose.q85.yaml "$@"
}
capture_server_logs() {
    local container_id log_path
    container_id=$(compose ps --all -q single 2>/dev/null | head -n 1 || true)
    [ -n "$container_id" ] || return 0
    log_path="$ROOT/artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-101/receipts/q101-server-boot-$(date -u +%Y%m%dT%H%M%SZ).log"
    Q101_LOG_CONTAINER_ID="$container_id" Q101_LOG_PATH="$log_path" Q101_COMPOSE_DIR="$COMPOSE_DIR" python3 - <<'PY'
import os
import subprocess
from pathlib import Path

result = subprocess.run(
    ["docker", "logs", "--tail", "1200", os.environ["Q101_LOG_CONTAINER_ID"]],
    capture_output=True,
)
data = (result.stdout + result.stderr).decode("utf-8", errors="replace")
env_path = Path(os.environ["Q101_COMPOSE_DIR"]) / ".env"
for line in env_path.read_text(encoding="utf-8").splitlines():
    if line.startswith("VLLM_API_KEY="):
        secret = line.split("=", 1)[1].strip().strip('"').strip("'")
        if secret:
            data = data.replace(secret, "[REDACTED]")
path = Path(os.environ["Q101_LOG_PATH"])
path.write_text(data, encoding="utf-8")
os.chmod(path, 0o600)
print("Q101_SERVER_LOG", path, flush=True)
PY
}
cleanup() {
    code=$?
    trap - EXIT
    if [ -n "${GUARD_PID:-}" ]; then kill "$GUARD_PID" 2>/dev/null || true; wait "$GUARD_PID" 2>/dev/null || true; fi
    capture_server_logs || echo "Q101_SERVER_LOG_CAPTURE_FAILED"
    compose down --timeout 30 >/dev/null 2>&1 || true
    echo "Q101_CANDIDATE_SERVER_STOPPED"
    exit "$code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

mkdir -p "$ROOT/artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-101/runs" "$ROOT/artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-101/receipts"
python3 "$ROOT/artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-101/runner/q101_memory_guard.py" \
  --main-pid "$$" \
  --samples "$ROOT/artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-101/runs/host-samples.jsonl" \
  --stop-reason "$ROOT/artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-101/receipts/memory-hard-stop.txt" &
GUARD_PID=$!

compose up -d --no-build --pull never single
healthy=0
for i in $(seq 1 180); do
    if curl -fsS --max-time 2 http://127.0.0.1:18142/health >/dev/null 2>&1; then
        healthy=1
        echo "Q101_SERVER_HEALTHY"
        break
    fi
    container_id=$(compose ps --all -q single | head -n 1)
    if [ -n "$container_id" ] && ! docker inspect -f '{{.State.Running}}' "$container_id" 2>/dev/null | grep -qx true; then
        echo "Q101_SERVER_EXITED_DURING_START"
        compose logs --no-color --tail=100 single
        exit 1
    fi
    if [ -n "$container_id" ]; then
        recent_logs=$(docker logs --tail=120 "$container_id" 2>&1 || true)
        if printf '%s\n' "$recent_logs" | grep -Eiq 'CUDA error: out of memory|CUDA out of memory|Worker failed with error|Worker proc .*died unexpectedly'; then
            echo "Q101_SERVER_FATAL_CUDA_OR_WORKER_ERROR"
            printf '%s\n' "$recent_logs" | tail -24
            exit 1
        fi
    fi
    if [ $((i % 6)) -eq 0 ]; then
        echo "Q101_WAITING_FOR_HEALTH_SECONDS $((i * 10))"
    fi
    sleep 10
done
if [ "$healthy" -ne 1 ]; then
    echo "Q101_SERVER_HEALTH_TIMEOUT"
    compose logs --no-color --tail=120 single
    exit 1
fi
compose logs --no-color --tail=180 single 2>&1 | grep -Ei 'KV cache|kv pool|available kv|GPU blocks|maximum concurrency|cache tokens|memory profiling' | tail -20 || true
python3 "$ROOT/artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-101/runner/q101_tool_canary.py"
