#!/usr/bin/env python3
"""Measure isolated TERRA-MTP-off Docker startup on both RTX 3090s."""
from __future__ import annotations
import hashlib,json,os,pathlib,socket,subprocess,time,urllib.request
from datetime import datetime,timezone

ART=pathlib.Path(__file__).resolve().parents[1]
REPO=pathlib.Path(__file__).resolve().parents[4]
TOKEN="2242863e-c78e-4fa9-9649-c1d1541f3919"
COMPOSE=pathlib.Path("/home/cristian/.cache/llamacode/club-3090-src/models/qwen3.8-27b/vllm/compose/dual/autoround-int4/mtp.yml")
OVERRIDE=pathlib.Path("/home/cristian/.cache/llamacode/club-3090-src/models/qwen3.8-27b/vllm/compose/dual/autoround-int4/vram-quarantine.override.yml")
MODEL_DIR=pathlib.Path("/media/cristian/Disco local/Models/llamacpp/club-3090/qwen3.8-27b-autoround-int4")
MANIFEST_SHA="b9b842e49ccc3f8b3a1459ce218d87884604a36725a46cb64b4741641ed7d231"
IMAGE_ID="sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967"
PROJECT="q176-terra-mtp-off-init"
CONTAINER="q176-terra-mtp-off-init"
PORT=18475
GIB=1024**3

def now():return datetime.now(timezone.utc).isoformat(timespec="seconds")
def lock_check():
    if json.loads((REPO/"WORK_QUEUE.lock").read_text()).get("token")!=TOKEN:raise RuntimeError("umbrella lock changed")
def env():
    return {**os.environ,"BIND_HOST":"127.0.0.1","PORT":str(PORT),"ESTATE_CONTAINER":CONTAINER,"MODEL_DIR":str(MODEL_DIR.parent),"SPEC_N":"0","SPEC":"","MAX_MODEL_LEN":"262144","MAX_NUM_SEQS":"1","TP":"2","W4A8":"1","OFFLINE":"1","ENABLE_THINKING":"true","TEMP":"0.6","TOP_P":"0.95","TOP_K":"20","MIN_P":"0.0","PRESENCE_PENALTY":"0.0","CLUB3090_RESTART":"no","NVIDIA_VISIBLE_DEVICES":"all","CUDA_VISIBLE_DEVICES":"0,1"}
def dc(*args,check=True):
    return subprocess.run(["docker","compose","-p",PROJECT,"-f",str(COMPOSE),"-f",str(OVERRIDE),*args],cwd=str(COMPOSE.parent),env=env(),capture_output=True,text=True,timeout=120,check=check)
def gpu():
    p=subprocess.run(["nvidia-smi","--query-gpu=index,memory.used,memory.total","--format=csv,noheader,nounits"],capture_output=True,text=True,check=True,timeout=10)
    return {int(a.strip()):{"used_mib":int(b.strip()),"total_mib":int(c.strip())} for a,b,c in (x.split(",") for x in p.stdout.splitlines())}
def compute_by_gpu():
    p=subprocess.run(["nvidia-smi","pmon","-c","1"],capture_output=True,text=True,check=True,timeout=10)
    ids={0:set(),1:set()}
    for line in p.stdout.splitlines():
        c=line.split()
        if len(c)>=3 and c[0].isdigit() and c[1].isdigit() and int(c[0]) in ids and c[2]=="C":ids[int(c[0])].add(int(c[1]))
    return {k:sorted(v) for k,v in ids.items()},p.stdout
def top_pids():
    p=subprocess.run(["docker","top",CONTAINER,"-eo","pid,comm"],capture_output=True,text=True,timeout=10,check=True)
    out=set()
    for line in p.stdout.splitlines()[1:]:
        c=line.split()
        if c and c[0].isdigit():out.add(int(c[0]))
    return out,p.stdout
def port_free():
    with socket.socket() as s:return s.connect_ex(("127.0.0.1",PORT))!=0
def preflight():
    lock_check()
    if hashlib.sha256((MODEL_DIR/".setup-verified.tsv").read_bytes()).hexdigest()!=MANIFEST_SHA:raise RuntimeError("AutoRound model verification manifest changed")
    img=subprocess.run(["docker","image","inspect","vllm/vllm-openai:v0.27.1","--format","{{.Id}}"],capture_output=True,text=True,timeout=15,check=True).stdout.strip()
    if img!=IMAGE_ID:raise RuntimeError(f"pinned vLLM image changed: {img}")
    cfg=dc("config","--format","json"); d=json.loads(cfg.stdout); service=next(iter(d["services"].values()))
    if service.get("container_name")!=CONTAINER or service.get("image")!="vllm/vllm-openai:v0.27.1":raise RuntimeError("resolved compose identity mismatch")
    port=service.get("ports",[{}])[0]
    if port.get("host_ip")!="127.0.0.1" or str(port.get("published"))!=str(PORT):raise RuntimeError(f"service would not stay on loopback: {port}")
    cmd=service.get("command",[])
    if "2" not in cmd or "262144" not in cmd or "1" not in cmd:raise RuntimeError("TERRA TP/context/seq config mismatch")
    ps=subprocess.run(["docker","ps","--format","{{.Names}} {{.Image}}"],capture_output=True,text=True,timeout=10,check=True).stdout
    if "llama" in ps.lower() or "vllm" in ps.lower() or "ninfer" in ps.lower() or not port_free():raise RuntimeError(f"pre-existing inference service or test port: {ps}")
    existing=subprocess.run(["docker","ps","-a","--filter",f"label=com.docker.compose.project={PROJECT}","--format","{{.ID}} {{.Names}}"],capture_output=True,text=True,timeout=10,check=True).stdout.strip()
    if existing:raise RuntimeError(f"Q176-owned compose project name already exists: {existing}")
    if subprocess.run(["pgrep","-af","llama-server|vllm serve|ninfer-serve|strata|dsx-server|ollama serve"],capture_output=True,text=True).stdout.strip():raise RuntimeError("host inference server process present")
    return {"resolved_compose_sha256":hashlib.sha256(cfg.stdout.encode()).hexdigest(),"image_id":img,"model_manifest_sha256":MANIFEST_SHA,"resolved_service":service,"docker_ps_before":ps,"gpu_before":gpu()}
def down():
    p=dc("down","--remove-orphans",check=False)
    if p.returncode!=0:raise RuntimeError(f"compose down failed: {p.stderr[-2000:]}")
    return p
def run(label):
    lock_check()
    if not port_free():raise RuntimeError("TERRA test port became occupied")
    started=time.monotonic();p=dc("up","-d","--pull","never")
    if p.returncode!=0:raise RuntimeError(f"compose up failed: {p.stderr[-3000:]}")
    STATE["compose_started"]=True
    health=None;deadline=started+900
    while time.monotonic()<deadline:
        lock_check()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health",timeout=3) as r:
                if r.status==200:health={"status":r.status,"body":r.read().decode(errors="replace")[:500]};break
        except Exception:pass
        time.sleep(1)
    if not health:raise RuntimeError("TERRA did not reach HTTP health within 900 s")
    pids,top=top_pids(); cm,pmon=compute_by_gpu(); at=gpu();base=STATE["gpu_before"]
    dual=all(any(pid in pids for pid in cm[i]) and at[i]["used_mib"]-base[i]["used_mib"]>1024 for i in (0,1))
    if not dual:raise RuntimeError(f"dual-GPU allocation/compute gate failed: pids={pids}, compute={cm}, gpu={at}")
    try:
        ss=subprocess.run(["ss","-H","-ltnp","sport = :"+str(PORT)],capture_output=True,text=True,timeout=5,check=False).stdout
        if ss and "127.0.0.1:" not in ss:raise RuntimeError(f"listener is not loopback: {ss}")
    except FileNotFoundError:pass
    logs=dc("logs","--no-color",check=False)
    return {"label":label,"launch_to_health_seconds":round(time.monotonic()-started,3),"health":health,"container_host_pids":sorted(pids),"compute_pids_by_gpu":cm,"pmon":pmon,"gpu_at_ready":at,"docker_top":top,"compose_up_stdout":p.stdout,"compose_logs":logs.stdout[-8000:],"status":"complete"}

STATE={}
def main():
    rec={"experiment_id":"Q176-TERRA-MTP-OFF-DUAL-COLD-HOT-INIT-01","started_utc":now(),"profile":"Qwen3.8-27B AutoRound INT4/W4A8, TP2, MTP off, fp8_e4m3 KV, context262144, max-num-seqs1, sampler .6/.95/20/0/1/0","gpu":"GPU0+GPU1 RTX3090; TP=2","requests_sent":False,"page_cache":"No global purge. First run is fresh container/process, not cold disk; second is immediate clean container relaunch.","runs":[],"status":"running"}
    try:
        STATE.update(preflight());rec["preflight"]=STATE.copy()
        for label in ("cold-process / cache uncontrolled","hot-likely / clean relaunch"):
            item=run(label);rec["runs"].append(item);down();STATE["compose_started"]=False;item["container_removed"]=True;item["port_free_after_cleanup"]=port_free();item["gpu_after_cleanup"]=gpu()
            remaining=subprocess.run(["docker","ps","-a","--filter",f"label=com.docker.compose.project={PROJECT}","--format","{{.ID}}"],capture_output=True,text=True,timeout=10,check=True).stdout.strip()
            if not item["port_free_after_cleanup"] or remaining:raise RuntimeError(f"TERRA cleanup incomplete: listener={item['port_free_after_cleanup']}, project={remaining}")
        rec["status"]="complete"
    except Exception as e:
        rec["status"]="failed";rec["error"]=f"{type(e).__name__}: {e}"
        if STATE.get("compose_started"):
            try:down()
            except Exception as clean:rec["cleanup_error"]=str(clean)
        raise
    finally:
        rec["finished_utc"]=now();(ART/"receipts/terra-mtp-off-cold-hot-init.json").write_text(json.dumps(rec,ensure_ascii=False,indent=2)+"\n")
if __name__=="__main__":main()
