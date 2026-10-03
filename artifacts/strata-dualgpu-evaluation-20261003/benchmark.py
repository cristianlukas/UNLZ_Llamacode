#!/usr/bin/env python3
"""Paired server-speed probe for Strata 0.1.35 and the DualGPU fork."""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
ENDPOINTS = {
    "baseline-0.1.35": "http://127.0.0.1:8352/v1/chat/completions",
    "fork-0.1.38": "http://127.0.0.1:8353/v1/chat/completions",
}


def post(url: str, body: dict, timeout: int = 900) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def source_context() -> str:
    pieces = []
    for path in (
        ROOT / "README.md",
        ROOT / "docs" / "harness.md",
        ROOT / "src" / "core" / "agent" / "HarnessDirectiveStore.cpp",
        ROOT / "src" / "core" / "profiles" / "HarnessSpec.cpp",
    ):
        if path.is_file():
            pieces.append(f"\n\n--- {path.relative_to(ROOT)} ---\n\n{path.read_text(errors='replace')}")
    block = "\n".join(pieces)
    # Repetition yields a stable long prompt from repository material. Prompt token
    # counts are recorded from Strata's own server timings for every request.
    return (block * 12)[:120_000]


def run_one(name: str, url: str, category: str, repeat: int, content: str, max_tokens: int) -> dict:
    started = time.perf_counter()
    result = post(
        url,
        {
            "model": "qwen3.8-flash-next-iq3_s",
            "messages": [{"role": "user", "content": content}],
            "temperature": 0,
            "top_p": 1,
            "top_k": 0,
            "reasoning_effort": "none",
            "max_tokens": max_tokens,
            "stream": False,
            "seed": 4242 + repeat,
        },
    )
    elapsed = time.perf_counter() - started
    message = result["choices"][0]["message"]
    text = message.get("content") or ""
    reasoning = message.get("reasoning_content") or ""
    item = {
        "candidate": name,
        "category": category,
        "repeat": repeat,
        "elapsedSec": round(elapsed, 3),
        "usage": result.get("usage"),
        "timings": result.get("timings"),
        "finishReason": result["choices"][0].get("finish_reason"),
        "completionSha256": hashlib.sha256(text.encode()).hexdigest(),
        "reasoningSha256": hashlib.sha256(reasoning.encode()).hexdigest(),
        "completion": text,
        "reasoning": reasoning,
    }
    print(json.dumps({k: v for k, v in item.items() if k != "completion"}), flush=True)
    return item


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", choices=ENDPOINTS)
    args = parser.parse_args()
    code = (
        "Write a robust Python 3 function `merge_intervals(intervals)` that accepts an iterable of "
        "integer [start, end] pairs, merges overlapping or touching intervals, validates malformed rows, "
        "and returns sorted lists. Include a short explanation and do not use third-party packages.\n\n"
        "Show the implementation first, then a concise set of edge cases."
    )
    prose = (
        "Write a self-contained 400-token literary vignette about a night train crossing the Andes. "
        "Use concrete sensory details, a restrained voice, and a clear ending. Do not mention these instructions."
    )
    long_base = source_context()
    all_results = []
    name = args.candidate
    url = ENDPOINTS[name]
    for name, url in [(name, url)]:
        health = urllib.request.urlopen(url.rsplit("/v1/", 1)[0] + "/health", timeout=10).read().decode()
        print(json.dumps({"candidate": name, "health": health}), flush=True)
        # One warm-up is excluded; each timed generation uses a fresh prompt.
        run_one(name, url, "warmup", 0, code + " Warmup seed A.", 64)
        for i in range(1, 5):
            all_results.append(run_one(name, url, "code", i, code + f" Variation marker {i}.", 400))
            all_results.append(run_one(name, url, "prose", i, prose + f" Variation marker {i}.", 400))
        for i in range(1, 3):
            all_results.append(run_one(name, url, "repo-context-32k", i,
                                       long_base + f"\n\nRequest marker: {i}. Summarize the important constraints above.",
                                       128))
    out = OUT / f"speed-results-{args.candidate}.json"
    out.write_text(json.dumps({"results": all_results}, indent=2, ensure_ascii=False))
    summary = {}
    for name in (args.candidate,):
        candidate = [r for r in all_results if r["candidate"] == name]
        summary[name] = {}
        for category in ("code", "prose", "repo-context-32k"):
            group = [r for r in candidate if r["category"] == category]
            summary[name][category] = {
                "completionTpsMedian": round(statistics.median(
                    r["timings"]["predicted_per_second"] for r in group), 1),
                "promptTpsMedian": round(statistics.median(
                    r["timings"]["prompt_per_second"] for r in group), 1),
                "promptTokens": [r["usage"]["prompt_tokens"] for r in group],
                "completionTokens": [r["usage"]["completion_tokens"] for r in group],
            }
    (OUT / f"speed-summary-{args.candidate}.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
