import time


class TTLCache:
    def __init__(self, clock=None):
        self._clock = clock if clock is not None else time.monotonic
        self._data = {}

    def set(self, key, value, ttl):
        if ttl <= 0:
            raise ValueError("ttl must be strictly positive")
        self._data[key] = (value, self._clock() + ttl)

    def get(self, key, default=None):
        if key not in self._data:
            return default
        value, expires_at = self._data[key]
        if self._clock() >= expires_at:
            del self._data[key]
            return default
        return value

    def delete(self, key):
        self._data.pop(key, None)

    def __len__(self):
        now = self._clock()
        expired = [k for k, (_, exp) in self._data.items() if now >= exp]
        for k in expired:
            del self._data[k]
        return len(self._data)
