"""Planificador puro de recurrencias."""

from __future__ import annotations

import calendar
from datetime import timedelta

from .models import VALID_RECURRENCES, parse_iso

MONTHLY = {"daily": 1, "weekly": 7}


def next_occurrence(due_date_iso: str, recurrence: str) -> str:
    """Proxima fecha ISO segun daily/weekly/monthly, con clamp de fin de mes."""
    if recurrence not in VALID_RECURRENCES:
        raise ValueError(
            f"recurrence invalida: {recurrence!r}; valida: {', '.join(VALID_RECURRENCES)}"
        )
    parsed = parse_iso(due_date_iso)
    if parsed is None:
        raise ValueError(f"due_date_iso no es una fecha ISO 8601 valida: {due_date_iso!r}")

    if recurrence in MONTHLY:
        nxt = parsed + timedelta(days=MONTHLY[recurrence])
    else:
        month = parsed.month + 1
        year = parsed.year
        if month > 12:
            month = 1
            year += 1
        day = min(parsed.day, calendar.monthrange(year, month)[1])
        nxt = parsed.replace(year=year, month=month, day=day)

    return nxt.date().isoformat()
