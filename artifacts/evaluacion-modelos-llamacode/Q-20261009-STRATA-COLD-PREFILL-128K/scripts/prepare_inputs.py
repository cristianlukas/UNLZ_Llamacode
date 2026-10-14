#!/usr/bin/env python3
"""Build a deterministic near-128K Codex conversation and validate rendered sizes."""
from __future__ import annotations

import bisect
import hashlib
import json
import random
import sys
from pathlib import Path

from prompt_utils import (TASK, base_request, count_prompt, load_prompt_renderer, make_tools,
                          messages_for_compaction, messages_for_initial)

OUT = TASK / "inputs"
TARGET_LOW, TARGET_HIGH = 120_000, 125_000
SEED = 20261012
SESSION, THREAD = "eval-session-20261012", "cold-prefill-128k-thread"

WORDS = ("build", "cache", "worker", "request", "record", "policy", "commit", "system", "review",
         "module", "state", "branch", "output", "input", "tool", "result", "check", "summary",
         "context", "token", "profile", "engine", "session", "evidence", "artifact", "runtime",
         "quality", "memory", "storage", "client", "server", "workspace", "history", "budget")


def make_lines(count: int) -> list[str]:
    rng = random.Random(SEED)
    lines = []
    for index in range(count):
        words = " ".join(rng.choice(WORDS) for _ in range(10))
        lines.append(f"Log {index:05d}: {words}.")
    return lines


def prompt_body(lines: list[str]) -> tuple[str, dict[str, str]]:
    facts = {
        "beginning": "KEY-ALPHA-7319",
        "middle": "KEY-BRAVO-2846",
        "late": "KEY-CHARLIE-9052",
        "ending": "KEY-DELTA-4173",
    }
    positions = {
        "beginning": max(3, len(lines) // 40),
        "middle": len(lines) // 2,
        "late": (len(lines) * 19) // 20,
        "ending": max(0, len(lines) - 5),
    }
    for label, index in positions.items():
        lines[index] += f" Verified control value {label}: {facts[label]}. Preserve exactly."
    data = "\n".join(lines)
    return data, facts


def build_user_message(body: str) -> str:
    return ("This is a long synthetic engineering log for a context-compaction test. "
            "Do not summarize it yet. Read it as conversation history. In this first turn, reply exactly READY. "
            "Do not call any tools.\n\nBEGIN LOG\n" + body + "\nEND LOG")


def make_scenario(lines: list[str]) -> tuple[dict, dict[str, str]]:
    body, facts = prompt_body(lines)
    user = build_user_message(body)
    compact = ("You are performing a CONTEXT CHECKPOINT COMPACTION. Create a concise handoff summary. "
               "Preserve these four verified control values exactly, with their labels: beginning, middle, late, ending. "
               "Do not invent values. Include one short line for each value.")
    return {"initial_user_message": user, "compaction_user_message": compact,
            "body_line_count": len(lines), "facts": facts, "target": "120000-125000 rendered tokens"}, facts


def main() -> int:
    cfg = TASK / "configs" / "control.json"
    svc_cfg, svc = load_prompt_renderer(cfg)
    tools = make_tools()
    best = None
    lo, hi = 1, 16000
    while lo <= hi:
        mid = (lo + hi) // 2
        scenario, facts = make_scenario(make_lines(mid))
        req = base_request(messages_for_initial(scenario), "turn", SESSION, THREAD, tools, 16)
        n, _ids, _shown = count_prompt(svc, req, False)
        candidate = (abs(n - 123000), n, mid, scenario, facts)
        if best is None or candidate[0] < best[0]:
            best = candidate
        if TARGET_LOW <= n <= TARGET_HIGH:
            break
        if n < TARGET_LOW:
            lo = mid + 1
        else:
            hi = mid - 1
    if not (TARGET_LOW <= best[1] <= TARGET_HIGH):
        # Recount the closest converged item, then fail closed if the target band was not reached.
        raise SystemExit(f"could not reach target token band; closest={best[1]} tokens / {best[2]} lines")

    scenario, facts = make_scenario(make_lines(best[2]))
    user_req = base_request(messages_for_initial(scenario), "turn", SESSION, THREAD, tools, 16)
    initial_tokens, _ids, _shown = count_prompt(svc, user_req, False)
    placeholder = {"output": [{"type": "message", "role": "assistant",
                               "content": [{"type": "output_text", "text": "READY"}]}]}
    # Count compaction twice to make cache ON/OFF behavior explicit before any GPU request.
    comp_req = base_request(messages_for_compaction(scenario, placeholder), "compaction", SESSION, THREAD, [], 512)
    baseline_compaction_tokens, _ids, _shown = count_prompt(svc, comp_req, False)
    import serve.responses as responses
    responses._kept_prompt_tools = (None, None)
    count_prompt(svc, user_req, True)
    cached_compaction_tokens, _ids, shown = count_prompt(svc, comp_req, True)
    if max(initial_tokens + 16, baseline_compaction_tokens + 512, cached_compaction_tokens + 512) > 131072:
        raise SystemExit("target prompt leaves insufficient context headroom; reduce and regenerate")

    OUT.mkdir(parents=True, exist_ok=True)
    scenario_path = OUT / "scenario.json"
    scenario_path.write_text(json.dumps(scenario, ensure_ascii=False, indent=2) + "\n")
    digest = hashlib.sha256(scenario_path.read_bytes()).hexdigest()
    manifest = {
        "generator_seed": SEED,
        "session_id": SESSION,
        "thread_id": THREAD,
        "body_line_count": best[2],
        "rendered_initial_tokens": initial_tokens,
        "rendered_compaction_tokens_cache_off": baseline_compaction_tokens,
        "rendered_compaction_tokens_cache_on": cached_compaction_tokens,
        "max_context": 131072,
        "initial_max_output_tokens": 16,
        "compaction_max_output_tokens": 512,
        "facts": facts,
        "tools": tools,
        "scenario_sha256": digest,
        "tokenizer_path": svc_cfg["tokenizer"],
        "cache_on_prompt_tools": shown,
    }
    (OUT / "prompt-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
