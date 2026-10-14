"""Modelo de dominio: Task normalizado y serializable."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

VALID_PRIORITIES = ("low", "medium", "high", "urgent")
VALID_STATUSES = ("todo", "doing", "blocked", "done", "cancelled")
VALID_RECURRENCES = ("daily", "weekly", "monthly")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_iso(value: Any) -> Optional[datetime]:
    """Acepta str ISO 8601 o datetime; devuelve None si no es parseable."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def normalize_tags(tags: Any) -> list[str]:
    """Trim + lowercase + dedup case-insensitive conservando orden."""
    result: list[str] = []
    seen: set[str] = set()
    for raw in tags or []:
        if not isinstance(raw, str):
            continue
        tag = raw.strip().lower()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        result.append(tag)
    return result


def normalize_depends_on(depends_on: Any) -> list[int]:
    result: list[int] = []
    seen: set[int] = set()
    for raw in depends_on or []:
        try:
            dep_id = int(raw)
        except (TypeError, ValueError):
            continue
        if dep_id in seen:
            continue
        seen.add(dep_id)
        result.append(dep_id)
    return result


@dataclass
class Task:
    id: int
    title: str
    description: str = ""
    priority: str = "medium"
    status: str = "todo"
    tags: list[str] = field(default_factory=list)
    depends_on: list[int] = field(default_factory=list)
    recurrence: Optional[str] = None
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    due_date: Optional[str] = None
    completed_at: Optional[str] = None

    def __post_init__(self) -> None:
        self.title = str(self.title).strip()
        if not self.title:
            raise ValueError("title no puede estar vacio")
        self.description = "" if self.description is None else str(self.description)
        self.priority = str(self.priority).strip().lower()
        if self.priority not in VALID_PRIORITIES:
            raise ValueError(
                f"priority invalida: {self.priority!r}; valida: {', '.join(VALID_PRIORITIES)}"
            )
        self.status = str(self.status).strip().lower()
        if self.status not in VALID_STATUSES:
            raise ValueError(
                f"status invalido: {self.status!r}; valido: {', '.join(VALID_STATUSES)}"
            )
        raw_recurrence = self.recurrence
        self.recurrence = (
            None if raw_recurrence is None else str(raw_recurrence).strip().lower()
        )
        if self.recurrence is not None and self.recurrence not in VALID_RECURRENCES:
            raise ValueError(
                f"recurrence invalida: {self.recurrence!r}; valida: {', '.join(VALID_RECURRENCES)}"
            )
        self.tags = normalize_tags(self.tags)
        self.depends_on = normalize_depends_on(self.depends_on)
        self.id = int(self.id)
        self.created_at = self._iso(self.created_at) or now_iso()
        self.updated_at = self._iso(self.updated_at) or self.created_at
        self.due_date = self._iso(self.due_date)
        self.completed_at = self._iso(self.completed_at)

    @staticmethod
    def _iso(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        text = str(value).strip()
        if not text:
            return None
        parsed = parse_iso(text)
        # Se conserva la forma original (date-only o datetime) para simetria.
        return text if parsed is not None else None

    def touch(self) -> None:
        self.updated_at = now_iso()

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
    def from_dict(cls, data: Any) -> "Task":
        if not isinstance(data, dict):
            raise ValueError("entrada malformada: se esperaba un dict")
        try:
            task_id = int(data.get("id", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError("entrada malformada: id invalido") from exc
        title = str(data.get("title", "")).strip()
        if not title:
            raise ValueError("entrada malformada: title vacio")
        return cls(
            id=task_id,
            title=title,
            description=str(data.get("description", "") or ""),
            priority=str(data.get("priority", "medium")),
            status=str(data.get("status", "todo")),
            tags=data.get("tags") or [],
            depends_on=data.get("depends_on") or [],
            recurrence=data.get("recurrence"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            due_date=data.get("due_date"),
            completed_at=data.get("completed_at"),
        )
