import sys,time,statistics,json,os
repo,model,inp,refwav,reftext,out=sys.argv[1:7]
sys.path.insert(0,repo)
import torch, soundfile as sf
from ming_tts import MingTTS
t=time.monotonic(); m=MingTTS(model,device="cuda:0",text_normalization=False); load=time.monotonic()-t
lines=[l.strip() for l in open(inp,encoding='utf-8') if l.strip()]
kw=dict(task="TTS",language_id="es",prompt_wav_path=refwav,prompt_text=reftext,use_spk_emb=True)
m.synthesize(text="Hola, ¿cómo estás?",**kw)  # warmup
os.makedirs(out,exist_ok=True); rows=[]
for i,l in enumerate(lines,1):
    torch.cuda.synchronize(); t=time.monotonic()
    wav=m.synthesize(text=l,output_path=f"{out}/{i}.wav",**kw)
    torch.cuda.synchronize(); el=time.monotonic()-t
    info=sf.info(f"{out}/{i}.wav"); rows.append((el,info.duration))
res={"load_s":load,"full_wav_median_s":statistics.median(r[0] for r in rows),"full_wav_p95_s":sorted(r[0] for r in rows)[18],
     "rtf_median":statistics.median(r[0]/r[1] for r in rows),"vram_peak_mib":torch.cuda.max_memory_allocated()/2**20}
print(json.dumps(res)); json.dump(res,open(out+"/summary.json","w"))
