#!/usr/bin/env python3
"""Immediate Q101 host and pinned-asset preflight; read-only except its JSON receipt."""
from __future__ import annotations
import json,os,re,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path("/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode")
TASK=ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-101"
Q85=ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-85/receipts"
TOKEN="f5f2021d-5cbf-4ae2-a0c9-878f53871914"
MODEL=Path("/media/cristian/HDD extra/Modelos-eval/Q85-HyperQwen/models/Qwen3.8-27B-W4A16-AutoRound")
DRAFTER=Path("/media/cristian/HDD extra/Modelos-eval/Q85-HyperQwen/models/Qwen3.8-27B-DFlash2-W4A16")
COMPOSE=Path("/media/cristian/HDD extra/Modelos-eval/Q85-HyperQwen/HyperQwen")
IMAGE="ghcr.io/syv-ai/hyperqwen@sha256:0acd4b9625473e51c9bab56406c30814bc0d0d7e0a38deb408c62664b5a77669"
def run(cmd,**kw): return subprocess.run(cmd,check=True,capture_output=True,text=True,**kw).stdout
def psi(path):
 out={}
 for line in Path(path).read_text().splitlines():
  p=line.split()
  if p and p[0] in {"some","full"}:
   d=dict(x.split("=",1) for x in p[1:] if "=" in x)
   if "avg10" in d: out[p[0]]=float(d["avg10"])
 return out
def mem():
 for line in Path("/proc/meminfo").read_text().splitlines():
  if line.startswith("MemAvailable:"): return int(line.split()[1])*1024
 raise RuntimeError("MemAvailable unavailable")
def oom():
 for line in Path("/proc/vmstat").read_text().splitlines():
  if line.startswith("oom_kill "): return int(line.split()[1])
 return 0
def ancestors():
 seen=set(); pid=os.getpid()
 while pid>1 and pid not in seen:
  seen.add(pid)
  try:
   s=Path(f"/proc/{pid}/stat").read_text(); tail=s[s.rfind(")")+2:].split(); pid=int(tail[1])
  except Exception: break
 return seen
def main():
 lock=json.loads((ROOT/"WORK_QUEUE.lock").read_text())
 if lock.get("task_id")!="Q-20261024-VF-ITERATION-101" or lock.get("token")!=TOKEN: raise SystemExit("Q101 lock mismatch")
 for path,floor in [("/",8*1024**3),("/var/lib/containerd",18*1024**3),("/media/cristian/HDD extra",20*1024**3)]:
  avail=int(run(["df","-B1","--output=avail",path]).splitlines()[-1]);
  if avail<floor: raise SystemExit(f"storage floor failed: {path} has {avail} bytes")
 names=run(["docker","ps","--format","{{.Names}} {{.Image}}"])
 listeners=run(["ss","-ltnp"])
 ports={str(p):not bool(re.search(r":"+str(p)+r"\b",listeners)) for p in (18142,8363,8364,18789)}
 if not all(ports.values()): raise SystemExit(f"candidate/protected port occupied; leaving untouched: {ports}")
 pattern=re.compile(r"(llama-server|vllm.*(serve|api|openai)|strata.*(serve|server)|hyperqwen.*(single|server)|peritosoft.*(serve|server))",re.I)
 anc=ancestors(); matches=[]
 for p in Path("/proc").iterdir():
  if not p.name.isdigit() or int(p.name) in anc: continue
  try: cmd=(p/"cmdline").read_bytes().replace(b"\0",b" ").decode(errors="ignore")
  except OSError: continue
  if pattern.search(cmd): matches.append({"pid":int(p.name),"command":cmd[:240]})
 if any(pattern.search(x) for x in names.splitlines()) or matches: raise SystemExit(f"external inference process active; left untouched: docker={names.strip()} processes={matches}")
 if not (COMPOSE/".env").is_file() or (COMPOSE/".env").stat().st_mode & 0o777 != 0o600: raise SystemExit("candidate API env file missing or permissions differ from 0600")
 for p in (MODEL,DRAFTER):
  if not p.is_dir(): raise SystemExit(f"pinned model directory missing: {p}")
 env=os.environ.copy(); env.update({"GPU_UTIL":"0.91","KV_MEM":"3000000000","GPU_COUNT":"2","EXTRA_ARGS":"--tensor-parallel-size 2"})
 config=json.loads(run(["docker","compose","--profile","single","-f","docker-compose.yml","-f","compose.q85.yaml","config","--format","json"],cwd=COMPOSE,env=env))
 svc=config["services"]["single"]; e=svc["environment"]
 expected={"GPU_UTIL":"0.91","KV_MEM":"3000000000","GPU_COUNT":"2","EXTRA_ARGS":"--tensor-parallel-size 2","MAX_LEN":"65536","SPEC":"dflash2"}
 actual={k:str(e.get(k)) for k in expected}
 if actual!=expected or svc.get("image")!=IMAGE: raise SystemExit(f"compose/image mismatch: {actual}; image={svc.get('image')}")
 inspect=json.loads(run(["docker","image","inspect",IMAGE]))[0]
 if not inspect.get("Id"): raise SystemExit("pinned image is not present locally; refusing any pull")
 gpu_lines=run(["nvidia-smi","--query-gpu=index,name,memory.free,memory.used,temperature.gpu","--format=csv,noheader,nounits"]).splitlines()
 gpus=[]
 for line in gpu_lines:
  ix,name,free,used,temp=[x.strip() for x in line.split(",",4)]
  gpus.append({"index":int(ix),"name":name,"freeMiB":int(free),"usedMiB":int(used),"temperatureC":int(temp)})
 if len(gpus)!=2 or any("RTX 3090" not in g["name"] or g["freeMiB"]<22000 for g in gpus): raise SystemExit(f"dual 3090/free VRAM gate failed: {gpus}")
 apps=run(["nvidia-smi","--query-compute-apps=pid,process_name,gpu_uuid,used_memory","--format=csv,noheader"])
 available=mem(); oom_base=oom()
 if available<32*1024**3: raise SystemExit("MemAvailable below calibrated 32 GiB hard floor")
 tmp=Path("/media/cristian/HDD extra/Modelos-eval/Q85-HyperQwen/tmp")
 if not tmp.is_dir() or not os.access(tmp,os.W_OK): raise SystemExit("candidate temporary workspace is unavailable")
 # The pinned prepare workflow rewrites three checkpoint files in place. Check
 # the already-verified raw sources and prepared outputs via the Q101 receipts;
 # do not compare transformed shards with their pre-prepare hashes or reread GBs.
 verification_path=TASK/"receipts/q101-attempt10-source-fingerprint-verification.json"
 verification=json.loads(verification_path.read_text())
 if verification.get("status")!="pass" or verification.get("lockOwned") is not True or verification.get("gpuInferenceStarted") is not False:
  raise SystemExit("Q101 prepared-model verification receipt is not a safe pass")
 structural=verification.get("preparedCheckpointStructuralVerification",{})
 if structural.get("status")!="pass" or structural.get("gpuDevicesPassed") is not False or structural.get("network")!="none" or structural.get("rootFilesystem")!="read-only":
  raise SystemExit("Q101 read-only prepared checkpoint verification did not pass")
 captured=datetime.fromisoformat(verification["capturedAtUtc"].replace("Z","+00:00"))
 if (datetime.now(timezone.utc)-captured).total_seconds()>900: raise SystemExit("prepared-model verification is older than 15 minutes")
 post=json.loads((Q85/"q85-dual-gpu-runtime-preflight.json").read_text())
 q85_verified=datetime.fromisoformat(post["observedAtUtc"].replace("Z","+00:00")).timestamp()
 source_checks=[]
 for item in verification["rawSourceChecks"]:
  path=Path(item["sourcePath"]); st=path.stat()
  if st.st_size!=item["sourceSizeBytes"] or st.st_mtime>q85_verified: raise SystemExit(f"pinned original changed since Q85 verification: {path.name}")
  source_checks.append({"path":str(path),"sizeBytes":st.st_size,"unchangedByMtimeSinceQ85Verification":True})
 for item in structural["modelShards"]:
  path=MODEL/Path(item["path"]).name; st=path.stat()
  if st.st_size!=item["sizeBytes"] or st.st_mtime>q85_verified: raise SystemExit(f"prepared shard changed since Q85 verification: {path.name}")
 source_checks.append({"preparedCheckpointVerificationReceipt":str(verification_path),"preparedState":"PASS; index, safetensors headers, offsets and pinned DFlash2 validated read-only without network/GPU"})
 receipt={"taskId":"Q-20261024-VF-ITERATION-101","capturedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),"status":"pass","lockOwned":True,"storageAvailableBytes":{p:int(run(["df","-B1","--output=avail",p]).splitlines()[-1]) for p in ("/","/var/lib/containerd","/media/cristian/HDD extra")},"runningDockerContainers":names.strip().splitlines(),"matchedInferenceProcesses":matches,"portsFree":ports,"gpus":gpus,"gpuComputeApplications":apps.strip().splitlines(),"hostMemAvailableBytes":available,"memoryPsiAvg10Pct":psi("/proc/pressure/memory"),"ioPsiAvg10Pct":psi("/proc/pressure/io"),"cpuPsiAvg10Pct":psi("/proc/pressure/cpu"),"globalOomKillBaseline":oom_base,"cgroupMemoryLimits":"not capped by experiment; transient systemd properties will be verified after launch","composeEnvironment":actual,"image":IMAGE,"imagePresentLocally":True,"apiEnvMode":"0o600","modelVerification":{"receipt":str(verification_path),"status":"pass","sourceAndPreparedFilesUnchanged":True,"checks":source_checks},"serverStarted":False,"gpuInferenceStarted":False,"guiLeftOpen":True}
 path=TASK/"receipts/q101-attempt10-host-preflight.json"; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(receipt,indent=2)+"\n"); print(json.dumps(receipt,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
