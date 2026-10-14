"""JSONL audit summary."""

import json
import math


def summarize_jsonl(lines):
    """Summarize an iterable of JSONL lines.

    Blank/whitespace-only lines are ignored. Each non-blank line must be a
    JSON object with 'id' (str), 'level' (str) and 'duration_ms' (int).
    A line with valid JSON but wrong types is fully invalid and contributes
    nothing.

    Returns:
        {
          'count': number of valid records,
          'by_level': {level: count} sorted alphabetically,
          'total_duration_ms': sum of valid durations,
          'p95_duration_ms': nearest-rank p95 over sorted valid durations,
          'invalid_lines': number of non-blank invalid lines,
        }
    The input is not mutated.
    """
    count = 0
    by_level = {}
    total = 0
    durations = []
    invalid_lines = 0

    for line in lines:
        if line is None:
            invalid_lines += 1
            continue
        if not isinstance(line, str):
            invalid_lines += 1
            continue
        if not line.strip():
            continue

        try:
            record = json.loads(line)
        except (ValueError, TypeError):
            invalid_lines += 1
            continue

        if not isinstance(record, dict):
            invalid_lines += 1
            continue
        if "id" not in record:
            invalid_lines += 1
            continue
        if not isinstance(record.get("level"), str):
            invalid_lines += 1
            continue
        duration = record.get("duration_ms")
        if isinstance(duration, bool) or not isinstance(duration, int):
            invalid_lines += 1
            continue

        count += 1
        by_level[record["level"]] = by_level.get(record["level"], 0) + 1
        total += duration
        durations.append(duration)

    if durations:
        ordered = sorted(durations)
        rank = max(1, math.ceil(0.95 * len(ordered)))
        p95 = ordered[rank - 1]
    else:
        p95 = None

    return {
        "count": count,
        "by_level": {level: by_level[level] for level in sorted(by_level)},
        "total_duration_ms": total,
        "p95_duration_ms": p95,
        "invalid_lines": invalid_lines,
    }
