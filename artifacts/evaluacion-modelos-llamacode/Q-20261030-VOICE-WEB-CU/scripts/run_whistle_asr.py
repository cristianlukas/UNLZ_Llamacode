#!/usr/bin/env python3
"""Q191 preregistered Whistle ASR on 20 FLEURS es_419 clips, two passes."""
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import time
import unicodedata

import needle
import psutil

BASE = Path(__file__).resolve().parents[1]
REPO = BASE.parents[2]
MANIFEST = BASE / 'receipts/fleurs-corpus-manifest.json'
OUT = BASE / 'runs/whistle-asr.json'


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


def main():
    assert os.environ.get('NEEDLE_TELEMETRY') == '0', 'telemetry must be disabled'
    lock = json.loads((REPO / 'WORK_QUEUE.lock').read_text())
    assert lock['token'] == 'q191-voice-web-cu-20261030'
    assert hashlib.sha256(Path('/home/cristian/.cache/cactus-needle/whistle/2.0.0/whistle.cact').read_bytes()).hexdigest() == 'b6e02f048568ac5d01a2042556c658061e699acbc0aa2a1439f52f3d461dffeb'
    manifest = json.loads(MANIFEST.read_text())
    assert len(manifest['clips']) == 20
    for clip in manifest['clips']:
        assert hashlib.sha256(Path(clip['path']).read_bytes()).hexdigest() == clip['sha256']
    start = time.monotonic()
    engine = needle.Whistle()
    init_seconds = time.monotonic() - start
    engine.transcribe(manifest['clips'][0]['path'], language='es')  # excluded warmup
    process = psutil.Process()
    results = []
    for pass_idx in (1, 2):
        for clip in manifest['clips']:
            rss_before = process.memory_info().rss
            started = time.monotonic()
            output = engine.transcribe(clip['path'], language='es')
            elapsed = time.monotonic() - started
            rss_after = process.memory_info().rss
            ref = normalize(clip['normalized_reference'])
            hyp = normalize(output.get('text', ''))
            ref_words, hyp_words = ref.split(), hyp.split()
            row = {'pass': pass_idx, 'row_index': clip['row_index'], 'filename': clip['filename'],
                   'duration_seconds': clip['duration_seconds'], 'reference': ref, 'hypothesis': hyp,
                   'elapsed_seconds': elapsed, 'rtf': elapsed / clip['duration_seconds'],
                   'ttft_ms_reported': output.get('ttft_ms'), 'decode_tps_reported': output.get('decode_tps'),
                   'wer_edits': edits(ref_words, hyp_words), 'wer_ref_words': len(ref_words),
                   'cer_edits': edits(ref, hyp), 'cer_ref_chars': len(ref),
                   'rss_before_bytes': rss_before, 'rss_after_bytes': rss_after}
            results.append(row)
            OUT.parent.mkdir(exist_ok=True)
            OUT.write_text(json.dumps({'status': 'running', 'init_seconds': init_seconds, 'results': results}, ensure_ascii=False, indent=2) + '\n')
            print(pass_idx, clip['row_index'], round(elapsed, 3), round(row['wer_edits']/max(1,row['wer_ref_words']),3), flush=True)
    first = [r for r in results if r['pass'] == 1]
    summary = {'status': 'complete', 'engine': 'Whistle 2.0.0 / cactus-needle 3.2.8',
               'init_seconds': init_seconds, 'warmup_excluded': True, 'clips': 20, 'passes': 2,
               'micro_wer': sum(r['wer_edits'] for r in first) / sum(r['wer_ref_words'] for r in first),
               'macro_wer': statistics.mean(r['wer_edits']/r['wer_ref_words'] for r in first),
               'micro_cer': sum(r['cer_edits'] for r in first) / sum(r['cer_ref_chars'] for r in first),
               'median_elapsed_seconds': statistics.median(r['elapsed_seconds'] for r in results),
               'p95_elapsed_seconds': sorted(r['elapsed_seconds'] for r in results)[int(0.95*(len(results)-1))],
               'median_rtf': statistics.median(r['rtf'] for r in results),
               'median_ttft_ms_reported': statistics.median(r['ttft_ms_reported'] for r in results if isinstance(r['ttft_ms_reported'], (int, float))),
               'max_rss_bytes': max(r['rss_after_bytes'] for r in results), 'results': results}
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print('summary', {k: summary[k] for k in ['micro_wer','micro_cer','median_elapsed_seconds','p95_elapsed_seconds','median_rtf']}, flush=True)


if __name__ == '__main__':
    main()
