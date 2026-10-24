#!/usr/bin/env python3
"""Q101 host memory-pressure guard: moderate PSI warns; calibrated hard gates stop this task only."""
from __future__ import annotations
import argparse, json, os, signal, time
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path("/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode")
TOKEN="f5f2021d-5cbf-4ae2-a0c9-878f53871914"
def pct(path:Path)->dict[str,float]:
    out={}
    for line in path.read_text().splitlines():
        parts=line.split()
        if parts and parts[0] in {"some","full"}:
            kv=dict(x.split("=",1) for x in parts[1:] if "=" in x)
            if "avg10" in kv: out[parts[0]]=float(kv["avg10"])
    return out
def evaluate_sample(sample:dict,previous_oom:int,severe_streak:int)->tuple[str|None,int,bool]:
    psi=sample["memoryPsiAvg10Pct"]
    severe=psi.get("full",0)>=60.0 or psi.get("some",0)>=80.0
    streak=severe_streak+1 if severe else 0
    warning=psi.get("full",0)>=20.0 or psi.get("some",0)>=70.0
    reason=None
    if sample["memAvailableGiB"]<32.0: reason="MemAvailable <32 GiB"
    elif sample["oomKill"]>previous_oom: reason="global oom_kill counter increased"
    elif streak>=15: reason="global PSI severe threshold persisted for 15 consecutive 1-second samples"
    return reason,streak,warning
def read_mem()->float:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"): return int(line.split()[1])*1024/(1024**3)
    raise RuntimeError("MemAvailable missing")
def read_oom()->int:
    for line in Path("/proc/vmstat").read_text().splitlines():
        if line.startswith("oom_kill "): return int(line.split()[1])
    return 0
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--main-pid",type=int,required=True); ap.add_argument("--samples",type=Path,required=True); ap.add_argument("--stop-reason",type=Path,required=True); ap.add_argument("--interval",type=float,default=1.0); args=ap.parse_args()
    lock=json.loads((ROOT/"WORK_QUEUE.lock").read_text())
    if lock.get("task_id")!="Q-20261024-VF-ITERATION-101" or lock.get("token")!=TOKEN: raise SystemExit("Q101 lock mismatch before guard start")
    baseline=read_oom(); streak=0; min_available=read_mem(); count=0; args.samples.parent.mkdir(parents=True,exist_ok=True)
    with args.samples.open("a",encoding="utf-8") as f:
        while True:
            try: os.kill(args.main_pid,0)
            except ProcessLookupError: break
            lock=json.loads((ROOT/"WORK_QUEUE.lock").read_text())
            if lock.get("task_id")!="Q-20261024-VF-ITERATION-101" or lock.get("token")!=TOKEN:
                args.stop_reason.write_text("Q101 no longer owns WORK_QUEUE.lock\n"); os.kill(args.main_pid,signal.SIGTERM); break
            sample={"atUtc":datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),"memAvailableGiB":round(read_mem(),3),"memoryPsiAvg10Pct":pct(Path("/proc/pressure/memory")),"ioPsiAvg10Pct":pct(Path("/proc/pressure/io")),"cpuPsiAvg10Pct":pct(Path("/proc/pressure/cpu")),"oomKill":read_oom()}
            reason,streak,warning=evaluate_sample(sample,baseline,streak); sample["warningOnlyModeratePressure"]=warning; sample["severeStreakSamples"]=streak
            f.write(json.dumps(sample)+"\n"); f.flush(); count+=1; min_available=min(min_available,sample["memAvailableGiB"])
            if reason:
                args.stop_reason.write_text(reason+"\n"); os.kill(args.main_pid,signal.SIGTERM); break
            time.sleep(args.interval)
    print(json.dumps({"samples":count,"minMemAvailableGiB":round(min_available,3),"baselineOomKill":baseline},sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
