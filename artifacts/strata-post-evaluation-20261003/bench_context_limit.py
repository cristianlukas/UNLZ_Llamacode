"""Boundary smoke for Strata IQ3_S at the trained 262144-token context."""
import json, pathlib, signal, subprocess, sys, time, urllib.request, urllib.error
ROOT=pathlib.Path('/home/cristian/.cache/strata-review-20261002/Strata-0.1.35')
OUT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools')); sys.path.insert(0,str(ROOT))
import strata_tokenizer as ST
import calibrate as CAL
cfg0=json.loads((ROOT/'strata-iq3_s.json').read_text())
t=pathlib.Path(cfg0['tokenizer']); v=json.loads((t/'vocab.json').read_text()); toks=[None]*len(v)
for tok,i in v.items(): toks[i]=tok
tok=ST.Tokenizer(toks,(t/'merges.txt').read_text().split('\n'),json.loads((t/'token_type.json').read_text()))
needle='STRATA_LIMIT_NEEDLE_20261003'
prefix='Find the unique marker in this long log and return only its exact identifier.\n'
filler='record: status pending; node alpha; task 417. '
def make_text(n):
 half=n//2
 return prefix+(filler*half)+'\nMARKER: '+needle+'\n'+(filler*(n-half))
lo,hi=0,100000
while lo<hi:
 mid=(lo+hi+1)//2
 if len(CAL.chat_ids(tok,make_text(mid)))<=261700: lo=mid
 else: hi=mid-1
text=make_text(lo)
input_tokens=len(CAL.chat_ids(tok,text))
print('INPUT_TOKENS',input_tokens,'REPEATS',lo,flush=True)
results=[]
for context in [262136,262144]:
 cfg=json.loads(json.dumps(cfg0)); a=cfg['args']; i=a.index('--max-context'); a[i+1]=str(context)
 cfgpath=ROOT/f'strata-iq3_s-context-{context}-test.json'; cfgpath.write_text(json.dumps(cfg,indent=1)+'\n')
 port=8361 if context==262136 else 8362
 log=OUT/f'strata-context-{context}.log'; logf=log.open('w')
 cmd=[str(ROOT/'.venv/bin/python'),str(ROOT/'serve/server.py'),'--engine','strata','--config',str(cfgpath),'--host','127.0.0.1','--port',str(port)]
 started=time.time(); p=subprocess.Popen(cmd,cwd=ROOT,stdout=logf,stderr=subprocess.STDOUT)
 endpoint=f'http://127.0.0.1:{port}/v1/chat/completions'; health=f'http://127.0.0.1:{port}/health'
 outcome={'context':context,'inputTokensByStrataTokenizer':input_tokens,'config':str(cfgpath),'log':str(log),'startCommand':cmd}
 try:
  ready=False
  while time.time()-started<600 and p.poll() is None:
   try:
    urllib.request.urlopen(health,timeout=3).read(); ready=True; break
   except Exception: time.sleep(3)
  if not ready: raise RuntimeError(f'server failed before ready, return={p.poll()}')
  outcome['readySeconds']=round(time.time()-started,1)
  body=json.dumps({'model':'qwen3.8-flash-next-iq3_s','messages':[{'role':'user','content':text}], 'max_tokens':256,'temperature':0,'stream':False}).encode()
  req=urllib.request.Request(endpoint,data=body,headers={'Content-Type':'application/json'})
  sent=time.time()
  try:
   with urllib.request.urlopen(req,timeout=1800) as r: response=json.loads(r.read().decode())
   outcome['requestSeconds']=round(time.time()-sent,1)
   outcome['response']=response.get('choices',[{}])[0].get('message')
   outcome['usage']=response.get('usage')
   outcome['ok']=needle in json.dumps(outcome.get('response'),ensure_ascii=False)
  except Exception as e:
   outcome['requestError']=repr(e); outcome['requestSeconds']=round(time.time()-sent,1); outcome['ok']=False
 finally:
  p.send_signal(signal.SIGINT)
  try: p.wait(90)
  except subprocess.TimeoutExpired: p.kill(); p.wait()
  logf.close()
  outcome['serverExit']=p.returncode
  results.append(outcome)
  (OUT/'context_limit_results.json').write_text(json.dumps({'inputTokens':input_tokens,'needle':needle,'runs':results},indent=2)+'\n')
  print(json.dumps(outcome,ensure_ascii=False),flush=True)
