#!/bin/bash
# usage: bcbrun.sh TAG SM KV CTX MODEL [extra]
TAG=$1; SM=$2; KV=$3; CTX=$4; MODEL=$5; shift 5
S=/c/Users/cristian/AppData/Local/Temp/claude/C--Users-cristian-Documents-LlamaCode/6e272aae-7f7c-43eb-802c-5b2a5eda4bdf/scratchpad
B=/d/Models/llamacpp/bench-runtime/b10964/unpacked
T="C:/Users/cristian/AppData/Local/LlamaCode/LlamaCode/chat-templates/qwen38-tools-fixed.jinja"
$B/llama-server.exe -m $MODEL --port 8791 -c $CTX -ngl 999 -fa on -b 512 -ub 128 -t 8 --split-mode $SM --tensor-split 0.5,0.5 \
  --cache-type-k $KV --cache-type-v $KV --no-context-shift --jinja --chat-template-file "$T" --parallel 1 --reasoning off \
  ${SPEC:---spec-type draft-mtp --spec-draft-n-max 3} "$@" > $S/bcbsrv_$TAG.log 2>&1 &
PID=$!
for i in $(seq 1 180); do curl -s localhost:8791/health | grep -q ok && break; kill -0 $PID 2>/dev/null || { echo DIED; tail -5 $S/bcbsrv_$TAG.log; exit 1; }; sleep 2; done
python $(cygpath -w $S/bcb8.py) run http://127.0.0.1:8791 $TAG $(cygpath -w $S/bcb_out) | tail -1
powershell -c 'Get-NetTCPConnection -LocalPort 8791 -State Listen -EA SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }'; kill $PID 2>/dev/null; sleep 4
