import json,sys,os,re,time,subprocess,tempfile,urllib.request
CORPUS=r'C:\Users\cristian\Documents\LlamaCode\artifacts\bigcodebench-hard-ubuntu-8.json'
d=json.load(open(CORPUS,encoding='utf-8'))
def grade(item,code):
    pre=(item.get('preamble') or '')
    if 'def '+(item.get('entryPoint') or 'task_func') in code or pre.rstrip().endswith(':'): pre=''
    src=pre+'\n'+code+'\n\n'+item['tests']+'\n\nif __name__=="__main__":\n    import unittest\n    unittest.main(verbosity=0)\n'
    with tempfile.TemporaryDirectory() as td:
        p=os.path.join(td,'t.py'); open(p,'w',encoding='utf-8').write(src)
        try:
            r=subprocess.run([sys.executable,p],cwd=td,capture_output=True,text=True,timeout=120,env={**os.environ,'MPLBACKEND':'Agg'})
            return r.returncode==0,(r.stderr or r.stdout)[-600:]
        except subprocess.TimeoutExpired: return False,'timeout'
def extract(txt):
    m=re.findall(r'```(?:python)?\n(.*?)```',txt,re.S)
    return max(m,key=len) if m else txt
mode=sys.argv[1]
if mode=='grade':  # grade existing files: prefix
    pre=sys.argv[2]; ok=0
    for it in d['items']:
        n=it['id'].split('/')[1]; code=open(f'{pre}-{n}.py',encoding='utf-8').read()
        p,det=grade(it,code); ok+=p; print(it['id'],p, '' if p else det[-200:].replace('\n',' | '))
    print('TOTAL',ok,'/',len(d['items']))
else:
    url=sys.argv[2]; tag=sys.argv[3]; out=sys.argv[4]; os.makedirs(out,exist_ok=True); res=[]; ok=0; tgen=0
    for it in d['items']:
        body=dict(model='x',messages=[{'role':'system','content':'You are an expert Python programmer. Reply with only executable Python code in a single ```python block. No explanations.'},{'role':'user','content':it['prompt']}],temperature=0.2,top_p=0.95,top_k=20,min_p=0.0,max_tokens=4096)
        t=time.time(); j=json.load(urllib.request.urlopen(urllib.request.Request(url+'/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'}),timeout=1200)); dt=time.time()-t; tgen+=dt
        code=extract(j['choices'][0]['message']['content'] or ''); n=it['id'].split('/')[1]
        open(os.path.join(out,f'{tag}-{n}.py'),'w',encoding='utf-8').write(code)
        p,det=grade(it,code); ok+=p
        res.append(dict(id=it['id'],passed=p,elapsed_s=round(dt,2),completion_tokens=j['usage']['completion_tokens'],detail='' if p else det[-300:]))
        print(it['id'],p,round(dt,1),flush=True)
    json.dump(dict(tag=tag,passed=ok,total=len(d['items']),gen_s=round(tgen,1),items=res),open(os.path.join(out,f'{tag}.json'),'w'),indent=1)
    print('TOTAL',ok,'/',len(d['items']),'gen_s',round(tgen,1))
