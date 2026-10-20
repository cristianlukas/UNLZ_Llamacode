"""Query engine: predicados combinables y ordenamiento por prioridad/fecha."""
from __future__ import annotations

from typing import Callable, Optional

from .models import Task, parse_iso

PriorityFilter = str | list[str] | tuple[str, ...]
Predicate = Callable[[Task], bool]

_PRIORITY_RANK = {"low": 0, "medium": 1, "high": 2, "urgent": 3}


def priority_rank(priority: str) -> int:
    return _PRIORITY_RANK.get(priority, 1)


def by_priority(*priorities: str) -> Predicate:
    wanted = set(priorities)
    return lambda t: t.priority in wanted


def by_tag(tag: str) -> Predicate:
    needle = str(tag).strip().lower()
    return lambda t: needle in t.tags


def by_status(*statuses: str) -> Predicate:
    wanted = set(statuses)
    return lambda t: t.status in wanted


def overdue(now: Optional[str] = None) -> Predicate:
    ref = parse_iso(now) if isinstance(now, str) else None
    from datetime import datetime, timezone

    def _pred(t: Task) -> bool:
        due = parse_iso(t.due_date)
        if due is None:
            return False
        current = ref or datetime.now(timezone.utc)
        return due < current and t.status not in ("done", "cancelled")

    return _pred


def due_before(iso_ts: str) -> Predicate:
    limit = parse_iso(iso_ts)
    return lambda t: (limit is not None and t.due_date is not None
                      and (parse_iso(t.due_date) or limit) <= limit)


def due_after(iso_ts: str) -> Predicate:
    limit = parse_iso(iso_ts)

    def _pred(t: Task) -> bool:
        due = parse_iso(t.due_date)
        return limit is not None and due is not None and due > limit

    return _pred


def combine(*predicates: Optional[Predicate]) -> Predicate:
    active = [p for p in predicates if p is not None]
    return lambda t: all(p(t) for p in active)


def sort_tasks(tasks: list[Task], key: str = "priority") -> list[Task]:
    """Ordena por 'priority' (desc, luego due_date asc) o 'due_date'."""
    if key == "due_date":
        return sorted(
            tasks,
            key=lambda t: (parse_iso(t.due_date) is None,
                           parse_iso(t.due_date) or parse_iso(t.created_at)),
        )
    return sorted(
        tasks,
        key=lambda t: (-priority_rank(t.priority),
                       parse_iso(t.due_date) or parse_iso(t.created_at),
                       t.id),
    )
