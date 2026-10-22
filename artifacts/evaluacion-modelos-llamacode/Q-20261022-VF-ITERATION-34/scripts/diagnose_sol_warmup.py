#!/usr/bin/env python3
"""One diagnostic minimal SOL request; logs captured before owned-container cleanup."""
import datetime as dt, hashlib, importlib.util, json, pathlib, re, subprocess, sys, time, urllib.error, urllib.request
REPO=pathlib.Path(__file__).resolve().parents[4]
ROOT=pathlib.Path(__file__).resolve().parents[1]
TASK="Q-20261022-VF-ITERATION-34"; TOKEN="4bb67f14-f9a8-4c64-971a-58ddfd497ab3"
HELPER=ROOT/"scripts/run_direct_speed.py"
spec=importlib.util.spec_from_file_location("q34_direct_speed",HELPER); m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; assert spec.loader; spec.loader.exec_module(m)
ATTEMPT=ROOT/"attempts/sol-diagnostic-02"; ATTEMPT.mkdir(parents=True,exist_ok=False)
for p in ("runs","logs","receipts"): (ATTEMPT/p).mkdir()
m.speed.ATTEMPT=ATTEMPT; m.speed.RUNS=ATTEMPT/"runs"; m.speed.LOGS=ATTEMPT/"logs"; m.speed.RECEIPTS=ATTEMPT/"receipts"
def utc(): return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
def scrub(s): return re.sub(r"(?i)(hf_[A-Za-z0-9]{16,}|Bearer\s+[^\s\"']+)","[REDACTED]",s)
def logs():
 p=subprocess.run(["docker","logs","--tail","2500",m.CONTAINER],capture_output=True,text=True,timeout=15)
 raw=scrub(p.stdout+p.stderr)[-250000:]
 (ATTEMPT/"logs/sol-engine.log").write_text(raw,encoding="utf-8")
 return {"returncode":p.returncode,"bytes_saved":len(raw),"tail_sha256":hashlib.sha256(raw.encode()).hexdigest()}
def state():
 status=subprocess.run(["docker","inspect","--format","{{.State.Status}} {{.State.ExitCode}} {{.State.OOMKilled}} {{.RestartCount}}","q34-sol-speed"],capture_output=True,text=True,timeout=10)
 return {"docker_state":status.stdout.strip() if status.returncode==0 else "container-absent","docker_inspect_rc":status.returncode}
def main():
 lock=json.loads((REPO/"WORK_QUEUE.lock").read_text())
 if lock.get("token")!=TOKEN or lock.get("task_id")!=TASK: raise SystemExit("Q34 lock lost")
 pre=m.resources("diagnostic02-preflight",allow_sol=False); m.port_free(m.SOL_PORT)
 receipt={"task_id":TASK,"attempt":"sol-diagnostic-02","started_at_utc":utc(),"lock_token":TOKEN,"preflight":pre,"startup_seconds":None,"request":None,"diagnostic_error":None,"cleanup":None}
 try:
  try:
   receipt["startup_seconds"]=m.start_sol()
   body={"model":m.SOL_MODEL_ID,"messages":[{"role":"user","content":"Reply READY."}],"max_tokens":8,"stream":False,"reasoning_effort":"medium"}
   req=urllib.request.Request(m.SOL_BASE+"/chat/completions",data=json.dumps(body).encode(),headers={"Content-Type":"application/json"},method="POST")
   start=time.monotonic()
   try:
    with urllib.request.urlopen(req,timeout=180) as r: data=json.loads(r.read().decode("utf-8","replace")); receipt["request"]={"http_status":r.status,"elapsed_seconds":time.monotonic()-start,"response":data}
   except urllib.error.HTTPError as e:
    receipt["request"]={"http_status":e.code,"elapsed_seconds":time.monotonic()-start,"body":scrub(e.read().decode("utf-8","replace"))[:4000]}
   except Exception as e:
    receipt["request"]={"transport_error":f"{type(e).__name__}: {e}","elapsed_seconds":time.monotonic()-start}
  except Exception as e:
   receipt["diagnostic_error"]=f"{type(e).__name__}: {e}"
  if m.SOL_STARTED:
   receipt["container_state_after_request"]=state()
   receipt["engine_logs_before_cleanup"]=logs()
   receipt["log_key_lines"]=[line for line in (ATTEMPT/"logs/sol-engine.log").read_text(errors="replace").splitlines() if re.search(r"traceback|exception|error|out of memory|nccl|rank.*(fail|exit)|enginecore",line,re.I)][-60:]
 finally:
  if m.SOL_STARTED:
   try:
    if not (ATTEMPT/"logs/sol-engine.log").exists(): receipt["engine_logs_before_cleanup"]=logs()
    m.stop_sol()
   except Exception as e: receipt["cleanup_error"]=f"{type(e).__name__}: {e}"
  receipt["finished_at_utc"]=utc()
  receipt["postflight"]={"inference_processes":m.q.inference_processes(),"docker_containers":m.docker_rows(),"cuda_compute_apps":m.real_compute_apps(),"gpus":m.temps(),"meminfo":m.q.meminfo()}
  (ATTEMPT/"receipts/diagnostic-result.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"attempt":receipt.get("attempt"),"request":receipt.get("request"),"diagnostic_error":receipt.get("diagnostic_error"),"postflight_servers":receipt["postflight"]["inference_processes"],"log_file":str(ATTEMPT/"logs/sol-engine.log")},ensure_ascii=False))
if __name__=="__main__": main()
