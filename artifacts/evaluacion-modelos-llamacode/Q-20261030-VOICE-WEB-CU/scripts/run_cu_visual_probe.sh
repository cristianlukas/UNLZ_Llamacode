#!/usr/bin/env bash
set -euo pipefail
root_dir="$(cd "$(dirname "$0")/.." && pwd)"
probe_bin="/home/cristian/.cache/llamacode/build_tests_linux/qa_visual_automation"
openbox >"$root_dir/logs/cu-openbox.log" 2>&1 &
wm_pid=$!
trap 'kill "$wm_pid" 2>/dev/null || true' EXIT
sleep 1
"$probe_bin" --matrix --execute-click
