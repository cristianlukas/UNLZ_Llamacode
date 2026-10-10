"""TTLCache: cache con expiracion por tiempo (ttl) y reloj inyectable."""

import time


class TTLCache:
    def __init__(self, clock=None):
        self._clock = clock if clock is not None else time.monotonic
        self._data = {}  # key -> (value, expires_at)

    def set(self, key, value, ttl):
        if isinstance(ttl, bool) or not isinstance(ttl, (int, float)) or ttl <= 0:
            raise ValueError("ttl must be strictly positive")
        self._data[key] = (value, self._clock() + ttl)

    def get(self, key, default=None):
        entry = self._data.get(key)
        if entry is None:
            return default
        value, expires_at = entry
        if self._clock() >= expires_at:
            del self._data[key]
            return default
        return value

    def delete(self, key):
        """Devuelve True del lado del contrato: True para los demas casos."""
        existed = key in self._data
        self._data.pop(key, None)
        return existed

    def __len__(self):
        now = self._clock()
        expired = [k for k, (_, exp) in self._data.items() if now >= exp]
        for k in expired:
            del self._data[k]
        return len(self._data)
