#!/usr/bin/env python3
"""CPU-only validation of the tokenizer-built ten-key fixture and scoring gate."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TASK = Path(__file__).resolve().parents[1]
SOURCE = Path('/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source')
TOKENIZER = Path('/media/cristian/Disco local/Strata-UD-Q4-review-20261003/data/packs/unsloth-ud-q4_k_xl/tokenizer')
CONFIG = TASK / 'receipts/configs/context262k-q4-q131.json'
FIXTURE = TASK / 'receipts/fixtures/ten-keys-seed-4242.json'


def main():
    path = TASK / 'scripts/probe_q4_262k_ten_keys.py'
    spec = importlib.util.spec_from_file_location('q131_probe', path)
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    expected = json.loads(FIXTURE.read_text(encoding='utf-8'))
    assert expected == probe.make_expected(4242)
    tokenizer = probe.load_tokenizer(TOKENIZER, SOURCE / 'tools/strata_tokenizer.py')
    prompt, count, prefix_tokens, fractions = probe.build_prompt(tokenizer, expected)
    assert 257_000 <= count <= 259_000
    assert len(prefix_tokens) == len(fractions) == 10
    assert all(prompt.count(value) == 1 for value in expected.values())
    assert all(abs(actual - target) <= 0.025
               for actual, target in zip(fractions, probe.TARGET_POSITIONS))
    usage = {'prompt_tokens': count}
    exact = probe.score_answer(json.dumps(expected), expected, usage)
    assert exact['screenPass'] and exact['exactFields'] == 10 and exact['exactKeySet']
    fenced = probe.score_answer('```json\n' + json.dumps(expected) + '\n```', expected, usage)
    assert fenced['screenPass']
    wrong = dict(expected); wrong['K10'] = 'wrong'
    assert not probe.score_answer(json.dumps(wrong), expected, usage)['screenPass']
    missing = dict(expected); missing.pop('K10')
    assert not probe.score_answer(json.dumps(missing), expected, usage)['screenPass']
    assert not probe.score_answer(json.dumps(expected), expected, {'prompt_tokens': 260_000})['screenPass']
    assert not probe.score_answer('not-json', expected, usage)['screenPass']
    receipt = {
        'taskId': 'Q-20261025-VF-ITERATION-131',
        'result': 'PASS',
        'modelInference': False,
        'gpuUse': False,
        'promptStored': False,
        'fixtureSha256': hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
        'configSha256': hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
        'promptSha256': hashlib.sha256(prompt.encode('utf-8')).hexdigest(),
        'tokenizerContentTokens': count,
        'keyPositions': [
            {'key': key, 'targetFraction': target, 'actualFraction': actual,
             'prefixTokens': prefix}
            for key, target, actual, prefix in zip(expected, probe.TARGET_POSITIONS, fractions, prefix_tokens)
        ],
        'valueOccurrencesExactlyOnce': True,
        'scorerCasesPassed': 6,
        'cases': ['exact 10/10 JSON', 'fenced JSON exact 10/10', 'one wrong value',
                  'missing key', 'usage outside range', 'invalid JSON'],
    }
    out = TASK / 'receipts/fixture-validation.json'
    out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(receipt, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
