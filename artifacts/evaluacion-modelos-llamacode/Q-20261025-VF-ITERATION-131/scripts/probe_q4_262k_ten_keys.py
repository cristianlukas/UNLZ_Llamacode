#!/usr/bin/env python3
"""One preregistered ten-key retrieval screen; never stores the expanded prompt."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

TARGET_TOKENS = 258_000
MIN_TOKENS = 257_000
MAX_TOKENS = 259_000
FILLER = "Meeting archive row 042: status stable, document reference verified, no action required.\n"
TARGET_POSITIONS = [0.05 + i * 0.10 for i in range(10)]
QUESTION = (
    "\nReturn only one JSON object with exactly the keys K01 through K10. "
    "For each key, copy its corresponding ARCHIVE FIELD value exactly. "
    "Do not add explanation or markdown."
)


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_tokenizer(directory: pathlib.Path, module_path: pathlib.Path):
    sys.path.insert(0, str(module_path.resolve().parent))
    from strata_tokenizer import Tokenizer

    cfg = json.loads((directory / "tokenizer.json").read_text(encoding="utf-8"))
    vocab = json.loads((directory / "vocab.json").read_text(encoding="utf-8"))
    tokens = [None] * len(vocab)
    for token, idx in vocab.items():
        tokens[int(idx)] = token
    if any(token is None for token in tokens):
        raise ValueError("tokenizer vocabulary has an ID gap")
    merges = (directory / "merges.txt").read_text(encoding="utf-8").splitlines()
    types = json.loads((directory / "token_type.json").read_text(encoding="utf-8"))
    return Tokenizer(tokens, merges, types, cfg.get("pre", "qwen35"), cfg.get("special_ids", {}))


def make_expected(seed: int = 4242) -> dict[str, str]:
    return {
        f"K{i:02d}": f"LC-K{i:02d}-{hashlib.sha256(f'q131:{seed}:{i}'.encode()).hexdigest()[:16].upper()}"
        for i in range(1, 11)
    }


def build_prompt(tokenizer, expected: dict[str, str]):
    filler_tokens = max(1, len(tokenizer.encode(FILLER)))
    key_lines = [f"\nARCHIVE FIELD {key}: {value}. Preserve it for final retrieval.\n"
                 for key, value in expected.items()]
    overhead = sum(len(tokenizer.encode(line)) for line in key_lines) + len(tokenizer.encode(QUESTION))
    repeat_count = max(1, (TARGET_TOKENS - overhead) // filler_tokens)

    def assemble(total_repeats: int):
        weights = [0.05] + [0.10] * 9 + [0.05]
        gaps = [int(total_repeats * weight) for weight in weights[:-1]]
        gaps.append(total_repeats - sum(gaps))
        parts, offsets, char_count = [], [], 0
        for i, line in enumerate(key_lines):
            gap = FILLER * gaps[i]
            parts.append(gap)
            char_count += len(gap)
            offsets.append(char_count)
            parts.append(line)
            char_count += len(line)
        parts.append(FILLER * gaps[-1])
        body = "".join(parts)
        prompt = body + QUESTION
        return prompt, offsets

    for _ in range(8):
        prompt, offsets = assemble(repeat_count)
        count = len(tokenizer.encode(prompt))
        if MIN_TOKENS <= count <= MAX_TOKENS:
            prefix_tokens = [len(tokenizer.encode(prompt[:offset])) for offset in offsets]
            fractions = [token_count / count for token_count in prefix_tokens]
            errors = [abs(actual - target) for actual, target in zip(fractions, TARGET_POSITIONS)]
            if max(errors) > 0.025:
                raise ValueError(f"injection position drift exceeds 2.5 points: {fractions}")
            return prompt, count, prefix_tokens, fractions
        delta = max(1, (abs(TARGET_TOKENS - count) + filler_tokens - 1) // filler_tokens)
        repeat_count += delta if count < MIN_TOKENS else -delta
        if repeat_count <= 0:
            break
    raise ValueError("could not fit prompt into preregistered 257K–259K token range")


def parse_json_answer(answer: str):
    text = answer.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.S | re.I)
    if fenced:
        text = fenced.group(1)
    return json.loads(text)


def score_answer(answer: str, expected: dict[str, str], usage):
    parse_error = None
    parsed = None
    try:
        parsed = parse_json_answer(answer)
    except Exception as exc:
        parse_error = f"{type(exc).__name__}: {exc}"
    exact = sum(parsed.get(key) == value for key, value in expected.items()) if isinstance(parsed, dict) else 0
    exact_key_set = isinstance(parsed, dict) and set(parsed) == set(expected)
    usage_tokens = usage.get("prompt_tokens") if isinstance(usage, dict) else None
    in_range = False
    if usage_tokens is not None:
        try:
            in_range = MIN_TOKENS <= int(usage_tokens) <= MAX_TOKENS
        except (TypeError, ValueError):
            in_range = False
    return {
        "parsed": parsed,
        "parseError": parse_error,
        "exactFields": exact,
        "exactKeySet": exact_key_set,
        "usagePromptTokensInRange": in_range,
        "screenPass": exact == 10 and exact_key_set and in_range,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokenizer-dir", required=True)
    ap.add_argument("--tokenizer-module", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--fixture", required=True)
    ap.add_argument("--endpoint", default="http://127.0.0.1:8350/v1/chat/completions")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    config_path = pathlib.Path(args.config)
    tokenizer_dir = pathlib.Path(args.tokenizer_dir)
    fixture_path = pathlib.Path(args.fixture)
    output_path = pathlib.Path(args.out)
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))
    if list(expected) != [f"K{i:02d}" for i in range(1, 11)] or len(set(expected.values())) != 10:
        raise ValueError("fixture must contain ten unique ordered K01–K10 values")
    tokenizer = load_tokenizer(tokenizer_dir, pathlib.Path(args.tokenizer_module))
    prompt, content_tokens, prefix_tokens, fractions = build_prompt(tokenizer, expected)
    for value in expected.values():
        if prompt.count(value) != 1:
            raise ValueError("a retrieval value does not appear exactly once in the prompt")

    result = {
        "taskId": "Q-20261025-VF-ITERATION-131",
        "status": "request_pending",
        "model": "Qwen3.8 Flash-Next UD-Q4_K_XL",
        "runtime": "Strata local 0.1.41 / CUDA 12.8",
        "targetContext": 262144,
        "targetContentTokens": TARGET_TOKENS,
        "localTokenizerContentTokens": content_tokens,
        "minimumContentTokens": MIN_TOKENS,
        "maximumContentTokens": MAX_TOKENS,
        "promptSha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "promptStored": False,
        "fixtureSha256": sha256(fixture_path),
        "configSha256": sha256(config_path),
        "tokenizerHashes": {name: sha256(tokenizer_dir / name) for name in
                             ("tokenizer.json", "vocab.json", "merges.txt", "token_type.json")},
        "keys": expected,
        "keyPositions": [
            {"key": key, "targetFraction": target, "actualFraction": actual,
             "prefixTokens": prefix}
            for key, target, actual, prefix in zip(expected, TARGET_POSITIONS, fractions, prefix_tokens)
        ],
        "sampling": {"temperature": 0.0, "top_p": 1.0, "top_k": 1, "seed": 4242,
                     "max_tokens": 512, "reasoning_budget_tokens": 32},
        "requestCount": 1,
        "retryCount": 0,
    }
    payload = json.dumps({
        "model": "qwen3.8-flash-next-ud-q4-k-xl-context262k-ten-keys",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0, "top_p": 1.0, "top_k": 1, "seed": 4242,
        "max_tokens": 512, "reasoning_budget_tokens": 32,
        "stream": True, "return_progress": True,
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(args.endpoint, data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
    answer, usage, timings, progress = [], None, None, None
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=1800) as response:
            result["httpStatus"] = response.status
            while True:
                line = response.readline()
                if not line:
                    break
                if not line.startswith(b"data: "):
                    continue
                raw = line[6:].strip()
                if raw == b"[DONE]":
                    break
                try:
                    item = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if item.get("usage"):
                    usage = item["usage"]
                if item.get("timings"):
                    timings = item["timings"]
                if item.get("prompt_progress"):
                    progress = item["prompt_progress"]
                for choice in item.get("choices", []):
                    text = choice.get("delta", {}).get("content", "")
                    if text:
                        answer.append(text)
        raw_answer = "".join(answer)
        score = score_answer(raw_answer, expected, usage)
        result.update({
            "status": "completed",
            "answer": raw_answer,
            "parsedAnswer": score["parsed"],
            "parseError": score["parseError"],
            "exactFields": score["exactFields"],
            "expectedFields": 10,
            "exactKeySet": score["exactKeySet"],
            "usagePromptTokensInRange": score["usagePromptTokensInRange"],
            "usage": usage,
            "timings": timings,
            "lastPromptProgress": progress,
            "screenPass": score["screenPass"],
            "elapsedSeconds": time.monotonic() - started,
        })
    except urllib.error.HTTPError as exc:
        result.update({"status": "http_error", "httpStatus": exc.code,
                       "error": exc.read().decode("utf-8", "replace")[:2000]})
    except Exception as exc:
        result.update({"status": "request_error", "error": f"{type(exc).__name__}: {exc}"})
    result["elapsedTotalSeconds"] = time.monotonic() - started
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: result.get(k) for k in
                      ("status", "httpStatus", "localTokenizerContentTokens", "exactFields",
                       "expectedFields", "usage", "screenPass", "elapsedSeconds", "error")},
                     ensure_ascii=False))
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
