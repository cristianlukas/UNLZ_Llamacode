"""Storage JSON persistente: tolerante a corrupción, guardado atómico y thread-safe."""
from __future__ import annotations

import json
import os
import tempfile
import threading
from typing import Iterable

from .models import Task


class JsonTaskStorage:
    def __init__(self, path: str) -> None:
        self.path = str(path)
        self._lock = threading.Lock()

    def load(self) -> list[Task]:
        """Carga tareas. Archivo inexistente o JSON corrupto -> lista vacía.

        Entradas malformadas individuales se ignoran sin romper la carga.
        """
        with self._lock:
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
            except (ValueError, TypeError, KeyError):
                continue
        return tasks

    def save(self, tasks: Iterable[Task]) -> None:
        """Persiste JSON de forma atómica (temporal + os.replace)."""
        payload = [task.to_dict() for task in tasks]
        with self._lock:
            directory = os.path.dirname(os.path.abspath(self.path))
            os.makedirs(directory, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(
                prefix=".taskflow-", suffix=".tmp", dir=directory
            )
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
