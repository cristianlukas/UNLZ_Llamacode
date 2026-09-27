import json,sys,time,urllib.request,statistics
URL=sys.argv[1]; tag=sys.argv[2]
sysmsg=("Sos Ingi, asistente de voz en español rioplatense. Respondé breve, natural, sin markdown. "*60)
turns=["¿Qué hora es en Tokio si acá son las diez?","Contame un dato curioso de los pulpos.","¿Cómo hago para cortar cebolla sin llorar?","Resumime qué es la fotosíntesis en dos frases.","Dame tres nombres para un gato naranja."]
tt=[];tot=[]
for i,t in enumerate(turns*2):
    body=dict(model='x',stream=True,max_tokens=80,temperature=0.6,messages=[{'role':'system','content':sysmsg},{'role':'user','content':t+f" (#{i})"}])
    t0=time.time(); first=None
    r=urllib.request.urlopen(urllib.request.Request(URL+'/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'}),timeout=120)
    for line in r:
        if line.startswith(b'data: ') and b'"content"' in line and first is None:
            j=json.loads(line[6:]); 
            if j['choices'] and j['choices'][0]['delta'].get('content'): first=time.time()-t0
    tot.append(time.time()-t0); tt.append(first)
res=dict(tag=tag,ttft_med_ms=round(statistics.median(tt[1:])*1000),ttft_p90_ms=round(sorted(tt[1:])[int(0.9*(len(tt)-1))-1]*1000),total_med_s=round(statistics.median(tot[1:]),2))
print(json.dumps(res))
