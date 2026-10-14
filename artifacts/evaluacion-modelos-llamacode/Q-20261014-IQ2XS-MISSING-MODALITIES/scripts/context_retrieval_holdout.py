#!/usr/bin/env python3
"""One-shot, objective long-context retrieval holdout for both local endpoints."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261014-IQ2XS-MISSING-MODALITIES"
PACK = Path("/media/cristian/Disco local/Models/FlashNext-IQ2XS-ISTA-Strata-eval-20261012/strata-data/packs/iq2_xs/tokenizer")
TOKENIZER_SOURCE = Path("/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source/tools")

FACTS = [
    ("archive_code", "KESTREL-419"),
    ("maintenance_window", "02:47 UTC"),
    ("coral_valve_serial", "P-6821"),
    ("priority_label", "fern glass"),
    ("package_suffix", "RAVEN-73"),
    ("invoice_checksum", "516204"),
    ("shuttle_gate", "North Lantern"),
]
DEPTHS = [0.04, 0.16, 0.31, 0.47, 0.62, 0.78, 0.94]
FILLER = (
    "Routine operating procedures are recorded in sequence. Each ledger entry is independent, "
    "and no value should be inferred from adjacent records. The facility keeps details in a "
    "uniform handbook for reliable retrieval. "
)


def load_tokenizer():
    sys.path.insert(0, str(TOKENIZER_SOURCE))
    import strata_tokenizer as ST

    vocab = json.loads((PACK / "vocab.json").read_text(encoding="utf-8"))
    tokens = [None] * len(vocab)
    for token, index in vocab.items():
        tokens[index] = token
    merges = (PACK / "merges.txt").read_text(encoding="utf-8").splitlines()
    types = json.loads((PACK / "token_type.json").read_text(encoding="utf-8"))
    return ST.Tokenizer(tokens, merges, types)


def make_context(tokenizer, target: int = 118_000):
    prefix = (
        "You are checking a sealed operations handbook. Treat the records as the only source of truth. "
        "Retrieve the exact values requested at the end; do not infer or normalize them.\n\n"
    )
    parts = [prefix]
    filler_tokens = len(tokenizer.encode(FILLER))
    current = len(tokenizer.encode(prefix))
    locations = []
    for (key, value), depth in zip(FACTS, DEPTHS):
        goal = int(target * depth)
        repeats = max(0, (goal - current) // filler_tokens)
        chunk = FILLER * repeats
        parts.append(chunk)
        current = len(tokenizer.encode("".join(parts)))
        fact_line = f"RECORD {key.upper()} = {value}.\n"
        token_position = current
        parts.append(fact_line)
        current = len(tokenizer.encode("".join(parts)))
        locations.append({"key": key, "requestedDepth": depth, "tokenPosition": token_position})
    if current < target:
        repeats = max(0, (target - current) // filler_tokens)
        parts.append(FILLER * repeats)
    content = "".join(parts)
    actual = len(tokenizer.encode(content))
    questions = ", ".join(f'"{key}"' for key, _ in FACTS)
    content += (
        "\nReturn only one JSON object with these seven keys and their exact string values: "
        + questions + ". No commentary."
    )
    total = len(tokenizer.encode(content))
    for row in locations:
        row["actualDepth"] = row["tokenPosition"] / max(1, total)
    return content, total, locations


def post_json(url: str, payload: dict, timeout: int):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(url, data=body, headers={"Content-Type": "application/json"})
    start = time.monotonic()
    try:
        with urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read())
            return response.status, result, time.monotonic() - start
    except HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace"), time.monotonic() - start


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8350/v1")
    ap.add_argument("--model", required=True)
    ap.add_argument("--profile", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--target-tokens", type=int, default=118_000)
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()

    tok = load_tokenizer()
    prompt, fixture_tokens, locations = make_context(tok, args.target_tokens)
    fixture_path = TASK / "fixtures" / f"context_retrieval_{args.target_tokens}.txt"
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.write_text(prompt, encoding="utf-8")
    body_hash = hashlib.sha256(prompt.encode()).hexdigest()
    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 768,
        "temperature": 0.0,
        "top_p": 1.0,
        "top_k": 20,
        "seed": 4242,
        "stream": False,
        "cache_prompt": False,
    }
    status, response, elapsed = post_json(
        args.base_url.rstrip("/") + "/chat/completions", payload, args.timeout
    )
    row = {
        "schema": "q14-context-retrieval-holdout-v1",
        "profile": args.profile,
        "model": args.model,
        "endpoint": args.base_url,
        "fixtureTokensByPackTokenizer": fixture_tokens,
        "fixturePath": str(fixture_path),
        "targetTokens": args.target_tokens,
        "factLocations": locations,
        "promptSha256": body_hash,
        "httpStatus": status,
        "elapsedSeconds": round(elapsed, 3),
        "expected": dict(FACTS),
    }
    content = ""
    if status == 200 and isinstance(response, dict):
        choices = response.get("choices") or []
        if choices:
            content = str((choices[0].get("message") or {}).get("content") or "")
        usage = response.get("usage")
        row["usage"] = usage
        row["timings"] = response.get("timings")
        row["finishReason"] = choices[0].get("finish_reason") if choices else None
        row["responseId"] = response.get("id")
    else:
        row["error"] = response
    row["rawContent"] = content
    match = re.search(r"\{.*\}", content, re.S)
    parsed = None
    if match:
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    row["parsed"] = parsed
    row["exactMatches"] = {
        key: isinstance(parsed, dict) and parsed.get(key) == value
        for key, value in FACTS
    }
    row["correct"] = sum(row["exactMatches"].values())
    row["passed"] = status == 200 and row["correct"] == len(FACTS)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"profile": args.profile, "httpStatus": status,
                      "fixtureTokens": fixture_tokens, "correct": row["correct"],
                      "passed": row["passed"], "elapsedSeconds": row["elapsedSeconds"]},
                     ensure_ascii=False), flush=True)
    return 0 if row["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
