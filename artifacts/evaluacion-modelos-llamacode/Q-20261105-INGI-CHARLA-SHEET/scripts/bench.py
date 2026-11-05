"""Voz en tiempo real mientras N agentes generan en el mismo llama-server.
Mide para la petición de voz: TTFT, tiempo a la primera oración y total;
para los agentes: tokens/s agregados. Uso: bench.py PORT WORKERS REPS OUT.json"""
import json, sys, os, threading, time, http.client, statistics, re
PIN=os.environ.get("PIN")=="1"; WARM=os.environ.get("WARM")=="1"
PORT=int(sys.argv[1]); WORKERS=int(sys.argv[2]); REPS=int(sys.argv[3]); OUT=sys.argv[4]
TOOLS=" ".join(f"Herramienta t{i}: busca, abre, lee y resume información del sistema número {i}, devuelve JSON con campos estado, detalle y fuente." for i in range(220))
VOICE_SYS="MODO VOZ (Ingi Charla): respondé en 1 a 3 frases cortas, naturales, sin markdown. "+TOOLS[:6000]
WORK_SYS="Sos un agente de investigación. "+TOOLS
VOICE_Q=["¿Cuánto es doce por treinta y siete?","Decime en una frase qué es un agujero negro.","¿Qué conviene llevar si mañana llueve?","Contame un dato curioso sobre los pulpos.","¿Cuántos días tiene un año bisiesto?"]
WORK_Q=["Escribí un informe detallado de 700 palabras sobre la historia de los ferrocarriles argentinos.","Escribí un informe detallado de 700 palabras sobre energía solar en Argentina.","Escribí un informe detallado de 700 palabras sobre la economía de Rosario.","Escribí un informe detallado de 700 palabras sobre la fauna patagónica.","Escribí un informe detallado de 700 palabras sobre la historia del tango.","Escribí un informe detallado de 700 palabras sobre la industria del software en Córdoba."]
def stream(sysmsg,user,max_tokens,rec,slot=None):
    extra={"id_slot":slot} if (PIN and slot is not None) else {}
    body=json.dumps({**extra,"messages":[{"role":"system","content":sysmsg},{"role":"user","content":user}],"max_tokens":max_tokens,"stream":True,"temperature":0.6,"chat_template_kwargs":{"enable_thinking":False}})
    c=http.client.HTTPConnection("127.0.0.1",PORT,timeout=600); t0=time.monotonic()
    c.request("POST","/v1/chat/completions",body,{"Content-Type":"application/json"}); r=c.getresponse()
    text="";first=None;sent=None;n=0
    for raw in r:
        line=raw.decode("utf-8","ignore").strip()
        if not line.startswith("data:") or line.endswith("[DONE]"): continue
        try: d=json.loads(line[5:])
        except Exception: continue
        ch=d.get("choices") or [{}]; delta=ch[0].get("delta",{}).get("content") or ""
        if delta:
            n+=1; text+=delta
            if first is None: first=time.monotonic()-t0
            if sent is None and re.search(r"[.!?](\s|$)",text) and len(text)>=12: sent=time.monotonic()-t0
    rec.update(ttft=first,first_sentence=sent if sent else time.monotonic()-t0,total=time.monotonic()-t0,chunks=n,text=text[:160])
def run():
    res={"idle":[],"loaded":[],"workers":[]}
    if WARM:
        t=time.monotonic()
        ws=[threading.Thread(target=stream,args=(WORK_SYS,"ok",1,{},j+1)) for j in range(WORKERS)]
        [w.start() for w in ws]; [w.join() for w in ws]
        stream(VOICE_SYS,"ok",1,{},slot=0)
        res["warmup_s"]=time.monotonic()-t; print("warmup",round(res["warmup_s"],1),flush=True)
    for i in range(REPS):
        r={}; stream(VOICE_SYS,VOICE_Q[i%5],120,r,slot=0); res["idle"].append(r); print("idle",i,{k:round(v,3) for k,v in r.items() if isinstance(v,float)},flush=True)
    for i in range(REPS):
        recs=[{} for _ in range(WORKERS)]
        ths=[threading.Thread(target=stream,args=(WORK_SYS,WORK_Q[(i+j)%6],900,recs[j],j+1)) for j in range(WORKERS)]
        t0=time.monotonic(); [t.start() for t in ths]; time.sleep(4.0)
        v={}; stream(VOICE_SYS,VOICE_Q[i%5],120,v,slot=0); res["loaded"].append(v)
        [t.join() for t in ths]; wall=time.monotonic()-t0
        toks=sum(x.get("chunks",0) for x in recs); res["workers"].append({"wall":wall,"chunks":toks,"agg_tok_s":toks/wall})
        print("loaded",i,{k:round(x,3) for k,x in v.items() if isinstance(x,float)},"workers agg tok/s",round(toks/wall,1),flush=True)
    summ={}
    for k in ("idle","loaded"):
        summ[k]={m:round(statistics.median(x[m] for x in res[k] if x.get(m) is not None),3) for m in ("ttft","first_sentence","total")}
    summ["workers_agg_tok_s"]=round(statistics.median(w["agg_tok_s"] for w in res["workers"]),1)
    res["summary"]=summ; json.dump(res,open(OUT,"w"),indent=1,ensure_ascii=False); print("SUMMARY",json.dumps(summ))
run()
