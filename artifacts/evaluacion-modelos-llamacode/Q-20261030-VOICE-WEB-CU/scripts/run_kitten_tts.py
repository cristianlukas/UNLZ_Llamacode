#!/usr/bin/env python3
"""Q191 Kitten-TTS2 batch CPU comparison on the fixed ten Spanish phrases."""
import hashlib
import json
from pathlib import Path
import statistics
import time
import wave

import psutil
from kitten_tts_cpp import KittenTTS

BASE = Path(__file__).resolve().parents[1]
REPO = BASE.parents[2]
PHRASES = BASE / 'receipts/tts-phrases.json'
ROOT = Path('/home/cristian/.cache/kitten-tts/KittenML/kitten-tts-2/c93cb7c271baa51d9ae8204d5277988906f235a2')
WEIGHTS = {'cpp/model-tq2_1.gguf':'c6ad7ee1dbda3fd7a2b3dc3b8b1689f4687f761b7bd6509569b5592f543548f7',
           'cpp/student_w4/decoder.pt':'47ea803ad46a87f876c1b3b02f05e93dad15e4d2b58eafeb34884f52cdec0268',
           'cpp/student_w4/voices.json':'5aa77686471a5fedfb6452322bce06d8bfdec8af33329aa24f450b9d71918d8b'}
WAVS = BASE / 'runs/kitten-wav'
OUT = BASE / 'runs/kitten-tts.json'


def main():
    assert json.loads((REPO/'WORK_QUEUE.lock').read_text())['token']=='q191-voice-web-cu-20261030'
    assert hashlib.sha256(PHRASES.read_bytes()).hexdigest()=='41af7111c8f2cc13da2fe13ea84d2bd66592ac0bc535a4716903d0d648677afb'
    for rel,digest in WEIGHTS.items():
        assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==digest
    phrases=json.loads(PHRASES.read_text())['phrases']
    assert len(phrases)==10
    start=time.monotonic()
    model=KittenTTS('KittenML/kitten-tts-2',revision='c93cb7c271baa51d9ae8204d5277988906f235a2',decoder='student_w4',threads=16,device='cpu',offline=True)
    init_seconds=time.monotonic()-start
    model.generate_to_file('Hola, ¿cómo estás?', '/home/cristian/.cache/q191-kitten-warmup.wav',voice='SpanishTango')
    process=psutil.Process()
    WAVS.mkdir(parents=True,exist_ok=True)
    rows=[]
    for pass_idx in (1,2):
        for phrase in phrases:
            path=WAVS/f'p{pass_idx}-row{phrase["row_index"]}.wav'
            rss_before=process.memory_info().rss
            started=time.monotonic()
            model.generate_to_file(phrase['text'],str(path),voice='SpanishTango',preset='stable')
            elapsed=time.monotonic()-started
            assert path.is_file() and path.stat().st_size>44
            with wave.open(str(path),'rb') as wav:
                duration=wav.getnframes()/wav.getframerate()
                rate=wav.getframerate()
            row={'pass':pass_idx,'row_index':phrase['row_index'],'elapsed_to_complete_wav_seconds':elapsed,
                 'audio_seconds':duration,'sample_rate':rate,'rtf':elapsed/duration,
                 'rss_before_bytes':rss_before,'rss_after_bytes':process.memory_info().rss,
                 'wav_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
            if pass_idx==1:row['wav_path']=str(path)
            else:path.unlink()
            rows.append(row)
            OUT.parent.mkdir(exist_ok=True)
            OUT.write_text(json.dumps({'status':'running','init_seconds':init_seconds,'results':rows},indent=2)+'\n')
            print('Q191',pass_idx,phrase['row_index'],round(elapsed,3),round(row['rtf'],3),flush=True)
    summary={'status':'complete','engine':'kitten_tts_cpp 0.2.0 / Kitten-TTS2 / SpanishTango / student_w4',
             'init_seconds':init_seconds,'warmup_excluded':True,'phrases':10,'passes':2,
             'median_complete_wav_seconds':statistics.median(r['elapsed_to_complete_wav_seconds'] for r in rows),
             'p95_complete_wav_seconds':sorted(r['elapsed_to_complete_wav_seconds'] for r in rows)[int(0.95*(len(rows)-1))],
             'median_rtf':statistics.median(r['rtf'] for r in rows),
             'max_rss_after_bytes':max(r['rss_after_bytes'] for r in rows),'results':rows}
    OUT.write_text(json.dumps(summary,indent=2)+'\n')
    print('Q191 SUMMARY',{k:round(summary[k],3) for k in ['init_seconds','median_complete_wav_seconds','p95_complete_wav_seconds','median_rtf']},flush=True)


if __name__=='__main__':main()
