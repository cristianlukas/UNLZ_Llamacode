"""Mini-lenguaje de filtros: 'status:todo priority:high tag:backend search:api'."""

from __future__ import annotations

from typing import Any, Union

from .models import Task

VALID_KEYS = ("status", "priority", "tag", "search", "recurrence")


def parse_query(text: str) -> dict[str, str]:
    """Convierte texto en filtros; claves invalidas se ignoran sin romper."""
    query: dict[str, str] = {}
    if not text:
        return query
    for token in str(text).split():
        if ":" not in token:
            continue
        key, _, value = token.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if key not in VALID_KEYS or not value:
            continue
        query[key] = value
    return query


def apply_query(tasks: list[Task], query: Union[str, dict[str, Any]]) -> list[Task]:
    """Filtra tareas aplicando los filtros combinables."""
    filters = parse_query(query) if isinstance(query, str) else dict(query or {})
    result: list[Task] = []
    for task in tasks:
        if filters.get("status") and task.status != filters["status"].lower():
            continue
        if filters.get("priority") and task.priority != filters["priority"].lower():
            continue
        if filters.get("tag") and filters["tag"].lower() not in task.tags:
            continue
        if filters.get("recurrence") and task.recurrence != filters["recurrence"].lower():
            continue
        search = filters.get("search")
        if search:
            needle = search.lower()
            if needle not in task.title.lower() and needle not in task.description.lower():
                continue
        result.append(task)
    return result
