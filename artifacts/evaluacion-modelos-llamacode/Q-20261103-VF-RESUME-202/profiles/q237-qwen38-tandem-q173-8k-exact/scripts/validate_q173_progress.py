#!/usr/bin/env python3
"""Validate effective request sizes from llama-benchy server progress events."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


def validate_events(
    events: Iterable[dict[str, Any]],
    *,
    expected_runs: int = 3,
    expected_prompt_tokens: int = 8192,
    expected_output_tokens: int = 128,
) -> dict[str, Any]:
    items = list(events)
    starts = [e for e in items if e.get("type") == "request_start"]
    ends = [e for e in items if e.get("type") == "request_end"]
    complete = [e for e in items if e.get("type") == "bench_complete"]
    errors: list[str] = []

    if len(starts) != expected_runs:
        errors.append(f"expected {expected_runs} request_start events, found {len(starts)}")
    if len(ends) != expected_runs:
        errors.append(f"expected {expected_runs} request_end events, found {len(ends)}")
    if len(complete) != 1 or complete[0].get("status") != "ok":
        statuses = [e.get("status") for e in complete]
        errors.append(f"expected one bench_complete status=ok, found {statuses}")

    start_ids = [e.get("request_id") for e in starts]
    end_ids = [e.get("request_id") for e in ends]
    if len(set(start_ids)) != len(start_ids):
        errors.append("request_start contains duplicate request_id values")
    if len(set(end_ids)) != len(end_ids):
        errors.append("request_end contains duplicate request_id values")
    if set(start_ids) != set(end_ids):
        errors.append("request_start/request_end request_id sets do not match")

    for i, event in enumerate(ends, 1):
        if event.get("prompt_tokens") != expected_prompt_tokens:
            errors.append(
                f"request_end #{i} prompt_tokens={event.get('prompt_tokens')!r}; "
                f"expected {expected_prompt_tokens}"
            )
        if event.get("total_tokens") != expected_output_tokens:
            errors.append(
                f"request_end #{i} total_tokens={event.get('total_tokens')!r}; "
                f"expected {expected_output_tokens}"
            )
        if event.get("error") not in (None, ""):
            errors.append(f"request_end #{i} reported error={event.get('error')!r}")

    client_prompt_sizes = [e.get("prompt_size") for e in starts]
    server_prompt_tokens = [e.get("prompt_tokens") for e in ends]
    output_tokens = [e.get("total_tokens") for e in ends]
    return {
        "valid": not errors,
        "errors": errors,
        "request_start_count": len(starts),
        "request_end_count": len(ends),
        "bench_complete_statuses": [e.get("status") for e in complete],
        "client_prompt_size_diagnostic": client_prompt_sizes,
        "server_prompt_tokens_per_run": server_prompt_tokens,
        "output_tokens_per_run": output_tokens,
    }


def validate_progress_file(
    path: str | Path,
    *,
    expected_runs: int = 3,
    expected_prompt_tokens: int = 8192,
    expected_output_tokens: int = 128,
) -> dict[str, Any]:
    events = []
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                return {
                    "valid": False,
                    "errors": [f"line {line_number} is invalid JSON: {exc.msg}"],
                    "request_start_count": 0,
                    "request_end_count": 0,
                    "bench_complete_statuses": [],
                    "client_prompt_size_diagnostic": [],
                    "server_prompt_tokens_per_run": [],
                    "output_tokens_per_run": [],
                }
    return validate_events(
        events,
        expected_runs=expected_runs,
        expected_prompt_tokens=expected_prompt_tokens,
        expected_output_tokens=expected_output_tokens,
    )
