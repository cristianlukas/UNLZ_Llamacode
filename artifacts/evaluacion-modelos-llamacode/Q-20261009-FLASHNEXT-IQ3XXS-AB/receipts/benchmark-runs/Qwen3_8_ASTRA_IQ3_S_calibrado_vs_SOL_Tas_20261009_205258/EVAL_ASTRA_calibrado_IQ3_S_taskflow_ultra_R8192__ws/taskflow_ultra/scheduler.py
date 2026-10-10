"""Scheduler puro: próxima ocurrencia según recurrencia, con clamp de fin de mes."""
from __future__ import annotations

import calendar
from datetime import datetime, timedelta

from .models import RECURRENCES, parse_iso_datetime


def _clamp_day(year: int, month: int, day: int) -> int:
    return min(day, calendar.monthrange(year, month)[1])


def next_occurrence(due_date_iso: str | None, recurrence: str | None) -> str | None:
    """Devuelve la próxima fecha ISO según daily/weekly/monthly.

    monthly hace clamp al último día válido del mes destino (ej: 31-ene -> 28-feb).
    Si no hay due_date, se toma 'now' como base. Recurrencia inválida o None -> None.
    """
    if recurrence is None or recurrence not in RECURRENCES:
        return None
    base = parse_iso_datetime(due_date_iso) if due_date_iso else datetime.now()
    if recurrence == "daily":
        nxt = base + timedelta(days=1)
    elif recurrence == "weekly":
        nxt = base + timedelta(weeks=1)
    else:  # monthly
        year, month = base.year, base.month + 1
        if month > 12:
            month, year = 1, year + 1
        nxt = base.replace(year=year, month=month, day=_clamp_day(year, month, base.day))
    return nxt.isoformat()
