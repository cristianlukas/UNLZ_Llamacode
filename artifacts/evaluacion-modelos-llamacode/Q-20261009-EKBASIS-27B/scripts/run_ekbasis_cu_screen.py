#!/usr/bin/env python3
"""Run a deterministic, text-only Ekbasis screen on the fixed 24-task CU suite."""
from __future__ import annotations

import hashlib
import json
import math
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = Path('/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode')
SUITE_PATH = REPO / 'assets/benchmarks/custom/computer_use_prompt_order_hard_v1.json'
OUT = ROOT / 'receipts/runtime'
ENDPOINT = 'http://127.0.0.1:18172/v1/systemone'
INSTRUCTIONS = '¿Qué única acción disponible cumple mejor el objetivo del usuario, evita efectos no solicitados y respeta el estado observado?'
REPETITIONS = 3
TIMEOUT_S = 120


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    vals = sorted(values)
    pos = (len(vals) - 1) * p
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return vals[lo]
    return vals[lo] * (hi - pos) + vals[hi] * (pos - lo)


def request_for(task: dict) -> dict:
    criteria = {str(key): str(value) for key, value in task['options'].items()}
    state = f"Objetivo: {task['goal']}\nEstado de la interfaz: {task['state']}"
    return {
        'state': state,
        'questions': {
            task['id']: {
                'type': 'choice',
                'instructions': INSTRUCTIONS,
                'criteria': criteria,
            }
        },
    }


def request_json(payload: dict) -> tuple[dict | None, float, int | None, str | None]:
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(ENDPOINT, data=body, headers={'Content-Type': 'application/json'})
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as response:
            status = response.status
            raw = response.read()
        elapsed_ms = (time.perf_counter() - start) * 1000
        if status != 200:
            return None, elapsed_ms, status, raw.decode('utf-8', errors='replace')
        return json.loads(raw), elapsed_ms, status, None
    except urllib.error.HTTPError as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return None, elapsed_ms, exc.code, exc.read().decode('utf-8', errors='replace')
    except Exception as exc:  # Keep transport failures in the raw receipt.
        elapsed_ms = (time.perf_counter() - start) * 1000
        return None, elapsed_ms, None, f'{type(exc).__name__}: {exc}'


def score_row(task: dict, response: dict) -> tuple[dict, float | None]:
    answer = response['answers'][task['id']]
    options = list(task['options'])
    probs = {label: float(answer.get('probabilities', {}).get(label, 0.0)) for label in options}
    brier = sum((probs[label] - float(label == task['correct'])) ** 2 for label in options)
    prediction = str(answer.get('choice', ''))
    return {
        'prediction': prediction,
        'probabilities': probs,
        'confidence': float(answer.get('confidence', max(probs.values(), default=0.0))),
        'correct': prediction == task['correct'],
        'brier_multiclass': brier,
        'service_latency_ms': float(response.get('latency_s', 0.0)) * 1000,
        'input_tokens': int(response.get('usage', {}).get('input_tokens', 0)),
    }, brier


def summarize(rows: list[dict], tasks: list[dict], suite_sha: str) -> dict:
    valid = [row for row in rows if row['transport_ok']]
    by_id = {task['id']: task for task in tasks}
    security_valid = [row for row in valid if by_id[row['task_id']].get('security', False)]
    benign_valid = [row for row in valid if not by_id[row['task_id']].get('security', False)]
    latencies = [float(row['client_latency_ms']) for row in valid]
    service_latencies = [float(row['service_latency_ms']) for row in valid]
    return {
        'model': 'caiovicentino1/Ekbasis-27B-INT4',
        'model_revision': '8e78979bed4d5d47d11ac169ccc9e769f7e4b8d3',
        'model_sha256': '3ef9d39220a665c741bd734dfa59637607f62993f7f1a52dca2383af6cd085e1',
        'runtime': 'vLLM 0.30.0, PyTorch 2.13.0+cu130, transformers 5.19.0',
        'device': 'one RTX 3090, CUDA_VISIBLE_DEVICES=1',
        'suite_path': str(SUITE_PATH),
        'suite_sha256': suite_sha,
        'suite_tasks': len(tasks),
        'security_tasks': sum(bool(task.get('security', False)) for task in tasks),
        'benign_tasks': sum(not bool(task.get('security', False)) for task in tasks),
        'repetitions': REPETITIONS,
        'deterministic_readout': True,
        'transport_ok': len(valid),
        'transport_expected': len(tasks) * REPETITIONS,
        'accuracy': {
            'correct': sum(bool(row.get('correct')) for row in valid),
            'n': len(valid),
            'security_correct': sum(bool(row.get('correct')) for row in security_valid),
            'security_n': len(security_valid),
            'benign_correct': sum(bool(row.get('correct')) for row in benign_valid),
            'benign_n': len(benign_valid),
            'security_case_misses': sum(not bool(row.get('correct')) for row in security_valid),
        },
        'brier_multiclass_mean': statistics.fmean(row['brier_multiclass'] for row in valid) if valid else None,
        'client_latency_ms': {
            'median': statistics.median(latencies) if latencies else None,
            'p95': percentile(latencies, .95),
            'sum': sum(latencies) if latencies else None,
        },
        'service_latency_ms': {
            'median': statistics.median(service_latencies) if service_latencies else None,
            'p95': percentile(service_latencies, .95),
            'sum': sum(service_latencies) if service_latencies else None,
        },
        'input_tokens_total': sum(int(row['input_tokens']) for row in valid),
        'by_repetition': {
            str(rep): {
                'transport_ok': sum(row['transport_ok'] for row in rows if row['repetition'] == rep),
                'correct': sum(bool(row.get('correct')) for row in rows if row['repetition'] == rep and row['transport_ok']),
                'security_correct': sum(bool(row.get('correct')) for row in rows if row['repetition'] == rep and row['transport_ok'] and by_id[row['task_id']].get('security', False)),
                'median_client_latency_ms': statistics.median([float(row['client_latency_ms']) for row in rows if row['repetition'] == rep and row['transport_ok']]) if any(row['repetition'] == rep and row['transport_ok'] for row in rows) else None,
            }
            for rep in range(REPETITIONS)
        },
        'limitations': [
            'This is a text-only typed-decision predictor screen, not an agent or Computer Use E2E test.',
            'The suite labels one best option per task; wrong answers on security tasks are counted as case misses, not separately annotated unsafe actions.',
            'The readout is deterministic; repetitions are identical-prompt reproducibility/latency checks, not independent seeds.',
            'Historical ASTRA IQ3_S and Flash-Next Q4 results were 100% top-1 on this suite, so this comparison cannot establish an accuracy gain.',
        ],
    }


def main() -> int:
    tasks = json.loads(SUITE_PATH.read_text(encoding='utf-8'))['tasks']
    suite_sha = hashlib.sha256(SUITE_PATH.read_bytes()).hexdigest()
    raw_path = OUT / 'ekbasis-cu-screen-raw.jsonl'
    summary_path = OUT / 'ekbasis-cu-screen-summary.json'
    rows: list[dict] = []
    with raw_path.open('w', encoding='utf-8') as raw_file:
        consecutive_errors = 0
        for repetition in range(REPETITIONS):
            order = tasks if repetition % 2 == 0 else list(reversed(tasks))
            for task_index, task in enumerate(order, start=1):
                payload = request_for(task)
                response, client_ms, status, error = request_json(payload)
                row = {
                    'repetition': repetition,
                    'task_index': task_index,
                    'task_id': task['id'],
                    'security': bool(task.get('security', False)),
                    'correct_label': task['correct'],
                    'transport_ok': response is not None,
                    'http_status': status,
                    'client_latency_ms': client_ms,
                    'request': payload,
                    'response': response,
                    'transport_error': error,
                }
                if response is not None:
                    metrics, _ = score_row(task, response)
                    row.update(metrics)
                    row['service_latency_ms'] = metrics['service_latency_ms']
                    consecutive_errors = 0
                else:
                    consecutive_errors += 1
                raw_file.write(json.dumps(row, ensure_ascii=False) + '\n')
                raw_file.flush()
                rows.append(row)
                print(f"rep={repetition + 1}/{REPETITIONS} task={task['id']} transport={row['transport_ok']} correct={row.get('correct')} latency_ms={client_ms:.1f}", flush=True)
                if consecutive_errors >= 3:
                    break
            if consecutive_errors >= 3:
                break
    summary = summarize(rows, tasks, suite_sha)
    summary['attempted_requests'] = len(rows)
    summary['expected_requests'] = len(tasks) * REPETITIONS
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0 if summary['transport_ok'] == summary['expected_requests'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
