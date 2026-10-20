"""Storage JSON persistente: atomico, thread-safe y tolerante a corrupcion."""
from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Optional

from .models import Task


class JsonTaskStorage:
    """Persiste tareas en un archivo JSON con guardado atomico y lock propio."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ io
    def load(self) -> list[Task]:
        """Carga tareas. Archivo inexistente -> []. Corrupto -> backup + []."""
        with self._lock:
            return self._load_unlocked()

    def save(self, tasks: list[Task]) -> None:
        """Guardado atomico: tmp en el mismo directorio + os.replace."""
        payload = {"version": 1, "tasks": [t.to_dict() for t in tasks]}
        text = json.dumps(payload, indent=2, ensure_ascii=False)
        with self._lock:
            self._write_atomic(text)

    # ------------------------------------------------------------- helpers
    def next_id(self) -> int:
        with self._lock:
            tasks = self._load_unlocked()
            return max((t.id for t in tasks), default=0) + 1

    def append(self, task: Task) -> None:
        with self._lock:
            tasks = self._load_unlocked()
            tasks.append(task)
            self._save_unlocked(tasks)

    def update(self, task: Task) -> bool:
        with self._lock:
            tasks = self._load_unlocked()
            for i, existing in enumerate(tasks):
                if existing.id == task.id:
                    tasks[i] = task
                    self._save_unlocked(tasks)
                    return True
            return False

    def delete(self, task_id: int) -> bool:
        with self._lock:
            tasks = self._load_unlocked()
            remaining = [t for t in tasks if t.id != task_id]
            if len(remaining) == len(tasks):
                return False
            self._save_unlocked(remaining)
            return True

    # ------------------------------------------------------------ internal
    def _load_unlocked(self) -> list[Task]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            self._backup_corrupt()
            return []
        if isinstance(raw, dict):
            items = raw.get("tasks", [])
        elif isinstance(raw, list):
            items = raw
        else:
            self._backup_corrupt()
            return []
        tasks: list[Task] = []
        changed = False
        for item in items:
            try:
                tasks.append(Task.from_dict(item))
            except (ValueError, TypeError, KeyError):
                changed = True  # descarta registros invalidos
        if changed:
            self._save_unlocked(tasks)
        return tasks

    def _save_unlocked(self, tasks: list[Task]) -> None:
        payload = {"version": 1, "tasks": [t.to_dict() for t in tasks]}
        text = json.dumps(payload, indent=2, ensure_ascii=False)
        self._write_atomic(text)

    def _write_atomic(self, text: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(self.path.parent), prefix=".taskflow_", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(text)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, self.path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    def _backup_corrupt(self) -> None:
        try:
            backup = self.path.with_suffix(self.path.suffix + ".corrupt")
            os.replace(self.path, backup)
        except OSError:
            pass
