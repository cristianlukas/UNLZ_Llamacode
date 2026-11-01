#!/usr/bin/env python3
"""Q190 Qwen3.6 NInfer-all Q173 driver. Uses only the Q190-owned server/process."""
from __future__ import annotations
import argparse, ctypes, hashlib, json, os, pathlib, signal, socket, subprocess, sys, time, urllib.error, urllib.request
from datetime import datetime, timezone
from statistics import fmean

ROOT=pathlib.Path(__file__).resolve().parents[6]
PROFILE=pathlib.Path(__file__).resolve().parents[1]
MODEL=pathlib.Path('/media/cristian/Disco local/Modelos-eval/Qwen3.6-35B-A3B-NInfer-all-20261101/qwen3_6_35b_a3b.ninfer')
SERVER=pathlib.Path('/mnt/q190/build-nospace/apps/ninfer-serve')
SOURCE=pathlib.Path('/mnt/q190/src/bench/fixtures/ttft/text')
HOST='127.0.0.1'; PORT=18493
TOKEN='d4618d1c-b63c-4d9c-b523-bd4b7d0eb4a0'
TASK='Q190-profile-qwen36-ninfer-all-v3-q173-q172'
MODEL_BYTES=22790484480
MODEL_SHA='3e33297645dc33557751be1a3c407a74ed7c00f34909b5d4e8cfdce91b3dbe84'
SERVE_SHA='7d839bb832f79605363f7a5fbe31944123b7cb54c0d980c1e3686865f163fdb1'
RUNS=PROFILE/'runs'; LOGS=PROFILE/'logs'; RECEIPTS=PROFILE/'receipts'
PIDFILE=RUNS/'owned-server.json'; TOKENS=RUNS/'q173-token-corpus.json'
CONTEXTS=(8192,32768,65536,131072,261888)


def utc(): return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); tmp.replace(path)
def read_json(url,timeout=30):
    with urllib.request.urlopen(url,timeout=timeout) as r: return json.loads(r.read())
def post_json(url,data,timeout=1800):
    req=urllib.request.Request(url,data=json.dumps(data,separators=(',',':')).encode(),headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=timeout) as r: return json.loads(r.read())
def check_lock():
    d=json.loads((ROOT/'WORK_QUEUE.lock').read_text())
    if d.get('token')!=TOKEN or d.get('worker')!='Q-20261029-VF-ITERATION-190': raise RuntimeError('WORK_QUEUE.lock ya no pertenece a Q190')
    prereg=json.loads((PROFILE/'receipts/preregistration.json').read_text())
    expected=prereg.get('q173_execution_method',{}).get('driver_sha256')
    if expected!=sha(pathlib.Path(__file__)): raise RuntimeError('SHA del driver no coincide con preregistro')
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
    return h.hexdigest()
def mem_available_kib():
    return next(int(x.split()[1]) for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))
def gpu_state():
    q=subprocess.run(['nvidia-smi','--query-gpu=index,uuid,name,memory.used,memory.total,temperature.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True,timeout=10)
    gpus={}
    for line in q.stdout.splitlines():
        i,u,n,used,total,temp=[x.strip() for x in line.split(',')]
        gpus[int(i)]={'uuid':u,'name':n,'used_mib':int(used),'total_mib':int(total),'temperature_c':int(temp)}
    c=subprocess.run(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_gpu_memory','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=10)
    compute={0:[],1:[]}; idx_by_uuid={x['uuid']:i for i,x in gpus.items()}
    if c.returncode==0:
        for line in c.stdout.splitlines():
            z=[x.strip() for x in line.split(',')]
            if len(z)>=3 and z[1] in idx_by_uuid: compute[idx_by_uuid[z[1]]].append({'pid':int(z[0]),'used_mib':int(z[2])})
    return {'gpus':gpus,'compute':compute,'mem_available_kib':mem_available_kib()}
def inference_processes(owned_pid=None):
    names={'llama-server','llama.cpp','ninfer-serve','vllm','ollama','strata','xolotl','dsx-server','koboldcpp','lmstudio','aphrodite-engine'}
    found=[]
    for p in pathlib.Path('/proc').iterdir():
        if not p.name.isdigit() or int(p.name) in {os.getpid(),owned_pid}: continue
        try:
            comm=(p/'comm').read_text().strip().lower(); argv=[x.decode(errors='replace') for x in (p/'cmdline').read_bytes().split(b'\0') if x]
        except OSError: continue
        exe=pathlib.Path(argv[0]).name.lower() if argv else comm
        if comm in names or exe in names:
            found.append({'pid':int(p.name),'comm':comm,'argv':' '.join(argv)[:400]})
        elif exe.startswith(('python','pypy')) and any(x in ' '.join(argv).lower() for x in ('vllm.entrypoints','aphrodite','sglang.launch_server','ninfer-serve')):
            found.append({'pid':int(p.name),'comm':comm,'argv':' '.join(argv)[:400]})
    return found
def assert_infrastructure(owned_pid=None):
    check_lock(); s=gpu_state()
    if any('RTX 3090' not in s['gpus'].get(i,{}).get('name','') for i in (0,1)): raise RuntimeError('faltan RTX 3090')
    if any(s['gpus'][i]['temperature_c']>=85 for i in (0,1)): raise RuntimeError('GPU >=85C')
    if s['mem_available_kib']<32*1024*1024: raise RuntimeError('MemAvailable <32 GiB')
    topo=subprocess.run(['nvidia-smi','topo','-p2p','r'],capture_output=True,text=True,check=True,timeout=10).stdout
    if topo.count('OK')<2: raise RuntimeError('P2P no da OK en ambas direcciones')
    targets='0000:01:00.0,0000:03:00.0'
    cmdline=pathlib.Path('/proc/cmdline').read_text()
    module=pathlib.Path('/sys/module/gpu_unlock/parameters/targets').read_text().strip()
    if 'gpu_unlock.targets='+targets not in cmdline or module!=targets: raise RuntimeError('gpu_unlock no está en ambas PCI')
    active=subprocess.run(['systemctl','is-active','vram-quarantine@GPU-af6de4b3-6497-b7f8-796d-6d69cba422e6.service'],capture_output=True,text=True).stdout.strip()
    q=subprocess.run(['systemctl','show','-p','StatusText','vram-quarantine@GPU-af6de4b3-6497-b7f8-796d-6d69cba422e6.service'],capture_output=True,text=True).stdout
    if active!='active' or '1636/1636 frames held, 0 pending' not in q: raise RuntimeError('reserva VRAM ASUS no está íntegra')
    j=subprocess.run(['journalctl','-b','-u','3090-helper-verify-boot.service','--no-pager','-o','cat'],capture_output=True,text=True).stdout
    if j.rfind('PASS: reserva ASUS')<j.rfind('FAIL:'): raise RuntimeError('última verificación de boot del 3090 HELPER no pasa')
    foreign=inference_processes(owned_pid)
    if foreign: raise RuntimeError('inference server ajeno: '+json.dumps(foreign))
    for p,m in [('/media/cristian/Disco local',10_000_000_000),('/media/cristian/HDD extra',20_000_000_000),('/',2_000_000_000)]:
        if shutil_free(p)<m: raise RuntimeError('espacio debajo del gate en '+p)
    return {'timestamp_utc':utc(),'gpu':s,'p2p':'OK both directions','gpu_unlock':targets,'asus_quarantine':q.strip(),'boot_helper':'PASS','foreign_inference_servers':foreign}
def shutil_free(path): return os.statvfs(path).f_bavail*os.statvfs(path).f_frsize
def port_free():
    with socket.socket() as s: return s.connect_ex((HOST,PORT))!=0
def mincore(path):
    size=path.stat().st_size; ps=os.sysconf('SC_PAGE_SIZE'); n=(size+ps-1)//ps; vec=(ctypes.c_ubyte*n)(); fd=os.open(path,os.O_RDONLY)
    libc=ctypes.CDLL(None,use_errno=True); libc.mmap.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_long]; libc.mmap.restype=ctypes.c_void_p
    libc.mincore.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_ubyte)]; libc.mincore.restype=ctypes.c_int; libc.munmap.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
    try:
        addr=libc.mmap(None,size,0,1,fd,0)
        if addr==ctypes.c_void_p(-1).value: raise OSError(ctypes.get_errno(),os.strerror(ctypes.get_errno()))
        try:
            if libc.mincore(addr,size,vec)!=0: raise OSError(ctypes.get_errno(),os.strerror(ctypes.get_errno()))
            resident=sum(bool(x&1) for x in vec)
        finally: libc.munmap(addr,size)
    finally: os.close(fd)
    return {'resident_pages':resident,'total_pages':n,'resident_fraction':resident/n if n else 0.0}
def evict_file():
    before=mincore(MODEL); fd=os.open(MODEL,os.O_RDONLY)
    try: advice=os.posix_fadvise(fd,0,0,os.POSIX_FADV_DONTNEED)
    finally: os.close(fd)
    after=mincore(MODEL)
    return {'method':'POSIX_FADV_DONTNEED on model file only; no global cache drop','before':before,'after':after,'verified':after['resident_fraction']<=0.05,'advice_return':advice}
def server_argv():
    return [str(SERVER),str(MODEL),'--model-id','qwen3.6-35b-a3b','--devices','0,1','--tensor-parallel','--host',HOST,'--port',str(PORT),'--max-context','262144','--kv-capacity','262144','--kv-dtype','rk4v4','--gdn-state-fp16','--spec','mtp','--draft-tokens','3','--lm-head-draft','--mtp-experts-q4','--prefill-chunk','512','--no-prefix-reuse']
def start(label):
    pre=assert_infrastructure()
    stat=MODEL.stat(); integrity=json.loads((RECEIPTS/'pre-inference-gates-20261101.json').read_text())['model']
    if stat.st_size!=MODEL_BYTES or (integrity.get('mtime_ns') is not None and stat.st_mtime_ns!=integrity['mtime_ns']): raise RuntimeError('tamaño/mtime del .ninfer no coincide')
    if label=='cold' and sha(MODEL)!=MODEL_SHA: raise RuntimeError('SHA del .ninfer no coincide')
    if not SERVER.is_file() or sha(SERVER)!=SERVE_SHA: raise RuntimeError('binario ninfer-serve SHA mismatch')
    if not port_free(): raise RuntimeError(f'puerto {PORT} ocupado')
    eviction=evict_file() if label=='cold' else None
    if label=='cold' and not eviction['verified']: print('WARN: evicción del archivo no verificable; init será cold-ish/no validado',flush=True)
    log=LOGS/f'ninfer-{label}.log'; log.parent.mkdir(parents=True,exist_ok=True)
    t0=time.monotonic(); started=utc()
    with log.open('ab') as out:
        p=subprocess.Popen(server_argv(),cwd=str(SERVER.parent),stdout=out,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
    write(PIDFILE,{'pid':p.pid,'pgid':p.pid,'port':PORT,'label':label,'started_utc':started,'argv':server_argv(),'log':str(log)})
    print(json.dumps({'event':'server_started','pid':p.pid,'label':label,'file_eviction':eviction},ensure_ascii=False),flush=True)
    deadline=time.monotonic()+1800; last_report=0
    while time.monotonic()<deadline:
        assert_infrastructure(p.pid)
        if p.poll() is not None: raise RuntimeError(f'ninfer-serve terminó rc={p.returncode}; revisar {log}')
        try:
            with urllib.request.urlopen(f'http://{HOST}:{PORT}/health',timeout=3) as r:
                if r.status==200:
                    models=read_json(f'http://{HOST}:{PORT}/v1/models')
                    s=gpu_state(); apps={i:[x for x in s['compute'][i] if x['pid']==p.pid] for i in (0,1)}
                    if any(not apps[i] or apps[i][0]['used_mib']<1024 for i in (0,1)):
                        time.sleep(5); s=gpu_state(); apps={i:[x for x in s['compute'][i] if x['pid']==p.pid] for i in (0,1)}
                    if any(not apps[i] or apps[i][0]['used_mib']<1024 for i in (0,1)):
                        raise RuntimeError('el mismo PID no reserva >=1GiB en ambas RTX 3090; se detendrá perfil propio')
                    receipt={'task_id':TASK,'stage':label+'-init','status':'PASS','started_utc':started,'ready_utc':utc(),'ready_seconds':round(time.monotonic()-t0,3),'pid':p.pid,'model_id':models.get('data',[{}])[0].get('id'),'health_status':r.status,'models':models,'gpu_state':s,'server_uses_both_gpus':'PASS','file_eviction':eviction,'argv':server_argv(),'lock_token':TOKEN}
                    write(RECEIPTS/f'q173-{label}-launch.json',receipt)
                    print(json.dumps({'event':'server_ready','ready_seconds':receipt['ready_seconds'],'gpu':apps,'model':receipt['model_id'],'eviction_verified':bool(eviction and eviction['verified'])},ensure_ascii=False),flush=True)
                    return 0
        except urllib.error.HTTPError as e:
            if e.code not in (503,): raise
        except (urllib.error.URLError,TimeoutError,ConnectionError): pass
        now=time.monotonic()
        if now-last_report>=30:
            s=gpu_state(); print(json.dumps({'event':'waiting_health','seconds':round(now-t0,1),'mem_available_kib':s['mem_available_kib'],'gpu':[s['gpus'].get(i,{}).get('used_mib') for i in (0,1)]}),flush=True); last_report=now
        time.sleep(2)
    raise TimeoutError('readiness excedió 1800 s')
def stop():
    if not PIDFILE.exists(): raise RuntimeError('sin PID de servidor Q190 propio')
    data=json.loads(PIDFILE.read_text()); pid=int(data['pid']); check_lock()
    try: os.killpg(pid,signal.SIGINT)
    except ProcessLookupError: pass
    deadline=time.monotonic()+45
    while time.monotonic()<deadline:
        if not pathlib.Path(f'/proc/{pid}').exists(): break
        time.sleep(.5)
    else:
        try: os.killpg(pid,signal.SIGTERM)
        except ProcessLookupError: pass
        deadline=time.monotonic()+10
        while time.monotonic()<deadline and pathlib.Path(f'/proc/{pid}').exists(): time.sleep(.5)
    free=port_free()
    record={'task_id':TASK,'stage':'stop-owned-server','timestamp_utc':utc(),'pid':pid,'port_free':free,'gpu_state':gpu_state(),'foreign_inference_servers':inference_processes()}
    write(RECEIPTS/f'server-stop-{record["timestamp_utc"].replace(":","")}.json',record)
    if not free: raise RuntimeError('el server propio no liberó el puerto')
    print(json.dumps(record,ensure_ascii=False)); return 0
def corpus():
    if not PIDFILE.exists(): raise RuntimeError('inicia el servidor antes de tokenizar')
    pid=int(json.loads(PIDFILE.read_text())['pid']); pre=assert_infrastructure(pid)
    texts=[]; hashes=[]
    for p in sorted(SOURCE.glob('*.json')):
        raw=p.read_bytes(); hashes.append({'path':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
        obj=json.loads(raw)
        def walk(x):
            if isinstance(x,str): texts.append(x)
            elif isinstance(x,list):
                for y in x: walk(y)
            elif isinstance(x,dict):
                if 'content' in x: walk(x['content'])
                else:
                    for k in sorted(x): walk(x[k])
        walk(obj)
    seen=set(); unique=[]
    for t in texts:
        if t.strip() and t not in seen: seen.add(t); unique.append(t)
    ids=[]; token_calls=[]
    for i,t in enumerate(unique):
        resp=post_json(f'http://{HOST}:{PORT}/tokenize',{'content':t,'parse_special':False,'add_special':False},timeout=600)
        part=[int(x) for x in resp.get('tokens',[])]
        ids.extend(part); token_calls.append({'segment':i,'chars':len(t),'tokens':len(part)})
    if len(ids)<261888: raise RuntimeError(f'fixtures only tokenize to {len(ids)} (<261888); preregister more source text before continuing')
    serial=json.dumps(ids,separators=(',',':')).encode(); digest=hashlib.sha256(serial).hexdigest()
    write(TOKENS,{'task_id':TASK,'source_revision':'NInfer-all commit 8bde0c064cb6cb7f7f86710ea4a614e7a821dceb','source_fixture_hashes':hashes,'tokenizer':'embedded model tokenizer via local POST /tokenize parse_special=false add_special=false','fixture_segments':token_calls,'total_tokens':len(ids),'ids_sha256':digest,'token_ids':ids})
    rec={'task_id':TASK,'stage':'q173-corpus-tokenization','status':'PASS','timestamp_utc':utc(),'sources':hashes,'segments':len(token_calls),'token_count':len(ids),'token_ids_sha256':digest,'request_api':'/tokenize','gpu_used':False,'infrastructure_preflight':pre}
    write(RECEIPTS/'q173-token-corpus.json',rec); print(json.dumps(rec,ensure_ascii=False)); return 0
def q173(ctx,reps):
    if ctx not in CONTEXTS or reps!=(3 if ctx==8192 else 1): raise RuntimeError('context/repetitions fuera de prerregistro')
    if not PIDFILE.exists() or not TOKENS.exists(): raise RuntimeError('servidor/token corpus no preparado')
    pid=int(json.loads(PIDFILE.read_text())['pid']); pre=assert_infrastructure(pid)
    live=read_json(f'http://{HOST}:{PORT}/v1/models'); model_id=live['data'][0]['id']
    ids=json.loads(TOKENS.read_text())['token_ids'][:ctx]
    if len(ids)!=ctx: raise RuntimeError('token count incorrecto')
    partial=[]; started=utc()
    out=RUNS/f'q173-context-{ctx}.json'; RUNS.mkdir(parents=True,exist_ok=True)
    write(out,{'task_id':TASK,'phase':'q173','context_tokens':ctx,'status':'running','started_utc':started,'repetitions_expected':reps,'results':[],'preflight':pre})
    for rep in range(reps):
        assert_infrastructure(pid)
        t0=time.perf_counter_ns(); first=None; last=None; usage={}; timings={}; finishes=[]; chunk_count=0; error=None
        body={'model':model_id,'prompt':ids,'max_tokens':128,'temperature':0.6,'top_p':0.95,'top_k':20,'min_p':0.0,'repeat_penalty':1.0,'presence_penalty':0.0,'seed':42+rep,'ignore_eos':True,'cache_prompt':False,'stream':True,'stream_options':{'include_usage':True}}
        req=urllib.request.Request(f'http://{HOST}:{PORT}/v1/completions',data=json.dumps(body,separators=(',',':')).encode(),headers={'Content-Type':'application/json'},method='POST')
        try:
            with urllib.request.urlopen(req,timeout=3600) as res:
                for raw in res:
                    line=raw.decode(errors='replace').strip()
                    if not line.startswith('data:'): continue
                    val=line[5:].strip()
                    if val=='[DONE]': break
                    d=json.loads(val); chunk_count+=1
                    if isinstance(d.get('usage'),dict): usage=d['usage']
                    if isinstance(d.get('timings'),dict): timings=d['timings']
                    if d.get('error'): error=d['error']; break
                    choices=d.get('choices') or []
                    if choices:
                        ch=choices[0]
                        if ch.get('finish_reason') is not None: finishes.append(ch['finish_reason'])
                        txt=ch.get('text') or ''
                        if txt:
                            now=time.perf_counter_ns()
                            if first is None: first=now
                            last=now
        except Exception as e: error=f'{type(e).__name__}: {e}'
        elapsed=time.perf_counter_ns()-t0
        prompt_tokens=int(usage.get('prompt_tokens',timings.get('prompt_n',0)) or 0)
        completion_tokens=int(usage.get('completion_tokens',timings.get('predicted_n',0)) or 0)
        ttft=(first-t0)/1e9 if first else None
        predicted_ms=float(timings.get('predicted_ms',0) or 0)
        predicted_n=int(timings.get('predicted_n',0) or 0)
        decode=float(timings.get('predicted_per_second',0) or (predicted_n*1000/predicted_ms if predicted_ms>0 else 0))
        decode_method='NInfer predicted_per_second' if timings.get('predicted_per_second') else ('NInfer predicted_n/predicted_ms' if predicted_ms>0 else 'E2E fallback')
        if decode<=0 and first is not None and last is not None and last>first and completion_tokens>1:
            decode=(completion_tokens-1)/((last-first)/1e9)
        result={'repetition':rep+1,'prompt_tokens_actual':prompt_tokens,'completion_tokens_actual':completion_tokens,'ttft_to_first_content_s':ttft,'effective_prefill_tok_s':prompt_tokens/ttft if ttft and prompt_tokens else None,'decode_server_tok_s':decode or None,'decode_method':decode_method,'server_timings':timings,'finish_reasons':finishes,'sse_chunks':chunk_count,'request_elapsed_s':elapsed/1e9,'error':error,'valid':not error and prompt_tokens==ctx and completion_tokens==128 and ttft is not None and decode>0}
        partial.append(result)
        write(out,{'task_id':TASK,'phase':'q173','context_tokens':ctx,'status':'running','started_utc':started,'repetitions_expected':reps,'results':partial,'preflight':pre,'server_model':model_id})
        print(json.dumps({'context':ctx,'repetition':rep+1,'result':result},ensure_ascii=False),flush=True)
        if not result['valid']: raise RuntimeError(f'Q173 invalid at {ctx}: '+json.dumps(result,ensure_ascii=False))
    p=fmean(x['effective_prefill_tok_s'] for x in partial); d=fmean(x['decode_server_tok_s'] for x in partial)
    rec={'task_id':TASK,'phase':'q173','status':'complete','context_tokens':ctx,'repetitions':reps,'prompt_source':'fixed public local NInfer TTFT text fixtures, lexicographic order; embedded tokenizer token ids; raw completion; no prefix cache','prefill_effective_mean_tok_s':p,'decode_server_mean_tok_s':d,'results':partial,'finished_utc':utc(),'preflight':pre,'token_corpus_sha256':json.loads(TOKENS.read_text())['ids_sha256'],'server_model':model_id}
    write(out,rec); print(json.dumps(rec,ensure_ascii=False)); return 0
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('action',choices=['start-cold','start-hot','stop','tokenize','smoke','q173']); ap.add_argument('--context',type=int); args=ap.parse_args()
    RUNS.mkdir(parents=True,exist_ok=True); LOGS.mkdir(parents=True,exist_ok=True); RECEIPTS.mkdir(parents=True,exist_ok=True)
    check_lock()
    if args.action in ('start-cold','start-hot'): return start('cold' if args.action=='start-cold' else 'hot')
    if args.action=='stop': return stop()
    if args.action=='tokenize': return corpus()
    if args.action=='q173':
        if args.context is None: raise RuntimeError('q173 requiere --context')
        return q173(args.context,3 if args.context==8192 else 1)
    if args.action=='smoke':
        pid=int(json.loads(PIDFILE.read_text())['pid']); pre=assert_infrastructure(pid); model=read_json(f'http://{HOST}:{PORT}/v1/models')['data'][0]['id']
        ids=[int(x) for x in post_json(f'http://{HOST}:{PORT}/tokenize',{'content':'A short deterministic runtime smoke.','parse_special':False,'add_special':False})['tokens']]
        body={'model':model,'prompt':ids,'max_tokens':16,'temperature':0.6,'top_p':0.95,'top_k':20,'min_p':0.0,'repeat_penalty':1.0,'presence_penalty':0.0,'seed':42,'ignore_eos':True,'cache_prompt':False,'stream':False}
        t=time.perf_counter(); result=post_json(f'http://{HOST}:{PORT}/v1/completions',body,timeout=1800); elapsed=time.perf_counter()-t
        usage=result.get('usage',{}); timings=result.get('timings',{})
        count=int(usage.get('completion_tokens',timings.get('predicted_n',0)) or 0)
        rec={'task_id':TASK,'stage':'q173-smoke','status':'PASS' if count==16 else 'FAIL','timestamp_utc':utc(),'model_id':model,'prompt_tokens':len(ids),'completion_tokens':count,'elapsed_s':elapsed,'server_timings':timings,'preflight':pre}
        write(RECEIPTS/'q173-smoke.json',rec); print(json.dumps(rec,ensure_ascii=False)); return 0 if count==16 else 2
    raise RuntimeError('acción no implementada')
if __name__=='__main__':
    try: raise SystemExit(main())
    except Exception as e:
        print(f'FAIL: {type(e).__name__}: {e}',file=sys.stderr,flush=True); raise
