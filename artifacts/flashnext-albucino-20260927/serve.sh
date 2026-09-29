#!/usr/bin/env bash
# usage: serve.sh <variant>   (env/<variant>.env; later keys override earlier ones)
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
F=${FN_REPO:?FN_REPO=path to DominikBucko/qwen38-flash-next-2x3090 checkout}
set -a; source "$here/env/$1.env"; set +a
export IMAGE=${IMAGE_OVERRIDE:-qwen38-flash-next-2x3090:v0.3.0-local} SERVED_MODEL_NAME=local
docker rm -f qwen38-flash-next >/dev/null 2>&1 || true
nohup "$F/scripts/docker_serve.sh" > "$here/server-$1.log" 2>&1 &
t0=$(date +%s); peak=0
until curl -sf "localhost:${PORT:-8000}/health" >/dev/null; do
  sleep 5
  used=$(free -m | awk '/^Mem/{print $3}'); sw=$(free -m | awk '/^Inter|^Swap/{print $3}')
  (( used+sw > peak )) && peak=$((used+sw))
  docker ps --filter name=qwen38-flash-next -q | grep -q . || { echo "DIED after $(( $(date +%s)-t0 ))s"; tail -30 "$here/server-$1.log"; exit 1; }
done
echo "healthy after $(( $(date +%s)-t0 ))s; peak RAM+swap ${peak} MiB"
free -m; nvidia-smi --query-gpu=memory.used --format=csv
