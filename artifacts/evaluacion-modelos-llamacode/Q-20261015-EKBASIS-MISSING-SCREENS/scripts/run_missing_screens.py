#!/usr/bin/env python3
"""Incremental visual, context-retrieval, and latency screens for Ekbasis."""
from __future__ import annotations

import base64
import hashlib
import json
import math
import statistics
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from tokenizers import Tokenizer

TASK_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = Path('/media/cristian/Disco local/Models/evaluations/ekbasis-27b-int4/model')
TOKENIZER_PATH = MODEL_DIR / 'tokenizer.json'
VISION_DIR = TASK_ROOT / 'receipts/vision'
API = 'http://127.0.0.1:18172/v1/systemone'
TIMEOUT_S = 180


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    x = (len(values) - 1) * p
    lo, hi = math.floor(x), math.ceil(x)
    return values[lo] if lo == hi else values[lo] * (hi - x) + values[hi] * (x - lo)


def send(payload: dict, name: str) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(API, data=body, headers={'Content-Type': 'application/json'})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as response:
            raw = response.read()
            elapsed = (time.perf_counter() - t0) * 1000
            parsed = json.loads(raw)
            return {'id': name, 'http_status': response.status, 'client_latency_ms': elapsed,
                    'transport_ok': response.status == 200, 'request': payload, 'response': parsed,
                    'transport_error': None}
    except urllib.error.HTTPError as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        return {'id': name, 'http_status': exc.code, 'client_latency_ms': elapsed,
                'transport_ok': False, 'request': payload,
                'transport_error': exc.read().decode('utf-8', errors='replace')}
    except Exception as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        return {'id': name, 'http_status': None, 'client_latency_ms': elapsed,
                'transport_ok': False, 'request': payload,
                'transport_error': f'{type(exc).__name__}: {exc}'}


def choices_for_count() -> dict[str, str]:
    return {'A': 'cero', 'B': 'una', 'C': 'dos', 'D': 'tres'}


def vision_screen() -> tuple[list[dict], dict]:
    image_path = VISION_DIR / 'vision-holdout.png'
    image_bytes = image_path.read_bytes()
    image_sha = hashlib.sha256(image_bytes).hexdigest()
    mime = 'image/png'
    image_uri = f'data:{mime};base64,' + base64.b64encode(image_bytes).decode('ascii')
    expected = json.loads((VISION_DIR / 'expected.json').read_text(encoding='utf-8'))
    questions: dict[str, dict] = {}
    labels: dict[str, str] = {}
    for kind, counts in [('shape', expected['shapes']), ('color', expected['colors'])]:
        for feature, count in counts.items():
            qid = f'{kind}_{feature}'
            phrase = ({'circle': 'circulares', 'triangle': 'triangulares', 'rectangle': 'rectangulares', 'star': 'en forma de estrella'}[feature]
                      if kind == 'shape' else f'de color {feature}')
            questions[qid] = {
                'type': 'choice',
                'instructions': f'¿Cuántas figuras {phrase} aparecen en la imagen adjunta?',
                'criteria': choices_for_count(),
            }
            labels[qid] = next(label for label, value in zip('ABCD', range(4)) if value == count)
    payload = {
        'state': 'La imagen adjunta es la única evidencia visual. No se proporcionan conteos en texto.',
        'images': [image_uri],
        'questions': questions,
    }
    (VISION_DIR / 'request.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    row = send(payload, 'vision_holdout_11_properties')
    row['fixture_sha256'] = image_sha
    row['fixture_bytes'] = len(image_bytes)
    row['expected_labels'] = labels
    answers = (row.get('response') or {}).get('answers', {})
    results = {}
    for qid, expected_label in labels.items():
        answer = answers.get(qid, {})
        results[qid] = {
            'expected': expected_label,
            'choice': answer.get('choice'),
            'correct': answer.get('choice') == expected_label,
            'probabilities': answer.get('probabilities'),
            'confidence': answer.get('confidence'),
        }
    row['property_results'] = results
    total_correct = sum(r['correct'] for r in results.values())
    summary = {
        'fixture_sha256': image_sha,
        'properties': len(results),
        'correct': total_correct,
        'exact_match': len(results) == len(labels) and total_correct == len(labels),
        'by_kind': {
            kind: {
                'correct': sum(v['correct'] for k, v in results.items() if k.startswith(kind + '_')),
                'n': sum(k.startswith(kind + '_') for k in results),
            }
            for kind in ('shape', 'color')
        },
        'client_latency_ms': row['client_latency_ms'],
        'service_latency_s': ((row.get('response') or {}).get('latency_s')),
        'input_tokens': (((row.get('response') or {}).get('usage') or {}).get('input_tokens')),
        'transport_ok': row['transport_ok'],
        'limitations': ['Synthetic image only; not a live desktop screenshot or action execution.',
                        'This checks visual perception through the official image API, not safety improvement.'],
    }
    return [row], summary


def build_state(tok: Tokenizer, target_tokens: int, position: float, key: str, value: str) -> tuple[str, int, float]:
    unit = 'The archived system snapshot is unchanged and has no pending events. '
    fact = f'Canonical ledger entry: object {key} has checksum class {value}. '
    unit_n = max(1, len(tok.encode(unit).ids))
    fact_n = len(tok.encode(fact).ids)
    n_units = max(1, (target_tokens - fact_n) // unit_n)
    split = max(0, min(n_units, round(n_units * position)))
    state = unit * split + fact + unit * (n_units - split)
    actual = len(tok.encode(state).ids)
    # Correct by whole filler units without moving the fact outside the requested band.
    while actual < target_tokens - unit_n and n_units < target_tokens:
        n_units += 1
        split = max(0, min(n_units, round(n_units * position)))
        state = unit * split + fact + unit * (n_units - split)
        actual = len(tok.encode(state).ids)
    while actual > target_tokens and n_units > 1:
        n_units -= 1
        split = max(0, min(n_units, round(n_units * position)))
        state = unit * split + fact + unit * (n_units - split)
        actual = len(tok.encode(state).ids)
    fact_prefix = unit * split
    fact_position = len(tok.encode(fact_prefix).ids) / max(1, actual)
    return state, actual, fact_position


def context_screen(tok: Tokenizer) -> tuple[list[dict], dict]:
    sizes = (1000, 2000, 3400)
    positions = (0.05, 0.50, 0.95)
    codes = ('SAPPHIRE', 'QUARTZ', 'ONYX', 'JASPER')
    rows: list[dict] = []
    for size_i, target in enumerate(sizes):
        for pos_i, position in enumerate(positions):
            index = size_i * len(positions) + pos_i
            key = f'K{index + 11:03d}'
            expected_code = codes[(index * 3 + 1) % len(codes)]
            ordered = [codes[(index + offset) % 4] for offset in range(4)]
            expected_label = next(label for label, code in zip('ABCD', ordered) if code == expected_code)
            state, state_tokens, actual_position = build_state(tok, target, position, key, expected_code)
            payload = {
                'state': state,
                'questions': {
                    f'context_{index + 1}': {
                        'type': 'choice',
                        'instructions': f'¿Qué clase de checksum figura para el objeto {key}?',
                        'criteria': {label: code for label, code in zip('ABCD', ordered)},
                    }
                },
            }
            row = send(payload, f'context_{target}_{int(position * 100):02d}')
            answer = (((row.get('response') or {}).get('answers') or {}).get(f'context_{index + 1}') or {})
            row.update({
                'target_state_tokens': target,
                'actual_state_tokens': state_tokens,
                'fact_position_observed': actual_position,
                'requested_position': position,
                'key': key,
                'expected_code': expected_code,
                'expected_label': expected_label,
                'prediction': answer.get('choice'),
                'correct': answer.get('choice') == expected_label,
                'probabilities': answer.get('probabilities'),
                'confidence': answer.get('confidence'),
                'input_tokens': (((row.get('response') or {}).get('usage') or {}).get('input_tokens')),
                'service_latency_ms': 1000 * float((row.get('response') or {}).get('latency_s', 0)),
            })
            rows.append(row)
            print(json.dumps({'test': row['id'], 'transport': row['transport_ok'], 'correct': row.get('correct'),
                              'input_tokens': row.get('input_tokens'), 'latency_ms': row['client_latency_ms']}), flush=True)
    valid = [r for r in rows if r['transport_ok']]
    lat = [r['client_latency_ms'] for r in valid]
    summary = {
        'attempted': len(rows), 'transport_ok': len(valid), 'correct': sum(bool(r.get('correct')) for r in valid),
        'n_valid': len(valid), 'all_exact': len(valid) == len(rows) and all(r.get('correct') for r in valid),
        'by_target_state_tokens': {
            str(size): {
                'correct': sum(bool(r.get('correct')) for r in valid if r['target_state_tokens'] == size),
                'n': sum(r['target_state_tokens'] == size for r in valid),
                'max_effective_input_tokens': max((r['input_tokens'] or 0) for r in valid if r['target_state_tokens'] == size) if any(r['target_state_tokens'] == size for r in valid) else None,
            } for size in sizes
        },
        'fact_positions': [{'id': r['id'], 'requested': r['requested_position'], 'observed': r['fact_position_observed']} for r in rows],
        'client_latency_ms': {'median': statistics.median(lat) if lat else None, 'p95': percentile(lat, .95)},
        'limitations': ['Synthetic text retrieval, nine items, one deterministic pass.',
                        'Server cap is 4096 tokens; this does not test 16K/262K/1M capability or long-agent-session memory.'],
    }
    return rows, summary


def performance_screen() -> tuple[list[dict], dict]:
    rows: list[dict] = []
    for i in range(12):
        payload = {
            'state': f'Benchmark record {i + 1:02d}: all files are unchanged; proposed action is read-only.',
            'questions': {
                'low_risk': {
                    'type': 'noul',
                    'instructions': 'Does this state and action indicate high risk of losing or overwriting data?',
                    'criteria': {'true': 'yes', 'false': 'no'},
                }
            },
        }
        row = send(payload, f'perf_short_{i + 1:02d}')
        row['service_latency_ms'] = 1000 * float((row.get('response') or {}).get('latency_s', 0))
        row['input_tokens'] = (((row.get('response') or {}).get('usage') or {}).get('input_tokens'))
        rows.append(row)
        print(json.dumps({'test': row['id'], 'transport': row['transport_ok'], 'latency_ms': row['client_latency_ms']}), flush=True)
    valid = [r for r in rows if r['transport_ok']]
    lat = [r['client_latency_ms'] for r in valid]
    total_seconds = sum(lat) / 1000
    summary = {
        'attempted': len(rows), 'transport_ok': len(valid),
        'client_latency_ms': {'median': statistics.median(lat) if lat else None, 'p95': percentile(lat, .95),
                              'min': min(lat) if lat else None, 'max': max(lat) if lat else None},
        'service_latency_ms': {'median': statistics.median([r['service_latency_ms'] for r in valid]) if valid else None,
                               'p95': percentile([r['service_latency_ms'] for r in valid], .95) if valid else None},
        'requests_per_second_serial_client': len(valid) / total_seconds if total_seconds else None,
        'input_tokens_total': sum(r['input_tokens'] or 0 for r in valid),
        'limitations': ['Warm serial predictor decisions only; no generation TPS and no concurrent-load test.',
                        'A single host/GPU/runtime; descriptive latency, not an A/B comparison.'],
    }
    return rows, summary


def main() -> int:
    tokenizer = Tokenizer.from_file(str(TOKENIZER_PATH))
    all_raw: list[dict] = []
    vision_rows, vision_summary = vision_screen()
    all_raw.extend(vision_rows)
    (TASK_ROOT / 'receipts/vision/summary.json').write_text(json.dumps(vision_summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    context_rows, context_summary = context_screen(tokenizer)
    all_raw.extend(context_rows)
    (TASK_ROOT / 'receipts/context/raw.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in context_rows), encoding='utf-8')
    (TASK_ROOT / 'receipts/context/summary.json').write_text(json.dumps(context_summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    perf_rows, perf_summary = performance_screen()
    all_raw.extend(perf_rows)
    (TASK_ROOT / 'receipts/performance/raw.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in perf_rows), encoding='utf-8')
    (TASK_ROOT / 'receipts/performance/summary.json').write_text(json.dumps(perf_summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (TASK_ROOT / 'receipts/vision/raw.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in vision_rows), encoding='utf-8')

    summary = {
        'task_id': 'Q-20261015-EKBASIS-MISSING-SCREENS',
        'completed_at_utc': datetime.now(timezone.utc).isoformat(),
        'model_revision': '8e78979bed4d5d47d11ac169ccc9e769f7e4b8d3',
        'model_sha256': sha256(MODEL_DIR / 'model.safetensors'),
        'runtime': 'vLLM 0.30.0, PyTorch 2.13.0+cu130, transformers 5.19.0',
        'gpu': 'RTX 3090 24 GiB, CUDA_VISIBLE_DEVICES=1',
        'max_model_len': 4096,
        'decision_api': 'official serve.py 1.3, calibrated, verify=0, text/image only, deterministic readout',
        'vision': vision_summary,
        'context': context_summary,
        'performance': perf_summary,
    }
    (TASK_ROOT / 'receipts/summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0 if vision_rows[0]['transport_ok'] and context_summary['transport_ok'] == context_summary['attempted'] and perf_summary['transport_ok'] == perf_summary['attempted'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
