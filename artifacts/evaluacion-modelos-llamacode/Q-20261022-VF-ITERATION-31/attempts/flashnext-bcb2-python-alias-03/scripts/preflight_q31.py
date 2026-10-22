#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,pathlib,shutil,subprocess,time
ROOT=pathlib.Path("/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode")
ATTEMPT=ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261022-VF-ITERATION-31/attempts/flashnext-bcb2-python-alias-03"
LOCK="fb13f0630f802012a3540c90520cf300"
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def meminfo():
 d={}
 for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
  k,*v=line.split()
  if k.rstrip(":") in {"MemAvailable","SwapFree"}:d[k.rstrip(":")]=int(v[0])*1024
 return d
def servers():
 names={"strata","llama-server","ollama","vllm","sglang","aphrodite","koboldcpp","localai","local-ai"};out=[]
 for p in pathlib.Path("/proc").iterdir():
  if not p.name.isdigit():continue
  try:comm=(p/"comm").read_text().strip().lower();argv=(p/"cmdline").read_bytes().replace(b"\0",b" ").decode(errors="replace").strip()
  except OSError:continue
  low=argv.lower();py=comm in {"python","python3"} and any(x in low for x in ("vllm serve","-m vllm","sglang serve","-m sglang","serve/server.py --engine strata","-m aphrodite"))
  if comm in names or py:out.append({"pid":int(p.name),"comm":comm,"argv":argv[:500]})
 return out
def main():
 reg=json.loads((ATTEMPT/"receipts/preregistration.json").read_text());lock=json.loads((ROOT/"WORK_QUEUE.lock").read_text())
 if lock.get("token")!=LOCK:raise SystemExit("lock token mismatch")
 for name,h in reg["instruction_hashes"].items():
  if sha(ROOT/name)!=h:raise SystemExit(f"instruction hash changed: {name}")
 if sha(ATTEMPT/"scripts/run_q31.py")!=reg["runner_sha256"]:raise SystemExit("runner changed")
 if sha(ATTEMPT/"work/diagnostic-suite.json")!=reg["suite"]["variant_sha256"]:raise SystemExit("suite changed")
 prep=json.loads((ATTEMPT/"receipts/preparation.json").read_text())
 if sha(ATTEMPT/"receipts/preparation.json")!=reg["prepared_receipt_sha256"]:raise SystemExit("preparation receipt changed")
 shim=pathlib.Path(reg["python_alias_path"])
 if sha(shim)!=reg["python_alias_sha256"]:raise SystemExit("python alias changed")
 mem=meminfo();gib=1024**3
 info={"MemAvailableGiB":round(mem["MemAvailable"]/gib,2),"SwapFreeGiB":round(mem["SwapFree"]/gib,2)}
 model=pathlib.Path("/media/cristian/HDD extra/Models/LlamaCodeEval/Q-20261010-STRATA-UDIQ4XS-POST")
 native=model/"models/unsloth-UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf"
 pack=model/"strata-data/packs/unsloth-ud-iq4_xs"
 app=pathlib.Path("/home/cristian/.cache/llamacode/build_linux/LlamaCode")
 strata=pathlib.Path("/home/cristian/.cache/strata-udiq4xs-screen-20261018/engine/strata")
 serverpy=pathlib.Path("/home/cristian/.cache/strata-udiq4xs-screen-20261018/.venv/bin/python")
 files=[native,pack,app,strata,serverpy]
 if not all(x.exists() for x in files):raise SystemExit("one or more pinned local model/runtime/app files missing")
 model_meta=[]
 for p in sorted(model.rglob("*.gguf")):
  st=p.stat();model_meta.append({"path":str(p),"size_bytes":st.st_size,"mtime_ns":st.st_mtime_ns})
 launches=json.loads((ATTEMPT/"work/isolated-runtime/profiles/launches.json").read_text())
 selected=next((x for x in launches if x.get("id")=="q14-udiq4xs-he0"),None)
 if selected is None:raise SystemExit("selected launch profile missing")
 backend_id=(selected.get("platformBackendIds") or {}).get("linux") or selected.get("backendProfileId")
 backends=json.loads((ATTEMPT/"work/isolated-runtime/profiles/backends.json").read_text())
 backend=next((x for x in backends if x.get("id")==backend_id),None)
 if backend is None or backend.get("cloudBaseUrl")!="http://127.0.0.1:8354":raise SystemExit(f"backend/server mismatch: {backend}")
 ss=subprocess.run(["ss","-ltnp"],capture_output=True,text=True,timeout=10).stdout.splitlines()
 port_rows=[x for x in ss if any(f":{port}" in x for port in (18767,8354))]
 gpu=subprocess.run(["nvidia-smi","--query-compute-apps=gpu_uuid,pid,process_name,used_memory","--format=csv,noheader"],capture_output=True,text=True,timeout=10)
 out={"checked_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"lock_token":LOCK,"instruction_hashes":reg["instruction_hashes"],"runner_sha256":reg["runner_sha256"],"suite_sha256":reg["suite"]["variant_sha256"],"python_alias_sha256":reg["python_alias_sha256"],"backend_endpoint":{"profile_id":"q14-udiq4xs-he0","backend_id":backend_id,"cloudBaseUrl":backend["cloudBaseUrl"]},"memory":info,"inference_processes":servers(),"test_port_listeners":port_rows,"nvidia_compute_apps_observed":gpu.stdout.strip().splitlines(),"model_files":model_meta,"paths_exist":{str(x):x.exists() for x in files},"disk_free_bytes":{"repo_drive":shutil.disk_usage(ROOT).free,"models_hdd":shutil.disk_usage("/media/cristian/HDD extra").free,"linux_root":shutil.disk_usage("/").free},"gui_processes_do_not_block":True}
 out["proceed"]=(not out["inference_processes"] and not port_rows and info["MemAvailableGiB"]>=80 and info["SwapFreeGiB"]>=1 and all(x.exists() for x in files))
 (ATTEMPT/"receipts/preflight.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(out,ensure_ascii=False,indent=2))
 if not out["proceed"]:raise SystemExit("preflight gate failed")
if __name__=="__main__":main()
