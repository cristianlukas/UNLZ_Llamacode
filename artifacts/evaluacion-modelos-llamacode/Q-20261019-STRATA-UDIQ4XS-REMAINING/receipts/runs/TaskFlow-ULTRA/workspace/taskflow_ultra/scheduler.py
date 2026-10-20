"""Scheduler: reglas de recurrencia y detección de vencidas, con reloj inyectable."""

from __future__ import annotations

import calendar
import datetime as dt
from typing import Iterable, List, Optional

from .clock import Clock, parse_iso
from .models import Task


def _add_months(moment: dt.datetime, months: int) -> dt.datetime:
    """Suma meses saturando el día al último del mes destino."""
    year = moment.year + (moment.month - 1 + months) // 12
    month = (moment.month - 1 + months) % 12 + 1
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)


def next_due_date(previous_due: dt.datetime, recurrence: str,
                  after: Optional[dt.datetime] = None) -> dt.datetime:
    """Calcula el próximo vencimiento a partir del anterior (no desde 'now').

    Anclar a la fecha anterior evita el drift: una tarea diaria completada
    tarde no empuja su vencimiento indefinidamente.
    """
    if recurrence == "daily":
        candidate = previous_due + dt.timedelta(days=1)
    elif recurrence == "weekly":
        candidate = previous_due + dt.timedelta(weeks=1)
    elif recurrence == "monthly":
        candidate = _add_months(previous_due, 1)
    else:
        raise ValueError(f"recurrencia desconocida: {recurrence!r}")
    # Si el anclaje quedó en el pasado (tarea muy atrasada), persigue a 'after'.
    if after is not None:
        while candidate <= after:
            if recurrence == "daily":
                candidate += dt.timedelta(days=1)
            elif recurrence == "weekly":
                candidate += dt.timedelta(weeks=1)
            else:
                candidate = _add_months(candidate, 1)
    return candidate


def is_overdue(task: Task, now: Optional[dt.datetime] = None) -> bool:
    """Vencida: tiene due_date en el pasado y no está done/cancelled."""
    if task.status in ("done", "cancelled"):
        return False
    due = parse_iso(task.due_date) if task.due_date else None
    if due is None:
        return False
    reference = now or dt.datetime.now(dt.timezone.utc)
    return due < reference


def due_before(tasks: Iterable[Task], moment: dt.datetime) -> List[Task]:
    return [t for t in tasks
            if t.due_date and parse_iso(t.due_date) is not None
            and parse_iso(t.due_date) <= moment
            and t.status not in ("done", "cancelled")]


def due_after(tasks: Iterable[Task], moment: dt.datetime) -> List[Task]:
    return [t for t in tasks
            if t.due_date and parse_iso(t.due_date) is not None
            and parse_iso(t.due_date) > moment
            and t.status not in ("done", "cancelled")]


class Scheduler:
    """Motor de recurrencia: al completar una tarea recurrente genera la siguiente."""

    def __init__(self, clock: Optional[Clock] = None) -> None:
        self.clock = clock or Clock()

    def next_occurrence(self, task: Task) -> Optional[Task]:
        """Copia 'futura' de la tarea con nuevo due_date; no la persiste."""
        if not task.recurrence:
            return None
        base = parse_iso(task.due_date) if task.due_date else self.clock.now()
        if base is None:
            base = self.clock.now()
        nxt = Task(
            id=0,  # el storage asigna el id real
            title=task.title,
            description=task.description,
            priority=task.priority,
            status="todo",
            tags=list(task.tags),
            depends_on=list(task.depends_on),
            recurrence=task.recurrence,
            due_date=next_due_date(base, task.recurrence,
                                   after=self.clock.now()).isoformat(),
        )
        return nxt

    def overdue(self, tasks: Iterable[Task]) -> List[Task]:
        now = self.clock.now()
        return [t for t in tasks if is_overdue(t, now)]
