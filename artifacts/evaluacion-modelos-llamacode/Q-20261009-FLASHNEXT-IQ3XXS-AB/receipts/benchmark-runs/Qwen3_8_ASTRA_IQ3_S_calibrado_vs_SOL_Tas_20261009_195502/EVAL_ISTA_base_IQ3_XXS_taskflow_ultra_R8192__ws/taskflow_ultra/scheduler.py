"""Scheduler puro: cálculo de próximas ocurrencias."""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from .models import VALID_RECURRENCES

_DATE_FMT = "%Y-%m-%d"


def _parse_date(value: str) -> date:
    text = str(value).strip()
    if not text:
        raise ValueError("due_date vacía")
    # Acepta ISO date o ISO datetime (toma la parte de fecha).
    if "T" in text:
        text = text.split("T", 1)[0]
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"due_date ISO inválida: {value!r}") from exc


def _shift_months(d: date, months: int) -> date:
    common = (d.year * 12 + d.month - 1) + months
    year, month = divmod(common, 12)
    month += 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def next_occurrence(due_date_iso: str, recurrence: str) -> str:
    """Devuelve la próxima fecha ISO según daily/weekly/monthly.

    monthly hace clamp al último día válido del mes destino.
    """
    if recurrence not in VALID_RECURRENCES:
        raise ValueError(
            f"recurrence inválida: {recurrence!r}. Válidas: {', '.join(VALID_RECURRENCES)}"
        )
    base = _parse_date(due_date_iso)
    if recurrence == "daily":
        nxt = base + timedelta(days=1)
    elif recurrence == "weekly":
        nxt = base + timedelta(weeks=1)
    else:
        nxt = _shift_months(base, 1)
    return nxt.isoformat()
