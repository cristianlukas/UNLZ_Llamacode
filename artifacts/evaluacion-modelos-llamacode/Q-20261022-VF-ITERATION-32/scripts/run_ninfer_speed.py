#!/usr/bin/env python3
"""Serial descriptive speed comparison of preregistered Qwen3.8 profiles."""
from __future__ import annotations
import hashlib, json, pathlib, random, re, statistics, subprocess, sys, threading, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
import run_ninfer_quality as q

NINFER_PORT, LLAMA_PORT = 18132, 18103
NINFER_URL, LLAMA_URL = f"http://127.0.0.1:{NINFER_PORT}/v1", f"http://127.0.0.1:{LLAMA_PORT}/v1"
ATTEMPT = ROOT / "attempts/speed-attempt-02"
RUNS, LOGS, RECEIPTS = ATTEMPT / "runs", ATTEMPT / "logs", ATTEMPT / "receipts"
ORDER_SEED, PROMPT_SEED = 32103, 4000
NINFER_UNIT, LLAMA_UNIT = "q32-ninfer-speed.scope", "q32-llama-speed.scope"
MODEL = q.MODEL
NINFER = q.SERVER
BASE_MODEL = pathlib.Path("/media/cristian/Disco local/Models/llamacpp/Qwen3.8-27B-GGUF-Q4_K_M/Qwen3.8-27B-Q4_K_M.gguf")
BASE_SHA = "c600de0300ae8a0eb3a6c0b8b5561b8b96f16bd2c863c2a66c42de29d391a747"
BASE_SIZE = 18_973_870_528
BASE_MTIME_NS = 1_791_940_321_744_422_000
LLAMA = pathlib.Path("/home/cristian/.cache/llamacode/embeddinggemma2-eval/runtime/llama-b11554/llama-server")
LLAMA_SHA = "fe8a7d6073d3e3a276193fcaec162cbf280d2572ad2016c9100fd924be19c6ed"
TEMPLATE = REPO / "assets/chat-templates/qwen38-tools-fixed.jinja"
TEMPLATE_SHA = "03c3e852d2c349ce306ed9ecd870c83487bf123918843387b179ead1fcce93af"
CELLS = (("fresh_generation",1024),("fresh_generation",8192),("fresh_generation",24576),("prompt_copy",2048),("prompt_copy",24576))
REPS = (1,2,3)
VOCAB = ("amber","bicycle","carbon","cedar","cobalt","compass","copper","crystal","garden","harbor","island","lantern","maple","meadow","museum","orbit","orange","parcel","planet","quartz","silver","station","velvet","violet","window","yellow")
VERIFIED_HASHES = None

def sha(path: pathlib.Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""): h.update(b)
    return h.hexdigest()

def write(path: pathlib.Path,obj: object) -> None: q.write_json(path,obj)

def apps_and_processes() -> tuple[list,list]:
    return q.inference_processes(),q.compute_apps()

def append(path:pathlib.Path,obj: object) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as f:f.write(json.dumps(obj,ensure_ascii=False)+"\n")

def guard(server_pid:int,cg:pathlib.Path) -> dict:
    mem=q.meminfo();temp=q.gpu_temp();apps=q.compute_apps();foreign=q.inference_processes({server_pid})
    bad=[x for x in apps if x["pid"]!=server_pid];events={}
    ep=cg/"memory.events"
    if ep.exists():
        for line in ep.read_text().splitlines():
            k,v=line.split();events[k]=int(v)
    state={"at_utc":q.utc(),"server_pid":server_pid,"meminfo":mem,"gpu_temp_c":temp,"cuda_compute_apps":apps,
           "foreign_inference_servers":foreign,"memory_current_bytes":int((cg/"memory.current").read_text()),"memory_events":events}
    if mem.get("MemAvailable",0)<q.MIN_MEM or mem.get("SwapFree",0)<q.MIN_SWAP or temp>q.MAX_TEMP:
        raise RuntimeError("Resource guard tripped: "+json.dumps(state))
    if bad or foreign:raise RuntimeError("Unexpected GPU/server process: "+json.dumps({"compute":bad,"servers":foreign}))
    if events.get("max",0) or events.get("oom",0) or events.get("oom_kill",0):raise RuntimeError("Cgroup OOM/max event: "+json.dumps(events))
    if not pathlib.Path(f"/proc/{server_pid}").exists():raise RuntimeError("Owned server exited")
    append(RECEIPTS/"speed-guard-progress.jsonl",state)
    return state

def preflight(profile: str,port: int) -> dict:
    global VERIFIED_HASHES
    lock=json.loads(q.LOCK.read_text()) if q.LOCK.is_file() else {}
    if lock.get("token")!=q.TOKEN or lock.get("task_id")!="Q-20261022-VF-ITERATION-32":
        raise RuntimeError("Q32 no longer owns WORK_QUEUE.lock")
    for p in (MODEL,NINFER,BASE_MODEL,LLAMA,TEMPLATE):
        if not p.is_file(): raise RuntimeError(f"Missing pinned artifact: {p}")
    if MODEL.stat().st_size!=q.MODEL_SIZE: raise RuntimeError("NInfer model size mismatch")
    if BASE_MODEL.stat().st_size!=BASE_SIZE or BASE_MODEL.stat().st_mtime_ns!=BASE_MTIME_NS:
        raise RuntimeError("Qwen Q4 baseline fingerprint mismatch")
    if VERIFIED_HASHES is None:
        VERIFIED_HASHES={"ninfer_model":sha(MODEL),"baseline_model":sha(BASE_MODEL),"llama":sha(LLAMA),"template":sha(TEMPLATE)}
    if VERIFIED_HASHES!={"ninfer_model":q.MODEL_SHA,"baseline_model":BASE_SHA,"llama":LLAMA_SHA,"template":TEMPLATE_SHA}:
        raise RuntimeError("One or more artifact hashes differ from preregistration: "+json.dumps(VERIFIED_HASHES))
    if sha(LLAMA)!=LLAMA_SHA or sha(TEMPLATE)!=TEMPLATE_SHA: raise RuntimeError("llama.cpp or template fingerprint changed after initial preflight")
    servers,compute=apps_and_processes()
    if servers or compute: raise RuntimeError("Existing inference/CUDA work: "+json.dumps({"servers":servers,"compute":compute}))
    q.PORT=port
    if port==NINFER_PORT:
        q.port_free()
    else:
        import socket
        with socket.socket() as s:s.bind(("127.0.0.1",port))
    mem=q.meminfo(); temp=q.gpu_temp()
    if mem["MemAvailable"]<q.MIN_MEM or mem["SwapFree"]<q.MIN_SWAP or temp>=q.MAX_TEMP:
        raise RuntimeError("RAM/swap/temperature preflight failed: "+json.dumps({"mem":mem,"temp":temp}))
    binary=NINFER if profile=="ninfer" else LLAMA
    version=subprocess.run([str(binary),"--version"],capture_output=True,text=True,timeout=20,check=True).stdout.strip()
    return {"at_utc":q.utc(),"profile":profile,"lock_token":q.TOKEN,"inference_servers":servers,"cuda_compute_apps":compute,
            "gui_preserved":True,"gpu_index":"1","gpu_temp_c":temp,"mem_available_bytes":mem["MemAvailable"],
            "swap_free_bytes":mem["SwapFree"],"model_sha256":q.MODEL_SHA if profile=="ninfer" else BASE_SHA,
            "runtime_version":version,"gate_passed":True}

def server_args(profile: str) -> tuple[list,int,str,str]:
    if profile=="ninfer":
        a=[str(NINFER),str(MODEL),"--host","127.0.0.1","--port",str(NINFER_PORT),"--model-id","qwen38-27b-ninfer-v3-speed",
           "--max-context","32768","--kv-capacity","32768","--max-concurrency","1","--max-pending-requests","1",
           "--pending-timeout-ms","600000","--prefill-chunk","2048","--kv-dtype","int8","--host-context-mib","8192",
           "--default-max-tokens","256","--default-thinking-budget","4096","--reasoning-effort","medium","--temperature","0.6",
           "--top-p","0.95","--top-k","20","--min-p","0","--presence-penalty","0","--spec","dflash2","--draft-tokens","7",
        "--lm-head-draft","--ngram-draft-tokens","15","--no-prefix-reuse","--prefill-cublas","--request-log-jsonl",
           str(LOGS/"speed-ninfer-requests.jsonl"),"--log-level","info"]
        return a,NINFER_PORT,"qwen38-27b-ninfer-v3-speed","ninfer-serve"
    a=[str(LLAMA),"--model",str(BASE_MODEL),"--alias","qwen38-27b-q4km-speed","--host","127.0.0.1","--port",str(LLAMA_PORT),
       "--n-gpu-layers","999","--ctx-size","32768","--batch-size","512","--ubatch-size","512","--threads","8",
       "--cache-type-k","q4_0","--cache-type-v","q4_0","--flash-attn","on","--jinja","--chat-template-file",str(TEMPLATE),
       "--reasoning-effort","medium","--reasoning-budget","4096","--n-predict","256","--spec-type","none"]
    return a,LLAMA_PORT,"qwen38-27b-q4km-speed","llama-server"

def make_messages(kind: str,target: int,rep: int) -> list[dict]:
    nonce=f"q32-{kind}-{target}-{rep}-a2"; rng=random.Random(PROMPT_SEED+target+rep)
    # Fresh-generation records average ~0.28 model tokens per source character.
    # Attempt 01 measured 37,836 prompt tokens for target=24,576 at 5.5 chars/token;
    # 3.55 chars/token keeps that cell below the preregistered 30k-token safety cap.
    chars=int(target*(3.55 if kind=="fresh_generation" else 5.5))
    if kind=="prompt_copy":
        phrase=" ".join(rng.sample(VOCAB,9)); unit=(phrase+" | ")*4; data=(unit*max(1,chars//len(unit)))[:chars]
        task="Copy the reference text sequence repeatedly, separated by one space. Output only copied text; continue until the response reaches its output limit."
    else:
        rows=[]; size=0; i=0
        while size<chars:
            w=rng.sample(VOCAB,5)
            line=f"Record {i:06d}: station {w[0]} measured {rng.randrange(100,999)} units; condition {w[1]}; operator {w[2]}; revision {rng.randrange(10,99)}; reference {w[3]} {w[4]}.\n"
            rows.append(line); size+=len(line); i+=1
        data="".join(rows)[:chars]
        task="Using only those records, identify the last station and write a detailed 180-to-220-word incident summary. Do not repeat the records verbatim."
    system=f"You are in a local performance test. Request identifier: {nonce}. Follow the user's task exactly."
    user=f"Trial {nonce}. Reference records follow:\n{data}\n{task}"
    return [{"role":"system","content":system},{"role":"user","content":user}]

def post(base_url:str,model:str,messages:list,max_tokens:int) -> tuple[dict,float]:
    body={"model":model,"messages":messages,"temperature":0.6,"top_p":0.95,"top_k":20,"min_p":0.0,"repeat_penalty":1.0,
          "presence_penalty":0.0,"max_tokens":max_tokens,"stream":False,"reasoning_effort":"medium"}
    req=urllib.request.Request(base_url+"/chat/completions",data=json.dumps(body).encode(),
        headers={"Content-Type":"application/json"},method="POST")
    start=time.monotonic()
    try:
        with urllib.request.urlopen(req,timeout=900) as response: raw=response.read()
    except urllib.error.HTTPError as exc:
        detail=exc.read().decode("utf-8","replace")[:2000]
        raise RuntimeError(f"HTTP {exc.code} from {base_url}/chat/completions: {detail}") from exc
    return json.loads(raw.decode("utf-8","replace")),time.monotonic()-start

def start(profile:str):
    unit=NINFER_UNIT if profile=="ninfer" else LLAMA_UNIT
    q.UNIT=unit
    _,port,model,comm=server_args(profile)
    pf=preflight(profile,port); write(RECEIPTS/f"speed-preflight-{profile}.json",pf)
    args=server_args(profile)[0]; log=(LOGS/f"speed-{profile}-server.log").open("wb")
    cmd=["systemd-run","--user","--scope","--quiet",f"--unit={unit}","-p","MemoryHigh=86G","-p","MemoryMax=96G","-p","MemorySwapMax=1G",
         "/usr/bin/env","CUDA_VISIBLE_DEVICES=1",*args]
    proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    write(RECEIPTS/f"speed-invocation-{profile}.json",{"at_utc":q.utc(),"unit":unit,"args":args,"cuda_visible_devices":"1","memory_limits":["86G","96G","1G"]})
    start_at=time.monotonic(); deadline=start_at+1800; pid=None; cg=None; next_guard=0
    try:
        while time.monotonic()<deadline:
            if proc.poll() is not None: raise RuntimeError(f"{profile} systemd-run exited {proc.returncode}")
            props=q.unit_props()
            group=props.get("ControlGroup","")
            path=pathlib.Path("/sys/fs/cgroup")/group.lstrip("/") if group else None
            if props.get("ActiveState")=="active" and path and path.exists():
                for rawpid in (path/"cgroup.procs").read_text().splitlines():
                    try:
                        if pathlib.Path(f"/proc/{rawpid}/comm").read_text().strip()==comm:pid=int(rawpid);cg=path;break
                    except (OSError,ProcessLookupError):pass
            if pid:
                try:
                    if time.monotonic()>=next_guard:
                        guard(pid,cg);next_guard=time.monotonic()+20
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models",timeout=3).read()
                    limits={name:(cg/name).read_text().strip() for name in ("memory.high","memory.max","memory.swap.max")}
                    expected={"memory.high":str(86*1024**3),"memory.max":str(96*1024**3),"memory.swap.max":str(1024**3)}
                    if limits!=expected:raise RuntimeError("Effective cgroup limits differ from preregistration: "+json.dumps(limits))
                    write(RECEIPTS/f"speed-ready-{profile}.json",{"at_utc":q.utc(),"pid":pid,"unit":unit,"cgroup":str(cg),"limits":limits,"startup_seconds":time.monotonic()-start_at})
                    return proc,log,pid,cg,unit,port,model,time.monotonic()-start_at
                except RuntimeError:raise
                except Exception:pass
            time.sleep(5)
        raise TimeoutError(f"{profile} not ready within 30 minutes")
    except BaseException:
        q.stop_owned(proc);log.close();raise

def parse_ninfer(path:pathlib.Path,start_lines:int)->dict:
    for _ in range(30):
        lines=path.read_text(encoding="utf-8",errors="replace").splitlines() if path.exists() else []
        docs=[]
        for line in lines[start_lines:]:
            try:docs.append(json.loads(line))
            except json.JSONDecodeError:pass
        done=[x for x in docs if x.get("event")=="request_done"]
        if done:
            d=done[-1]; r=d.get("result",{}); t=d.get("timings_seconds",{})
            return {"server_prompt_tokens":r.get("prompt_tokens"),"server_completion_tokens":r.get("completion_tokens"),
                    "prefill_tps":r.get("computed_prefill_tokens",0)/t["prefill"] if t.get("prefill",0) else None,
                    "decode_tps":r.get("completion_tokens",0)/t["decode"] if t.get("decode",0) else None,
                    "ttft_seconds":t.get("ttft"),"server_e2e_seconds":t.get("total"),"speculative":d.get("speculative")}
        time.sleep(.1)
    return {"telemetry_error":"missing NInfer request_done"}

def parse_llama(path:pathlib.Path,offset:int)->dict:
    text=path.read_text(encoding="utf-8",errors="replace")[offset:]
    p=re.findall(r"prompt eval time\s*=\s*([0-9.]+)\s*ms\s*/\s*([0-9]+)\s*tokens.*?([0-9.]+)\s*tokens per second",text)
    g=re.findall(r"eval time\s*=\s*([0-9.]+)\s*ms\s*/\s*([0-9]+)\s*tokens.*?([0-9.]+)\s*tokens per second",text)
    if not p or not g:return {"telemetry_error":"missing llama.cpp slot print_timing"}
    return {"server_prompt_tokens":int(p[-1][1]),"server_completion_tokens":int(g[-1][1]),"prefill_tps":float(p[-1][2]),"decode_tps":float(g[-1][2]),
            "prefill_seconds":float(p[-1][0])/1000,"decode_seconds":float(g[-1][0])/1000}

def run_profile(profile:str,order:list[tuple[str,int,int]],prompts:dict) -> list[dict]:
    proc=log=None; results=[]; reqlog=LOGS/"speed-ninfer-requests.jsonl"; serverlog=LOGS/f"speed-{profile}-server.log"
    proc,log,pid,cg,unit,port,model,startup=start(profile)
    q.UNIT=unit; base=NINFER_URL if profile=="ninfer" else LLAMA_URL
    watch_stop=threading.Event(); watch_errors=[]
    def watch():
        while not watch_stop.wait(20):
            try:
                guard(pid,cg)
            except BaseException as e:
                watch_errors.append(f"{type(e).__name__}: {e}")
                watch_stop.set()
                return
    watcher=threading.Thread(target=watch,daemon=True);watcher.start()
    try:
        # Warm-up, excluded from the measurements.
        post(base,model,[{"role":"user","content":"Say READY in one word."}],8)
        write(RECEIPTS/f"speed-warmup-{profile}.json",{"at_utc":q.utc(),"passed":True,"excluded":True})
        for index,(kind,target,rep) in enumerate(order,1):
            msgs=prompts[(kind,target,rep)]; text="\n".join(m["content"] for m in msgs)
            before=sum(1 for _ in reqlog.open()) if profile=="ninfer" and reqlog.exists() else 0
            offset=len(serverlog.read_text(encoding="utf-8",errors="replace")) if profile=="llama" and serverlog.exists() else 0
            response,e2e=post(base,model,msgs,256)
            if watch_errors:raise RuntimeError("Resource watchdog failed: "+watch_errors[0])
            source=response.get("usage",{})
            if source.get("prompt_tokens",0)>30000:
                raise RuntimeError(f"Request used {source['prompt_tokens']} input tokens; preregistered maximum is 30000")
            time.sleep(.2)
            server=parse_ninfer(reqlog,before) if profile=="ninfer" else parse_llama(serverlog,offset)
            prompt=source.get("prompt_tokens") or server.get("server_prompt_tokens")
            completion=source.get("completion_tokens") or server.get("server_completion_tokens")
            out={"at_utc":q.utc(),"profile":profile,"cell":kind,"target_prompt_tokens":target,"repetition":rep,"index":index,
                 "prompt_sha256":hashlib.sha256(text.encode()).hexdigest(),"prompt_characters":len(text),"prompt_tokens":prompt,
                 "completion_tokens":completion,"max_output_tokens":256,"finish_reason":response.get("choices",[{}])[0].get("finish_reason"),
                 "e2e_client_seconds":e2e,"client_total_tps":completion/e2e if completion and e2e else None,
                 "server_metrics":server,"response_id":response.get("id")}
            results.append(out); append(RUNS/"speed-measurements.jsonl",out)
            append(RECEIPTS/"speed-progress.jsonl",{"at_utc":q.utc(),"profile":profile,"completed":len(results),"total":len(order),"cell":kind,"target":target,"rep":rep})
            guard(pid,cg)
            print(f"{profile} {len(results)}/{len(order)} {kind} target={target} rep={rep} prompt={prompt} output={completion} e2e={e2e:.2f}s",flush=True)
        return results
    finally:
        watch_stop.set();watcher.join(timeout=15)
        q.stop_owned(proc)
        postflight={"at_utc":q.utc(),"profile":profile,"inference_processes":q.inference_processes(),"cuda_compute_apps":q.compute_apps(),
                    "meminfo":q.meminfo(),"gpu_temp_c":q.gpu_temp()}
        q.write_json(RECEIPTS/f"speed-postflight-{profile}.json",postflight)
        log.close()
        if postflight["inference_processes"] or postflight["cuda_compute_apps"]:raise RuntimeError("Unexpected server/compute process after cleanup")

def main()->int:
    if any(p.exists() for p in (RUNS/"speed-measurements.jsonl", LOGS/"speed-ninfer-requests.jsonl", RECEIPTS/"speed-execution-start.json")):
        raise RuntimeError("Speed phase has prior receipts; refusing to overwrite or append a second run")
    for directory in (RUNS, LOGS, RECEIPTS): directory.mkdir(parents=True, exist_ok=True)
    campaign_start=time.monotonic()
    prompts={(k,t,r):make_messages(k,t,r) for k,t in CELLS for r in REPS}
    order=[(k,t,r) for k,t in CELLS for r in REPS];random.Random(ORDER_SEED).shuffle(order)
    q.write_json(RECEIPTS/"speed-order.json",{"seed":ORDER_SEED,"prompt_seed":PROMPT_SEED,"order":order,"same_for_both_profiles":True})
    write(RECEIPTS/"speed-execution-start.json",{"at_utc":q.utc(),"profiles_order":["llama","ninfer"],"requests_per_profile":len(order),
          "total_requests":len(order)*2,"quality_gate_passed":False,"reason":"descriptive local speed claim; quality rejection remains in force"})
    allres={}
    for p in ("llama","ninfer"):allres[p]=run_profile(p,order,prompts)
    summary=[]
    for kind,target in CELLS:
        row={"cell":kind,"target_prompt_tokens":target,"profiles":{}}
        for profile in ("llama","ninfer"):
            xs=[x for x in allres[profile] if x["cell"]==kind and x["target_prompt_tokens"]==target]
            row["profiles"][profile]={k:statistics.median([x.get(k) for x in xs if x.get(k)is not None]) if any(x.get(k)is not None for x in xs) else None
                for k in ("prompt_tokens","completion_tokens","e2e_client_seconds","client_total_tps")}
            for key in ("prefill_tps","decode_tps","ttft_seconds","server_e2e_seconds"):
                values=[x.get("server_metrics",{}).get(key) for x in xs if x.get("server_metrics",{}).get(key) is not None]
                row["profiles"][profile][key]=statistics.median(values) if values else None
            row["profiles"][profile]["repetitions"]=len(xs)
        b=row["profiles"]["llama"]["e2e_client_seconds"];n=row["profiles"]["ninfer"]["e2e_client_seconds"]
        row["ninfer_e2e_speedup_fraction"]=b/n-1 if b and n else None;summary.append(row)
    wins=sum(x["ninfer_e2e_speedup_fraction"] is not None and x["ninfer_e2e_speedup_fraction"]>=.10 for x in summary)
    startup={p:json.loads((RECEIPTS/f"speed-ready-{p}.json").read_text()).get("startup_seconds") for p in ("llama","ninfer")}
    final={"status":"completed","finished_at_utc":q.utc(),"campaign_seconds":time.monotonic()-campaign_start,"startup_seconds":startup,
           "measurements":len(allres["llama"])+len(allres["ninfer"]),"summary":summary,
           "ninfer_cells_at_least_10pct_faster":wins,"speed_gate_passed":wins>=2,"quality_gate_passed":False,
           "adoption_recommendation":"do not adopt for agent tool use; quality safety gates failed independent of speed"}
    write(RECEIPTS/"speed-results.json",final);print("SPEED_FINAL "+json.dumps(final,ensure_ascii=False),flush=True);return 0

if __name__=="__main__":raise SystemExit(main())
