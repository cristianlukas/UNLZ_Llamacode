#!/usr/bin/env python3
"""Single synthetic long-context retrieval smoke; stores hashes and receipt, never the expanded prompt."""
import argparse
import hashlib
import json
import pathlib
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

GIB = 1024 ** 3
MIN_AVAILABLE = 32 * GIB
MAX_SWAP_USED = 2 * GIB
TARGET_CONTENT_TOKENS = 258_000
MIN_CONTENT_TOKENS = 257_000
MAX_CONTENT_TOKENS = 259_000
KEY = "LC-95P-7D3A9C"
FILLER = "Meeting archive row 042: status stable, document reference verified, no action required.\n"
QUESTION = "\nReturn only the archive key recorded once in this message. Do not invent or explain it."


class GuardViolation(RuntimeError):
    pass


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def memory_snapshot():
    info = {}
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        name, value = line.split(":", 1)
        if name in ("MemAvailable", "SwapTotal", "SwapFree"):
            info[name] = int(value.strip().split()[0]) * 1024
    swap_used = max(0, info.get("SwapTotal", 0) - info.get("SwapFree", 0))
    try:
        gpu = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu",
             "--format=csv,noheader,nounits"],
            check=True, capture_output=True, text=True, timeout=5,
        ).stdout.strip().splitlines()
    except Exception as exc:
        gpu = [f"telemetry unavailable: {type(exc).__name__}: {exc}"]
    return {
        "memAvailableBytes": info.get("MemAvailable"),
        "swapUsedBytes": swap_used,
        "gpuCsv": gpu,
        "atUnix": time.time(),
    }


def enforce_guard(snapshot):
    available = snapshot["memAvailableBytes"]
    swap = snapshot["swapUsedBytes"]
    if available is None or available < MIN_AVAILABLE:
        raise GuardViolation(f"MemAvailable below {MIN_AVAILABLE} bytes: {available}")
    if swap >= MAX_SWAP_USED:
        raise GuardViolation(f"swap used reached {MAX_SWAP_USED} bytes: {swap}")


def load_tokenizer(directory, module_path):
    sys.path.insert(0, str(pathlib.Path(module_path).resolve().parent))
    from strata_tokenizer import Tokenizer
    directory = pathlib.Path(directory)
    cfg = json.loads((directory / "tokenizer.json").read_text(encoding="utf-8"))
    vocab = json.loads((directory / "vocab.json").read_text(encoding="utf-8"))
    tokens = [None] * len(vocab)
    for token, idx in vocab.items():
        tokens[int(idx)] = token
    if any(t is None for t in tokens):
        raise ValueError("tokenizer vocabulary has an ID gap")
    merges = (directory / "merges.txt").read_text(encoding="utf-8").splitlines()
    types = json.loads((directory / "token_type.json").read_text(encoding="utf-8"))
    return Tokenizer(tokens, merges, types, cfg.get("pre", "qwen35"), cfg.get("special_ids", {}))


def build_prompt(tokenizer):
    filler_tokens = max(1, len(tokenizer.encode(FILLER)))
    repeats = max(1, TARGET_CONTENT_TOKENS // filler_tokens)
    prefix_repeats = int(repeats * 0.95)
    suffix_repeats = repeats - prefix_repeats
    needle = f"\nARCHIVE KEY: {KEY}. Keep this exact key for the final retrieval question.\n"

    def assemble(n_suffix):
        prefix = FILLER * prefix_repeats
        body = prefix + needle + FILLER * n_suffix
        prompt = body + QUESTION
        return prefix, prompt

    while True:
        prefix, prompt = assemble(suffix_repeats)
        count = len(tokenizer.encode(prompt))
        if count < MIN_CONTENT_TOKENS:
            suffix_repeats += max(1, (MIN_CONTENT_TOKENS - count) // filler_tokens)
            continue
        if count > MAX_CONTENT_TOKENS:
            suffix_repeats -= max(1, (count - MAX_CONTENT_TOKENS) // filler_tokens)
            if suffix_repeats < 0:
                raise RuntimeError("could not fit prompt to preregistered range")
            continue
        before = len(tokenizer.encode(prefix))
        return prompt, count, before, before / count


def write_json(path, result):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokenizer-dir", required=True)
    ap.add_argument("--tokenizer-module", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--endpoint", default="http://127.0.0.1:8351/v1/chat/completions")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    started = time.time()
    config_hash = sha256(args.config)
    tokenizer = load_tokenizer(args.tokenizer_dir, args.tokenizer_module)
    prompt, content_tokens, prefix_tokens, position = build_prompt(tokenizer)
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    before = memory_snapshot()
    enforce_guard(before)
    result = {
        "status": "running",
        "model": "ISTA Qwen3.8-Flash-Next IQ3_XXS",
        "runtime": "Strata v0.1.41, CUDA 12.8, SM86",
        "configPath": str(pathlib.Path(args.config).resolve()),
        "configSha256": config_hash,
        "tokenizerDirectory": str(pathlib.Path(args.tokenizer_dir).resolve()),
        "tokenizerHashes": {name: sha256(pathlib.Path(args.tokenizer_dir) / name)
                            for name in ("tokenizer.json", "vocab.json", "merges.txt", "token_type.json")},
        "targetContext": 262144,
        "targetContentTokens": TARGET_CONTENT_TOKENS,
        "localTokenizerContentTokens": content_tokens,
        "localTokenizerPrefixTokensBeforeNeedle": prefix_tokens,
        "needleFractionOfContentTokens": position,
        "promptSha256": prompt_hash,
        "needle": KEY,
        "sampling": {"temperature": 0.0, "top_p": 1.0, "top_k": 1, "seed": 4242},
        "promptStored": False,
        "before": before,
    }
    try:
        body = json.dumps({
            "model": "qwen3.8-flash-next-iq3_xxs-context262k",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "top_p": 1.0,
            "top_k": 1,
            "seed": 4242,
            "max_tokens": 32,
            "stream": True,
            "return_progress": True,
        }, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(args.endpoint, data=body,
                                         headers={"Content-Type": "application/json"}, method="POST")
        chunks, answer, usage, timings, progress = [], [], None, None, None
        last_sample = 0.0
        wall_start = time.monotonic()
        with urllib.request.urlopen(request, timeout=10) as response:
            result["httpStatus"] = response.status
            response.fp.raw._sock.settimeout(5)
            while True:
                try:
                    line = response.readline()
                except (TimeoutError, socket.timeout):
                    line = b""
                    if time.monotonic() - last_sample >= 5:
                        snap = memory_snapshot()
                        enforce_guard(snap)
                        result.setdefault("during", []).append(snap)
                        last_sample = time.monotonic()
                    continue
                if not line:
                    break
                if not line.startswith(b"data: "):
                    if time.monotonic() - last_sample >= 5:
                        snap = memory_snapshot()
                        enforce_guard(snap)
                        result.setdefault("during", []).append(snap)
                        last_sample = time.monotonic()
                    continue
                payload = line[6:].strip()
                if payload == b"[DONE]":
                    break
                try:
                    item = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                chunks.append(item)
                if item.get("usage"):
                    usage = item["usage"]
                if item.get("timings"):
                    timings = item["timings"]
                if item.get("prompt_progress"):
                    progress = item["prompt_progress"]
                for choice in item.get("choices", []):
                    delta = choice.get("delta", {})
                    text = delta.get("content", "")
                    if text:
                        answer.append(text)
                if time.monotonic() - last_sample >= 5:
                    snap = memory_snapshot()
                    enforce_guard(snap)
                    result.setdefault("during", []).append(snap)
                    last_sample = time.monotonic()
        result.update({
            "status": "completed",
            "answer": "".join(answer),
            "retrievalExact": KEY in "".join(answer),
            "usage": usage,
            "timings": timings,
            "lastPromptProgress": progress,
            "streamChunkCount": len(chunks),
            "elapsedSeconds": time.monotonic() - wall_start,
        })
    except urllib.error.HTTPError as exc:
        result.update({"status": "http_error", "httpStatus": exc.code,
                       "error": exc.read().decode("utf-8", "replace")[:2000]})
    except GuardViolation as exc:
        result.update({"status": "aborted_guard", "error": str(exc)})
    except Exception as exc:
        result.update({"status": "error", "error": f"{type(exc).__name__}: {exc}"})
    result["after"] = memory_snapshot()
    result["elapsedTotalSeconds"] = time.time() - started
    write_json(args.out, result)
    print(json.dumps({k: result.get(k) for k in (
        "status", "httpStatus", "localTokenizerContentTokens", "needleFractionOfContentTokens",
        "usage", "retrievalExact", "answer", "elapsedSeconds", "error")}, ensure_ascii=False))
    return 0 if result.get("status") == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
