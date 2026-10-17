#!/usr/bin/env python3
import datetime, hashlib, json, sys, time, urllib.request, subprocess
from pathlib import Path
ART=Path(__file__).parent
RECEIPTS=ART/'receipts'
if len(sys.argv)!=3 or sys.argv[1] not in ('off','on') or sys.argv[2] not in ('A','B','C'):
    raise SystemExit('usage: run_speed_sample.py off|on A|B|C')
mode,prompt_id=sys.argv[1:]
rows=json.loads((RECEIPTS/'speed-prompts.json').read_text())['prompts']
fixture=next(x for x in rows if x['id']==prompt_id)
def get(url):
    req=urllib.request.Request(url)
    with urllib.request.urlopen(req,timeout=20) as r: return r.read().decode()
def resource(label):
    mem={}
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'): mem['MemAvailable_bytes']=int(line.split()[1])*1024
    oom=next((int(line.split()[1]) for line in Path('/proc/vmstat').read_text().splitlines() if line.startswith('oom_kill ')),0)
    gpu=subprocess.run(['nvidia-smi','--query-gpu=index,memory.used,memory.total,utilization.gpu','--format=csv,noheader'],text=True,stdout=subprocess.PIPE,timeout=10).stdout.strip()
    compute=subprocess.run(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'],text=True,stdout=subprocess.PIPE,timeout=10).stdout.strip()
    own=subprocess.run(['docker','top',f'lc-qwen36-auto-int4-mtp-{mode}','-eo','pid,comm,args'],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
    own_pids={line.split()[0] for line in own.stdout.splitlines()[1:] if line.strip()} if own.returncode==0 else set()
    comp_pids={line.split(',')[0].strip() for line in compute.splitlines() if line.strip()}
    assert comp_pids <= own_pids, {'compute':compute,'own_pids':sorted(own_pids)}
    assert mem.get('MemAvailable_bytes',0)>=20*1024**3
    return {'label':label,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mem_available_bytes':mem['MemAvailable_bytes'],'oom_kill':oom,'psi':Path('/proc/pressure/memory').read_text(),'gpu':gpu,'compute_apps':compute}
payload={'model':'qwen36-auto-int4','messages':fixture['messages'],'temperature':0,'top_p':1.0,'top_k':1,'seed':4242,'min_tokens':320,'max_tokens':320,'ignore_eos':True,'chat_template_kwargs':{'enable_thinking':False},'include_reasoning':False,'repetition_penalty':1.0,'presence_penalty':0.0,'frequency_penalty':0.0,'stream':True,'stream_options':{'include_usage':True},'request_id':f'Q20261017-{mode}-{prompt_id}'}
pre=resource('before')
assert pre['mem_available_bytes']>=40*1024**3
before_metrics=get('http://127.0.0.1:18051/metrics')
req=urllib.request.Request('http://127.0.0.1:18051/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
start=time.perf_counter(); first=None; usage=None; text=[]; events=0; err=None
with urllib.request.urlopen(req,timeout=600) as resp:
    status=resp.status
    for raw in resp:
        if not raw.startswith(b'data:'): continue
        data=raw[5:].strip()
        if data==b'[DONE]': break
        item=json.loads(data); events+=1
        if item.get('usage'): usage=item['usage']
        for choice in item.get('choices',[]):
            delta=choice.get('delta') or {}
            chunk=delta.get('content') or delta.get('reasoning') or ''
            if chunk:
                if first is None: first=time.perf_counter()
                text.append(chunk)
end=time.perf_counter(); post=resource('after'); after_metrics=get('http://127.0.0.1:18051/metrics')
assert post['oom_kill']==pre['oom_kill']
assert usage is not None, 'stream response did not include usage'
output=''.join(text)
ttft=(first-start) if first is not None else None
total=end-start
completion=usage.get('completion_tokens',0)
result={'task_id':'Q-20261017-RX7600-TEST-RESUME','mode':mode,'prompt_id':prompt_id,'prompt_tokens_target':fixture['prompt_tokens'],'prompt_sha256':fixture['messages_sha256'],'server_id':'qwen36-auto-int4','request':payload,'http_status':status,'usage':usage,'events':events,'ttft_seconds':ttft,'total_seconds':total,'decode_seconds':(total-ttft) if ttft is not None else None,'decode_tokens_per_second':completion/(total-ttft) if ttft is not None and total>ttft else None,'output_sha256':hashlib.sha256(output.encode()).hexdigest(),'output_text':output,'preflight':pre,'postflight':post,'metrics_before':before_metrics,'metrics_after':after_metrics,'valid':status==200 and usage.get('prompt_tokens') in range(4055,4147) and completion==320 and ttft is not None}
path=RECEIPTS/f'speed-{mode}-{prompt_id}.json'; path.write_text(json.dumps(result,indent=2,ensure_ascii=False))
print(json.dumps({'mode':mode,'prompt':prompt_id,'valid':result['valid'],'usage':usage,'ttft_s':round(ttft,4) if ttft is not None else None,'total_s':round(total,4),'decode_tps':round(result['decode_tokens_per_second'],2) if result['decode_tokens_per_second'] else None,'output_sha256':result['output_sha256']}))
