#!/usr/bin/env python3
"""Q191 ASR proxy for intelligibility of Piper and Kitten outputs."""
import hashlib
import json
from pathlib import Path
import statistics
import subprocess

from run_whistle_asr import normalize, edits

BASE=Path(__file__).resolve().parents[1]
REPO=BASE.parents[2]
PHRASES=BASE/'receipts/tts-phrases.json'
BIN=Path('/home/cristian/.cache/q191-whisper.cpp/build-q191/bin/parakeet-cli')
MODEL=Path('/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/AppData/Local/LlamaCode/LlamaCode/voice/parakeet-tdt-0.6b-v3/ggml-parakeet-tdt-0.6b-v3-q4_0.bin')
CACHE=Path('/home/cristian/.cache/q191-tts-intelligibility')
OUT=BASE/'runs/tts-intelligibility.json'


def main():
    assert json.loads((REPO/'WORK_QUEUE.lock').read_text())['token']=='q191-voice-web-cu-20261030'
    assert hashlib.sha256(PHRASES.read_bytes()).hexdigest()=='41af7111c8f2cc13da2fe13ea84d2bd66592ac0bc535a4716903d0d648677afb'
    assert hashlib.sha256(BIN.read_bytes()).hexdigest()=='c7a8f59e67d6bbe61066da2fbf3d9e0eb2876e337cfb2a51d51cbabd4bfda80b'
    assert hashlib.sha256(MODEL.read_bytes()).hexdigest()=='aa7fe2f5fb47d863ca23e8b1d490632d63a2599f515268b6d6bd656158dad45e'
    phrases=json.loads(PHRASES.read_text())['phrases']
    CACHE.mkdir(exist_ok=True)
    rows=[]
    for arm in ('piper','kitten'):
        for phrase in phrases:
            idx=phrase['row_index']
            source=BASE/f'runs/{arm}-wav'/ (f'row{idx}.wav' if arm=='piper' else f'p1-row{idx}.wav')
            assert source.is_file(),source
            pcm=CACHE/f'{arm}-row{idx}-16k.wav'
            subprocess.run(['ffmpeg','-nostdin','-loglevel','error','-y','-i',str(source),'-ac','1','-ar','16000','-sample_fmt','s16',str(pcm)],check=True)
            prefix=CACHE/f'{arm}-row{idx}'
            cmd=[str(BIN),'-m',str(MODEL),'-f',str(pcm),'-t','16','-ng','-otxt','-of',str(prefix),'-np']
            proc=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
            txt=prefix.with_suffix('.txt')
            if proc.returncode!=0 or not txt.is_file() or not txt.stat().st_size:
                raise RuntimeError(f'{arm} row {idx}: exit {proc.returncode}; {proc.stderr[-300:]}')
            ref=normalize(phrase['text']); hyp=normalize(txt.read_text(encoding='utf-8'))
            rw,hw=ref.split(),hyp.split()
            row={'arm':arm,'row_index':idx,'reference':ref,'asr_hypothesis':hyp,
                 'wer_edits':edits(rw,hw),'wer_ref_words':len(rw),
                 'cer_edits':edits(ref,hyp),'cer_ref_chars':len(ref),
                 'source_wav_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
            rows.append(row)
            OUT.write_text(json.dumps({'status':'running','results':rows},ensure_ascii=False,indent=2)+'\n')
            print(arm,idx,round(row['wer_edits']/len(rw),3),flush=True)
    summary={'status':'complete','proxy':'Parakeet TDT v3 Q4 ASR on first-pass TTS WAVs; not MOS',
             'results':rows,'arms':{}}
    for arm in ('piper','kitten'):
        a=[r for r in rows if r['arm']==arm]
        summary['arms'][arm]={'clips':len(a),'micro_wer':sum(r['wer_edits'] for r in a)/sum(r['wer_ref_words'] for r in a),
                              'macro_wer':statistics.mean(r['wer_edits']/r['wer_ref_words'] for r in a),
                              'micro_cer':sum(r['cer_edits'] for r in a)/sum(r['cer_ref_chars'] for r in a)}
    OUT.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print('summary',summary['arms'])


if __name__=='__main__':main()
