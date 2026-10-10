"""Storage JSON persistente, atómico y thread-safe."""
from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path

from .models import Task


class JsonTaskStorage:
    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()

    def load(self) -> list[Task]:
        with self._lock:
            return self._load_unlocked()

    def _load_unlocked(self) -> list[Task]:
        try:
            raw = self.path.read_text(encoding="utf-8")
        except (FileNotFoundError, NotADirectoryError, IsADirectoryError, PermissionError):
            return []
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return []
        if not isinstance(data, list):
            return []
        tasks: list[Task] = []
        for entry in data:
            try:
                tasks.append(Task.from_dict(entry))
            except (ValueError, TypeError, KeyError):
                continue
        return tasks

    def save(self, tasks: list[Task]) -> None:
        payload = [t.to_dict() for t in tasks]
        self._write_atomic(payload)

    def _write_atomic(self, payload: list[dict]) -> None:
        with self._lock:
            directory = self.path.parent
            common_dir = str(directory) if str(directory) else "."
            os.makedirs(common_dir, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(
                dir=common_dir, prefix=".taskflow_", suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, ensure_ascii=False, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp_name, self.path)
            except Exception:
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass
                raise
