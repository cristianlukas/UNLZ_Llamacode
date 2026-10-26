#!/usr/bin/env python3
"""Build the preregistered Q154 token-exact, matched prefill requests offline."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

from strata_tokenizer import Tokenizer
from frontend import ChatTemplate
from server import Service


WORDS = """agent artifact audit buffer cache candidate control decode deterministic device document engine
evaluation expert fixture framework generation graph harness inference input layer latency memory metric
model module nonce output pair profile prompt quality request result runtime safety sample shard system task
template token tokenizer throughput validation vector workspace response compile boundary sequence route
document code assertion useful local reproducible performance policy trace monitor channel integration""".split()
SIZES = (4096, 16384, 32512)
REPEATS = (1, 2, 3)


def load_tokenizer(directory: Path):
    meta = json.loads((directory / "tokenizer.json").read_text(encoding="utf-8"))
    vocab = json.loads((directory / "vocab.json").read_text(encoding="utf-8"))
    tokens = [token for token, _ in sorted(vocab.items(), key=lambda item: item[1])]
    merges = (directory / "merges.txt").read_text(encoding="utf-8").splitlines()
    token_types = json.loads((directory / "token_type.json").read_text(encoding="utf-8"))
    return Tokenizer(tokens, merges, token_types, meta["pre"], meta["special_ids"])


def token_count(service, content: str) -> int:
    messages = [{"role": "user", "content": content}]
    return len(service.encode_prompt(messages, None, {"temperature": 0.0}, store=False))


def make_words(seed: int, count: int) -> list[str]:
    rng = random.Random(seed)
    words = []
    for i in range(count):
        word = rng.choice(WORDS)
        if i % 19 == 18:
            word += "."
        elif i % 7 == 6:
            word += ","
        words.append(word)
    return words


def exact_content(service, target: int, replicate: int, variant: int = 0) -> tuple[str, int, int, str]:
    seed = 15420261026 + target * 10 + replicate + variant * 100000
    nonce = hashlib.sha256(f"Q154:{target}:{replicate}:{variant}:{seed}".encode()).hexdigest()[:16]
    # Put the nonce at the very start of the user content so the server cannot
    # reuse a shared natural-language prefix across scored prompts.
    prefix = f"{nonce} Q154 throughput fixture; window={target}; replicate={replicate}; variant={variant}.\n"
    words = make_words(seed, target * 3)

    def count(n: int) -> int:
        return token_count(service, prefix + " ".join(words[:n]))

    lo, hi = 0, len(words)
    if count(hi) <= target:
        raise RuntimeError(f"fixture upper bound too small for target {target}")
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if count(mid) <= target:
            lo = mid
        else:
            hi = mid

    # Complete the last few tokens with a one-token ASCII unit, validating the
    # full rendered prompt each time so Jinja/special tokens remain included.
    for n in range(lo, max(-1, lo - 128), -1):
        base = prefix + " ".join(words[:n])
        base_count = token_count(service, base)
        if base_count > target:
            continue
        gap = target - base_count
        for units in range(max(0, gap - 2), gap + 3):
            content = base + (" a" * units)
            actual = token_count(service, content)
            if actual == target:
                return content, actual, seed, nonce
    raise RuntimeError(f"could not create exact {target}-token prompt for replicate {replicate}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--control-tokenizer", type=Path, required=True)
    ap.add_argument("--candidate-tokenizer", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--control-model", required=True)
    ap.add_argument("--candidate-model", required=True)
    args = ap.parse_args()

    control_tok = load_tokenizer(args.control_tokenizer)
    control_svc = Service(None, control_tok, ChatTemplate(args.control_tokenizer / "chat_template.jinja"),
                          model_name=args.control_model)
    candidate_tok = load_tokenizer(args.candidate_tokenizer)
    candidate_svc = Service(None, candidate_tok, ChatTemplate(args.candidate_tokenizer / "chat_template.jinja"),
                             model_name=args.candidate_model)

    manifest = {
        "iteration": "Q154",
        "purpose": "offline exact-token fixture generation; no model/server/GPU use",
        "tokenizer_control": str(args.control_tokenizer),
        "tokenizer_candidate": str(args.candidate_tokenizer),
        "target_prompt_tokens": list(SIZES),
        "target_output_tokens": 256,
        "replicates": list(REPEATS),
        "sampling_override": {"temperature": 0.0},
        "request_fields": {"max_tokens": 256, "stream": False},
        "warmup": {},
        "matched_order": {
            "control": [f"{size}:{rep}" for size in SIZES for rep in REPEATS],
            "candidate": [f"{size}:{rep}" for size in reversed(SIZES) for rep in REPEATS],
        },
        "fixtures": [],
    }

    for size in SIZES:
        for replicate in REPEATS:
            key = f"{size}-rep{replicate}"
            fixture = {"key": key, "prompt_tokens_expected": size, "completion_cap": 256, "variants": []}
            for variant in (0, 1):
                content, count, seed, nonce = exact_content(control_svc, size, replicate, variant)
                control_count = token_count(control_svc, content)
                candidate_count = token_count(candidate_svc, content)
                if control_count != size or candidate_count != size:
                    raise RuntimeError(f"token parity failure: target={size} control={control_count} candidate={candidate_count}")
                item = {"variant": variant, "replicate_seed": seed, "nonce": nonce,
                        "token_count_control": control_count, "token_count_candidate": candidate_count}
                for arm, model in (("control", args.control_model), ("candidate", args.candidate_model)):
                    request = {
                        "model": model,
                        "messages": [{"role": "user", "content": content}],
                        "temperature": 0.0,
                        "max_tokens": 256,
                        "stream": False,
                    }
                    prefix = "retry-" if variant else ""
                    path = args.output / arm / f"{prefix}{key}.json"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    payload = json.dumps(request, ensure_ascii=False, indent=2) + "\n"
                    path.write_text(payload, encoding="utf-8")
                    item[f"request_{arm}"] = str(path.relative_to(args.output))
                    item[f"request_{arm}_sha256"] = hashlib.sha256(payload.encode()).hexdigest()
                fixture["variants"].append(item)
            manifest["fixtures"].append(fixture)

    warmup_nonce = hashlib.sha256(b"Q154-throughput-warmup-v1").hexdigest()[:16]
    warmup_content = f"{warmup_nonce} Q154 throughput warmup. Reply with OK and no explanation."
    warmup_counts = {"control": token_count(control_svc, warmup_content),
                     "candidate": token_count(candidate_svc, warmup_content)}
    if warmup_counts["control"] != warmup_counts["candidate"]:
        raise RuntimeError(f"warmup token parity failure: {warmup_counts}")
    manifest["warmup"] = {"purpose": "one unscored short warmup per freshly loaded profile",
                           "prompt_tokens_control": warmup_counts["control"],
                           "prompt_tokens_candidate": warmup_counts["candidate"], "nonce": warmup_nonce}
    for arm, model in (("control", args.control_model), ("candidate", args.candidate_model)):
        request = {"model": model, "messages": [{"role": "user", "content": warmup_content}],
                   "temperature": 0.0, "max_tokens": 32, "stream": False}
        path = args.output / arm / "warmup.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(request, ensure_ascii=False, indent=2) + "\n"
        path.write_text(payload, encoding="utf-8")
        manifest["warmup"][f"request_{arm}"] = str(path.relative_to(args.output))
        manifest["warmup"][f"request_{arm}_sha256"] = hashlib.sha256(payload.encode()).hexdigest()

    args.output.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), "fixtures": len(manifest["fixtures"]),
                      "counts": [x["prompt_tokens_expected"] for x in manifest["fixtures"]],
                      "all_tokenizer_parity": all(v["token_count_control"] == v["token_count_candidate"]
                                                   for x in manifest["fixtures"] for v in x["variants"]),
                      "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest()}, indent=2))


if __name__ == "__main__":
    main()
