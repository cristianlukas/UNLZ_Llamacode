"""Mini-lenguaje de consulta: parse + apply."""
from __future__ import annotations

from typing import Any

from .models import Task, VALID_PRIORITIES, VALID_STATUSES

_KNOWN_KEYS = {"status", "priority", "tag", "search"}


def parse_query(text: str) -> dict[str, str]:
    """Convierte 'status:todo priority:high tag:backend search:api' en filtros.

    Claves desconocidas se ignoran sin romper.
    """
    result: dict[str, str] = {}
    if not text:
        return result
    for token in text.split():
        if ":" not in token:
            continue
        key, _, value = token.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if not value:
            continue
        if key not in _KNOWN_KEYS:
            continue
        if key == "status" and value not in VALID_STATUSES:
            continue
        if key == "priority" and value not in VALID_PRIORITIES:
            continue
        result[key] = value
    return result


def apply_query(tasks: list[Task], query: dict[str, Any] | str) -> list[Task]:
    """Filtra una lista de Task según los filtros de parse_query."""
    if isinstance(query, str):
        query = parse_query(query)
    status = query.get("status")
    priority = query.get("priority")
    tag = query.get("tag")
    search = query.get("search")
    wanted_tag = tag.strip().lower() if tag else None
    needle = search.lower() if search else None
    out: list[Task] = []
    for task in tasks:
        if status and task.status != status:
            continue
        if priority and task.priority != priority:
            continue
        if wanted_tag and wanted_tag not in task.tags:
            continue
        if needle and needle not in task.title.lower() and needle not in task.description.lower():
            continue
        out.append(task)
    return out
