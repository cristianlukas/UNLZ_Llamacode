#!/usr/bin/env python3
"""llama-benchy wrapper: generate exact local tokenizer-length prompt text."""
import runpy
import uuid
import numpy as np
from llama_benchy.prompts import PromptGenerator

_ORIGINAL_GENERATE = PromptGenerator.generate

def exact_generate(self, prompt_tokens: int, context_tokens: int = 0, no_cache: bool = False):
    if context_tokens != 0:
        return _ORIGINAL_GENERATE(self, prompt_tokens, context_tokens, no_cache)
    suffix = f" {uuid.uuid4()}" if no_cache else ""
    tok = self.tokenizer
    suffix_len = len(tok.encode(suffix, add_special_tokens=False))
    base_len = max(1, prompt_tokens - suffix_len)
    tokens = self.all_tokens
    if len(tokens) < base_len + 128:
        tokens = tokens * (base_len // max(1, len(tokens)) + 2)
    max_start = max(1, len(tokens) - base_len - 128)
    start0 = int(np.random.randint(0, max_start))
    shifts = [0]
    for n in range(1, 17):
        shifts.extend((n, -n))
    tried = set()
    best = None
    for shift in shifts:
        start = max(0, min(len(tokens) - base_len - 1, start0 + shift))
        length = base_len
        visited = set()
        for _ in range(12):
            if length <= 0 or length in visited:
                break
            visited.add(length)
            text = tok.decode(tokens[start:start + length])
            actual = len(tok.encode(text + suffix, add_special_tokens=False))
            delta = prompt_tokens - actual
            if best is None or abs(delta) < best[0]:
                best = (abs(delta), actual)
            if delta == 0:
                return "", text + suffix
            tried.add((start, length, actual))
            length += delta if delta else 1
    raise RuntimeError(f"cannot construct exact prompt: target={prompt_tokens}; best={best}; attempts={len(tried)}")

PromptGenerator.generate = exact_generate

if __name__ == "__main__":
    runpy.run_module("llama_benchy", run_name="__main__")
