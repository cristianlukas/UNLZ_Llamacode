#!/usr/bin/env python3
"""Read-only preflight: ensure no known local inference service is active."""
import json, os, socket, subprocess
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path("/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode")
TASK=ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-111"
TOKEN="b680a96eba14d849b2a46f80cffb89a2"
lock=json.loads((ROOT/"WORK_QUEUE.lock").read_text())
if lock.get("task_id")!="Q-20261024-VF-ITERATION-111" or lock.get("token")!=TOKEN: raise SystemExit("lock mismatch")
patterns=("llama-server","vllm.entrypoints","vllm serve","sglang.launch_server","strata/serve/server.py","ollama serve","llama_cpp.server","ninfer","openjet")
processes=[]
for item in Path("/proc").iterdir():
 if not item.name.isdigit(): continue
 try: cmd=(item/"cmdline").read_bytes().replace(b"\0",b" ").decode(errors="replace").strip()
 except OSError: continue
 if cmd and any(p in cmd.lower() for p in patterns):
  processes.append({"pid":int(item.name),"cmdline":cmd[:500]})
ss=subprocess.run(["ss","-ltnp"],capture_output=True,text=True,check=True)
listeners=[line.strip() for line in ss.stdout.splitlines()[1:] if line.strip()]
known_ports={8363,8364,18789,8000,8001,8080,5000,5001,11434,1234,50051}
occupied=[]
for line in listeners:
 fields=line.split()
 if len(fields)<4: continue
 addr=fields[3]
 try: port=int(addr.rsplit(":",1)[1].rstrip("]"))
 except ValueError: continue
 if port in known_ports: occupied.append({"port":port,"listener":line})
result={"taskId":"Q-20261024-VF-ITERATION-111","capturedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),"status":"pass" if not processes and not occupied else "blocked","lockOwned":True,"knownInferenceProcesses":processes,"knownInferencePorts":{"checked":sorted(known_ports),"occupied":occupied},"allListeningSockets":listeners,"gpuUsed":False,"modelStarted":False}
(TASK/"receipts/q111-host-preflight.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2))
if result["status"]!="pass": raise SystemExit(1)
