"""Modelo de dominio: Task con validación, normalización y serialización ISO 8601."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

PRIORITIES: tuple[str, ...] = ("low", "medium", "high", "urgent")
STATUSES: tuple[str, ...] = ("todo", "doing", "blocked", "done", "cancelled")
RECURRENCES: tuple[str, ...] = ("daily", "weekly", "monthly")


def normalize_tags(tags: Any) -> list[str]:
    """Trim + lowercase + dedupe case-insensitive conservando orden."""
    result: list[str] = []
    seen: set[str] = set()
    for raw in tags or []:
        tag = str(raw).strip().lower()
        if tag and tag not in seen:
            seen.add(tag)
            result.append(tag)
    return result


def normalize_depends_on(depends_on: Any) -> list[int]:
    """Lista de ids int sin duplicados, conservando orden."""
    result: list[int] = []
    seen: set[int] = set()
    for raw in depends_on or []:
        try:
            value = int(raw)
        except (TypeError, ValueError):
            raise ValueError(f"dependency id must be an integer, got {raw!r}")
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def parse_iso_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid ISO 8601 datetime: {value!r}") from exc


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Task:
    id: int
    title: str
    description: str = ""
    priority: str = "medium"
    status: str = "todo"
    tags: list[str] = field(default_factory=list)
    depends_on: list[int] = field(default_factory=list)
    recurrence: str | None = None
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    due_date: str | None = None
    completed_at: str | None = None

    def __post_init__(self) -> None:
        self.id = int(self.id)
        self.title = str(self.title or "").strip()
        if not self.title:
            raise ValueError("title cannot be empty")
        self.description = "" if self.description is None else str(self.description)
        if self.priority not in PRIORITIES:
            raise ValueError(
                f"invalid priority {self.priority!r}; expected one of: {', '.join(PRIORITIES)}"
            )
        if self.status not in STATUSES:
            raise ValueError(
                f"invalid status {self.status!r}; expected one of: {', '.join(STATUSES)}"
            )
        if self.recurrence is not None and self.recurrence not in RECURRENCES:
            raise ValueError(
                f"invalid recurrence {self.recurrence!r}; expected one of: {', '.join(RECURRENCES)}"
            )
        self.tags = normalize_tags(self.tags)
        self.depends_on = normalize_depends_on(self.depends_on)
        for name in ("created_at", "updated_at", "due_date", "completed_at"):
            value = getattr(self, name)
            if value:
                parse_iso_datetime(value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "tags": list(self.tags),
            "depends_on": list(self.depends_on),
            "recurrence": self.recurrence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "due_date": self.due_date,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        if not isinstance(data, dict):
            raise ValueError("task entry must be a dict")
        if "id" not in data or "title" not in data:
            raise ValueError("task entry requires at least 'id' and 'title'")
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description") or "",
            priority=data.get("priority", "medium"),
            status=data.get("status", "todo"),
            tags=data.get("tags") or [],
            depends_on=data.get("depends_on") or [],
            recurrence=data.get("recurrence"),
            created_at=data.get("created_at") or now_iso(),
            updated_at=data.get("updated_at") or now_iso(),
            due_date=data.get("due_date"),
            completed_at=data.get("completed_at"),
        )
