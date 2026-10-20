"""Modelo de dominio: dataclass Task con validacion y serializacion simetrica."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

VALID_PRIORITIES: tuple[str, ...] = ("low", "medium", "high", "urgent")


class InvalidTaskError(ValueError):
    """Error de validación de dominio (campos inválidos, tarea inexistente)."""


VALID_STATUSES: tuple[str, ...] = ("todo", "doing", "blocked", "done", "cancelled")
VALID_RECURRENCES: tuple[str, ...] = ("daily", "weekly", "monthly")


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    """Convierte ISO 8601 a datetime (naive -> UTC). None/invalido -> None."""
    if not value or not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def normalize_tags(tags: Any) -> list[str]:
    """Trim + lowercase + dedupe case-insensitive conservando orden."""
    if not tags:
        return []
    if isinstance(tags, str):
        tags = [tags]
    out: list[str] = []
    seen: set[str] = set()
    for raw in tags:
        if raw is None:
            continue
        tag = str(raw).strip().lower()
        if tag and tag not in seen:
            seen.add(tag)
            out.append(tag)
    return out


def normalize_depends_on(depends_on: Any) -> list[int]:
    """Lista de ids int sin duplicados, conservando orden."""
    if not depends_on:
        return []
    if isinstance(depends_on, int):
        depends_on = [depends_on]
    out: list[int] = []
    seen: set[int] = set()
    for raw in depends_on:
        try:
            tid = int(raw)
        except (TypeError, ValueError):
            continue
        if tid not in seen:
            seen.add(tid)
            out.append(tid)
    return out


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
        self.title = str(self.title).strip()
        if not self.title:
            raise ValueError("title no puede estar vacio")
        self.description = str(self.description or "")
        self.validate_priority(self.priority)
        self.validate_status(self.status)
        self.validate_recurrence(self.recurrence)
        self.tags = normalize_tags(self.tags)
        self.depends_on = normalize_depends_on(self.depends_on)
        self.id = int(self.id)
        if not self.created_at:
            self.created_at = _now_iso()
        if not self.updated_at:
            self.updated_at = self.created_at

    def validate(self) -> None:
        """Revalida invariantes tras una mutación (campos ya normalizados)."""
        if not self.title:
            raise InvalidTaskError("title no puede estar vacio")
        self.validate_priority(self.priority)
        self.validate_status(self.status)
        self.validate_recurrence(self.recurrence)

    @staticmethod
    def validate_priority(priority: str) -> None:
        if priority not in VALID_PRIORITIES:
            raise InvalidTaskError(
                f"priority invalida: {priority!r}; validas: {', '.join(VALID_PRIORITIES)}"
            )

    @staticmethod
    def validate_status(status: str) -> None:
        if status not in VALID_STATUSES:
            raise InvalidTaskError(
                f"status invalida: {status!r}; validas: {', '.join(VALID_STATUSES)}"
            )

    @staticmethod
    def validate_recurrence(recurrence: Optional[str]) -> None:
        if recurrence is not None and recurrence not in VALID_RECURRENCES:
            raise InvalidTaskError(
                f"recurrence invalida: {recurrence!r}; validas: "
                f"{', '.join(VALID_RECURRENCES)} o None"
            )

    @property
    def due_at(self) -> Optional[datetime]:
        return parse_iso(self.due_date)

    @property
    def created_at_dt(self) -> datetime:
        parsed = parse_iso(self.created_at)
        return parsed if parsed is not None else datetime.now(timezone.utc)

    def is_overdue(self, now: Optional[datetime] = None) -> bool:
        """Vencida: due_date en el pasado y estado no terminal."""
        if self.status in ("done", "cancelled"):
            return False
        due = self.due_at
        if due is None:
            return False
        reference = now or datetime.now(timezone.utc)
        return due < reference

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
            raise ValueError("entrada de tarea debe ser un objeto JSON")
        if "id" not in data or "title" not in data:
            raise ValueError("tarea requiere 'id' y 'title'")
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        clean = {k: v for k, v in data.items() if k in known}
        clean["id"] = int(clean["id"])
        clean["title"] = str(clean["title"])
        return cls(**clean)
