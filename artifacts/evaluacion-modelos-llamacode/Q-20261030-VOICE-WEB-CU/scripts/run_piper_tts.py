#!/usr/bin/env python3
"""Q191 Piper es_AR Daniela TTS: fixed ten phrases, two resident passes."""
import hashlib
import json
from pathlib import Path
import statistics
import time
import wave

import psutil
from piper.voice import PiperVoice

BASE = Path(__file__).resolve().parents[1]
REPO = BASE.parents[2]
PHRASES = BASE / 'receipts/tts-phrases.json'
MODEL = Path('/media/cristian/7CFE1E0FFE1DC1F6/piper/voices/es_AR/daniela_high/es/es_AR/daniela/high/es_AR-daniela-high.onnx')
WAVS = BASE / 'runs/piper-wav'
OUT = BASE / 'runs/piper-tts.json'


def main():
    assert json.loads((REPO/'WORK_QUEUE.lock').read_text())['token'] == 'q191-voice-web-cu-20261030'
    assert hashlib.sha256(PHRASES.read_bytes()).hexdigest() == '41af7111c8f2cc13da2fe13ea84d2bd66592ac0bc535a4716903d0d648677afb'
    assert hashlib.sha256(MODEL.read_bytes()).hexdigest() == '7ceb1fc0dab349418c5b54a639ae9ee595212d7c9ea422220d8419163d5cc985'
    phrases = json.loads(PHRASES.read_text())['phrases']
    assert len(phrases)==10
    start = time.monotonic()
    voice = PiperVoice.load(MODEL, use_cuda=False)
    init_seconds = time.monotonic()-start
    list(voice.synthesize('Hola, ¿cómo estás?'))  # excluded warmup
    process=psutil.Process()
    rows=[]
    WAVS.mkdir(parents=True,exist_ok=True)
    for pass_idx in (1,2):
        for phrase in phrases:
            started=time.monotonic()
            first=None
            chunks=[]
            rss_peak=process.memory_info().rss
            for chunk in voice.synthesize(phrase['text']):
                if first is None:first=time.monotonic()-started
                chunks.append(chunk)
                rss_peak=max(rss_peak,process.memory_info().rss)
            elapsed=time.monotonic()-started
            assert chunks and first is not None
            pcm=b''.join(x.audio_int16_bytes for x in chunks)
            sample_rate=chunks[0].sample_rate
            assert all(x.sample_rate==sample_rate and x.sample_width==2 and x.sample_channels==1 for x in chunks)
            audio_seconds=len(pcm)/(sample_rate*2)
            row={'pass':pass_idx,'row_index':phrase['row_index'],'first_chunk_seconds':first,
                 'elapsed_seconds':elapsed,'audio_seconds':audio_seconds,'rtf':elapsed/audio_seconds,
                 'chunks':len(chunks),'peak_rss_bytes':rss_peak}
            if pass_idx==1:
                path=WAVS/f'row{phrase["row_index"]}.wav'
                with wave.open(str(path),'wb') as wav:
                    wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(sample_rate);wav.writeframes(pcm)
                row['wav_path']=str(path)
                row['wav_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            rows.append(row)
            OUT.parent.mkdir(exist_ok=True)
            OUT.write_text(json.dumps({'status':'running','init_seconds':init_seconds,'results':rows},indent=2)+'\n')
            print(pass_idx,phrase['row_index'],round(first,3),round(elapsed,3),round(row['rtf'],3),flush=True)
    summary={'status':'complete','engine':'piper-tts 1.8.0 / es_AR Daniela high','init_seconds':init_seconds,
             'warmup_excluded':True,'phrases':10,'passes':2,
             'median_first_chunk_seconds':statistics.median(r['first_chunk_seconds'] for r in rows),
             'p95_first_chunk_seconds':sorted(r['first_chunk_seconds'] for r in rows)[int(0.95*(len(rows)-1))],
             'median_rtf':statistics.median(r['rtf'] for r in rows),
             'median_elapsed_seconds':statistics.median(r['elapsed_seconds'] for r in rows),
             'peak_rss_bytes':max(r['peak_rss_bytes'] for r in rows),'results':rows}
    OUT.write_text(json.dumps(summary,indent=2)+'\n')
    print('summary',{k:round(summary[k],3) for k in ['median_first_chunk_seconds','p95_first_chunk_seconds','median_rtf','peak_rss_bytes']})


if __name__=='__main__':main()
