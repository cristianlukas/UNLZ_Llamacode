"""TTL cache with an injectable monotonic clock."""

import time


class TTLCache:
    """Cache with per-entry TTL, expiring when now >= expires_at."""

    def __init__(self, clock=None):
        self._clock = clock if clock is not None else time.monotonic
        self._entries = {}  # key -> (value, expires_at)

    def set(self, key, value, ttl):
        if ttl <= 0:
            raise ValueError("ttl must be strictly positive")
        self._entries[key] = (value, self._clock() + ttl)

    def get(self, key, default=None):
        entry = self._entries.get(key)
        if entry is None:
            return default
        value, expires_at = entry
        if self._clock() >= expires_at:
            del self._entries[key]
            return default
        return value

    def delete(self, key):
        if key in self._entries:
            del self._entries[key]
            return True
        return False

    def __len__(self):
        now = self._clock()
        expired = [key for key, (_, expires_at) in self._entries.items() if now >= expires_at]
        for key in expired:
            del self._entries[key]
        return len(self._entries)
