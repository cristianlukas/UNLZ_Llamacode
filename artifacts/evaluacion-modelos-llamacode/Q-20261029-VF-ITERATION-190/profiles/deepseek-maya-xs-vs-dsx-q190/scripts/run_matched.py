#!/usr/bin/env python3
from __future__ import annotations
import argparse, ctypes, datetime, hashlib, json, mmap, os, pathlib, signal, socket, statistics, subprocess, sys, time, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[6]
PROFILE = pathlib.Path(__file__).resolve().parents[1]
RECEIPTS = PROFILE / 'receipts'
PREREG = RECEIPTS / 'preregistration.json'
TOKEN = 'fa21acd2-f286-4981-9254-552a027a464f'
MODEL_ID = 'deepseek-v4.1-flash'
HOST = '127.0.0.1'
MAYA_ROOT = pathlib.Path('/media/cristian/HDD extra/LlamaCode-evals/Q189-project-maya-v1.1.37')
MAYA_RUN = MAYA_ROOT / 'run-maya-ds4.sh'
MAYA_ENGINE = MAYA_ROOT / 'build/maya-ds4'
MAYA_PACK = pathlib.Path('/media/cristian/7CFE1E0FFE1DC1F6/LlamaCode-evals/Q189/Maya-XS/maya-ds4')
MAYA_FILES = sorted(MAYA_PACK.parent.glob('DeepSeek-V4.1-Flash-1017-Maya-XS-IQ1_S-*.gguf'))
DSX_ROOT = pathlib.Path('/media/cristian/Disco local/Modelos-eval/Q-20261027-VF-ITERATION-172/DeepSeek-dsx-T16')
DSX_MODEL = DSX_ROOT / 'models/DeepSeek-V4.1-Flash-1017-dsx-t16.gguf'
DSX_RANK = DSX_ROOT / 'models/expert-rank.json'
DSX_BIN = DSX_ROOT / 'build/release/dsx-server'
TOKENIZER = pathlib.Path('/home/cristian/.cache/q173-tokenizers/deepseek-v41-flash-1017/tokenizer.json')
BENCHY = pathlib.Path('/home/cristian/.cache/q173-llama-benchy-0.4.0/bin/llama-benchy')
BENCHY_SHA = 'e8a892fe937d5ae1b6a43c31e8cb286ce4774f70396f62ab71008c9ddb0a01a1'
TOOL = pathlib.Path('/home/cristian/.cache/codex-tool-eval-bench-v2.8.0/.venv/bin/tool-eval-bench')
TOOL_SHA = '31e3c8f5fa9140738cde4e1cecc909f5335cf928a90fbdd062ec7935e0526472'
TOKENIZER_SHA = 'c90dfa01249db1be4245780a052ede752e1361c612ac6d08e2bdada7d599476b'
OUT = pathlib.Path('/media/cristian/HDD extra/LlamaCode-evals/Q190-maya-xs-vs-dsx')
HOST_FLOOR_KIB = 16 * 1024 * 1024
TIMEOUT_START = 1800
INTERVAL = 5
SERVER_EXEC_NAMES = {'llama-server', 'dsx-server', 'ninfer-serve', 'vllm', 'aphrodite-engine', 'ollama', 'maya-ds4', 'strata', 'koboldcpp', 'lmstudio', 'whisper-server'}
SERVER_PYTHON_MODULES = ('vllm.', 'aphrodite', 'exllama', 'sglang.', 'ninfer', 'dsx.')


def utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')


def write_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def sha(path: pathlib.Path) -> str:
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def check_lock() -> None:
    lock = json.loads((ROOT / 'WORK_QUEUE.lock').read_text())
    queue = (ROOT / 'WORK_QUEUE.md').read_text()
    if lock.get('token') != TOKEN or lock.get('worker') != 'Q-20261031-DEEPSEEK-MAYA-VS-DSX':
        raise RuntimeError('El lock raíz ya no pertenece a esta comparación; abortar.')
    if 'Q-20261031-DEEPSEEK-MAYA-VS-DSX | En curso' not in queue or TOKEN not in queue:
        raise RuntimeError('WORK_QUEUE ya no muestra esta tarea en curso; abortar.')


def mem_available_kib() -> int:
    for line in pathlib.Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'):
            return int(line.split()[1])
    raise RuntimeError('MemAvailable no está disponible')


def memory_psi() -> str:
    return pathlib.Path('/proc/pressure/memory').read_text().strip()


def port_free(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex((HOST, port)) != 0


def gpu_state() -> dict:
    g = subprocess.run(['nvidia-smi', '--query-gpu=index,uuid,name,memory.used,memory.total,utilization.gpu', '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=10, check=True)
    apps = subprocess.run(['nvidia-smi', '--query-compute-apps=pid,gpu_uuid,used_gpu_memory', '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=10, check=True)
    gpus = {}
    for line in g.stdout.splitlines():
        vals=[x.strip() for x in line.split(',')]
        if len(vals)==6:
            idx=int(vals[0]); gpus[idx]={'uuid':vals[1],'name':vals[2],'memory_used_mib':int(vals[3]),'memory_total_mib':int(vals[4]),'utilization_percent':int(vals[5]),'compute':[]}
    for line in apps.stdout.splitlines():
        vals=[x.strip() for x in line.split(',')]
        if len(vals)==3:
            pid,uuid,used=int(vals[0]),vals[1],int(vals[2])
            for item in gpus.values():
                if item['uuid']==uuid: item['compute'].append({'pid':pid,'used_mib':used})
    return gpus


def proc_info(pid: int) -> dict | None:
    try:
        comm=pathlib.Path(f'/proc/{pid}/comm').read_text().strip()
        args=pathlib.Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace').strip()
        status=pathlib.Path(f'/proc/{pid}/status').read_text()
        ppid=next(int(x.split()[1]) for x in status.splitlines() if x.startswith('PPid:'))
        return {'pid':pid,'ppid':ppid,'comm':comm,'cmdline':args}
    except (OSError,StopIteration,ValueError):
        return None


def inference_processes() -> list[dict]:
    found=[]
    for p in pathlib.Path('/proc').iterdir():
        if not p.name.isdigit(): continue
        info=proc_info(int(p.name))
        if not info: continue
        try:
            exe=pathlib.Path(os.readlink(f'/proc/{info["pid"]}/exe')).name.lower()
            argv=[x.decode(errors='replace') for x in pathlib.Path(f'/proc/{info["pid"]}/cmdline').read_bytes().split(b'\0') if x]
        except OSError:
            continue
        server=exe in SERVER_EXEC_NAMES or info['comm'].lower() in SERVER_EXEC_NAMES
        if exe.startswith(('python','pypy')):
            for i,arg in enumerate(argv[:-1]):
                if arg in ('-m','--module') and argv[i+1].lower().startswith(SERVER_PYTHON_MODULES): server=True
            if any(pathlib.Path(arg).name.lower()=='maya.py' for arg in argv[1:]): server=True
        if server:
            info['executable']=exe
            found.append(info)
    return found


def unit_pids(unit: str) -> set[int]:
    p=subprocess.run(['systemctl','--user','show',unit,'-p','MainPID','--value'],capture_output=True,text=True)
    try: main=int(p.stdout.strip())
    except ValueError: main=0
    if not main: return set()
    allp=[]
    for ent in pathlib.Path('/proc').iterdir():
        if ent.name.isdigit():
            info=proc_info(int(ent.name))
            if info: allp.append(info)
    kids={x['ppid']:[] for x in allp}
    for x in allp: kids.setdefault(x['ppid'],[]).append(x['pid'])
    result={main}; todo=[main]
    while todo:
        parent=todo.pop()
        for child in kids.get(parent,[]):
            if child not in result: result.add(child); todo.append(child)
    return result


def foreign_inference(allowed: set[int]) -> list[dict]:
    return [p for p in inference_processes() if p['pid'] not in allowed]


def api_models(port: int) -> dict | None:
    try:
        with urllib.request.urlopen(f'http://{HOST}:{port}/v1/models', timeout=4) as r:
            data=json.loads(r.read())
            return data if r.status==200 else None
    except Exception:
        return None


def service_name(model: str, stage: str) -> str:
    return f'q190-{model}-{stage}'


def service_port(model: str) -> int:
    return 18190 if model=='maya' else 18192


def files_for(model: str) -> list[pathlib.Path]:
    return MAYA_FILES if model=='maya' else [DSX_MODEL]


def file_residency(path: pathlib.Path) -> dict:
    size=path.stat().st_size
    pagesize=os.sysconf('SC_PAGE_SIZE')
    page_count=(size+pagesize-1)//pagesize
    vec=(ctypes.c_ubyte*page_count)()
    fd=os.open(path,os.O_RDONLY)
    libc=ctypes.CDLL(None,use_errno=True)
    libc.mmap.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_long]
    libc.mmap.restype=ctypes.c_void_p
    libc.mincore.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_ubyte)]
    libc.mincore.restype=ctypes.c_int
    libc.munmap.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
    addr=libc.mmap(None,size,mmap.PROT_READ,mmap.MAP_SHARED,fd,0)
    failed=ctypes.c_void_p(-1).value
    if addr==failed:
        err=ctypes.get_errno(); os.close(fd); raise OSError(err,os.strerror(err),str(path))
    try:
        rc=libc.mincore(addr,size,vec)
        if rc!=0:
            err=ctypes.get_errno(); raise OSError(err,os.strerror(err),str(path))
        resident=sum(1 for b in vec if b&1)
        return {'path':str(path),'bytes':size,'pages':page_count,'resident_pages':resident,'resident_percent':round(resident*100/page_count,4)}
    finally:
        libc.munmap(addr,size); os.close(fd)


def evict_model_cache(model: str) -> dict:
    check_lock()
    details=[]
    for path in files_for(model):
        if not path.exists(): raise FileNotFoundError(path)
        before=file_residency(path)
        fd=os.open(path,os.O_RDONLY)
        try:
            rc=os.posix_fadvise(fd,0,0,os.POSIX_FADV_DONTNEED)
        finally:
            os.close(fd)
        after=file_residency(path)
        details.append({'before':before,'posix_fadvise_return':rc,'after':after})
    total=sum(x['after']['pages'] for x in details)
    resident=sum(x['after']['resident_pages'] for x in details)
    percent=round(resident*100/total,4) if total else 100
    return {'method':'file-scoped POSIX_FADV_DONTNEED; verified with mincore for each model shard','files':details,'aggregate_resident_percent':percent,'coldish_verified':percent<10.0 and all(x['posix_fadvise_return']==0 for x in details)}


def verify_assets(model: str) -> dict:
    p=json.loads(PREREG.read_text())
    if sha(BENCHY)!=BENCHY_SHA or sha(TOKENIZER)!=TOKENIZER_SHA:
        raise RuntimeError('SHA mismatch de llama-benchy/tokenizer')
    if not TOOL.is_file() or sha(TOOL)!=TOOL_SHA: raise RuntimeError('SHA mismatch de Tool-Eval')
    if model=='maya':
        if not MAYA_RUN.is_file() or not MAYA_ENGINE.is_file(): raise RuntimeError('Falta runner/engine Project Maya')
        if sha(MAYA_ENGINE)!=p['models'][0]['engine_sha256']: raise RuntimeError('SHA mismatch de engine Maya')
        rec=json.loads((ROOT/'artifacts/evaluacion-modelos-llamacode/Q-20261029-VF-ITERATION-189/receipts/download-complete.json').read_text())
        expected={x['name']:x for x in rec['verifiedShards']}
        actual=[]
        for f in MAYA_FILES:
            key=f.name
            st=f.stat()
            if key not in expected or st.st_size!=expected[key]['bytes']: raise RuntimeError(f'Tamaño/shard no coincide con recibo Q189: {f}')
            actual.append({'path':str(f),'bytes':st.st_size,'sha256_pinned':expected[key]['sha256'],'sha_reverified':False,'symlink_target':str(f.resolve())})
        if len(actual)!=5: raise RuntimeError(f'Se esperaban cinco shards Maya, hay {len(actual)}')
        cfgs=p['configs']
        for key in ('q172-131k','q173-262k'):
            c=pathlib.Path(cfgs[key]['path'])
            if sha(c)!=cfgs[key]['sha256']: raise RuntimeError(f'SHA mismatch config {key}')
        return {'model':model,'verified_engine_sha256':sha(MAYA_ENGINE),'shards':actual,'prior_pinned_shard_receipt':str(rec['task'])}
    model_size=p['models'][1]['model_bytes']
    if DSX_MODEL.stat().st_size!=model_size or DSX_RANK.stat().st_size!=251479 or not DSX_BIN.is_file(): raise RuntimeError('Falta GGUF/rank/runtime DSX o tamaño distinto')
    if sha(DSX_BIN)!=p['models'][1]['engine_sha256']: raise RuntimeError('SHA mismatch de dsx-server')
    return {'model':model,'model_path':str(DSX_MODEL),'bytes':DSX_MODEL.stat().st_size,'pinned_sha256':p['models'][1]['model_sha256'],'sha_reverified':False,'rank_bytes':DSX_RANK.stat().st_size,'engine_sha256':sha(DSX_BIN)}


def preflight(model: str) -> dict:
    check_lock()
    assets=verify_assets(model)
    if mem_available_kib()<HOST_FLOOR_KIB: raise RuntimeError('MemAvailable <16 GiB')
    gpus=gpu_state()
    if any(i not in gpus or 'RTX 3090' not in gpus[i]['name'] for i in (0,1)): raise RuntimeError('No se ven ambas RTX 3090')
    if inference_processes(): raise RuntimeError('Inference server activo antes del turno: '+json.dumps(inference_processes(),ensure_ascii=False))
    if not port_free(service_port(model)): raise RuntimeError(f'Puerto {service_port(model)} ocupado')
    disk=pathlib.Path(OUT)
    disk.mkdir(parents=True,exist_ok=True)
    st=os.statvfs(disk)
    free=st.f_bavail*st.f_frsize
    if free<3_000_000_000: raise RuntimeError('Menos de 3 GB libres en el volumen de resultados')
    return {'timestamp_utc':utc(),'model':model,'assets':assets,'mem_available_kib':mem_available_kib(),'memory_psi':memory_psi(),'gpus':gpus,'inference_servers':[],'port_free':True,'result_volume_free_bytes':free,'swap':subprocess.run(['swapon','--show','--bytes','--noheadings'],capture_output=True,text=True).stdout.strip()}


def launch_argv(model: str, stage: str, unit: str) -> list[str]:
    port=service_port(model)
    common=['systemd-run','--user',f'--unit={unit}','--property=ManagedOOMPreference=avoid','--property=Restart=no','--property=KillMode=control-group']
    if model=='maya':
        p=json.loads(PREREG.read_text())
        key='q172-131k' if stage=='q172' else 'q173-262k'
        cfg=p['configs'][key]['path']
        return common+[f'--property=WorkingDirectory={MAYA_ROOT}','--setenv=CUDA_VISIBLE_DEVICES=0,1',str(MAYA_RUN),'--config',cfg,'--port',str(port),'--plain']
    ctx='131072' if stage=='q172' else '262144'
    arena='90' if stage=='q172' else '70'
    return common+[f'--property=WorkingDirectory={DSX_ROOT / "build/release"}','/usr/bin/env','DSX_GPUS=0,1','DSX_DEFER=off','DSX_ENGRAM_FP8=off',str(DSX_BIN),'--model',str(DSX_MODEL),'--rank',str(DSX_RANK),'--ctx',ctx,'--arena-gb',arena,'--no-vision','--host',HOST,'--port',str(port),'--model-name',MODEL_ID]


def start_server(model: str, stage: str) -> dict:
    check_lock()
    pf=preflight(model)
    port=service_port(model)
    unit=service_name(model,stage)
    if stage.endswith('-cold'):
        cache=evict_model_cache(model)
    else:
        cache={'method':'no eviction; cache left warm','coldish_verified':False,'files':[file_residency(x) for x in files_for(model)]}
    if not port_free(port): raise RuntimeError(f'Puerto {port} ocupado antes de start')
    argv=launch_argv(model,stage,unit)
    started=utc(); t0=time.monotonic()
    launch=subprocess.run(argv,capture_output=True,text=True,timeout=30)
    rec={'model':model,'stage':stage,'unit':unit,'port':port,'start_utc':started,'command':argv,'launcher_rc':launch.returncode,'launcher_stdout':launch.stdout,'launcher_stderr':launch.stderr,'baseline':pf,'file_cache':cache,'status':'starting','samples':[]}
    path=RECEIPTS/f'startup-{model}-{stage}.json'
    if launch.returncode!=0:
        rec.update({'status':'launch_failed','finish_utc':utc()}); write_json(path,rec); raise RuntimeError(f'systemd-run rc={launch.returncode}: {launch.stderr[-1000:]}')
    low=0; deadline=time.monotonic()+TIMEOUT_START
    while time.monotonic()<deadline:
        check_lock()
        avail=mem_available_kib(); low=low+1 if avail<HOST_FLOOR_KIB else 0
        models=api_models(port)
        pids=unit_pids(unit)
        foreign=foreign_inference(pids)
        gpus=gpu_state()
        on_gpu={i:[x['pid'] for x in gpus[i]['compute'] if x['pid'] in pids] for i in (0,1)}
        sample={'at_utc':utc(),'elapsed_seconds':round(time.monotonic()-t0,2),'mem_available_kib':avail,'memory_psi':memory_psi(),'unit_active':subprocess.run(['systemctl','--user','is-active',unit],capture_output=True,text=True).stdout.strip(),'api_models':models,'service_pids':sorted(pids),'service_compute_pids_by_gpu':on_gpu,'foreign_servers':foreign}
        rec['samples'].append(sample)
        if low>=2:
            subprocess.run(['systemctl','--user','stop',unit],capture_output=True,text=True)
            rec.update({'status':'stopped_memory_floor','finish_utc':utc()}); write_json(path,rec); raise RuntimeError('MemAvailable debajo de 16 GiB en dos muestras; detenido sólo servicio propio')
        if foreign:
            subprocess.run(['systemctl','--user','stop',unit],capture_output=True,text=True)
            rec.update({'status':'stopped_foreign_inference','finish_utc':utc()}); write_json(path,rec); raise RuntimeError('Apareció inferencia ajena; se detuvo sólo el servicio propio')
        if models and any(x.get('id')==MODEL_ID for x in models.get('data',[]) if isinstance(x,dict)):
            if all(on_gpu[i] for i in (0,1)):
                rec.update({'status':'ready','ready_utc':utc(),'seconds_to_ready':round(time.monotonic()-t0,3),'served_models':models,'dual_gpu_gate':'same evaluation service has compute PID(s) on both RTX 3090','finish_utc':utc()})
                write_json(path,rec)
                write_json(RECEIPTS/'active-service.json',{'model':model,'stage':stage,'unit':unit,'port':port,'started_utc':started,'ready_utc':rec['ready_utc'],'lock_token':TOKEN})
                return rec
        if subprocess.run(['systemctl','--user','is-active',unit],capture_output=True,text=True).stdout.strip() in ('failed','inactive'):
            rec.update({'status':'service_exited','finish_utc':utc(),'journal':subprocess.run(['journalctl','--user','-u',unit,'-n','120','--no-pager'],capture_output=True,text=True).stdout})
            write_json(path,rec); raise RuntimeError('El servicio salió antes de readiness; ver receipt/journal')
        time.sleep(INTERVAL)
    subprocess.run(['systemctl','--user','stop',unit],capture_output=True,text=True)
    rec.update({'status':'startup_timeout','finish_utc':utc(),'journal':subprocess.run(['journalctl','--user','-u',unit,'-n','120','--no-pager'],capture_output=True,text=True).stdout})
    write_json(path,rec)
    raise TimeoutError(f'{model} no alcanzó /v1/models + dual-GPU en {TIMEOUT_START}s')


def active_service(model: str) -> dict:
    check_lock()
    p=RECEIPTS/'active-service.json'
    if not p.exists(): raise RuntimeError('No hay servicio propio activo registrado')
    state=json.loads(p.read_text())
    if state.get('model')!=model or state.get('lock_token')!=TOKEN: raise RuntimeError('El servicio activo no coincide con el modelo o lock')
    if subprocess.run(['systemctl','--user','is-active',state['unit']],capture_output=True,text=True).stdout.strip()!='active': raise RuntimeError('Servicio propio inactivo')
    return state


def monitor_state(model: str, state: dict) -> dict:
    check_lock()
    avail=mem_available_kib()
    pids=unit_pids(state['unit'])
    foreign=foreign_inference(pids)
    gpus=gpu_state()
    on_gpu={i:[x['pid'] for x in gpus[i]['compute'] if x['pid'] in pids] for i in (0,1)}
    if foreign: raise RuntimeError('Inference ajeno detectado: '+json.dumps(foreign,ensure_ascii=False))
    if not all(on_gpu[i] for i in (0,1)): raise RuntimeError('El servicio propio dejó de usar ambas RTX 3090')
    if not api_models(state['port']): raise RuntimeError('API propia dejó de responder')
    return {'at_utc':utc(),'model':model,'mem_available_kib':avail,'memory_psi':memory_psi(),'service_pids':sorted(pids),'service_compute_pids_by_gpu':on_gpu,'foreign_servers':foreign}


def effective_prefill_from_events(events_path: pathlib.Path, expected_runs: int) -> dict:
    """Use actual prompt tokens / first content-token elapsed time.

    llama-benchy 0.4.0's default pp_throughput uses est_ppt derived from the
    first SSE chunk. Some compatible servers send an empty/role-only chunk
    before prefill finishes, so that estimate can be spuriously near zero.
    The progress stream distinguishes that event from first content token.
    """
    starts: dict[int, float] = {}
    first_tokens: dict[int, float] = {}
    endings: dict[int, dict] = {}
    for line in events_path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        event=json.loads(line)
        kind=event.get('type'); request_id=event.get('request_id')
        if request_id is None:
            continue
        request_id=int(request_id)
        if kind=='request_start':
            starts[request_id]=float(event['ts'])
        elif kind=='request_first_token':
            first_tokens[request_id]=float(event['ttft_s'])
        elif kind=='request_end':
            endings[request_id]=event
    ids=sorted(endings)
    if len(ids)!=expected_runs or any(i not in starts or i not in first_tokens for i in ids):
        raise RuntimeError(f'No se puede calcular prefill E2E: runs incompletos; starts={sorted(starts)}, first_tokens={sorted(first_tokens)}, ends={ids}')
    samples=[]
    for request_id in ids:
        end=endings[request_id]
        elapsed_s=first_tokens[request_id]
        prompt_tokens=int(end.get('prompt_tokens') or 0)
        if end.get('error') or elapsed_s<=0 or prompt_tokens<=0:
            raise RuntimeError(f'Solicitud Q173 inválida para prefill: {json.dumps(end,ensure_ascii=False)}')
        samples.append({'request_id':request_id,'prompt_tokens':prompt_tokens,'first_content_token_elapsed_s':elapsed_s,'effective_prefill_tps_e2e':prompt_tokens/elapsed_s})
    rates=[x['effective_prefill_tps_e2e'] for x in samples]
    return {'method':'actual prompt_tokens / request_start-to-first-content-token elapsed seconds; end-to-end effective prefill, includes client/network overhead','n':len(samples),'per_run':samples,'mean_tps':statistics.fmean(rates),'sample_stdev_tps':statistics.stdev(rates) if len(rates)>1 else 0.0}


def run_bench(model: str, phase: str, pp: int|None, runs: int|None, seed: int|None) -> dict:
    state=active_service(model)
    model_dir=OUT/'runs'/phase/model
    logdir=OUT/'logs'/phase/model
    model_dir.mkdir(parents=True,exist_ok=True); logdir.mkdir(parents=True,exist_ok=True)
    tag=f'context-{pp}-runs-{runs}' if phase=='q173' else f'seed-{seed}'
    result=model_dir/f'{tag}.json'; events=model_dir/f'{tag}-events.jsonl'; log=logdir/f'{tag}.log'
    if result.exists() or events.exists() or log.exists(): raise FileExistsError(f'No se sobrescriben corridas previas: {tag}')
    if phase=='q173':
        argv=[str(BENCHY),'--base-url',f'http://{HOST}:{state["port"]}/v1','--model',MODEL_ID,'--tokenizer',str(TOKENIZER),'--pp',str(pp),'--tg','128','--exact-tg','--depth','0','--concurrency','1','--runs',str(runs),'--latency-mode','generation','--no-cache','--skip-coherence','--no-adapt-prompt','--extra-body','temperature=0.6,top_p=0.95,top_k=20,min_p=0.0,repetition_penalty=1.0,presence_penalty=0.0,seed=42','--format','json','--exit-on-first-fail','--save-result',str(result),'--emit-progress',str(events)]
    else:
        argv=[str(TOOL),'run','--model',MODEL_ID,'--backend','openai','--base-url',f'http://{HOST}:{state["port"]}/v1','--format','openai','--temperature','0.6','--top-p','0.95','--top-k','20','--min-p','0.0','--repeat-penalty','1.0','--seed',str(seed),'--backend-kwargs',json.dumps({'reasoning_effort':'medium','presence_penalty':0.0}),'--variant-seed','20261010','--hardmode','--scenarios',*[f'TC-{i}' for i in range(70,98)],'--timeout','120','--max-turns','8','--trials','1','--parallel','1','--no-warmup','--fail-on-safety','--label',f'Q190-{model}-matched-Q172-seed{seed}','--redact-url','--output-dir',str(model_dir/'reports'),'--json-file',str(result)]
    write_json(model_dir/f'{tag}.argv.json',{'argv':argv,'created_utc':utc(),'lock_token':TOKEN})
    started=utc(); t0=time.monotonic(); snapshots=[]
    env={**os.environ,'CUDA_VISIBLE_DEVICES':''}
    with log.open('w',encoding='utf-8') as stream:
        proc=subprocess.Popen(argv,stdout=stream,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        low=0
        try:
            while proc.poll() is None:
                snap=monitor_state(model,state); snapshots.append(snap)
                low=low+1 if snap['mem_available_kib']<HOST_FLOOR_KIB else 0
                if low>=2: raise RuntimeError('MemAvailable <16 GiB dos muestras seguidas')
                time.sleep(INTERVAL)
        except Exception:
            if proc.poll() is None:
                try: os.killpg(proc.pid,signal.SIGTERM); proc.wait(timeout=15)
                except Exception:
                    try: os.killpg(proc.pid,signal.SIGKILL)
                    except ProcessLookupError: pass
            subprocess.run(['systemctl','--user','stop',state['unit']],capture_output=True,text=True)
            raise
        rc=proc.returncode
    write_json(model_dir/f'{tag}-monitor.json',{'samples':snapshots,'started_utc':started,'finish_utc':utc()})
    if not result.is_file(): raise RuntimeError(f'El cliente terminó rc={rc} sin guardar resultado JSON; revisar {log}')
    data=json.loads(result.read_text())
    valid_rc=(0,2) if phase=='q172' else (0,)
    if rc not in valid_rc: raise RuntimeError(f'Cliente terminó rc={rc}; conservar resultado/log y no inferir validez automática')
    if phase=='q173':
        benches=data.get('benchmarks',[])
        summary=[]
        for b in benches:
            if not isinstance(b,dict): continue
            item={k:b.get(k) for k in ('prompt_size','response_size','pp_throughput','tg_throughput','e2e_ttft','latency_mode')}
            item['effective_prefill_tps_e2e']=effective_prefill_from_events(events,runs)
            item['raw_pp_throughput_status']='diagnostic only; exclude from decisions if first SSE response precedes first content-bearing token'
            summary.append(item)
    else:
        summary={'status':data.get('status'),'final_score':data.get('final_score',data.get('scores',{}).get('final_score')),'total_scenarios':data.get('total_scenarios'),'safety_warnings':data.get('safety_warnings',data.get('safety_gate',{}).get('warnings',[])),'critical_failures':data.get('critical_failures')}
    receipt={'task':'Q-20261031-DEEPSEEK-MAYA-VS-DSX','model':model,'phase':phase,'context_tokens':pp if phase=='q173' else 131072,'runs':runs if phase=='q173' else 1,'seed':seed if phase=='q172' else 42,'started_utc':started,'finished_utc':utc(),'elapsed_seconds':round(time.monotonic()-t0,3),'exit_code':rc,'argv':argv,'result_path':str(result),'event_path':str(events) if phase=='q173' else None,'log_path':str(log),'summary':summary,'lock_token':TOKEN}
    receipt_path=RECEIPTS/f'{phase}-{model}-{tag}.json'
    write_json(receipt_path,receipt)
    print(json.dumps(receipt,ensure_ascii=False,indent=2))
    return receipt


def stop_server(model: str) -> dict:
    check_lock()
    state=active_service(model)
    start=utc()
    p=subprocess.run(['systemctl','--user','stop',state['unit']],capture_output=True,text=True,timeout=120)
    deadline=time.monotonic()+30
    while time.monotonic()<deadline and not port_free(state['port']): time.sleep(0.5)
    remaining=foreign_inference(set())
    owned=[x for x in remaining if ('q190-' in x['cmdline'] or 'Q190-maya-xs-vs-dsx' in x['cmdline'])]
    if owned: raise RuntimeError('Quedó proceso propio tras stop: '+json.dumps(owned))
    free=port_free(state['port'])
    rec={'model':model,'unit':state['unit'],'stop_started_utc':start,'finished_utc':utc(),'systemctl_rc':p.returncode,'systemctl_stderr':p.stderr,'port_free':free,'remaining_inference_servers':remaining,'mem_available_kib':mem_available_kib(),'gpus':gpu_state(),'gui_preserved':'Artcraft GUI intentionally untouched'}
    write_json(RECEIPTS/f'stop-{model}-{state["stage"]}.json',rec)
    (RECEIPTS/'active-service.json').unlink(missing_ok=True)
    if p.returncode!=0 or not free or remaining: raise RuntimeError('Postflight de stop no pasó: '+json.dumps(rec,ensure_ascii=False))
    print(json.dumps(rec,ensure_ascii=False,indent=2)); return rec


def postflight() -> dict:
    check_lock()
    servers=inference_processes()
    state={'at_utc':utc(),'inference_servers':servers,'ports':{'maya_18190_free':port_free(18190),'dsx_18192_free':port_free(18192)},'mem_available_kib':mem_available_kib(),'memory_psi':memory_psi(),'gpus':gpu_state()}
    if servers or not all(state['ports'].values()): raise RuntimeError('Quedaron servicios o puertos de evaluación activos: '+json.dumps(state,ensure_ascii=False))
    write_json(RECEIPTS/'postflight.json',state)
    print(json.dumps(state,ensure_ascii=False,indent=2)); return state


def main() -> int:
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest='cmd',required=True)
    pf=sub.add_parser('preflight'); pf.add_argument('--model',choices=['maya','dsx'],required=True)
    st=sub.add_parser('start'); st.add_argument('--model',choices=['maya','dsx'],required=True); st.add_argument('--stage',choices=['q173-cold','q173-hot','q172'],required=True)
    bn=sub.add_parser('bench'); bn.add_argument('--model',choices=['maya','dsx'],required=True); bn.add_argument('--phase',choices=['q173','q172'],required=True); bn.add_argument('--pp',type=int); bn.add_argument('--runs',type=int); bn.add_argument('--seed',type=int)
    sp=sub.add_parser('stop'); sp.add_argument('--model',choices=['maya','dsx'],required=True)
    sub.add_parser('postflight')
    a=ap.parse_args()
    try:
        check_lock()
        if a.cmd=='preflight': print(json.dumps(preflight(a.model),ensure_ascii=False,indent=2))
        elif a.cmd=='start': print(json.dumps(start_server(a.model,a.stage),ensure_ascii=False,indent=2))
        elif a.cmd=='bench':
            if a.phase=='q173' and (not a.pp or not a.runs): ap.error('Q173 requiere --pp y --runs')
            if a.phase=='q172' and not a.seed: ap.error('Q172 requiere --seed')
            run_bench(a.model,a.phase,a.pp,a.runs,a.seed)
        elif a.cmd=='stop': stop_server(a.model)
        elif a.cmd=='postflight': postflight()
    except Exception as e:
        print(f'ERROR: {type(e).__name__}: {e}',file=sys.stderr)
        return 1
    return 0

if __name__=='__main__': raise SystemExit(main())
