#!/usr/bin/env python3
"""Detached Q237: three-repeat exact-token 8K Q173 point on Tandem SM86."""
import hashlib, json, os, pathlib, re, shutil, signal, subprocess, threading, time
from datetime import datetime, timezone
from urllib.request import urlopen
from validate_q173_progress import validate_progress_file

ROOT=pathlib.Path('/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode')
BASE=ROOT/'artifacts/evaluacion-modelos-llamacode/Q-20261103-VF-RESUME-202'
PROFILE=BASE/'profiles/q237-qwen38-tandem-q173-8k-exact'
MODEL=pathlib.Path('/media/cristian/Disco local/Models/llamacpp/Qwen3.8-27B-GGUF/Qwen3.8-27B-UD-Q4_K_XL.gguf')
SERVER=pathlib.Path('/home/cristian/.cache/llamacode-evaluations/Q210-tandem-sm86-20261115/llama.cpp/build/bin/llama-server')
PYTHON=pathlib.Path('/home/cristian/.cache/q173-llama-benchy-0.4.0/bin/python')
CLIENT=BASE/'profiles/qwen38-megakernel-v2026.11.01/scripts/run_seeded_benchy.py'
TOKENIZER=pathlib.Path('/media/cristian/HDD extra/Modelos-eval/Q208-UD31-Qwen38/tokenizer')
PORT=18776
UUIDS={'GPU-af6de4b3-6497-b7f8-796d-6d69cba422e6','GPU-5b9f385f-6a8e-b802-f69c-e62a71c91049'}
EXPECTED_MODEL_SHA='3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e'
EXPECTED_SERVER_SHA='31de89f011944d9f88d7f8fd188df04d6d1c93db5faad1a697820ad36c0eae96'
OUT=PROFILE/'runs/q173-8k-exact-tandem.json'; PROGRESS=PROFILE/'runs/q173-8k-exact-tandem-progress.jsonl'
LOG=PROFILE/'logs/server.log'; CLIENTLOG=PROFILE/'logs/client.log'; RECEIPT=PROFILE/'receipts/q237-result.json'

def utc(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def run(a,timeout=20): return subprocess.run(a,capture_output=True,text=True,timeout=timeout,check=False)
def atomic(path,obj):
 p=path.with_suffix(path.suffix+'.tmp'); p.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n'); p.replace(path)
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
 return h.hexdigest()
def port_free():
 x=run(['ss','-H','-ltn',f'sport = :{PORT}']); return x.returncode==0 and not x.stdout.strip(),x.stdout.strip()
def mem_avail():
 for l in pathlib.Path('/proc/meminfo').read_text().splitlines():
  if l.startswith('MemAvailable:'): return int(l.split()[1])*1024
 return 0
def psi_avg10():
 d={}
 for l in pathlib.Path('/proc/pressure/memory').read_text().splitlines():
  p=l.split(); d[p[0]]=dict(kv.split('=',1) for kv in p[1:])
 return max(float(d[k]['avg10']) for k in ('some','full'))
def main():
 for p in (PROFILE/'runs',PROFILE/'logs',PROFILE/'receipts'): p.mkdir(parents=True,exist_ok=True)
 t0=time.time(); server=None; client=None; logf=None; stop=threading.Event(); monitor=None
 r={'id':'Q237-TANDEM-QWEN38-Q173-8K-EXACT-01','status':'RUNNING','started_utc':utc(),'worker_pid':os.getpid(),'profile':'Qwen3.8-27B UD-Q4_K_XL; Tandem CUDA SM86; dual RTX3090 layer split 1:1','scope':'Q173 throughput only; 8192 server prompt tokens x 3 sequential runs, 128 output; no Q172/quality/adoption claim'}
 try:
  modelsha=sha(MODEL); serversha=sha(SERVER)
  gpu=run(['nvidia-smi','--query-gpu=index,uuid,temperature.gpu,memory.used,utilization.gpu','--format=csv,noheader']).stdout.strip()
  compute=run(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader,nounits']).stdout.strip()
  pmon=run(['nvidia-smi','pmon','-c','1','-s','um']).stdout.strip()
  procs=[]
  for d in pathlib.Path('/proc').iterdir():
   if d.name.isdigit() and int(d.name)!=os.getpid():
    try: c=(d/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
    except OSError: continue
    if re.search(r'(^|/)(llama-server|strata-server|ninfer|vllm|ollama)(\s|$)',c,re.I): procs.append({'pid':int(d.name),'cmd':c[:200]})
  qsvc=run(['systemctl','show','vram-quarantine@GPU-af6de4b3-6497-b7f8-796d-6d69cba422e6.service','-p','ActiveState','-p','Result','--no-pager']).stdout
  helper=run(['systemctl','show','3090-helper-verify-boot.service','-p','Result','-p','ExecMainStatus','--no-pager']).stdout
  helperlog=run(['journalctl','-u','3090-helper-verify-boot.service','-b','-n','8','--no-pager']).stdout
  p2pr=run(['nvidia-smi','topo','-p2p','r']).stdout; p2pw=run(['nvidia-smi','topo','-p2p','w']).stdout
  cmdline=pathlib.Path('/proc/cmdline').read_text().strip()
  unlock=bool(re.search(r'^gpu_unlock\s',run(['lsmod']).stdout,re.M))
  pfree,pl=port_free(); diskfree=shutil.disk_usage(PROFILE).free
  temps=[int(x.strip()) for x in run(['nvidia-smi','--query-gpu=temperature.gpu','--format=csv,noheader,nounits']).stdout.splitlines() if x.strip().isdigit()]
  r['preflight']={'gpu':gpu,'compute_apps':compute,'pmon':pmon,'inference_processes':procs,'memavailable_bytes':mem_avail(),'memory_psi_avg10':psi_avg10(),'gpu_temps_c':temps,'port_free':pfree,'port_state':pl,'output_free_bytes':diskfree,'model_sha256':modelsha,'server_sha256':serversha,'quarantine':qsvc.strip(),'helper':helper.strip(),'helper_log':helperlog.strip(),'p2p_read':p2pr.strip(),'p2p_write':p2pw.strip(),'gpu_unlock_loaded':unlock,'kernel_cmdline':cmdline}
  reasons=[]
  if modelsha!=EXPECTED_MODEL_SHA: reasons.append('model fingerprint mismatch')
  if serversha!=EXPECTED_SERVER_SHA: reasons.append('Tandem binary fingerprint mismatch')
  if compute.strip() or procs: reasons.append('inference/compute process already active')
  if not pfree: reasons.append('port occupied')
  if mem_avail()<32*1024**3: reasons.append('MemAvailable below 32 GiB')
  if psi_avg10()>=1.0: reasons.append('memory PSI avg10 >= 1%')
  if not temps or max(temps)>83: reasons.append('GPU temperature gate failed')
  if diskfree<5*1024**3: reasons.append('less than 5 GiB output space')
  if 'ActiveState=active' not in qsvc or 'Result=success' not in qsvc: reasons.append('ASUS VRAM quarantine inactive')
  if 'Result=success' not in helper or 'ExecMainStatus=0' not in helper or 'PASS: reserva ASUS, P2P bidireccional y gpu-unlock en ambas RTX 3090.' not in helperlog: reasons.append('3090 helper boot verification missing')
  if p2pr.count('OK')<2 or p2pw.count('OK')<2: reasons.append('P2P gate failed')
  if not unlock or 'gpu_unlock.targets=0000:01:00.0,0000:03:00.0' not in cmdline: reasons.append('gpu_unlock not configured for both GPUs')
  if reasons: raise RuntimeError('preflight blocked: '+'; '.join(reasons))
  env=os.environ.copy(); env['CUDA_DEVICE_ORDER']='PCI_BUS_ID'
  argv=[str(SERVER),'--model',str(MODEL),'--host','127.0.0.1','--port',str(PORT),'--ctx-size','8320','--parallel','1','--device','CUDA0,CUDA1','--split-mode','layer','--tensor-split','1,1','--gpu-layers','all','--fit','off','--flash-attn','on','--cache-type-k','q8_0','--cache-type-v','q8_0','--batch-size','512','--ubatch-size','64','--no-context-shift','--metrics','--no-warmup','--jinja','--chat-template-kwargs','{"enable_thinking":false}','--reasoning','off','--predict','4096','--temp','0.6','--top-p','0.95','--top-k','20','--min-p','0.0','--repeat-penalty','1.0','--presence-penalty','0.0']
  r['server_argv']=argv; logf=LOG.open('wb'); server=subprocess.Popen(argv,stdout=logf,stderr=subprocess.STDOUT,env=env,start_new_session=True); r['server_pid']=server.pid; atomic(RECEIPT,r)
  ready=None; deadline=time.monotonic()+600; last=''
  while time.monotonic()<deadline:
   if server.poll() is not None: raise RuntimeError(f'server exited before readiness rc={server.returncode}')
   try:
    with urlopen(f'http://127.0.0.1:{PORT}/health',timeout=2) as x:
     if x.status==200: ready=time.time(); break
   except Exception as e: last=repr(e)
   time.sleep(.5)
  if ready is None: raise TimeoutError('server readiness timeout: '+last)
  r['api_ready_seconds_diagnostic']=round(ready-t0,3)
  cli=[str(PYTHON),str(PROFILE/'scripts/run_seeded_benchy_exact.py'),'--base-url',f'http://127.0.0.1:{PORT}/v1','--model',MODEL.name,'--tokenizer',str(TOKENIZER),'--pp','8191','--tg','128','--runs','3','--no-cache','--skip-coherence','--latency-mode','none','--format','json','--save-result',str(OUT),'--emit-progress',str(PROGRESS),'--extra-body','temperature=0.6,top_p=0.95,top_k=20,min_p=0,repeat_penalty=1.0,presence_penalty=0,seed=42']
  r['harness_argv']=cli; atomic(RECEIPT,r)
  with CLIENTLOG.open('wb') as cf: client=subprocess.Popen(cli,stdout=cf,stderr=subprocess.STDOUT,env={**env,'LLAMA_BENCHY_SEED':'42'},start_new_session=True); rc=client.wait(timeout=900)
  r['harness_returncode']=rc
  if OUT.exists(): r['harness_result']=json.loads(OUT.read_text())
  bench=(r.get('harness_result',{}).get('benchmarks') or [{}])[0]
  # The client prompt_size counts user-text tokens; server request_end.prompt_tokens
  # is the effective token count consumed by inference and is the Q173 gate.
  r['client_prompt_size_reported']=bench.get('prompt_size'); r['output_tokens_reported']=bench.get('response_size')
  r['server_event_validation']=validate_progress_file(PROGRESS,expected_runs=3,expected_prompt_tokens=8192,expected_output_tokens=128)
  r['prefill_mean_tok_s']=(bench.get('pp_throughput') or {}).get('mean'); r['decode_mean_tok_s']=(bench.get('tg_throughput') or {}).get('mean')
  r['validity']='PASS' if rc==0 and r['server_event_validation']['valid'] and r['output_tokens_reported']==128 and r['prefill_mean_tok_s'] and r['decode_mean_tok_s'] else 'INVALID_OR_FAILED'
  r['status']=r['validity']
 except Exception as e:
  r['status']='BLOCKED_OR_FAILED'; r['error']=f'{type(e).__name__}: {e}'
 finally:
  if client is not None and client.poll() is None:
   client.send_signal(signal.SIGTERM)
   try: client.wait(timeout=15)
   except subprocess.TimeoutExpired: client.kill(); client.wait(timeout=5)
  if server is not None and server.poll() is None:
   server.send_signal(signal.SIGTERM)
   try: server.wait(timeout=30)
   except subprocess.TimeoutExpired: server.kill(); server.wait(timeout=5)
  if logf: logf.flush(); os.fsync(logf.fileno()); logf.close()
  pf,_=port_free(); r['port_free_after_cleanup']=pf; r['server_exit_code']=server.returncode if server else None; r['finished_utc']=utc(); r['duration_seconds']=round(time.time()-t0,3)
  atomic(RECEIPT,r)
 print(json.dumps({'id':r['id'],'status':r['status'],'error':r.get('error'),'P':r.get('prefill_mean_tok_s'),'D':r.get('decode_mean_tok_s'),'out':str(RECEIPT),'port_free':r['port_free_after_cleanup']}))
 return 0 if r['status']=='PASS' and r['port_free_after_cleanup'] and r['server_exit_code']==0 else 1
if __name__=='__main__': raise SystemExit(main())
