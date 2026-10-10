"""summarize_jsonl: resume un iterable de lineas JSONL con validacion estricta.

Ignora lineas vacias o de solo espacios. Cada linea no vacia debe ser un objeto
JSON con id, level y duration_ms de tipos correctos; una linea con JSON valido
pero tipos incorrectos es invalida completa y no suma.

Devuelve:
  count, by_level (alfabetico), total_duration_ms,
  p95_duration_ms (nearest-rank sobre duraciones validas ordenadas; None si no
  hay datos validos), invalid_lines.
No muta la entrada y mantiene enteros cuando corresponde.
"""

import json
import math


def _valid_entry(record):
    """Devuelve (ident, level, duration) si es valido; None si no lo es."""
    if not isinstance(record, dict):
        return None

    if "id" not in record or "level" not in record or "duration_ms" not in record:
        return None

    ident = record["id"]
    level = record["level"]
    duration = record["duration_ms"]

    # id: string no vacio o entero (bool no cuenta como entero).
    if isinstance(ident, bool):
        return None
    if not isinstance(ident, (str, int)):
        return None
    if isinstance(ident, str) and ident == "":
        return None

    # level: string no vacio.
    if not isinstance(level, str) or level == "":
        return None

    # duration_ms: entero (no bool, no float, no string).
    if isinstance(duration, bool) or not isinstance(duration, int):
        return None

    return ident, level, duration


def summarize_jsonl(lines):
    if isinstance(lines, (str, bytes)):
        raise ValueError("lines debe ser un iterable, no un string")

    count = 0
    invalid_lines = 0
    level_counts = {}
    total_duration_ms = 0
    durations = []

    for raw in lines:
        item = raw

        if isinstance(item, bytes):
            try:
                item = item.decode("utf-8")
            except UnicodeDecodeError:
                invalid_lines += 1
                continue

        if not isinstance(item, str):
            invalid_lines += 1
            continue

        if item.strip() == "":
            continue

        try:
            record = json.loads(item)
        except ValueError:
            invalid_lines += 1
            continue

        entry = _valid_entry(record)
        if entry is None:
            invalid_lines += 1
            continue

        ident, level, duration = entry
        count += 1
        level_counts[level] = level_counts.get(level, 0) + 1
        total_duration_ms += duration
        durations.append(duration)

    if durations:
        durations.sort()
        rank = math.ceil(0.95 * len(durations))
        percentile = durations[rank - 1]
    else:
        percentile = None

    ordered = {}
    for name in sorted(level_counts):
        ordered[name] = level_counts[name]

    return {
        "count": count,
        "by_level": ordered,
        "total_duration_ms": total_duration_ms,
        "p95_duration_ms": percentile,
        "invalid_lines": invalid_lines,
    }
