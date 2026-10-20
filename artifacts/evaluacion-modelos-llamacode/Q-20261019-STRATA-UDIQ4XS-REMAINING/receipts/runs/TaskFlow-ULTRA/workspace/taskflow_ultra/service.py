"""Servicio de tareas con bloqueo para concurrencia."""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Iterable, List, Optional

from .models import InvalidTaskError, Task, parse_iso
from .storage import JsonTaskStorage


class TaskService:
    """Fachada de negocio sobre el storage, protegida por RLock."""

    def __init__(self, storage: JsonTaskStorage):
        self._storage = storage
        self._lock = threading.RLock()

    @property
    def storage(self) -> JsonTaskStorage:
        return self._storage

    def list_tasks(self) -> List[Task]:
        with self._lock:
            return self._storage.load()

    def get_task(self, task_id: int) -> Optional[Task]:
        with self._lock:
            for task in self._storage.load():
                if task.id == task_id:
                    return task
        return None

    def create_task(self, title: str, **kwargs) -> Task:
        with self._lock:
            task_id = self._storage.next_id()
            task = Task(id=task_id, title=title, **kwargs)
            task.validate()
            self._storage.append(task)
            return task

    def update_task(self, task_id: int, **fields) -> Task:
        """Actualiza campos permitidos. `tags`/`depends_on` reemplazan."""
        with self._lock:
            tasks = self._storage.load()
            target = None
            for task in tasks:
                if task.id == task_id:
                    target = task
                    break
            if target is None:
                raise InvalidTaskError(f"tarea {task_id} inexistente")
            for key, value in fields.items():
                if key in {"id", "created_at"}:
                    raise InvalidTaskError(f"campo no editable: {key}")
                if not hasattr(target, key):
                    raise InvalidTaskError(f"campo desconocido: {key}")
                setattr(target, key, value)
            target.updated_at = (
                datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            )
            target.validate()
            self._storage.update(target)
            return target

    def delete_task(self, task_id: int) -> bool:
        """Elimina la tarea y la quita de las dependencias restantes."""
        with self._lock:
            removed = self._storage.delete(task_id)
            if not removed:
                return False
            for task in self._storage.load():
                if task_id in task.depends_on:
                    task.depends_on = [d for d in task.depends_on if d != task_id]
                    self._storage.update(task)
            return True

    def complete_task(self, task_id: int) -> Task:
        return self.update_task(task_id, status="done")

    def filter_tasks(
        self,
        *,
        priority: Optional[str] = None,
        tag: Optional[str] = None,
        status: Optional[str] = None,
        overdue: Optional[bool] = None,
        due_before: Optional[str] = None,
        due_after: Optional[str] = None,
    ) -> List[Task]:
        tasks = self.list_tasks()
        if priority:
            tasks = [t for t in tasks if t.priority == priority]
        if tag:
            tasks = [t for t in tasks if tag in t.tags]
        if status:
            tasks = [t for t in tasks if t.status == status]
        if overdue is not None:
            now = datetime.now(timezone.utc)
            tasks = [t for t in tasks if t.is_overdue(now) == overdue]
        if due_before:
            limit = parse_iso(due_before)
            tasks = [
                t for t in tasks if t.due_at is not None and t.due_at <= limit
            ]
        if due_after:
            limit = parse_iso(due_after)
            tasks = [
                t for t in tasks if t.due_at is not None and t.due_at >= limit
            ]
        return tasks

    def sort_tasks(self, key: str = "priority") -> List[Task]:
        tasks = self.list_tasks()
        if key == "priority":
            order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
            return sorted(
                tasks, key=lambda t: (order.get(t.priority, 2), t.id)
            )
        if key == "due":
            far = datetime.max.replace(tzinfo=timezone.utc)
            return sorted(tasks, key=lambda t: t.due_at or far)
        if key == "created":
            return sorted(tasks, key=lambda t: t.created_at_dt)
        raise InvalidTaskError(f"criterio de orden inválido: {key}")

    def ready_tasks(self, now: Optional[datetime] = None) -> List[Task]:
        """Pendientes cuyas dependencias están todas 'done'."""
        now = now or datetime.now(timezone.utc)
        with self._lock:
            tasks = self._storage.load()
        done_ids = {t.id for t in tasks if t.status == "done"}
        return [
            t
            for t in tasks
            if t.status in ("todo", "doing")
            and all(d in done_ids for d in t.depends_on)
        ]

    def blocked_tasks(self) -> List[Task]:
        """Pendientes con al menos una dependencia no completada."""
        now = datetime.now(timezone.utc)
        ready_ids = {t.id for t in self.ready_tasks(now)}
        return [
            t
            for t in self.list_tasks()
            if t.status in ("todo", "doing", "blocked") and t.id not in ready_ids
        ]

    def detect_cycles(self) -> List[List[int]]:
        """Ciclos de dependencias entre tareas existentes (DFS, id ordenado)."""
        with self._lock:
            tasks = self._storage.load()
        by_id = {t.id: t for t in tasks}
        graph = {
            t.id: [d for d in t.depends_on if d in by_id] for t in tasks
        }
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {tid: WHITE for tid in graph}
        stack: List[int] = []
        cycles: List[List[int]] = []

        def visit(node: int) -> None:
            color[node] = GRAY
            stack.append(node)
            for dep in graph[node]:
                if color[dep] == GRAY:
                    start = stack.index(dep)
                    cycle = stack[start:]
                    cycles.append(sorted(cycle))
                elif color[dep] == WHITE:
                    visit(dep)
            stack.pop()
            color[node] = BLACK

        for tid in sorted(graph):
            if color[tid] == WHITE:
                visit(tid)
        unique: List[List[int]] = []
        seen = set()
        for cycle in cycles:
            marker = tuple(cycle)
            if marker not in seen:
                seen.add(marker)
                unique.append(cycle)
        return unique
