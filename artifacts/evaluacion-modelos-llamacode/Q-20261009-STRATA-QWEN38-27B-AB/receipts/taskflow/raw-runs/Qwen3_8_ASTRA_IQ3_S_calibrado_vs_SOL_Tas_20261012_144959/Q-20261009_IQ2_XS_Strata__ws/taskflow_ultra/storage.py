"""Persistencia JSON atomica y thread-safe."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from typing import Optional

from .models import Task


class JsonTaskStorage:
    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.Lock()

    def load(self) -> list[Task]:
        with self._lock:
            if not os.path.exists(self.path):
                return []
            try:
                with open(self.path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
            except (OSError, ValueError):
                return []
            if not isinstance(data, list):
                return []
            tasks: list[Task] = []
            for entry in data:
                try:
                    tasks.append(Task.from_dict(entry))
                except ValueError:
                    continue  # entrada malformada: se ignora sin romper la carga
            return tasks

    def save(self, tasks: list[Task]) -> None:
        with self._lock:
            payload = [task.to_dict() for task in tasks]
            directory = os.path.dirname(os.path.abspath(self.path)) or "."
            os.makedirs(directory, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, ensure_ascii=False, indent=2)
                os.replace(tmp_path, self.path)
            except OSError:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise

    def path_of(self) -> Optional[str]:
        return self.path
