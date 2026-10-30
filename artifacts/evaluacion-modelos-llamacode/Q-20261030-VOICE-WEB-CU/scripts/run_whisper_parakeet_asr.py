#!/usr/bin/env python3
"""Q191 CPU ASR controls on the exact Whistle corpus, per-turn CLI route."""
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import time

import psutil
from run_whistle_asr import normalize, edits

BASE = Path(__file__).resolve().parents[1]
REPO = BASE.parents[2]
MANIFEST = BASE / 'receipts/fleurs-corpus-manifest.json'
RUNS = BASE / 'runs'
LOGS = BASE / 'logs'
SRC = Path('/home/cristian/.cache/q191-whisper.cpp/build-q191/bin')
MODELS = {
    'whisper-base': (SRC / 'whisper-cli', Path('/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/AppData/Local/LlamaCode/LlamaCode/voice/whisper-base/ggml-base.bin'),
                     'afe26eb6413f59967d8307fd6ded82eb8b4d2debecc058c52a747ecb8702c551',
                     '60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe'),
    'parakeet-q4': (SRC / 'parakeet-cli', Path('/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/AppData/Local/LlamaCode/LlamaCode/voice/parakeet-tdt-0.6b-v3/ggml-parakeet-tdt-0.6b-v3-q4_0.bin'),
                    'c7a8f59e67d6bbe61066da2fbf3d9e0eb2876e337cfb2a51d51cbabd4bfda80b',
                    'aa7fe2f5fb47d863ca23e8b1d490632d63a2599f515268b6d6bd656158dad45e')
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def one(arm, clip, pass_idx):
    binary, model, _, _ = MODELS[arm]
    prefix = RUNS / f'{arm}-p{pass_idx}-row{clip["row_index"]}'
    argv = [str(binary), '-m', str(model), '-f', clip['path'], '-t', '16', '-ng', '-otxt', '-of', str(prefix), '-np']
    if arm == 'whisper-base':
        argv.extend(['-l', 'es', '-nt'])
    log = LOGS / f'{arm}-p{pass_idx}-row{clip["row_index"]}.log'
    started = time.monotonic()
    with log.open('wb') as stream:
        proc = subprocess.Popen(argv, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        samples = []
        while proc.poll() is None:
            try: samples.append(psutil.Process(proc.pid).memory_info().rss)
            except psutil.NoSuchProcess: pass
            time.sleep(0.01)
        exit_code = proc.wait()
    elapsed = time.monotonic() - started
    txt = prefix.with_suffix('.txt')
    if exit_code != 0 or not txt.is_file() or txt.stat().st_size == 0:
        raise RuntimeError(f'{arm} row {clip["row_index"]}: exit={exit_code}, text_exists={txt.exists()}, log={log}')
    ref = normalize(clip['normalized_reference'])
    hyp = normalize(txt.read_text(encoding='utf-8'))
    rw, hw = ref.split(), hyp.split()
    return {'arm': arm, 'pass': pass_idx, 'row_index': clip['row_index'], 'filename': clip['filename'],
            'reference': ref, 'hypothesis': hyp, 'elapsed_seconds': elapsed,
            'duration_seconds': clip['duration_seconds'], 'rtf': elapsed/clip['duration_seconds'],
            'wer_edits': edits(rw, hw), 'wer_ref_words': len(rw),
            'cer_edits': edits(ref, hyp), 'cer_ref_chars': len(ref),
            'peak_rss_bytes': max(samples, default=0), 'exit_code': exit_code,
            'text_path': str(txt), 'log_path': str(log)}


def main():
    assert json.loads((REPO/'WORK_QUEUE.lock').read_text())['token'] == 'q191-voice-web-cu-20261030'
    clips = json.loads(MANIFEST.read_text())['clips']
    assert len(clips) == 20
    for binary, model, binary_sha, model_sha in MODELS.values():
        assert sha(binary) == binary_sha and sha(model) == model_sha
    RUNS.mkdir(exist_ok=True)
    LOGS.mkdir(exist_ok=True)
    for arm in MODELS:
        rows = []
        for pass_idx in (1, 2):
            for clip in clips:
                row = one(arm, clip, pass_idx)
                rows.append(row)
                (RUNS/f'{arm}-asr-progress.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
                print(arm,pass_idx,clip['row_index'],round(row['elapsed_seconds'],3),round(row['wer_edits']/row['wer_ref_words'],3),flush=True)
        first = [r for r in rows if r['pass']==1]
        summary = {'status':'complete','arm':arm,'clips':20,'passes':2,'route':'per-turn process, model reload each clip',
                   'micro_wer':sum(r['wer_edits'] for r in first)/sum(r['wer_ref_words'] for r in first),
                   'macro_wer':statistics.mean(r['wer_edits']/r['wer_ref_words'] for r in first),
                   'micro_cer':sum(r['cer_edits'] for r in first)/sum(r['cer_ref_chars'] for r in first),
                   'median_elapsed_seconds':statistics.median(r['elapsed_seconds'] for r in rows),
                   'p95_elapsed_seconds':sorted(r['elapsed_seconds'] for r in rows)[int(0.95*(len(rows)-1))],
                   'median_rtf':statistics.median(r['rtf'] for r in rows),
                   'peak_rss_bytes':max(r['peak_rss_bytes'] for r in rows), 'results':rows}
        (RUNS/f'{arm}-asr.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
        print('summary',arm,{k:round(summary[k],4) for k in ['micro_wer','micro_cer','median_elapsed_seconds','p95_elapsed_seconds','median_rtf']},flush=True)


if __name__=='__main__':
    main()
