"""Modelo de dominio: Task."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

VALID_PRIORITIES = ("low", "medium", "high", "urgent")
VALID_STATUSES = ("todo", "doing", "blocked", "done", "cancelled")
VALID_RECURRENCES = ("daily", "weekly", "monthly")

_ISO_FMT = "%Y-%m-%dT%H:%M:%S+00:00"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime(_ISO_FMT)


def normalize_tags(tags: Any) -> list[str]:
    """Trim + lowercase + dedup case-insensitive conservando orden."""
    if tags is None:
        return []
    if isinstance(tags, str):
        tags = [tags]
    out: list[str] = []
    seen: set[str] = set()
    for raw in tags:
        if raw is None:
            continue
        tag = str(raw).strip().lower()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        out.append(tag)
    return out


def normalize_depends_on(depends_on: Any) -> list[int]:
    """Lista normalizada de ids int sin duplicados, conservando orden."""
    if depends_on is None:
        return []
    if isinstance(depends_on, int) and not isinstance(depends_on, bool):
        depends_on = [depends_on]
    out: list[int] = []
    seen: set[int] = set()
    for raw in depends_on:
        try:
            tid = int(raw)
        except (TypeError, ValueError):
            raise ValueError(f"depends_on inválido: {raw!r}")
        if tid in seen:
            continue
        seen.add(tid)
        out.append(tid)
    return out


def validate_common_fields(priority: str, status: str, recurrence: Optional[str]) -> None:
    if priority not in VALID_PRIORITIES:
        raise ValueError(
            f"priority inválida: {priority!r}. Válidas: {', '.join(VALID_PRIORITIES)}"
        )
    if status not in VALID_STATUSES:
        raise ValueError(
            f"status inválida: {status!r}. Válidas: {', '.join(VALID_STATUSES)}"
        )
    if recurrence is not None and recurrence not in VALID_RECURRENCES:
        raise ValueError(
            f"recurrence inválida: {recurrence!r}. Válidas: {', '.join(VALID_RECURRENCES)}"
        )


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
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    due_date: Optional[str] = None
    completed_at: Optional[str] = None

    def __post_init__(self) -> None:
        title = str(self.title).strip()
        if not title:
            raise ValueError("title no puede estar vacío")
        self.title = title
        self.common_validate()
        self.tags = normalize_tags(self.tags)
        self.depends_on = normalize_depends_on(self.depends_on)
        self.common_validate()

    def common_validate(self) -> None:
        validate_common_fields(self.priority, self.status, self.recurrence)

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
            raise ValueError("entrada de tarea debe ser un dict")
        try:
            common = int(data["id"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("id inválido o faltante")
        return cls(
            id=common,
            title=data.get("title", ""),
            description=str(data.get("description", "") or ""),
            priority=data.get("priority", "medium"),
            status=data.get("status", "todo"),
            tags=data.get("tags") or [],
            depends_on=data.get("depends_on") or [],
            recurrence=data.get("recurrence"),
            created_at=str(data.get("created_at") or _now_iso()),
            updated_at=str(data.get("updated_at") or _now_iso()),
            due_date=data.get("due_date"),
            completed_at=data.get("completed_at"),
        )
