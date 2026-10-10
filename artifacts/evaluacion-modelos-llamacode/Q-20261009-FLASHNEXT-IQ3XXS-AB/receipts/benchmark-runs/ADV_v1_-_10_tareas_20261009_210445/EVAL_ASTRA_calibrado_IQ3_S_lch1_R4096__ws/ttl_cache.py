import time
class TTLCache:
    def __init__(self, clock=None):
        self._clock = clock if clock is not None else time.monotonic
        self._data = {}
    def set(self, key, value, ttl):
        if isinstance(ttl, bool) or not isinstance(ttl, (int, float)):
            raise ValueError("ttl must be a strictly positive number")
        if not ttl > 0:
            raise ValueError("ttl must be a strictly positive number")
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
        return self._data.pop(key, None) is not None
    def _purge_expired(self):
        now = self._clock()
        expired = [k for k, (_, exp) in self._data.items() if now >= exp]
        for k in expired:
            del self._data[k]
    def __len__(self):
        self._purge_expired()
        return len(self._data)