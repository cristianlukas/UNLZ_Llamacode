#!/usr/bin/env python3
"""Measure DSX T16 fresh-process readiness on two GPUs, with immediate restart."""
from __future__ import annotations
import hashlib, json, os, pathlib, signal, socket, subprocess, time, urllib.request
from datetime import datetime, timezone

ART = pathlib.Path(__file__).resolve().parents[1]
REPO = pathlib.Path(__file__).resolve().parents[4]
PLAN, OUT = ART / "receipts/prereg-dsx-t16-cold-hot-init.json", ART / "receipts/dsx-t16-cold-hot-init.json"
LOG = ART / "logs"
LOCK_TOKEN = "2242863e-c78e-4fa9-9649-c1d1541f3919"
HOST, PORT = "127.0.0.1", 18177
MODEL = pathlib.Path("/media/cristian/Disco local/Modelos-eval/Q-20261027-VF-ITERATION-172/DeepSeek-dsx-T16/models/DeepSeek-V4.1-Flash-1017-dsx-t16.gguf")
RANK = pathlib.Path("/media/cristian/Disco local/Modelos-eval/Q-20261027-VF-ITERATION-172/DeepSeek-dsx-T16/models/expert-rank.json")
BIN = pathlib.Path("/media/cristian/Disco local/Modelos-eval/Q-20261027-VF-ITERATION-172/DeepSeek-dsx-T16/build/release/dsx-server")
MODEL_SHA = "31b3852636237c63b3e42b2403f172e372d36c4ad486e65f5c3920307bcfb3fa"
BIN_SHA = "bec3b3e59803108b81834227bfb4ba5f722473af34e1ab960510e723fe07ad27"
MODEL_SIZE = 251592261632
MODEL_MTIME_NS = 1793190727914386700
ARGV = ["/usr/bin/env", "DSX_GPUS=0,1", "DSX_DEFER=off", "DSX_ENGRAM_FP8=off", str(BIN), "--model", str(MODEL), "--rank", str(RANK), "--ctx", "131072", "--arena-gb", "70", "--no-vision", "--host", HOST, "--port", str(PORT), "--model-name", "q176-dsx-t16", "--max-tokens", "128", "--temperature", "0.6", "--top-p", "0.95"]

def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""): h.update(b)
    return h.hexdigest()
def lock_check():
    if json.loads((REPO/"WORK_QUEUE.lock").read_text()).get("token") != LOCK_TOKEN: raise RuntimeError("umbrella lock changed")
def servers():
    out=[]
    for p in pathlib.Path("/proc").iterdir():
        if not p.name.isdigit() or int(p.name)==os.getpid(): continue
        try: comm=(p/"comm").read_text().strip().lower(); cmd=(p/"cmdline").read_bytes().replace(b"\0",b" ").decode(errors="replace")
        except OSError: continue
        if comm in {"llama-server","ninfer-serve","dsx-server","ollama","vllm","aphrodite-engine"}: out.append({"pid":int(p.name),"comm":comm,"cmdline":cmd[:300]})
    return out
def gpu():
    p=subprocess.run(["nvidia-smi","--query-gpu=index,memory.used,memory.total,utilization.gpu","--format=csv,noheader,nounits"],capture_output=True,text=True,timeout=10,check=True)
    return {int(a.strip()):{"used_mib":int(b.strip()),"total_mib":int(c.strip()),"util_percent":int(d.strip())} for a,b,c,d in (line.split(",") for line in p.stdout.splitlines())}
def compute_gpus(pid):
    p=subprocess.run(["nvidia-smi","pmon","-c","1"],capture_output=True,text=True,timeout=10,check=True)
    out=set()
    for line in p.stdout.splitlines():
        cols=line.split()
        if len(cols)>=3 and cols[0].isdigit() and cols[1].isdigit() and int(cols[1])==pid and cols[2]=="C": out.add(int(cols[0]))
    return sorted(out),p.stdout
def mem_kib(): return next(int(x.split()[1]) for x in pathlib.Path("/proc/meminfo").read_text().splitlines() if x.startswith("MemAvailable:"))
def port_free():
    with socket.socket() as s: return s.connect_ex((HOST,PORT)) != 0
def stop(p):
    if p.poll() is None:
        p.send_signal(signal.SIGINT)
        try:p.wait(timeout=45)
        except subprocess.TimeoutExpired:
            p.terminate()
            try:p.wait(timeout=15)
            except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
def wait_health(p):
    start=time.monotonic(); deadline=start+600; low_since=None
    while time.monotonic()<deadline and p.poll() is None:
        lock_check()
        if mem_kib()<32*1024*1024:
            low_since=low_since or time.monotonic()
            if time.monotonic()-low_since>=30: raise RuntimeError("MemAvailable below 32 GiB for 30s")
        else: low_since=None
        try:
            with urllib.request.urlopen(f"http://{HOST}:{PORT}/health",timeout=3) as r:
                body=json.loads(r.read())
                if r.status==200 and body.get("status") in (None,"ok","healthy"): return body,round(time.monotonic()-start,3)
        except Exception: pass
        time.sleep(1)
    raise RuntimeError(f"health timeout; exit={p.poll()}")
def run(label, base, logpath):
    lock_check()
    if servers() or not port_free(): raise RuntimeError(f"server/port gate: {servers()}")
    with logpath.open("w",encoding="utf-8") as log:
        p=subprocess.Popen(ARGV,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env={**os.environ,"CUDA_VISIBLE_DEVICES":"0,1"})
        try:
            body,elapsed=wait_health(p); at=gpu(); compute, pmon=compute_gpus(p.pid)
            dual=all(i in compute for i in (0,1))
            if not dual: raise RuntimeError(f"same-PID dual compute gate failed: {compute}; {pmon}")
            return {"label":label,"pid":p.pid,"launch_to_health_seconds":elapsed,"health_body":body,"gpu_baseline":base,"gpu_at_readiness":at,"compute_gpu_indices_at_readiness":compute,"pmon_at_readiness":pmon,"dual_gpu_gate":dual,"mem_available_at_ready_kib":mem_kib(),"log":str(logpath),"status":"complete"},p
        except Exception: stop(p); raise
def main():
    lock_check(); prereg=json.loads(PLAN.read_text())
    if prereg.get("status")!="preregistered": raise RuntimeError("no active preregistration")
    model_stat=MODEL.stat()
    if model_stat.st_size!=MODEL_SIZE or model_stat.st_mtime_ns!=MODEL_MTIME_NS: raise RuntimeError("model differs from attempt-01 SHA-verified file identity")
    if sha(BIN)!=BIN_SHA: raise RuntimeError("pinned runtime SHA mismatch")
    if not RANK.is_file() or servers() or not port_free(): raise RuntimeError(f"preflight failed; servers={servers()}")
    base=gpu()
    if mem_kib()<32*1024*1024: raise RuntimeError("MemAvailable below 32 GiB before start")
    rec={"experiment_id":"Q176-DSX-T16-DUAL3090-COLD-HOT-INIT-01","started_utc":now(),"model_sha256":MODEL_SHA,"runtime_sha256":BIN_SHA,"argv":ARGV,"gpu_topology":"DSX_GPU0+GPU1","initial_mem_available_kib":mem_kib(),"initial_gpu":base,"inference_request_sent":False,"runs":[]}
    try:
        for label, logfile in (("cold-process / cache-state-uncontrolled","dsx-t16-cold-init.log"),("hot-page-cache / fresh-process","dsx-t16-hot-init.log")):
            item,p=run(label,gpu(),LOG/logfile);rec["runs"].append(item);stop(p)
            item.update({"server_exit_code":p.returncode,"port_free_after_cleanup":port_free(),"gpu_after_cleanup":gpu(),"mem_available_after_cleanup_kib":mem_kib()})
            if not item["port_free_after_cleanup"]: raise RuntimeError("port remained occupied after cleanup")
            if label.startswith("cold"): time.sleep(2)
        rec["status"]="complete"
    except Exception as e: rec["status"]="failed";rec["error"]=f"{type(e).__name__}: {e}";raise
    finally: rec["finished_utc"]=now();OUT.write_text(json.dumps(rec,ensure_ascii=False,indent=2)+"\n")
if __name__=="__main__": main()
