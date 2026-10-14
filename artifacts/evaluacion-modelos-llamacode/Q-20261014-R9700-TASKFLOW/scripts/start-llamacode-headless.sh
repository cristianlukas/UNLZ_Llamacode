#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT="/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode/artifacts/evaluacion-modelos-llamacode/Q-20261014-R9700-TASKFLOW"
export LLAMACODE_CONTROL_PORT=8898
export LLAMACODE_PROFILES_DIR="$TASK_ROOT/runtime/profiles"
export XDG_DATA_HOME="$TASK_ROOT/runtime/xdg-data"
export XDG_CACHE_HOME="$TASK_ROOT/runtime/xdg-cache"
export XDG_CONFIG_HOME="$TASK_ROOT/runtime/xdg-config"
cd "/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode"
exec "/home/cristian/.cache/llamacode/build_linux/LlamaCode" --agent-daemon
