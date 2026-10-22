#!/usr/bin/env python3
"""Preregistered speed-only A/B: Qwen3.8-27B NInfer v3 vs current SOL profile."""
from __future__ import annotations
import datetime as dt, hashlib, importlib.util, json, os, pathlib, random, re, socket, statistics, subprocess, sys, time, urllib.request

REPO = pathlib.Path(__file__).resolve().parents[4]
ROOT = pathlib.Path(__file__).resolve().parents[1]
TOKEN = "4bb67f14-f9a8-4c64-971a-58ddfd497ab3"
TASK = "Q-20261022-VF-ITERATION-34"
BASE_HELPER = REPO / "artifacts/evaluacion-modelos-llamacode/Q-20261022-VF-ITERATION-32/scripts/run_ninfer_speed.py"
BASE_HELPER_SHA = "160dc3385d0f6dd542a8b511a38306307d692c9fed938696494e15bc8cf0941f"
spec = importlib.util.spec_from_file_location("q32_speed_helper", BASE_HELPER)
speed = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = speed
assert spec.loader
spec.loader.exec_module(speed)
q = speed.q

speed.ROOT = ROOT
speed.REPO = REPO
ATTEMPT_NAME = os.environ.get("Q34_ATTEMPT_NAME", "direct-sol-speed")
speed.ATTEMPT = ROOT / "attempts" / ATTEMPT_NAME
speed.RUNS = speed.ATTEMPT / "runs"
speed.LOGS = speed.ATTEMPT / "logs"
speed.RECEIPTS = speed.ATTEMPT / "receipts"
speed.NINFER_PORT = 18132
speed.NINFER_URL = "http://127.0.0.1:18132/v1"
speed.NINFER_UNIT = "q34-ninfer-speed.scope"
speed.NINFER = q.SERVER
q.ROOT = ROOT
q.TOKEN = TOKEN
q.LOCK = REPO / "WORK_QUEUE.lock"
q.UNIT = speed.NINFER_UNIT
q.PORT = speed.NINFER_PORT
q.BASE_URL = speed.NINFER_URL
q.MIN_MEM = 30 * 1024**3
q.MIN_SWAP = 1 * 1024**3
q.MAX_TEMP = 80

COMPOSE = pathlib.Path("/home/cristian/.cache/llamacode/club-3090-src/models/qwen3.8-27b/vllm/compose/dual/autoround-int4/mtp.yml")
COMPOSE_OVERRIDE = COMPOSE.parent / "vram-quarantine.override.yml"
ISOLATION = ROOT / "work/sol-isolated.compose.yml"
MODEL_DIR = pathlib.Path("/media/cristian/Disco local/Models/llamacpp/club-3090")
SOL_MODEL_DIR = MODEL_DIR / "qwen3.8-27b-autoround-int4"
CANDIDATE = pathlib.Path("/media/cristian/HDD extra/Modelos-eval/Q-20261022-VF-ITERATION-32/models/qwen3_8_27b.ninfer")
CANDIDATE_SHA = "7f2a0086a071ee932c66106e1552d118a85cfec8ddef13c67a54cd64abb39706"
SOL_PORT = 18113
SOL_MODEL_ID = "qwen3.8-27b"
PROJECT = "q34-sol-speed"
CONTAINER = "q34-sol-speed"
SOL_BASE = f"http://127.0.0.1:{SOL_PORT}/v1"
ENV_OVERRIDES = {
    "BIND_HOST":"127.0.0.1","PORT":str(SOL_PORT),"ESTATE_CONTAINER":CONTAINER,
    "MODEL_DIR":str(MODEL_DIR),"TP":"2","MAX_MODEL_LEN":"262144","GPU_MEMORY_UTILIZATION":"0.90",
    "MAX_NUM_SEQS":"8","MAX_NUM_BATCHED_TOKENS":"8192","SPEC_N":"4","W4A8":"1",
    "ENABLE_THINKING":"true","TEMP":"0.6","TOP_P":"0.95","TOP_K":"20","MIN_P":"0.0","PRESENCE_PENALTY":"0.0"
}
SOL_FILES = [
    ("model-00001-of-00007.safetensors","83c0adb0f1141142a25c5f7937a09272fef2baee7d6b07afe60a076feffe3b66"),
    ("model-00002-of-00007.safetensors","6c86c3917cd228d5699cb1435d9216e2baf281582ba4282a98638163605be7ec"),
    ("model-00003-of-00007.safetensors","bfb9613b3f6ba3d0c5b3efa74f92cc14ec5c9266b341a79bf6b45247a5857770"),
    ("model-00004-of-00007.safetensors","8e9fbd476aa3055c3c0a886298f9beb93c5275c748c533835746f6648f6dae55"),
    ("model-00005-of-00007.safetensors","f0cd639621eb26410d96b8c073344ae008f646572a9c4713326ff43d406cf276"),
    ("model-00006-of-00007.safetensors","55a14ee79d3e5a65a8731d89426f4df477e8bdc7daa7976d41254d8afb9432f0"),
    ("model-00007-of-00007.safetensors","6866cf8adcccc4cc6a00e74bc025f1a774fb52103b70f2674d0288272951a733")
]

# Keep incidental desktop CUDA work observable without treating it as an inference server.
real_compute_apps = q.compute_apps

def utc(): return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
def write(path,obj): q.write_json(path,obj)
def append(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as f: f.write(json.dumps(obj,ensure_ascii=False)+"\n")
def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""): h.update(b)
    return h.hexdigest()
def lock_ok():
    d=json.loads(q.LOCK.read_text())
    if d.get("token")!=TOKEN or d.get("task_id")!=TASK: raise RuntimeError("Q34 no longer owns WORK_QUEUE.lock")
def temps():
    p=subprocess.run(["nvidia-smi","--query-gpu=index,temperature.gpu,memory.used,utilization.gpu","--format=csv,noheader,nounits"],capture_output=True,text=True,timeout=10,check=True)
    rows=[]
    for line in p.stdout.splitlines():
        f=[x.strip() for x in line.split(",")]
        rows.append({"index":int(f[0]),"temperature_c":int(f[1]),"memory_used_mib":int(f[2]),"utilization_pct":int(f[3])})
    return rows
def container_pids():
    p=subprocess.run(["docker","inspect","--format","{{.State.Pid}}","q34-sol-speed"],capture_output=True,text=True,timeout=10)
    if p.returncode or not p.stdout.strip() or p.stdout.strip()=="0": return set()
    pid=int(p.stdout.strip()); out={pid}
    try:
        cg=pathlib.Path("/sys/fs/cgroup") / next(x.split("::",1)[1].lstrip("/") for x in pathlib.Path(f"/proc/{pid}/cgroup").read_text().splitlines() if x.startswith("0::"))
        if cg.exists():
            for f in cg.rglob("cgroup.procs"):
                try: out.update(int(x) for x in f.read_text().splitlines() if x.isdigit())
                except OSError: pass
    except (OSError,StopIteration,ValueError): pass
    return out
def docker_rows():
    p=subprocess.run(["docker","ps","--format","{{json .}}"],capture_output=True,text=True,timeout=10,check=True)
    return [json.loads(x) for x in p.stdout.splitlines() if x.strip()]
def resources(stage,allow_sol=False):
    lock_ok()
    mem=q.meminfo(); gpu=temps(); servers=q.inference_processes(container_pids() if allow_sol else set())
    containers=docker_rows()
    foreign_containers=[]
    for c in containers:
        name=(c.get("Names","")+" "+c.get("Image","")+" "+c.get("Ports","")).lower()
        if c.get("Names")==CONTAINER and allow_sol: continue
        if any(t in name for t in ("vllm","ninfer","llama-server","ollama","strata","openjet","sglang","aphrodite")):
            foreign_containers.append(c)
    disk=pathlib.Path("/var/lib/docker").stat().st_dev
    import os as _os
    st=_os.statvfs("/var/lib/docker"); docker_free=st.f_bavail*st.f_frsize
    state={"at_utc":utc(),"stage":stage,"mem_available_bytes":mem.get("MemAvailable"),"swap_free_bytes":mem.get("SwapFree"),"gpus":gpu,
           "cuda_compute_apps_observed":real_compute_apps(),"foreign_inference_processes":servers,"foreign_inference_containers":foreign_containers,
           "docker_free_bytes":docker_free,"docker_device":disk}
    if mem.get("MemAvailable",0)<q.MIN_MEM or mem.get("SwapFree",0)<q.MIN_SWAP: raise RuntimeError("RAM/swap gate: "+json.dumps(state))
    if not gpu or max(x["temperature_c"] for x in gpu)>=q.MAX_TEMP: raise RuntimeError("GPU temperature gate: "+json.dumps(state))
    if servers or foreign_containers: raise RuntimeError("Another inference server appeared: "+json.dumps(state))
    if docker_free < 8*1024**3: raise RuntimeError("Docker storage free space fell below 8 GiB: "+json.dumps(state))
    return state

def port_free(port):
    with socket.socket() as s: s.bind(("127.0.0.1",port))
def preflight(profile,port):
    state=resources("preflight-"+profile,allow_sol=False)
    port_free(port)
    if profile=="ninfer":
        if not CANDIDATE.is_file() or CANDIDATE.stat().st_size!=18_982_458_624: raise RuntimeError("NInfer candidate size changed")
        model_sha=sha(CANDIDATE)
        if model_sha!=CANDIDATE_SHA: raise RuntimeError("NInfer model SHA mismatch: "+model_sha)
        rt=speed.NINFER
        version=subprocess.run([str(rt),"--version"],capture_output=True,text=True,timeout=20,check=True).stdout.strip()
        state.update({"model_sha256":model_sha,"runtime_version":version,"gpu_scope":"physical GPU1"})
    else:
        state.update({"control":"SOL current compose profile","compose_sha256":sha(COMPOSE),"image_id":"sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967"})
    state["gate_passed"]=True
    write(speed.RECEIPTS/f"speed-preflight-{profile}.json",state)
    return state

# Override the Q32 helper's profile-specific gate; run_profile still owns launch/stop of NInfer.
speed.preflight=preflight
q.compute_apps=lambda: []
def max_temp(): return max(x["temperature_c"] for x in temps())
q.gpu_temp=max_temp

def compose_cmd(action):
    return ["docker","compose","--project-directory",str(COMPOSE.parent),"-p",PROJECT,"-f",str(COMPOSE),"-f",str(COMPOSE_OVERRIDE),"-f",str(ISOLATION),*action]
SOL_STARTED = False
def start_sol():
    global SOL_STARTED
    resources("before-sol-start")
    preflight("sol",SOL_PORT)
    env=os.environ.copy(); env.update(ENV_OVERRIDES)
    cmd=compose_cmd(["up","-d","--remove-orphans"])
    p=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=180)
    SOL_STARTED = True  # cleanup owns only the unique Q34 project/container
    write(speed.RECEIPTS/"sol-compose-start.json",{"at_utc":utc(),"returncode":p.returncode,"stdout":p.stdout[-2000:],"stderr":p.stderr[-2000:],"project":PROJECT,"container":CONTAINER})
    if p.returncode: raise RuntimeError("isolated SOL compose up failed; see sol-compose-start.json")
    started=time.monotonic(); deadline=started+1800
    while time.monotonic()<deadline:
        state=resources("sol-startup",allow_sol=True)
        status=subprocess.run(["docker","inspect","--format","{{.State.Status}} {{.State.ExitCode}} {{.State.OOMKilled}} {{.RestartCount}}","q34-sol-speed"],capture_output=True,text=True,timeout=10)
        if status.returncode==0 and status.stdout.startswith("exited"):
            log=subprocess.run(["docker","logs","q34-sol-speed"],capture_output=True,text=True,timeout=10)
            (speed.LOGS/"sol-startup-failure.log").write_text((log.stdout+log.stderr)[-30000:])
            raise RuntimeError("isolated SOL container exited during startup: "+status.stdout.strip())
        try:
            with urllib.request.urlopen(SOL_BASE+"/models",timeout=3) as r:
                data=json.loads(r.read().decode())
            models=[x.get("id") for x in data.get("data",[])]
            if r.status==200 and SOL_MODEL_ID in models:
                elapsed=time.monotonic()-started
                write(speed.RECEIPTS/"speed-ready-sol.json",{"at_utc":utc(),"startup_seconds":elapsed,"models":models,"container_state":status.stdout.strip(),"resource_snapshot":state})
                return elapsed
        except Exception: pass
        time.sleep(10)
    raise TimeoutError("isolated SOL did not reach /v1/models in 30 minutes")

def stop_sol():
    global SOL_STARTED
    if not SOL_STARTED: return
    env=os.environ.copy(); env.update(ENV_OVERRIDES)
    p=subprocess.run(compose_cmd(["down","--remove-orphans","--timeout","15"]),env=env,capture_output=True,text=True,timeout=90)
    write(speed.RECEIPTS/"sol-compose-stop.json",{"at_utc":utc(),"returncode":p.returncode,"stdout":p.stdout[-2000:],"stderr":p.stderr[-2000:]})
    if p.returncode: raise RuntimeError("failed to stop Q34-owned SOL container")
    post=resources("after-sol-stop",allow_sol=False)
    if any(c.get("Names")==CONTAINER for c in docker_rows()): raise RuntimeError("Q34 SOL container remains after cleanup")
    write(speed.RECEIPTS/"speed-postflight-sol.json",post)
    SOL_STARTED = False

def capture_sol_logs():
    try:
        p=subprocess.run(["docker","logs","--tail","2500",CONTAINER],capture_output=True,text=True,timeout=15)
        raw=re.sub(r"(?i)(hf_[A-Za-z0-9]{16,}|Bearer\s+[^\s\"']+)","[REDACTED]",p.stdout+p.stderr)[-250000:]
        path=speed.LOGS/"sol-engine-before-cleanup.log"
        path.write_text(raw,encoding="utf-8")
        write(speed.RECEIPTS/"sol-engine-log-capture.json",{"at_utc":utc(),"returncode":p.returncode,"bytes_saved":len(raw),
              "tail_sha256":hashlib.sha256(raw.encode()).hexdigest(),"path":str(path)})
    except Exception as e:
        write(speed.RECEIPTS/"sol-engine-log-capture.json",{"at_utc":utc(),"capture_error":f"{type(e).__name__}: {e}"})

def sol_post(base_url:str,model:str,messages:list,max_tokens:int) -> tuple[dict,float]:
    # SOL's profile already fixes these sampler values; omit duplicate request overrides.
    body={"model":model,"messages":messages,"max_tokens":max_tokens,"stream":False,"reasoning_effort":"medium"}
    req=urllib.request.Request(base_url+"/chat/completions",data=json.dumps(body).encode(),
        headers={"Content-Type":"application/json"},method="POST")
    start=time.monotonic()
    try:
        with urllib.request.urlopen(req,timeout=900) as response: raw=response.read()
    except urllib.error.HTTPError as exc:
        detail=exc.read().decode("utf-8","replace")[:2000]
        raise RuntimeError(f"HTTP {exc.code} from {base_url}/chat/completions: {detail}") from exc
    return json.loads(raw.decode("utf-8","replace")),time.monotonic()-start

def scrape_metrics():
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{SOL_PORT}/metrics",timeout=5) as r: raw=r.read().decode("utf-8","replace")
    except Exception as e: return {"telemetry_error":str(e)}
    sums={}
    pat=re.compile(r"^([^{}\s]+)(?:\{[^}]*\})?\s+([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)")
    for line in raw.splitlines():
        m=pat.match(line)
        if m:
            try:sums[m.group(1)]=sums.get(m.group(1),0.0)+float(m.group(2))
            except ValueError:pass
    return sums
def delta_suffix(before,after,suffix):
    keys={k for k in set(before)|set(after) if k.endswith(suffix)}
    vals=[after.get(k,0.0)-before.get(k,0.0) for k in keys]
    return sum(vals) if vals else None
def sol_metrics(before,after,prompt_tokens,completion_tokens):
    ttft=delta_suffix(before,after,"time_to_first_token_seconds_sum")
    ttft_count=delta_suffix(before,after,"time_to_first_token_seconds_count")
    tpot=delta_suffix(before,after,"time_per_output_token_seconds_sum")
    tpot_count=delta_suffix(before,after,"time_per_output_token_seconds_count")
    e2e=delta_suffix(before,after,"e2e_request_latency_seconds_sum")
    prompt_delta=delta_suffix(before,after,"prompt_tokens_total")
    output_delta=delta_suffix(before,after,"generation_tokens_total")
    return {"ttft_seconds":ttft if ttft_count==1 else None,"ttft_histogram_count_delta":ttft_count,
            "effective_prefill_tps_approx":prompt_tokens/ttft if prompt_tokens and ttft and ttft>0 else None,
            "time_per_output_token_seconds_sum":tpot if tpot_count and tpot_count>0 else None,
            "time_per_output_token_count_delta":tpot_count,
            "decode_tps_from_tpot_histogram":tpot_count/tpot if tpot_count and tpot and tpot>0 else None,
            "server_e2e_seconds":e2e if e2e is not None else None,"prompt_tokens_metric_delta":prompt_delta,
            "generation_tokens_metric_delta":output_delta}

def run_sol(order,prompts):
    startup=None; base=SOL_BASE; results=[]
    try:
        startup=start_sol()
        resources("sol-before-warmup",allow_sol=True)
        sol_post(base,SOL_MODEL_ID,[{"role":"user","content":"Say READY in one word."}],8)
        write(speed.RECEIPTS/"speed-warmup-sol.json",{"at_utc":utc(),"passed":True,"excluded":True})
        for i,(kind,target,rep) in enumerate(order,1):
            state=resources(f"sol-request-{i}-before",allow_sol=True)
            messages=prompts[(kind,target,rep)]; text="\n".join(m["content"] for m in messages)
            before=scrape_metrics(); response,e2e=sol_post(base,SOL_MODEL_ID,messages,256); after=scrape_metrics()
            usage=response.get("usage",{}); pm=usage.get("prompt_tokens"); cm=usage.get("completion_tokens")
            if pm is None or cm is None: raise RuntimeError("SOL response omitted prompt/completion token usage")
            if pm>30000: raise RuntimeError(f"SOL prompt {pm} exceeds preregistered 30000-token cap")
            metrics=sol_metrics(before,after,pm,cm)
            row={"at_utc":utc(),"profile":"SOL","cell":kind,"target_prompt_tokens":target,"repetition":rep,"index":i,
                 "prompt_sha256":hashlib.sha256(text.encode()).hexdigest(),"prompt_characters":len(text),"prompt_tokens":pm,"completion_tokens":cm,
                 "max_output_tokens":256,"finish_reason":response.get("choices",[{}])[0].get("finish_reason"),"e2e_client_seconds":e2e,
                 "client_total_tps":cm/e2e if e2e else None,"server_metrics":metrics,"response_id":response.get("id"),"resource_snapshot":state}
            results.append(row); append(speed.RUNS/"speed-measurements.jsonl",row)
            append(speed.RECEIPTS/"speed-progress.jsonl",{"at_utc":utc(),"profile":"SOL","completed":i,"total":len(order),"cell":kind,"target":target,"rep":rep})
            print(f"SOL {i}/{len(order)} {kind} target={target} rep={rep} prompt={pm} output={cm} e2e={e2e:.2f}s",flush=True)
        return results,startup
    except BaseException:
        if SOL_STARTED: capture_sol_logs()
        raise
    finally:
        if SOL_STARTED:
            if not (speed.RECEIPTS/"sol-engine-log-capture.json").exists(): capture_sol_logs()
            stop_sol()

def server_guard(server_pid,cg):
    mem=q.meminfo(); gpu=temps(); foreign=q.inference_processes({server_pid}); events={}
    ep=cg/"memory.events"
    if ep.exists():
        for line in ep.read_text().splitlines():
            k,v=line.split(); events[k]=int(v)
    state={"at_utc":utc(),"server_pid":server_pid,"mem_available_bytes":mem.get("MemAvailable"),"swap_free_bytes":mem.get("SwapFree"),
           "gpus":gpu,"cuda_compute_apps_observed":real_compute_apps(),"foreign_inference_servers":foreign,
           "memory_current_bytes":int((cg/"memory.current").read_text()),"memory_events":events}
    if mem.get("MemAvailable",0)<q.MIN_MEM or mem.get("SwapFree",0)<q.MIN_SWAP or max(x["temperature_c"] for x in gpu)>=q.MAX_TEMP or foreign:
        raise RuntimeError("NInfer resource/server guard: "+json.dumps(state))
    if any(events.get(k,0) for k in ("max","oom","oom_kill")): raise RuntimeError("NInfer cgroup OOM/max event: "+json.dumps(state))
    append(speed.RECEIPTS/"speed-guard-progress.jsonl",state)
    return state

def main():
    if any(p.exists() for p in (speed.RUNS/"speed-measurements.jsonl",speed.LOGS/"speed-ninfer-requests.jsonl",speed.RECEIPTS/"speed-execution-start.json")):
        raise RuntimeError("Q34 has prior speed execution artifacts; refuse overwrite/repeat")
    for p in (speed.RUNS,speed.LOGS,speed.RECEIPTS):p.mkdir(parents=True,exist_ok=True)
    lock_ok()
    # Preflight actual SOL checkpoint manifest against full shard hashes from the prereg receipt.
    expected={n:h for n,h in SOL_FILES}
    for name,digest in expected.items():
        p=SOL_MODEL_DIR/name
        if not p.is_file() or sha(p)!=digest: raise RuntimeError("SOL model shard fingerprint mismatch: "+str(p))
    if sha(CANDIDATE)!=CANDIDATE_SHA: raise RuntimeError("NInfer candidate model fingerprint mismatch")
    for profile,port in (("sol",SOL_PORT),("ninfer",speed.NINFER_PORT)):
        preflight(profile,port)
    order=[(k,t,r) for k,t in speed.CELLS for r in speed.REPS]
    random.Random(speed.ORDER_SEED).shuffle(order)
    prompts={(k,t,r):speed.make_messages(k,t,r) for k,t in speed.CELLS for r in speed.REPS}
    write(speed.RECEIPTS/"speed-order.json",{"seed":speed.ORDER_SEED,"prompt_seed":speed.PROMPT_SEED,"order":order,"same_for_both_profiles":True,
          "prompt_sha256_by_cell":{f"{k}:{t}:{r}":hashlib.sha256("\n".join(m["content"] for m in prompts[(k,t,r)]).encode()).hexdigest() for k,t,r in prompts}})
    write(speed.RECEIPTS/"speed-execution-start.json",{"at_utc":utc(),"profiles_order":["SOL","NInfer v3"],"requests_per_profile":len(order),"total_requests":len(order)*2,
          "quality_gate_passed":False,"reason":"Q32 quality/security gate remains failed; this test evaluates only speed vs current SOL"})
    campaign=time.monotonic()
    sol_results,sol_start=run_sol(order,prompts)
    # The SOL container and listener are removed before NInfer uses GPU1.
    resources("before-ninfer-start")
    old_compute=q.compute_apps; q.compute_apps=lambda: []  # user allows unrelated desktop CUDA activity
    speed.guard=server_guard
    try:
        # s.run_profile owns only the Q34 systemd unit and stops it in its finally block.
        ninfer_results=speed.run_profile("ninfer",order,prompts)
    finally:
        q.compute_apps=old_compute
    prompt_map={}
    for profile,rows in (("SOL",sol_results),("NInfer v3",ninfer_results)):
        for x in rows: prompt_map.setdefault(x["prompt_sha256"],{})[profile]=x.get("prompt_tokens")
    mismatches=[]
    for h,d in prompt_map.items():
        a,b=d.get("SOL"),d.get("NInfer v3")
        if a is None or b is None or abs(a-b)/max(a,b)>.01: mismatches.append({"prompt_sha256":h,"tokens":d})
    if mismatches: raise RuntimeError("Matched prompts differed by >1% in actual tokens: "+json.dumps(mismatches))
    summary=[]
    for kind,target in speed.CELLS:
        row={"cell":kind,"target_prompt_tokens":target,"profiles":{}}
        for name,rows in (("SOL",sol_results),("NInfer v3",ninfer_results)):
            xs=[x for x in rows if x["cell"]==kind and x["target_prompt_tokens"]==target]
            row["profiles"][name]={"prompt_tokens":statistics.median([x["prompt_tokens"] for x in xs]),
                "completion_tokens":statistics.median([x["completion_tokens"] for x in xs]),
                "e2e_client_seconds":statistics.median([x["e2e_client_seconds"] for x in xs]),"repetitions":len(xs)}
            for key in ("prefill_tps","decode_tps","ttft_seconds","server_e2e_seconds"):
                vals=[x.get("server_metrics",{}).get(key) for x in xs if x.get("server_metrics",{}).get(key) is not None]
                if vals: row["profiles"][name][key]=statistics.median(vals)
            # SOL Prometheus metrics use explicit proxy/metric names, retain their definitions.
            for key in ("effective_prefill_tps_approx","decode_tps_from_tpot_histogram"):
                vals=[x.get("server_metrics",{}).get(key) for x in xs if x.get("server_metrics",{}).get(key) is not None]
                if vals: row["profiles"][name][key]=statistics.median(vals)
        sol_e2e=row["profiles"]["SOL"]["e2e_client_seconds"]; ninfer_e2e=row["profiles"]["NInfer v3"]["e2e_client_seconds"]
        row["ninfer_speedup_fraction_vs_SOL"]=sol_e2e/ninfer_e2e-1 if sol_e2e and ninfer_e2e else None
        summary.append(row)
    wins=sum(x["ninfer_speedup_fraction_vs_SOL"] is not None and x["ninfer_speedup_fraction_vs_SOL"]>=.10 for x in summary)
    ninfer_start=json.loads((speed.RECEIPTS/"speed-ready-ninfer.json").read_text()).get("startup_seconds")
    mean_saving=statistics.mean([x["profiles"]["SOL"]["e2e_client_seconds"]-x["profiles"]["NInfer v3"]["e2e_client_seconds"] for x in summary])
    startup_delta=(ninfer_start-sol_start) if ninfer_start is not None else None
    break_even=(startup_delta/mean_saving if startup_delta is not None and mean_saving>0 else None)
    final={"status":"completed","finished_at_utc":utc(),"campaign_seconds":time.monotonic()-campaign,"startup_seconds":{"SOL":sol_start,"NInfer v3":ninfer_start},
           "startup_delta_ninfer_minus_sol_seconds":startup_delta,"mean_request_saving_sol_minus_ninfer_seconds":mean_saving,"approx_break_even_requests":break_even,
           "measurements":len(sol_results)+len(ninfer_results),"summary":summary,"ninfer_cells_at_least_10pct_faster_vs_SOL":wins,
           "speed_gate_passed":wins>=2,"quality_gate_passed":False,"prompt_token_mismatches":mismatches,
           "adoption_recommendation":"Do not adopt for agents with tools: Q32 quality/security failures remain blocking. Speed result applies only to the current SOL vs NInfer profile pair and synthetic workload."}
    write(speed.RECEIPTS/"speed-results.json",final)
    write(speed.RECEIPTS/"speed-final-verification.json",{"at_utc":utc(),"final":final,"postflight_inference_servers":q.inference_processes(),"docker_containers":docker_rows(),"cuda_compute_apps_observed":real_compute_apps(),"gpu_snapshot":temps(),"meminfo":q.meminfo()})
    print("Q34_SPEED_FINAL "+json.dumps(final,ensure_ascii=False),flush=True)

if __name__=="__main__": main()
