"""Mini-lenguaje de consultas: 'status:todo priority:high tag:backend search:api'."""
from __future__ import annotations

from typing import Any

from .models import PRIORITIES, STATUSES, Task

VALID_KEYS: tuple[str, ...] = ("status", "priority", "tag", "tags", "search", "due", "recurrence")


def parse_query(text: str) -> dict[str, str]:
    """Convierte el texto en un dict de filtros. Claves inválidas se ignoran."""
    filters: dict[str, str] = {}
    for token in str(text or "").split():
        if ":" not in token:
            continue
        key, _, value = token.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if not key or not value:
            continue
        if key not in VALID_KEYS:
            continue
        if key == "status" and value.lower() not in STATUSES:
            continue
        if key == "priority" and value.lower() not in PRIORITIES:
            continue
        if key == "recurrence" and value.lower() not in ("daily", "weekly", "monthly"):
            continue
        filters[key] = value
    return filters


def apply_query(tasks: list[Task], query: dict[str, str] | str) -> list[Task]:
    """Filtra una lista de Task según los filtros. No rompe con claves desconocidas."""
    filters = parse_query(query) if isinstance(query, str) else dict(query or {})
    result = list(tasks)
    if "status" in filters:
        result = [t for t in result if t.status == filters["status"].lower()]
    if "priority" in filters:
        result = [t for t in result if t.priority == filters["priority"].lower()]
    if "tag" in filters:
        needle = filters["tag"].strip().lower()
        result = [t for t in result if needle in t.tags]
    if "tags" in filters:
        needle = filters["tags"].strip().lower()
        result = [t for t in result if needle in t.tags]
    if "recurrence" in filters:
        result = [t for t in result if t.recurrence == filters["recurrence"].lower()]
    if "due" in filters:
        result = [t for t in result if bool(t.due_date)]
    if "search" in filters:
        needle = filters["search"].strip().lower()
        result = [
            t for t in result
            if needle in t.title.lower() or needle in t.description.lower()
        ]
    return result
