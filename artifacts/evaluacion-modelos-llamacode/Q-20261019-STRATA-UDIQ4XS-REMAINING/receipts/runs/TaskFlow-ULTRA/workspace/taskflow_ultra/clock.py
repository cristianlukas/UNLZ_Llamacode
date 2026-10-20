"""Cronómetro con inyección de reloj para tests deterministas."""

from __future__ import annotations

import datetime as dt
from typing import Callable, Optional


class Clock:
    """Reloj inyectable: por defecto UTC real; los tests fijan uno falso."""

    def __init__(self, fixed: Optional[dt.datetime] = None) -> None:
        self._fixed = fixed

    def now(self) -> dt.datetime:
        if self._fixed is not None:
            return self._fixed
        return dt.datetime.now(dt.timezone.utc)

    def set_fixed(self, moment: Optional[dt.datetime]) -> None:
        self._fixed = moment

    def advance(self, **delta_kwargs) -> None:
        if self._fixed is None:
            self._fixed = self.now()
        self._fixed = self._fixed + dt.timedelta(**delta_kwargs)


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def parse_iso(value: str) -> dt.datetime:
    """Convierte ISO 8601 a datetime aware (UTC si naive)."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("fecha ISO vacía o no válida")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = dt.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed
