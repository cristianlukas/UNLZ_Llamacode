import json,subprocess,sys,time
AD=sys.argv[1]
def ad(*a):
    t=time.monotonic(); p=subprocess.run([AD,*a],capture_output=True,text=True); return json.loads(p.stdout or '{}'), (time.monotonic()-t)*1000
def walk(n,out):
    if isinstance(n,dict):
        if n.get('ref_id'): out.append(n)
        for c in n.get('children',[]): walk(c,out)
    return out
res=[]
for trial in range(5):
    t0=time.monotonic(); lat=[]
    snap,ms=ad('snapshot','--app','gnome-calculator','-i','--compact'); lat.append(ms)
    nodes=walk(snap['data']['tree'],[])
    byname={n.get('name'):n['ref_id'] for n in nodes if n.get('role')=='button'}
    field=[n['ref_id'] for n in nodes if n.get('role')=='textfield'][0]
    ad('clear',field)
    seq=['3','×','3','=']
    missing=[s for s in seq if s not in byname]
    if missing: print('faltan',missing,sorted(k for k in byname if k)); break
    oks=[]
    for s in seq:
        r,ms=ad('click',byname[s]); lat.append(ms); oks.append(r.get('ok'))
        time.sleep(0.3)
    g,ms=ad('get',field,'--property','value'); lat.append(ms)
    snap2,_=ad('snapshot','--app','gnome-calculator','--compact')
    txt=json.dumps(snap2,ensure_ascii=False)
    val=g.get('data',{}).get('value')
    res.append({'trial':trial,'clicks_ok':all(oks),'field':val,'has9':' 9' in txt or '"9"' in txt or (val and '9' in str(val)),'total_ms':round((time.monotonic()-t0)*1000),'median_cmd_ms':round(sorted(lat)[len(lat)//2])})
    print(res[-1],flush=True)
json.dump(res,open('e2e.json','w'),indent=1)
