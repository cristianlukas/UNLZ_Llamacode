import sys,time,statistics,asyncio,json
import soundfile as sf
from kokoro_onnx import Kokoro, EspeakConfig
model,voices,voice,inp,out=sys.argv[1:6]
t=time.monotonic(); k=Kokoro(model,voices,espeak_config=EspeakConfig(lib_path="/usr/lib/x86_64-linux-gnu/libespeak-ng.so.1",data_path="/usr/lib/x86_64-linux-gnu/espeak-ng-data")); load=time.monotonic()-t
lines=[l.strip() for l in open(inp,encoding='utf-8') if l.strip()]
k.create("Hola.",voice=voice,speed=1.0,lang="es")  # warmup
async def first_chunk(text):
    t=time.monotonic(); first=None; chunks=[]
    async for samples,sr in k.create_stream(text,voice=voice,speed=1.0,lang="es"):
        if first is None: first=time.monotonic()-t
        chunks.append(samples)
    return first,time.monotonic()-t,chunks,sr
import numpy as np, os
os.makedirs(out,exist_ok=True); rows=[]
for i,l in enumerate(lines,1):
    first,total,chunks,sr=asyncio.run(first_chunk(l))
    a=np.concatenate(chunks); sf.write(f"{out}/{i}.wav",a,sr)
    rows.append((first,total,len(a)/sr))
res={"load_s":load,"first_audio_median_s":statistics.median(r[0] for r in rows),"first_audio_p95_s":sorted(r[0] for r in rows)[18],
     "rtf_median":statistics.median(r[1]/r[2] for r in rows)}
print(json.dumps(res)); json.dump(res,open(out+"/summary.json","w"))
