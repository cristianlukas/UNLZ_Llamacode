#!/usr/bin/env python3
"""Derive client-observed prefill/decode rates from llama-benchy JSONL events."""
import hashlib
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def main(source: str, destination: str) -> None:
    raw = Path(source).read_bytes()
    groups = defaultdict(list)
    for line in raw.splitlines():
        if line.strip():
            event = json.loads(line)
            if event.get("request_id") is not None:
                groups[event["request_id"]].append(event)

    rows = []
    for request_id, events in sorted(groups.items()):
        start = next((e for e in events if e.get("type") == "request_start"), {})
        first = next((e for e in events if e.get("type") == "request_first_token"), {})
        end = next((e for e in events if e.get("type") == "request_end"), {})
        if not start or not end or end.get("error"):
            continue
        prompt = end.get("prompt_tokens") or start.get("prompt_size")
        completion = end.get("total_tokens", 0)
        ttft = first.get("ttft_s")
        decode_s = end.get("decode_seconds")
        rows.append({
            "request_id": request_id,
            "run_index": start.get("run_index"),
            "requested_pp": start.get("prompt_size"),
            "actual_prompt_tokens": prompt,
            "actual_completion_tokens": completion,
            "ttft_seconds_client_observed": ttft,
            "decode_seconds_client_observed": decode_s,
            "prefill_tok_s_client_observed": prompt / ttft if prompt and ttft else None,
            "decode_tok_s_client_observed": completion / decode_s if completion and decode_s else None,
        })

    def summary(field: str):
        values = [r[field] for r in rows if r[field] is not None]
        return {
            "n": len(values),
            "median": statistics.median(values) if values else None,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
        }

    output = {
        "receipt_type": "q173_llama_benchy_event_derived_metrics",
        "source_events": str(Path(source)),
        "source_events_sha256": hashlib.sha256(raw).hexdigest(),
        "derivation": {
            "prefill_tok_s": "server prompt_tokens / request_first_token.ttft_s",
            "decode_tok_s": "request_end.total_tokens / request_end.decode_seconds",
            "interpretation": "client-observed streaming latency, not engine-internal kernel timing",
        },
        "requests": rows,
        "summary": {
            "prefill_tok_s_client_observed": summary("prefill_tok_s_client_observed"),
            "decode_tok_s_client_observed": summary("decode_tok_s_client_observed"),
        },
    }
    Path(destination).write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output["summary"], indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(f"usage: {sys.argv[0]} EVENTS.jsonl OUTPUT.json")
    main(sys.argv[1], sys.argv[2])
