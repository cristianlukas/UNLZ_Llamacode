#!/usr/bin/env python3
"""Measure Qwen Flash-Next Strata 1M clean-process readiness on both RTX 3090s."""
from __future__ import annotations
import hashlib, json, os, pathlib, signal, socket, subprocess, time, urllib.request
from datetime import datetime, timezone

ART=pathlib.Path(__file__).resolve().parents[1]
REPO=pathlib.Path(__file__).resolve().parents[4]
PLAN=ART/"receipts/prereg-qwen-flashnext-strata-1m-init.json"
OUT=ART/"receipts/qwen-flashnext-strata-1m-init.json"
LOG=ART/"logs"
LOCK="2242863e-c78e-4fa9-9649-c1d1541f3919"
HOST,PORT="127.0.0.1",8350
ROOT=pathlib.Path("/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source")
PYTHON=ROOT/".venv/bin/python"
SERVER=ROOT/"serve/server.py"
ENGINE=ROOT/"engine/strata"
CFG=pathlib.Path("/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode/artifacts/evaluacion-modelos-llamacode/Q-20261014-ISTA-CONTEXT-SWEEP/receipts/configs/context-1048576.json")
PACK=pathlib.Path("/media/cristian/Disco local/Models/FlashNext-IQ2XS-ISTA-Strata-eval-20261012/strata-data/packs/iq2_xs")
SHARDS=[pathlib.Path("/media/cristian/Disco local/Models/FlashNext-IQ2XS-ISTA-Strata-eval-20261012/IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf"),pathlib.Path("/media/cristian/Disco local/Models/FlashNext-IQ2XS-ISTA-Strata-eval-20261012/IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00002-of-00002.gguf")]
EXPECTED_SIZES=[39225954592,28800138432]
EXPECTED_MTIMES=[1791824778113101000,1791823874746058600]
RUNTIME_SHA="770ecf303a4c6271654339c639392ecb455de3a999bf5d2e8dbc73c879103602"
CFG_SHA="cf5e910f72de441eec9b8bead6af4a24170ba919f62638e0c80b925257497b7e"
MODEL_SHAS=["92cee27ae5bbadcd732416a0f7a7f0acc092399dbbe8f5a5efa707c2ec0a49d7","316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113"]
GIB=1024**3

def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(4*1024*1024),b""): h.update(b)
 return h.hexdigest()
def lock_check():
 if json.loads((REPO/"WORK_QUEUE.lock").read_text()).get("token")!=LOCK: raise RuntimeError("umbrella lock changed")
def mem_kib(): return next(int(x.split()[1]) for x in pathlib.Path("/proc/meminfo").read_text().splitlines() if x.startswith("MemAvailable:"))
def gpu():
 p=subprocess.run(["nvidia-smi","--query-gpu=index,memory.used,memory.total,utilization.gpu","--format=csv,noheader,nounits"],capture_output=True,text=True,timeout=10,check=True)
 return {int(a.strip()):{"used_mib":int(b.strip()),"total_mib":int(c.strip()),"util_percent":int(d.strip())} for a,b,c,d in (line.split(",") for line in p.stdout.splitlines())}
def port_free():
 with socket.socket() as s:return s.connect_ex((HOST,PORT))!=0
def active_servers():
 found=[]
 for p in pathlib.Path("/proc").iterdir():
  if not p.name.isdigit() or int(p.name)==os.getpid():continue
  try: comm=(p/"comm").read_text().strip().lower(); cmd=(p/"cmdline").read_bytes().replace(b"\0",b" ").decode(errors="replace")
  except OSError:continue
  if comm in {"llama-server","ninfer-serve","dsx-server","ollama","vllm","aphrodite-engine"} or ("serve/server.py" in cmd and "--engine strata" in cmd):found.append({"pid":int(p.name),"comm":comm,"cmd":cmd[:350]})
 return found
def tree(root):
 parents={}
 for p in pathlib.Path("/proc").iterdir():
  if not p.name.isdigit():continue
  try:
   t=(p/"stat").read_text();parents[int(p.name)]=int(t[t.rfind(")")+2:].split()[1])
  except (OSError,ValueError,IndexError):pass
 found={root};changed=True
 while changed:
  changed=False
  for pid,ppid in parents.items():
   if ppid in found and pid not in found:found.add(pid);changed=True
 return found
def compute_map(owned):
 p=subprocess.run(["nvidia-smi","pmon","-c","1"],capture_output=True,text=True,timeout=10,check=True);by={0:set(),1:set()}
 for line in p.stdout.splitlines():
  c=line.split()
  if len(c)>=3 and c[0].isdigit() and c[1].isdigit() and int(c[1]) in owned and c[2]=="C" and int(c[0]) in by:by[int(c[0])].add(int(c[1]))
 return {k:sorted(v) for k,v in by.items()},p.stdout
def stop(p):
 if p.poll() is None:
  try:os.killpg(p.pid,signal.SIGINT)
  except ProcessLookupError:pass
  try:p.wait(timeout=60)
  except subprocess.TimeoutExpired:
   try:os.killpg(p.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   try:p.wait(timeout=15)
   except subprocess.TimeoutExpired:
    try:os.killpg(p.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    p.wait(timeout=5)
def preflight():
 lock_check()
 cfg=json.loads(CFG.read_text())
 if sha(CFG)!=CFG_SHA or sha(ENGINE)!=RUNTIME_SHA:raise RuntimeError("pinned context config/runtime SHA mismatch")
 if cfg.get("gpu")!=[0,1] or "1048576" not in cfg["args"] or "yarn" not in cfg["args"] or "4" not in cfg["args"]:raise RuntimeError("config is not the pinned dual-GPU YaRN×4 1M profile")
 stats=[]
 for i,p in enumerate(SHARDS):
  s=p.stat(); row={"path":str(p),"size_bytes":s.st_size,"mtime_ns":s.st_mtime_ns}
  if row["size_bytes"]!=EXPECTED_SIZES[i] or row["mtime_ns"]!=EXPECTED_MTIMES[i]:raise RuntimeError(f"model shard identity changed: {row}")
  stats.append(row)
 if not PYTHON.is_file() or not SERVER.is_file() or not PACK.is_dir():raise RuntimeError("pinned Strata runtime inputs missing")
 if active_servers() or not port_free():raise RuntimeError(f"inference/port preflight failed: {active_servers()}")
 base=gpu()
 if mem_kib()<32*1024*1024:raise RuntimeError("MemAvailable under 32 GiB before start")
 return cfg,stats,base
def run(label,base,logpath):
 lock_check()
 if active_servers() or not port_free():raise RuntimeError(f"server/port gate failed: {active_servers()}")
 argv=[str(PYTHON),str(SERVER),"--engine","strata","--config",str(CFG),"--host",HOST,"--port",str(PORT)]
 env={**os.environ,"STRATA_ROOT":str(ROOT)}
 cfg=json.loads(CFG.read_text())
 for k,v in cfg.get("env",{}).items():env[str(k)]=str(v)
 low_since=None;start=time.monotonic();p=None
 with logpath.open("wb") as log:
  p=subprocess.Popen(argv,cwd=str(ROOT),env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  try:
   health=None;deadline=start+900
   while time.monotonic()<deadline and p.poll() is None:
    lock_check()
    if mem_kib()<20*1024*1024:
     low_since=low_since or time.monotonic()
     if time.monotonic()-low_since>=30:raise RuntimeError("MemAvailable below 20 GiB for 30 seconds")
    else:low_since=None
    try:
     with urllib.request.urlopen(f"http://{HOST}:{PORT}/health",timeout=3) as r:
      body=json.loads(r.read())
      if r.status==200 and body.get("status")=="ok":health=body;break
    except Exception:pass
    time.sleep(1)
   if not health:raise RuntimeError(f"healthy readiness timeout; exit={p.poll()}")
   if health.get("max_context")!=1048576 or health.get("loaded") is not True:raise RuntimeError(f"health profile mismatch: {health}")
   owned=tree(p.pid);at=gpu();cmap,pmon=compute_map(owned);dual=all(cmap[i] for i in (0,1)) and all(at[i]["used_mib"]-base[i]["used_mib"]>1024 for i in (0,1))
   if not dual:raise RuntimeError(f"dual compute/allocation gate failed: cmap={cmap}, gpu={at}, pmon={pmon}")
   return {"label":label,"pid":p.pid,"launch_to_health_seconds":round(time.monotonic()-start,3),"health":health,"owned_processes_at_ready":sorted(owned),"compute_pids_by_gpu":cmap,"pmon_at_ready":pmon,"gpu_baseline":base,"gpu_at_ready":at,"mem_available_at_ready_kib":mem_kib(),"log":str(logpath),"status":"complete"},p
  except Exception:stop(p);raise
def main():
 cfg,stats,base=preflight()
 rec={"experiment_id":"Q176-QWEN-FLASHNEXT-STRATA-YARN4-1M-COLD-HOT-INIT-01","started_utc":now(),"config_sha256":CFG_SHA,"runtime_sha256":RUNTIME_SHA,"model_shard_sha256":MODEL_SHAS,"model_shard_stats":stats,"context_limit":1048576,"rope_scaling":"YaRN factor4 original context262144","gpu_topology":"Strata config GPU0+GPU1; require engine compute+VRAM on both","initial_gpu":base,"initial_mem_available_kib":mem_kib(),"inference_request_sent":False,"runs":[]}
 try:
  for label,filename in (("cold-process / page-cache uncontrolled","qwen-flashnext-strata-1m-cold-init.log"),("hot-likely / fresh process after first load","qwen-flashnext-strata-1m-hot-init.log")):
   item,p=run(label,gpu(),LOG/filename);rec["runs"].append(item);stop(p);item["server_exit_code"]=p.returncode;item["port_free_after_cleanup"]=port_free();item["gpu_after_cleanup"]=gpu();item["mem_available_after_cleanup_kib"]=mem_kib()
   if not item["port_free_after_cleanup"] or active_servers():raise RuntimeError("owned Strata service remained after cleanup")
   if label.startswith("cold"):time.sleep(2)
  rec["status"]="complete"
 except Exception as e:rec["status"]="failed";rec["error"]=f"{type(e).__name__}: {e}";raise
 finally:rec["finished_utc"]=now();OUT.write_text(json.dumps(rec,ensure_ascii=False,indent=2)+"\n")
if __name__=="__main__":main()
