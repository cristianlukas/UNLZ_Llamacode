#!/usr/bin/env bash
set -euo pipefail

TASK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_ROOT="/media/cristian/Disco local/LlamaCode-cache/build_linux"
DISPLAY="${EVAL_DISPLAY:-:97}"
SCREEN="${EVAL_SCREEN:-1440x900x24}"
PORT="${LLAMACODE_CONTROL_PORT:-8898}"
LOG_DIR="$TASK_ROOT/receipts/sessions/${EVAL_RUN_ID:-manual}"
ISOLATION_ID="${EVAL_ISOLATION_ID:-default}"
STATE_ROOT="$TASK_ROOT/runtime/sessions/$ISOLATION_ID"

export DISPLAY
export HOME="$TASK_ROOT/runtime/home"
export XDG_CONFIG_HOME="$STATE_ROOT/config"
export XDG_CACHE_HOME="$STATE_ROOT/cache"
export XDG_DATA_HOME="$STATE_ROOT/data"
export XDG_STATE_HOME="$STATE_ROOT/data/state"
export XDG_RUNTIME_DIR="$STATE_ROOT/run"
export LLAMACODE_PROFILES_DIR="$TASK_ROOT/runtime/profiles"
export LLAMACODE_CONTROL_PORT="$PORT"
export QT_QPA_PLATFORM=xcb
export GDK_BACKEND=x11
export GTK_A11Y=atspi
export GTK_USE_PORTAL=0
export GIO_USE_VFS=local
export LANG="${EVAL_LANG:-C.UTF-8}"

mkdir -p "$LOG_DIR" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" "$XDG_DATA_HOME" \
    "$XDG_STATE_HOME" "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"
if [[ -n "${EVAL_GTK_THEME:-}" ]]; then
    export GTK_THEME="$EVAL_GTK_THEME"
else
    unset GTK_THEME || true
fi

Xvfb "$DISPLAY" -screen 0 "$SCREEN" -nolisten tcp \
    >"$LOG_DIR/xvfb.log" 2>&1 &
XVFB_PID=$!
WM_PID=""
cleanup() {
    if [[ -n "$WM_PID" ]]; then kill "$WM_PID" 2>/dev/null || true; fi
    kill "$XVFB_PID" 2>/dev/null || true
    wait "$WM_PID" 2>/dev/null || true
    wait "$XVFB_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

for _ in $(seq 1 80); do
    if DISPLAY="$DISPLAY" xprop -root >/dev/null 2>&1; then break; fi
    sleep 0.1
done
DISPLAY="$DISPLAY" python3 "$TASK_ROOT/scripts/minimal_ewmh_wm.py" \
    >"$LOG_DIR/window-manager.log" 2>&1 &
WM_PID=$!
for _ in $(seq 1 80); do
    if DISPLAY="$DISPLAY" xprop -root _NET_SUPPORTING_WM_CHECK 2>/dev/null \
        | rg -q 'window id'; then break; fi
    sleep 0.1
done

cd "/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode"
"$BUILD_ROOT/LlamaCode" --agent-daemon 2>&1 \
    | tee "$LOG_DIR/llamacode-daemon.log"
