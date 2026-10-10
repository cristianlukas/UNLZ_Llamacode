import json
from math import ceil
def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)
def _as_int_if_integral(value):
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value
def summarize_jsonl(lines):
    count = 0
    invalid_lines = 0
    by_level = {}
    durations = []
    for line in lines:
        if not isinstance(line, str):
            invalid_lines += 1
            continue
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError:
            invalid_lines += 1
            continue
        if not isinstance(record, dict):
            invalid_lines += 1
            continue
        if "id" not in record or "level" not in record or "duration_ms" not in record:
            invalid_lines += 1
            continue
        identifier = record["id"]
        level = record["level"]
        duration = record["duration_ms"]
        id_ok = isinstance(identifier, str) or (
            isinstance(identifier, int) and not isinstance(identifier, bool)
        )
        if not id_ok:
            invalid_lines += 1
            continue
        if not isinstance(level, str) or not level:
            invalid_lines += 1
            continue
        if not _is_number(duration) or duration < 0:
            invalid_lines += 1
            continue
        count += 1
        by_level[level] = by_level.get(level, 0) + 1
        durations.append(duration)
    by_level = {level: by_level[level] for level in sorted(by_level)}
    sorted_durations = sorted(durations)
    if sorted_durations:
        rank = max(1, ceil(0.95 * len(sorted_durations)))
        p95 = _as_int_if_integral(sorted_durations[rank - 1])
        total = _as_int_if_integral(sum(sorted_durations))
    else:
        p95 = None
        total = 0
    return {
        "count": count,
        "by_level": by_level,
        "total_duration_ms": total,
        "p95_duration_ms": p95,
        "invalid_lines": invalid_lines,
    }