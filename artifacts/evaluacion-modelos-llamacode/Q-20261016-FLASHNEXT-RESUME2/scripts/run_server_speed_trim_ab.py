#!/usr/bin/env python3
"""Paired Server Speed v1 run for Q4 with/without Strata stage trimming."""
from __future__ import annotations
import datetime as dt, hashlib, json, os, pathlib, signal, socket, statistics, subprocess, sys, threading, time, urllib.request
ROOT = pathlib.Path(__file__).resolve().parents[4]
TASK = ROOT / 'artifacts/evaluacion-modelos-llamacode/Q-20261016-FLASHNEXT-FOLLOWUP'
SOURCE = pathlib.Path('/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source')
SERVER = SOURCE / 'serve/server.py'
CORPUS = ROOT / 'assets/benchmarks/server_speed_v1.json'
CONFIGS = {'A': TASK/'receipts/configs/speed-control.json', 'B': TASK/'receipts/configs/speed-trim.json'}
PORT, SEED, PAIR_ORDER, GIB = 8350, 424242, ['AB','BA','AB'], 1024**3
MIN_SWAP_START = 0.55 * GIB

def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def mem():
    d={}
    for line in pathlib.Path('/proc/meminfo').read_text().splitlines():
        k,v=line.split(':',1)
        if k in ('MemAvailable','SwapFree','SwapTotal'): d[k]=int(v.split()[0])*1024
    d['SwapUsed']=d['SwapTotal']-d['SwapFree']; return d
def pressure():
    out={}
    for line in pathlib.Path('/proc/pressure/memory').read_text().splitlines():
        f=dict(x.split('=') for x in line.split()[1:]); out[line.split()[0]]={k:float(v) for k,v in f.items() if k.startswith('avg')}
    return out
def oom():
    for line in pathlib.Path('/proc/vmstat').read_text().splitlines():
        if line.startswith('oom_kill '): return int(line.split()[1])
    return 0
def gpu():
    p=subprocess.run(['nvidia-smi','--query-gpu=index,name,memory.used,memory.total,utilization.gpu,power.draw,temperature.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=10)
    return [x.strip() for x in p.stdout.splitlines()] if p.returncode==0 else [p.stderr]
def snap(): return {'atUtc':now(),'mem':mem(),'psi':pressure(),'oomKillCount':oom(),'gpu':gpu()}
def free_port():
    with socket.socket() as s: return s.connect_ex(('127.0.0.1',PORT)) != 0
def get_json(url,timeout=8):
    with urllib.request.urlopen(url,timeout=timeout) as r: return json.loads(r.read())
def monitor(proc,path,stop,reason):
    base=oom(); low=low_swap=psi_high=0
    with path.open('w') as f:
        while proc.poll() is None and not stop.is_set():
            s=snap(); f.write(json.dumps(s)+'\n'); f.flush()
            low=low+1 if s['mem'].get('MemAvailable',0)<20*GIB else 0
            low_swap=low_swap+1 if s['mem'].get('SwapFree',0)<512*1024**2 else 0
            some=s['psi'].get('some',{}).get('avg10',0); full=s['psi'].get('full',{}).get('avg10',0)
            psi_high=psi_high+1 if some>=80 or full>=60 else 0
            if oom()>base: reason.append('system oom_kill counter increased')
            elif low>=15: reason.append(f'MemAvailable <20 GiB for 15 samples; latest={s["mem"]["MemAvailable"]/GIB:.2f} GiB')
            elif low_swap>=15: reason.append(f'SwapFree <0.5 GiB for 15 samples; latest={s["mem"]["SwapFree"]/GIB:.2f} GiB')
            elif psi_high>=15: reason.append(f'memory PSI threshold sustained: some={some} full={full}')
            if reason:
                stop.set()
                try: os.killpg(proc.pid,signal.SIGTERM)
                except ProcessLookupError: pass
                break
            time.sleep(1)
def stop_server(proc):
    if proc.poll() is None:
        proc.send_signal(signal.SIGINT)
        try: proc.wait(timeout=45)
        except subprocess.TimeoutExpired:
            try: os.killpg(proc.pid,signal.SIGTERM)
            except ProcessLookupError: pass
            try: proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                try: os.killpg(proc.pid,signal.SIGKILL)
                except ProcessLookupError: pass
                proc.wait(timeout=10)
    deadline=time.monotonic()+15
    while time.monotonic()<deadline and not free_port(): time.sleep(.5)
    return proc.returncode,free_port()
def stream(prompt,max_tokens):
    body=json.dumps({'model':'benchmark','messages':[{'role':'user','content':prompt}], 'stream':True,
      'max_tokens':max_tokens,'temperature':0.0,'top_p':1.0,'cache_prompt':True,'seed':SEED,
      'stream_options':{'include_usage':True}},ensure_ascii=False).encode()
    req=urllib.request.Request(f'http://127.0.0.1:{PORT}/v1/chat/completions',data=body,headers={'Content-Type':'application/json'})
    t0=time.monotonic(); ttft=None; content=[]; reasoning=[]; use={}; timings={}; finish=None
    try:
        with urllib.request.urlopen(req,timeout=1800) as r:
            for raw in r:
                line=raw.decode('utf-8','replace').strip()
                if not line.startswith('data: ') or line[6:]=='[DONE]': continue
                try: obj=json.loads(line[6:])
                except json.JSONDecodeError: continue
                timings.update(obj.get('timings') or {}); use.update(obj.get('usage') or {})
                choices=obj.get('choices') or []
                if choices:
                    c=choices[0]; finish=c.get('finish_reason',finish); d=c.get('delta') or {}
                    a=d.get('content') or ''; b=d.get('reasoning_content') or ''
                    if a or b:
                        if ttft is None: ttft=(time.monotonic()-t0)*1000
                        content.append(a); reasoning.append(b)
    except Exception as e:
        return {'failed':True,'error':f'{type(e).__name__}: {e}','elapsedMs':(time.monotonic()-t0)*1000}
    elapsed=(time.monotonic()-t0)*1000; text=''.join(content).strip() or ''.join(reasoning).strip()
    n=int(timings.get('predicted_n') or use.get('completion_tokens') or 0); pt=int(use.get('prompt_tokens') or timings.get('prompt_n') or 0)
    first=ttft if ttft is not None else -1; dec=float(timings.get('predicted_per_second') or 0)
    if dec<=0 and n and first>=0: dec=n/max(.001,(elapsed-first)/1000)
    pm=float(timings.get('prompt_ms') or 0); pp=float(timings.get('prompt_per_second') or 0)
    if pp<=0 and pt and pm>0: pp=pt*1000/pm
    if pp<=0 and pt and first>0: pp=pt*1000/first
    return {'failed':False,'elapsedMs':round(elapsed,3),'ttftMs':round(first,3),'decodeTps':dec,'promptTokens':pt,
      'completionTokens':n,'promptMs':pm,'promptTps':pp,'generationMs':timings.get('predicted_ms'),
      'timingSource':'llama-timings' if timings else 'client-sse','finishReason':finish,'response':text,
      'responseSha256':hashlib.sha256(text.encode()).hexdigest(),'usage':use,'timings':timings}
def run_arm(arm,pair,order_index,corpus):
    rid=f'pair{pair:02d}-{arm}-order{order_index:02d}'; d=TASK/'receipts/server-speed'/rid; d.mkdir(parents=True,exist_ok=True)
    cfg=json.loads(CONFIGS[arm].read_text()); cfg['log']=str(d/'engine.log')
    cp=d/'effective-config.json'; cp.write_text(json.dumps(cfg,indent=2,ensure_ascii=False)+'\n')
    before=snap()
    run={'taskId':TASK.name,'runId':rid,'arm':arm,'pair':pair,'orderIndex':order_index,
      'configPath':str(cp),'configSha256':hashlib.sha256(cp.read_bytes()).hexdigest(),
      'preflight':before,'warmup':None,'samples':[]}
    if not free_port():
        run.update({'status':'preflight-blocked','error':f'port {PORT} is not free','startedAtUtc':now(),'stoppedAtUtc':now(),'portFreeAfterStop':False})
        (d/'run.json').write_text(json.dumps(run,indent=2,ensure_ascii=False)+'\n'); return run
    if before['mem'].get('MemAvailable',0)<32*GIB or before['mem'].get('SwapFree',0)<MIN_SWAP_START:
        run.update({'status':'preflight-blocked','error':f'preflight failed: {before["mem"]}',
          'startedAtUtc':now(),'stoppedAtUtc':now(),'portFreeAfterStop':True,'postflight':snap()})
        (d/'run.json').write_text(json.dumps(run,indent=2,ensure_ascii=False)+'\n'); return run
    cmd=[sys.executable,str(SERVER),'--engine','strata','--config',str(cp),'--host','127.0.0.1','--port',str(PORT),'--gpu','0,1']
    env=dict(os.environ); env['PYTHONUNBUFFERED']='1'
    out=(d/'server.stdout.log').open('w'); p=subprocess.Popen(cmd,cwd=SOURCE,env=env,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
    abort=threading.Event(); reason=[]; mon=threading.Thread(target=monitor,args=(p,d/'resource-monitor.jsonl',abort,reason),daemon=True); mon.start()
    run.update({'command':cmd,'startedAtUtc':now()})
    start=time.monotonic()
    try:
        deadline=time.monotonic()+900; health=None
        while time.monotonic()<deadline and p.poll() is None and not abort.is_set():
            try:
                health=get_json(f'http://127.0.0.1:{PORT}/health')
                if health.get('status')=='ok': break
            except Exception: pass
            time.sleep(1)
        if abort.is_set(): raise RuntimeError('resource guard: '+'; '.join(reason))
        if p.poll() is not None: raise RuntimeError(f'server exited during load ({p.returncode})')
        if not health or health.get('status')!='ok': raise TimeoutError('server health not ready in 900 seconds')
        run['health']=health; run['apiReadyAtUtc']=now(); run['loadSeconds']=round(time.monotonic()-start,3)
        warm=stream(corpus['items'][0]['prompt'],8)
        if warm.get('failed'): raise RuntimeError('warmup failed: '+warm['error'])
        run['warmup']=warm
        for i,item in enumerate(corpus['items']):
            for phase in (0,1):
                nonce=f'[LlamaCode server-speed-v1 nonce {i*2+phase:06d}]'
                prompt=item['prompt'] if phase else nonce+'\n'+item['prompt']
                row=stream(prompt,int(item['maxTokens']))
                row.update({'sampleId':f'{item["id"]}-{("cold" if phase==0 else "warm")}','category':item['category'],
                  'promptId':item['id'],'measurementPhase':'cold' if phase==0 else 'warm','pass':1,'nonce':nonce,
                  'promptHash':hashlib.sha256(prompt.encode()).hexdigest(),'seed':SEED,'cachePrompt':True,
                  'requestedPromptTokens':0,'maxTokens':int(item['maxTokens'])})
                run['samples'].append(row); (d/'run.json').write_text(json.dumps(run,indent=2,ensure_ascii=False)+'\n')
                if row.get('failed'): raise RuntimeError(f'{row["sampleId"]} failed: {row.get("error")}')
                if abort.is_set(): raise RuntimeError('resource guard: '+'; '.join(reason))
        run['status']='complete'
    except Exception as e:
        run['status']='aborted' if abort.is_set() else 'failed'; run['error']=f'{type(e).__name__}: {e}'
    finally:
        code,freed=stop_server(p); mon.join(timeout=5); out.close()
        run.update({'stoppedAtUtc':now(),'exitCode':code,'portFreeAfterStop':freed,'postflight':snap(),
                    'abortReason':reason,'wallSeconds':round(time.monotonic()-start,3)})
        (d/'run.json').write_text(json.dumps(run,indent=2,ensure_ascii=False)+'\n')
    if not run['portFreeAfterStop']: raise RuntimeError('own server did not release port 8350')
    if run['status']!='complete': raise RuntimeError(run.get('error','incomplete arm'))
    return run
def summarise(runs):
    metrics=['decodeTps','promptTps','ttftMs','elapsedMs']; out={'arms':[],'paired':[]}
    for arm in ('A','B'):
        ss=[s for r in runs if r['arm']==arm for s in r['samples']]
        arm_metrics={}
        for m in metrics:
            values=[float(x[m]) for x in ss if x.get(m) is not None]
            arm_metrics[m]={'n':len(values),'mean':statistics.mean(values),'median':statistics.median(values),
              'min':min(values),'max':max(values)} if values else {'n':0}
        out['arms'].append({'arm':arm,'n':len(ss),'metrics':arm_metrics})
    for pair in range(1,len(PAIR_ORDER)+1):
        aa=[r for r in runs if r['pair']==pair and r['arm']=='A']; bb=[r for r in runs if r['pair']==pair and r['arm']=='B']
        if not aa or not bb: continue
        a,b=aa[0],bb[0]
        am={(x['promptId'],x['measurementPhase']):x for x in a['samples']}; bm={(x['promptId'],x['measurementPhase']):x for x in b['samples']}; keys=sorted(set(am)&set(bm))
        deltas={}
        for m in metrics:
            v=[float(bm[k][m])-float(am[k][m]) for k in keys if am[k].get(m) is not None and bm[k].get(m) is not None]
            deltas[m]={'meanDeltaBMinusA':statistics.mean(v),'medianDeltaBMinusA':statistics.median(v),'n':len(v)} if v else {'n':0}
        bad=[k for k in keys if am[k].get('responseSha256')!=bm[k].get('responseSha256')]
        out['paired'].append({'pair':pair,'order':PAIR_ORDER[pair-1],'nMatched':len(keys),'metrics':deltas,
          'outputHashMismatchCount':len(bad),'outputHashMismatchSamples':bad})
    return out
def main():
    raw=CORPUS.read_bytes(); corpus=json.loads(raw); dest=TASK/'receipts/server-speed'; dest.mkdir(parents=True,exist_ok=True)
    campaign=dest/'campaign.json'; report=json.loads(campaign.read_text()) if campaign.exists() else {}
    expected_hash=hashlib.sha256(raw).hexdigest()
    if report and (report.get('corpusSha256')!=expected_hash or report.get('seed')!=SEED):
        raise RuntimeError('existing campaign does not match the preregistered corpus/seed; refusing to mix runs')
    report.update({'taskId':TASK.name,'corpusPath':str(CORPUS),'corpusSha256':expected_hash,
      'corpus':corpus,'seed':SEED,'sampling':{'temperature':0.0,'top_p':1.0},'pairs':3,'order':PAIR_ORDER,
      'warmupPerServer':1,'items':len(corpus['items']),'coldAndWarm':True,'includePrefillSweep':False,'includeConcurrency':False})
    report.setdefault('startedAtUtc',now())
    runs_by_id={r['runId']:r for r in report.get('runs',[]) if r.get('status')=='complete'}
    for pair,order in enumerate(PAIR_ORDER,1):
        for pos,arm in enumerate(order,1):
            rid=f'pair{pair:02d}-{arm}-order{pos:02d}'; receipt=dest/rid/'run.json'
            if receipt.exists():
                saved=json.loads(receipt.read_text())
                if saved.get('status')=='complete': runs_by_id[rid]=saved
                elif saved.get('samples'):
                    raise RuntimeError(f'{rid} has partial samples; refusing to repeat them automatically')
    planned=[f'pair{pair:02d}-{arm}-order{pos:02d}' for pair,order in enumerate(PAIR_ORDER,1) for pos,arm in enumerate(order,1)]
    report['runs']=[runs_by_id[rid] for rid in planned if rid in runs_by_id]
    report['summary']=summarise(report['runs']); report['completedAtUtc']=now(); campaign.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    for pair,order in enumerate(PAIR_ORDER,1):
        for pos,arm in enumerate(order,1):
            rid=f'pair{pair:02d}-{arm}-order{pos:02d}'
            if rid in runs_by_id:
                print(f'SKIP {rid}: complete receipt already exists',flush=True); continue
            partial=dest/rid/'run.json'
            if partial.exists() and json.loads(partial.read_text()).get('samples'):
                raise RuntimeError(f'{rid} has partial samples; refusing to repeat them automatically')
            print(f'START pair={pair} order={order} arm={arm} {now()}',flush=True)
            row=run_arm(arm,pair,pos,corpus)
            if row.get('status')!='complete':
                report['lastAttempt']=row; report['status']='paused-preflight'; report['completedAtUtc']=now()
                report['runs']=[runs_by_id[x] for x in planned if x in runs_by_id]
                report['summary']=summarise(report['runs']); campaign.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
                print(json.dumps({'runId':rid,'status':row.get('status'),'error':row.get('error')},ensure_ascii=False),flush=True)
                return
            runs_by_id[rid]=row
            report['runs']=[runs_by_id[x] for x in planned if x in runs_by_id]; report['summary']=summarise(report['runs'])
            report['completedAtUtc']=now(); campaign.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
            print(json.dumps({'pair':pair,'order':order,'arm':arm,'status':row['status'],'wallSeconds':row['wallSeconds'],
              'loadSeconds':row.get('loadSeconds'),'samples':len(row['samples']),'error':row.get('error')},ensure_ascii=False),flush=True)
    report['status']='complete'; report['completedAtUtc']=now(); report['summary']=summarise(report['runs'])
    campaign.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(report['summary'],indent=2,ensure_ascii=False),flush=True)
if __name__=='__main__': main()
