#!/bin/bash
# usage: run.sh TAG SM KV CTX [extra...]
TAG=$1; SM=$2; KV=$3; CTX=$4; shift 4
S=/c/Users/cristian/AppData/Local/Temp/claude/C--Users-cristian-Documents-LlamaCode/6e272aae-7f7c-43eb-802c-5b2a5eda4bdf/scratchpad
B=/d/Models/llamacpp/bench-runtime/b10964/unpacked
M=/c/models/Qwen3.8-27B-ByteShape-IQ4_XS
T="C:/Users/cristian/AppData/Local/LlamaCode/LlamaCode/chat-templates/qwen38-tools-fixed.jinja"
$B/llama-server.exe -m ${MODEL:-$M/Qwen3.8-27B-IQ4_XS-3.84bpw.gguf} --mmproj $M/mmproj-bf16.gguf --port 8791 -c $CTX -ngl 999 -fa on -b 512 -ub 128 -t 8 \
  --split-mode $SM --tensor-split 0.5,0.5 --cache-type-k $KV --cache-type-v $KV --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0 \
  --no-context-shift --metrics --jinja --chat-template-file "$T" --parallel 1 --reasoning off ${SPEC:---spec-type draft-mtp --spec-draft-n-max 3} "$@" > $S/srv_$TAG.log 2>&1 &
PID=$!
for i in $(seq 1 180); do curl -s localhost:8791/health | grep -q ok && break; kill -0 $PID 2>/dev/null || { echo DIED; tail -20 $S/srv_$TAG.log; exit 1; }; sleep 2; done
nvidia-smi --query-gpu=memory.used --format=csv,noheader | tr '\n' ' '; echo
LC_IMG=$(cygpath -w $S/vis.png) python $(cygpath -w $S/srvbench.py) http://127.0.0.1:8791 $TAG
grep -E "draft acceptance|n_drafted" $S/srv_$TAG.log | tail -2
powershell -c 'Get-NetTCPConnection -LocalPort 8791 -State Listen -EA SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }'; kill $PID 2>/dev/null; sleep 4
