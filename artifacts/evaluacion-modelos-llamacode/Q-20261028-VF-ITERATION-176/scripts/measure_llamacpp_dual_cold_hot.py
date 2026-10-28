#!/usr/bin/env python3
"""Measure process-cold and cache-warm readiness for pinned dual-GPU GGUF profiles."""
from __future__ import annotations
import hashlib, json, os, pathlib, signal, socket, subprocess, time, urllib.request
from datetime import datetime, timezone

ART = pathlib.Path(__file__).resolve().parents[1]
REPO = pathlib.Path(__file__).resolve().parents[4]
LOCK = "2242863e-c78e-4fa9-9649-c1d1541f3919"
GIB = 1024**3
PROFILES = {
    "prism": {
        "name": "Ternary Bonsai 2 27B PQ2_0 / PrismML",
        "model": pathlib.Path("/media/cristian/Disco local/Modelos-eval/Q-20261027-VF-ITERATION-172/Bonsai2-Prism-PQ2_0/models/Ternary-Bonsai-2-27B-PQ2_0.gguf"),
        "model_sha": "3907dc1658db1f78a9826bf8d5bcb8dc65db0d466388937af57f2294fae62ec1",
        "server": pathlib.Path("/media/cristian/Disco local/Modelos-eval/Q-20261027-VF-ITERATION-172/Bonsai2-Prism-PQ2_0/runtime/llama-prism-b10826-c9c34bc/llama-server"),
        "server_sha": "3ad6c90f0f25fec776be6d70b0bfe3ada0a8bf6a765b53f7a97cf985b0ea560a",
        "port": 18178, "ctx": 8448, "extra": ["--flash-attn", "on", "--perf", "--seed", "42"],
        "log_prefix": "prism",
    },
    "gemma": {
        "name": "Gemma 4 12B IT QAT Q4_0 / opti-llama.cpp",
        "model": pathlib.Path("/media/cristian/Disco local/Models/llamacpp/gemma-4-12b-it-qat-q4_0.gguf"),
        "model_sha": "93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b",
        "server": pathlib.Path("/media/cristian/Disco local/LlamaCode-cache/opti-llama.cpp/build/bin/llama-server"),
        "server_sha": "b760910e1fa0af38d0a9a4589fc011520d408f208b1cc872f13e44ee068d4d1d",
        "template": pathlib.Path("/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode/artifacts/evaluacion-modelos-llamacode/Q-20261028-VF-ITERATION-173/runtime/gemma4-q4/gemma4-tools-fixed.jinja"),
        "template_sha": "ae53464bf3be25802b3a5b37def7fd89667067d7577049b3b2d74c4d8de4c6d4",
        "port": 18179, "ctx": 8448,
        "extra": ["--flash-attn", "on", "--perf", "--seed", "42", "--no-warmup", "--reasoning", "on", "--reasoning-effort", "medium", "--jinja", "--chat-template-file", "/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode/artifacts/evaluacion-modelos-llamacode/Q-20261028-VF-ITERATION-173/runtime/gemma4-q4/gemma4-tools-fixed.jinja"],
        "log_prefix": "gemma",
    },
}

def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""): h.update(b)
    return h.hexdigest()
def lock_check():
    if json.loads((REPO/"WORK_QUEUE.lock").read_text()).get("token") != LOCK: raise RuntimeError("umbrella lock changed")
def gpu():
    p=subprocess.run(["nvidia-smi","--query-gpu=index,memory.used,memory.total","--format=csv,noheader,nounits"],capture_output=True,text=True,check=True,timeout=10)
    return {int(a.strip()):{"used_mib":int(b.strip()),"total_mib":int(c.strip())} for a,b,c in (x.split(",") for x in p.stdout.splitlines())}
def port_free(port):
    with socket.socket() as s: return s.connect_ex(("127.0.0.1",port)) != 0
def servers():
    found=[]
    for p in pathlib.Path("/proc").iterdir():
        if not p.name.isdigit() or int(p.name)==os.getpid(): continue
        try: comm=(p/"comm").read_text().strip().lower(); cmd=(p/"cmdline").read_bytes().replace(b"\0",b" ").decode(errors="replace")
        except OSError: continue
        if comm in {"llama-server","vllm","ninfer-serve","ollama","aphrodite-engine"} or "vllm serve" in cmd.lower(): found.append({"pid":int(p.name),"comm":comm,"cmd":cmd[:220]})
    try:
        d=subprocess.run(["docker","ps","--format","{{.ID}} {{.Names}} {{.Image}}"],capture_output=True,text=True,timeout=5,check=False)
        containers=[x for x in d.stdout.splitlines() if any(t in x.lower() for t in ("llama","vllm","ninfer","ollama","aphrodite"))]
    except Exception: containers=[]
    return {"processes":found,"containers":containers}
def tree(root):
    parents={}
    for p in pathlib.Path("/proc").iterdir():
        if not p.name.isdigit(): continue
        try:
            t=(p/"stat").read_text(); parents[int(p.name)]=int(t[t.rfind(")")+2:].split()[1])
        except Exception: pass
    out={root}; changed=True
    while changed:
        changed=False
        for pid,ppid in parents.items():
            if ppid in out and pid not in out: out.add(pid); changed=True
    return out
def stop(p):
    if p is None or p.poll() is not None:return
    try: os.killpg(p.pid,signal.SIGINT); p.wait(timeout=30)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid,signal.SIGTERM)
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=5)
def pmon(owned):
    p=subprocess.run(["nvidia-smi","pmon","-c","1"],capture_output=True,text=True,check=True,timeout=10); by={0:set(),1:set()}
    for line in p.stdout.splitlines():
        c=line.split()
        if len(c)>=3 and c[0].isdigit() and c[1].isdigit() and int(c[0]) in by and int(c[1]) in owned and c[2]=="C":by[int(c[0])].add(int(c[1]))
    return {i:sorted(v) for i,v in by.items()},p.stdout
def check_profile(p):
    for key in ("model","server"):
        path=p[key]
        if not path.is_file() or sha(path)!=p[key+"_sha"]: raise RuntimeError(f"pinned {key} missing/hash mismatch: {path}")
    if "template" in p and sha(p["template"])!=p["template_sha"]: raise RuntimeError("pinned Gemma template hash mismatch")
def run_one(profile_id,p,label):
    lock_check(); base=gpu()
    if servers()["processes"] or servers()["containers"] or not port_free(p["port"]): raise RuntimeError("existing inference service or occupied test port")
    argv=[str(p["server"]),"--model",str(p["model"]),"--host","127.0.0.1","--port",str(p["port"]),"--device","CUDA0,CUDA1","--split-mode","layer","--tensor-split","1,1","--gpu-layers","all","--ctx-size",str(p["ctx"]),"--parallel","1",*p["extra"]]
    log=ART/"logs"/f"{p['log_prefix']}-{label}-init.log"; log.parent.mkdir(parents=True,exist_ok=True)
    started=time.monotonic(); proc=None
    with log.open("wb") as f:
        proc=subprocess.Popen(argv,cwd=str(p["server"].parent),env={**os.environ,"CUDA_VISIBLE_DEVICES":"0,1"},stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            health=None; deadline=started+600
            while time.monotonic()<deadline and proc.poll() is None:
                lock_check()
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{p['port']}/health",timeout=3) as r:
                        if r.status==200: health={"status":r.status,"body":r.read().decode(errors="replace")[:500]}; break
                except Exception: pass
                time.sleep(.5)
            if health is None: raise RuntimeError(f"readiness failed; exit={proc.poll()}")
            owned=tree(proc.pid); at=gpu(); cp,pm=pmon(owned)
            if not all(cp[i] and at[i]["used_mib"]-base[i]["used_mib"]>1024 for i in (0,1)): raise RuntimeError(f"dual-GPU gate failed: compute={cp}, base={base}, ready={at}; pmon={pm}")
            return {"profile":profile_id,"label":label,"argv":argv,"host_pid":proc.pid,"process_tree":sorted(owned),"launch_to_health_seconds":round(time.monotonic()-started,3),"health":health,"compute_pids_by_gpu":cp,"pmon":pm,"gpu_baseline":base,"gpu_at_ready":at,"log":str(log),"status":"complete"},proc
        except Exception: stop(proc); raise
def main():
    import sys
    ids=sys.argv[1:] or ["prism","gemma"]
    if any(i not in PROFILES for i in ids):raise SystemExit("profiles: prism gemma")
    lock_check()
    rec={"task":"Q176 dual-GPU llama.cpp cold/hot readiness","started_utc":now(),"context_tokens":8448,"requests_sent":False,"cache_policy":"No global page-cache flush; SHA preflight reads model files, so disk-cold is not claimed.","profiles":{},"status":"running"}
    try:
        for profile_id in ids:
            p=PROFILES[profile_id]; check_profile(p); results=[]
            for label in ("cold-process","hot-likely"):
                item,proc=run_one(profile_id,p,label); results.append(item); stop(proc); item["exit_code"]=proc.returncode; item["port_free_after_cleanup"]=port_free(p["port"]); item["gpu_after_cleanup"]=gpu()
                if not item["port_free_after_cleanup"] or servers()["processes"] or servers()["containers"]:raise RuntimeError("cleanup/service gate failed")
            rec["profiles"][profile_id]={"name":p["name"],"model_sha256":p["model_sha"],"server_sha256":p["server_sha"],"runs":results}
        rec["status"]="complete"
    except Exception as e: rec["status"]="failed";rec["error"]=f"{type(e).__name__}: {e}";raise
    finally:
        rec["finished_utc"]=now(); out=ART/"receipts/llamacpp-dual-cold-hot-init.json";out.write_text(json.dumps(rec,ensure_ascii=False,indent=2)+"\n")
if __name__=="__main__":main()
