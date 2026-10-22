#!/usr/bin/env python3
"""Offline semantic re-grade for Q35 outputs; never contacts a model server."""

from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path
from typing import Any


CASE_HEADING = re.compile(
    r"(?im)^\s*(?:[-*]\s*)?(\d+)[.)]\s+(?:\*{0,2})?(case-\d+-\d+)(?:\*{0,2}).*$"
)
NUMBERED_LINE = re.compile(r"^\s*(\d+)[.)]\s+(.+?)\s*$")


def clean_value(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^(?:\*{1,2}|_{1,2}|`+)", "", value)
    value = re.sub(r"(?:\*{1,2}|_{1,2}|`+)$", "", value)
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1].strip()
    return value


def parse_numbered_answers(raw: str, count: int, *, final_section_only: bool = False) -> dict[int, str] | None:
    text = raw
    markers = list(re.finditer(r"(?im)^\s*\*{0,2}final answers:?\*{0,2}\s*$", text))
    if final_section_only:
        if not markers:
            return None
        text = text[markers[-1].end():]
    elif markers:
        text = text[markers[-1].end():]

    lines = [line for line in text.splitlines() if line.strip()]
    parsed: dict[int, str] = {}
    for line in lines:
        match = NUMBERED_LINE.match(line)
        if not match:
            if final_section_only:
                continue
            return None
        index = int(match.group(1))
        if index < 1 or index > count or index in parsed:
            return None
        parsed[index] = clean_value(match.group(2))
    if set(parsed) != set(range(1, count + 1)):
        return None
    return parsed


def _case_value(block: str) -> tuple[str | None, bool]:
    """Return an explicit answer, or an authoritative FINAL_APPROVED value."""
    answer_matches = re.findall(
        r"(?im)^\s*(?:[-*]\s*)?(?:\*{0,2})answer(?:\*{0,2})\s*:\s*(.+?)\s*$",
        block,
    )
    if answer_matches:
        values = {clean_value(v) for v in answer_matches}
        return (next(iter(values)), False) if len(values) == 1 else (None, True)

    value_matches = re.findall(
        r"(?im)^\s*(?:[-*]\s*)?(?:\*{0,2})value(?:\*{0,2})\s*:\s*(.+?)\s*$",
        block,
    )
    if value_matches:
        values = {clean_value(v) for v in value_matches}
        return (next(iter(values)), False) if len(values) == 1 else (None, True)

    approved_records = re.findall(
        r"(?i)status\s*=\s*FINAL_APPROVED\s*;\s*value\s*=\s*([^;\]\n]+)",
        block,
    )
    if approved_records:
        values = {clean_value(v.rstrip(". ")) for v in approved_records}
        return (next(iter(values)), False) if len(values) == 1 else (None, True)

    approved_phrases = re.findall(
        r"(?is)FINAL_APPROVED.{0,180}?(?:lists? the value|value\s*(?:is|:))\s*(?:\*\*|`)?([^*`\n]+?)(?:\*\*|`)?(?=\s*[.(\[]|\s*$)",
        block,
    )
    if approved_phrases:
        values = {clean_value(v.rstrip(". ")) for v in approved_phrases}
        return (next(iter(values)), False) if len(values) == 1 else (None, True)
    return None, False


def parse_case_answers(raw: str, expected: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    headings = list(CASE_HEADING.finditer(raw))
    parsed: dict[str, str] = {}
    ambiguous: list[str] = []
    for pos, heading in enumerate(headings):
        case_id = heading.group(2).lower()
        if case_id not in expected:
            continue
        end = headings[pos + 1].start() if pos + 1 < len(headings) else len(raw)
        value, conflict = _case_value(raw[heading.start():end])
        if conflict:
            ambiguous.append(case_id)
        elif value is not None:
            if case_id in parsed and parsed[case_id] != value:
                ambiguous.append(case_id)
                parsed.pop(case_id, None)
            elif case_id not in ambiguous:
                parsed[case_id] = value
    return parsed, ambiguous


def semantic_score(raw: str, expected: dict[str, str]) -> dict[str, Any]:
    try:
        parsed = json.loads(raw.strip())
    except json.JSONDecodeError:
        parsed = None

    if isinstance(parsed, dict):
        answers = {key: str(parsed[key]) for key in expected if key in parsed}
        method = "json_object"
        ambiguous: list[str] = []
    else:
        numbered = parse_numbered_answers(raw, len(expected), final_section_only=True)
        if numbered is None:
            numbered = parse_numbered_answers(raw, len(expected))
        if numbered is not None:
            answers = {
                key: numbered[index]
                for index, key in enumerate(expected, start=1)
            }
            method = "numbered_requests_in_prompt_order"
            ambiguous = []
        else:
            answers, ambiguous = parse_case_answers(raw, expected)
            method = "case_scoped_explicit_answer_or_approved_record"

    matches = {
        key: key in answers and answers[key] == expected[key] and key not in ambiguous
        for key in expected
    }
    return {
        "method": method,
        "answers_extracted": answers,
        "correct": sum(matches.values()),
        "total": len(expected),
        "percent": round(100 * sum(matches.values()) / max(1, len(expected)), 2),
        "matches": matches,
        "unresolved_case_ids": sorted(ambiguous),
        "unanswered_case_ids": [key for key in expected if key not in answers and key not in ambiguous],
    }


def regrade_campaign(campaign_root: Path) -> dict[str, Any]:
    runs = campaign_root / "runs"
    output: list[dict[str, Any]] = []
    expected_by_seed: dict[int, dict[str, str]] = {}
    expected_hash_by_seed: dict[int, str] = {}
    for context in (131072, 262144, 524288, 1048576):
        for seed in (2026101, 2026102, 2026103):
            run_dir = runs / str(context) / str(seed)
            receipt_path = run_dir / "receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            expected_path = campaign_root / "fixtures" / str(context) / str(seed) / "probe-expected.json"
            expected = json.loads(expected_path.read_text(encoding="utf-8"))
            if receipt.get("expected") != expected:
                raise ValueError(f"receipt/fixture expected mismatch: {context}/{seed}")
            expected_hash = hashlib.sha256(
                json.dumps(expected, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            if seed in expected_by_seed and expected_by_seed[seed] != expected:
                raise ValueError(f"same-seed expected answers changed across contexts: {seed}")
            expected_by_seed[seed] = expected
            expected_hash_by_seed[seed] = expected_hash
            semantic = semantic_score(receipt.get("raw_answer") or "", expected)
            output.append({
                "context": context,
                "seed": seed,
                "prompt_sha256": receipt.get("prompt_sha256"),
                "expected_sha256": expected_hash,
                "completion_status": "complete" if receipt.get("finish_reason") == "stop" else "incomplete",
                "finish_reason": receipt.get("finish_reason"),
                "original_json_score": receipt.get("quality_score"),
                "original_strict_output_valid": receipt.get("strict_output_valid"),
                "semantic_score": semantic,
                "prefill_tokens_per_second": receipt.get("prefill_tokens_per_second"),
                "decode_tokens_per_second": receipt.get("decode_tokens_per_second"),
                "request_elapsed_seconds": receipt.get("request_elapsed_seconds"),
                "total_server_session_seconds": receipt.get("total_server_session_seconds"),
                "min_system_mem_available_bytes": receipt.get("min_system_mem_available_bytes"),
                "run_cgroup_memory_swap_delta_bytes": receipt.get("run_cgroup_memory_swap_delta_bytes"),
                "receipt": str(receipt_path),
            })
    return {
        "task": "Q-20261022-VF-ITERATION-37",
        "experiment_id": "Q35-SEMANTIC-REGRADE-01",
        "campaign": "Q-20261022-VF-ITERATION-35",
        "method": "offline re-grade per preregistration; original receipts preserved",
        "same_seed_expected_answers_identical_across_contexts": {
            str(seed): digest for seed, digest in expected_hash_by_seed.items()
        },
        "runs": output,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = regrade_campaign(args.campaign_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "runs": len(result["runs"])}, indent=2))
