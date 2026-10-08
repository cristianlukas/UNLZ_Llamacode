#!/usr/bin/env python3
"""Short repeated decode check at the configured context allocation."""
import argparse,json,statistics,time
from pathlib import Path
from urllib.request import Request,urlopen

def main():
 p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8038/v1/chat/completions');p.add_argument('--model',default='Swift-Qwen3.8-27B-Genesis-NVFP4-v4');p.add_argument('--context',type=int,default=65536);p.add_argument('--passes',type=int,default=5);p.add_argument('--out',type=Path,required=True);a=p.parse_args();rows=[]
 for i in range(1,a.passes+1):
  payload={'model':a.model,'messages':[{'role':'system','content':'Sos un asistente de programación. Respondé sólo con la función pedida.'},{'role':'user','content':'Escribí una función Python llamada add(a, b) que devuelva a + b. Incluí una docstring breve y un ejemplo de uso.'}],'temperature':0.6,'top_p':0.95,'top_k':20,'min_p':0.0,'max_tokens':128,'chat_template_kwargs':{'enable_thinking':False},'stream':True,'stream_options':{'include_usage':True},'seed':42}
  req=Request(a.url,data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'});t=time.perf_counter()
  try:
   timing={}; usage={}; content=[]; reasoning=[]
   with urlopen(req,timeout=600) as r:
    for line in r:
     line=line.decode('utf-8',errors='replace').strip()
     if not line.startswith('data: '):continue
     raw=line[6:]
     if raw=='[DONE]':continue
     event=json.loads(raw)
     if isinstance(event.get('timings'),dict):timing.update(event['timings'])
     if isinstance(event.get('usage'),dict):usage.update(event['usage'])
     choices=event.get('choices') or []
     if choices:
      delta=choices[0].get('delta') or {}
      content.append(str(delta.get('content') or ''))
      reasoning.append(str(delta.get('reasoning_content') or ''))
   row={'pass':i,'transportOk':True,'wallMs':round((time.perf_counter()-t)*1000,2),'promptTps':timing.get('prompt_per_second'),'decodeTps':timing.get('predicted_per_second'),'promptTokens':timing.get('prompt_n',usage.get('prompt_tokens')),'generatedTokens':timing.get('predicted_n',usage.get('completion_tokens')),'content':''.join(content),'reasoning':''.join(reasoning)[:1000]}
  except Exception as e:row={'pass':i,'transportOk':False,'error':f'{type(e).__name__}: {e}'}
  rows.append(row);print(f"{i}/{a.passes}: decode={row.get('decodeTps')} t/s; wall={row.get('wallMs')}ms",flush=True)
 good=[r for r in rows if r['transportOk'] and r.get('decodeTps') is not None]
 out={'benchmark':'short_decode_5_repeats','model':a.model,'allocatedContext':a.context,'mtpDraftMax':4,'temperature':0.6,'topP':0.95,'topK':20,'reasoning':'off','passes':a.passes,'medianDecodeTps':statistics.median(r['decodeTps'] for r in good) if good else None,'rows':rows};a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print('median=',out['medianDecodeTps'],'out=',a.out);return 0 if len(good)==a.passes else 2
if __name__=='__main__':raise SystemExit(main())
