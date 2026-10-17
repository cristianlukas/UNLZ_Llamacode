#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT="/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode/artifacts/evaluacion-modelos-llamacode/Q-20261017-QWEN38-27B-OVERTHINKING-RETEST/runtime"
export LLAMACODE_CONTROL_PORT=18219
export LLAMACODE_PROFILES_DIR="$TASK_ROOT/profiles"
export LLAMACODE_SYSTEM_PROFILES="$TASK_ROOT/system_profiles.json"
export LLAMACODE_MODELS_DIR="$TASK_ROOT/models"
export XDG_DATA_HOME="$TASK_ROOT/xdg-data"
export XDG_CACHE_HOME="$TASK_ROOT/xdg-cache"
export XDG_CONFIG_HOME="$TASK_ROOT/xdg-config"
export QT_QPA_PLATFORM=offscreen
export LD_LIBRARY_PATH="/usr/local/cuda-12.8/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cd "/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode"
exec "/media/cristian/Disco local/LlamaCode-cache/build_linux/LlamaCode" --agent-daemon
