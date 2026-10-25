#!/usr/bin/env python3
"""Offline-only structure audit of pre-existing Q41 TaskFlow receipts.
Does not load models, call endpoints, or print conversation contents.
"""
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261020-VF-20261019-01/receipts/source41"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "receipts/q134-q41-offline-tooltrace-audit.json"
SEEDS = ["4242", "4243", "4244"]
ARMS = {
    "ASTRA_control_presence0": lambda seed: BASE / "control" / f"seed-{seed}" / "taskflow.json",
    "ASTRA_candidate_presence1": lambda seed: BASE / "candidate" / f"seed-{seed}" / "taskflow.json",
}
EVENTS = {
    "ASTRA_control_presence0": lambda seed: BASE / "control" / f"seed-{seed}" / "taskflow.events.jsonl",
    "ASTRA_candidate_presence1": lambda seed: BASE / "candidate" / f"seed-{seed}" / "taskflow.events.jsonl",
}
RAW_KEYS = ("raw_tool", "raw_call", "tool_payload", "function_arguments", "tool_arguments", "assistant_message", "message_content")
ERROR_KEYS = ("error", "exception", "parse", "parser", "malformed", "syntax", "schema")
SEMANTIC_KEYS = ("pass", "assert", "expected", "quality", "invalidcalls", "successfultoolcalls", "toolcallquality")
FINISH_KEYS = ("finish_reason", "finishreason", "stop_reason")

def walk(obj, path="$", depth=0):
    if depth > 12:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}"
            yield k.lower(), v, p
            yield from walk(v, p, depth + 1)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:5000]):
            yield from walk(v, f"{path}[{i}]", depth + 1)

def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"__load_error_type__": type(e).__name__}

def summarize_result(path):
    obj = load_json(path)
    entries = list(walk(obj))
    key_counts = Counter(k for k, _, _ in entries)
    outcome_keys = ("toolcalls", "invalidcalls", "successfultoolcalls", "failedtoolcalls", "retries", "repairs")
    outcome_occurrences = {key: key_counts[key] for key in outcome_keys if key_counts[key]}
    keys = set(key_counts)
    return {
        "path": str(path.relative_to(ROOT)),
        "loadErrorType": obj.get("__load_error_type__"),
        "outcomeCounterFieldOccurrencesOnly": outcome_occurrences,
        "nestedCounterValuesNotSummed": True,
        "rawOutputFieldNamesPresent": sorted(k for k in keys if any(x in k for x in RAW_KEYS)),
        "errorClassificationFieldNamesPresent": sorted(k for k in keys if any(x in k for x in ERROR_KEYS)),
        "semanticOutcomeFieldNamesPresent": sorted(k for k in keys if any(x in k for x in SEMANTIC_KEYS)),
        "finishReasonFieldNamesPresent": sorted(k for k in keys if any(x in k for x in FINISH_KEYS)),
        "keyNameCounts": {k: key_counts[k] for k in sorted(key_counts) if any(x in k for x in RAW_KEYS + ERROR_KEYS + SEMANTIC_KEYS + FINISH_KEYS)},
    }

def summarize_events(path):
    events = []
    malformed = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                events.append(obj)
            else:
                malformed += 1
        except Exception:
            malformed += 1
    event_names = Counter(str(e.get("event", "<missing>")) for e in events)
    key_names = Counter(k.lower() for e in events for k in e)
    keys = set(key_names)
    return {
        "path": str(path.relative_to(ROOT)),
        "lines": len(events) + malformed,
        "validJsonEvents": len(events),
        "malformedLines": malformed,
        "eventNameCounts": dict(sorted(event_names.items())),
        "rawOutputFieldNamesPresent": sorted(k for k in keys if any(x in k for x in RAW_KEYS)),
        "errorClassificationFieldNamesPresent": sorted(k for k in keys if any(x in k for x in ERROR_KEYS)),
        "semanticOutcomeFieldNamesPresent": sorted(k for k in keys if any(x in k for x in SEMANTIC_KEYS)),
        "finishReasonFieldNamesPresent": sorted(k for k in keys if any(x in k for x in FINISH_KEYS)),
    }

report = {
    "taskId": "Q-20261025-VF-ITERATION-134",
    "audit": "Q41 ASTRA IQ2_XS / Strata existing TaskFlow receipts only",
    "offlineOnly": True,
    "noModelOrEndpointCalls": True,
    "arms": {},
}
for arm, path_fn in ARMS.items():
    report["arms"][arm] = {"results": [], "events": []}
    for seed in SEEDS:
        rp, ep = path_fn(seed), EVENTS[arm](seed)
        if rp.is_file(): report["arms"][arm]["results"].append({"seed": seed, **summarize_result(rp)})
        else: report["arms"][arm]["results"].append({"seed": seed, "missing": str(rp)})
        if ep.is_file(): report["arms"][arm]["events"].append({"seed": seed, **summarize_events(ep)})
        else: report["arms"][arm]["events"].append({"seed": seed, "missing": str(ep)})

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"output": str(OUT), "arms": {k: {"resultFiles": len(v['results']), "eventFiles": len(v['events'])} for k,v in report['arms'].items()}}, ensure_ascii=False))
