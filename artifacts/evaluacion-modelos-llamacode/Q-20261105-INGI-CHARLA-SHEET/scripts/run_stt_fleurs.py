import json,subprocess,sys,time,statistics
from pathlib import Path
A=Path('/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode/artifacts/evaluacion-modelos-llamacode/Q-20261030-VOICE-WEB-CU')
import unicodedata
def normalize(text):
    text = unicodedata.normalize('NFC', text.lower())
    text = ''.join(ch if ch.isalnum() or ch.isspace() else ' ' for ch in text)
    return ' '.join(text.split())
def edits(ref, hyp):
    prior = list(range(len(hyp) + 1))
    for i, a in enumerate(ref, 1):
        curr = [i]
        for j, b in enumerate(hyp, 1):
            curr.append(min(curr[-1] + 1, prior[j] + 1, prior[j-1] + (a != b)))
        prior = curr
    return prior[-1]
B=Path('/home/cristian/.cache/q191-whisper.cpp/build-q191/bin'); V=Path.home()/'.local/share/LlamaCode/LlamaCode/voice'
ARMS={'whisper-small':(B/'whisper-cli',V/'whisper-small/ggml-small.bin',['-l','es','-nt']),
      'whisper-large-v3-turbo-q8':(B/'whisper-cli',V/'whisper-large-v3-turbo/ggml-large-v3-turbo-q8_0.bin',['-l','es','-nt']),
      'parakeet-q4':(B/'parakeet-cli',Path('/media/cristian/Disco local/LlamaCode-cache/voice-models/parakeet-tdt-0.6b-v3/ggml-parakeet-tdt-0.6b-v3-q4_0.bin'),[])}
clips=json.loads((A/'receipts/fleurs-corpus-manifest.json').read_text())['clips']
out=Path(sys.argv[1]); out.mkdir(exist_ok=True); res={}
for arm,(bin_,model,extra) in ARMS.items():
    rows=[]
    for c in clips:
        wav=Path.home()/'.cache/q191-fleurs-es419/selected'/c['filename'].replace('.wav','-pcm16.wav')
        pre=out/f"{arm}-{c['row_index']}"
        t=time.monotonic()
        subprocess.run([str(bin_),'-m',str(model),'-f',str(wav),'-t','16','-ng','-otxt','-of',str(pre),'-np',*extra],env={'LD_LIBRARY_PATH':str(B)},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
        el=time.monotonic()-t
        ref=normalize(c['normalized_reference']); hyp=normalize(pre.with_suffix('.txt').read_text())
        rows.append((edits(ref.split(),hyp.split()),len(ref.split()),edits(ref,hyp),len(ref),el,c['duration_seconds']))
    res[arm]={'micro_wer':sum(r[0] for r in rows)/sum(r[1] for r in rows),'micro_cer':sum(r[2] for r in rows)/sum(r[3] for r in rows),
              'median_s':statistics.median(r[4] for r in rows),'p95_s':sorted(r[4] for r in rows)[18],'median_rtf':statistics.median(r[4]/r[5] for r in rows)}
    print(arm,{k:round(v,4) for k,v in res[arm].items()},flush=True)
(out/'summary.json').write_text(json.dumps(res,indent=2))
