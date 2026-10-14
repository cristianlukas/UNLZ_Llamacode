"""Servicio de tareas: validaciones, dependencias, historial, undo y concurrencia."""

from __future__ import annotations

import copy
import csv
import threading
from datetime import datetime
from typing import Any, Optional

from .models import Task, now_iso, parse_iso
from .reports import markdown_report
from .scheduler import next_occurrence
from .storage import JsonTaskStorage

VALID_PRIORITIES = ("low", "medium", "high", "urgent")
VALID_STATUSES = ("todo", "doing", "blocked", "done", "cancelled")


class TaskService:
    def __init__(self, storage: Optional[JsonTaskStorage] = None) -> None:
        self.storage = storage
        self._lock = threading.RLock()
        self._tasks: dict[int, Task] = {}
        self._next_id = 1
        self._history: dict[int, list[dict[str, Any]]] = {}
        self._undo_stack: list[dict[str, Any]] = []
        if self.storage is not None:
            for task in self.storage.load():
                self._tasks[task.id] = task
                self._next_id = max(self._next_id, task.id + 1)

    # ------------------------------------------------------------------- API

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        tags: Optional[list[str]] = None,
        due_date: Optional[str] = None,
        depends_on: Optional[list[int]] = None,
        recurrence: Optional[str] = None,
    ) -> Task:
        if not str(title).strip():
            raise ValueError("title no puede estar vacio")
        with self._lock:
            task = Task(
                id=self._next_id,
                title=title,
                description=description,
                priority=priority,
                status="todo",
                tags=tags or [],
                depends_on=depends_on or [],
                recurrence=recurrence,
                due_date=due_date,
            )
            for dep_id in task.depends_on:
                if dep_id not in self._tasks:
                    raise KeyError(f"dependencia inexistente: {dep_id}")
            self._check_cycles(task.depends_on, task.id)
            self._next_id += 1
            self._tasks[task.id] = task
            self._record(task.id, "create", {"title": task.title}, None)
            self._persist()
            return task

    def list_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        tag: Optional[str] = None,
        search: Optional[str] = None,
    ) -> list[Task]:
        with self._lock:
            needle = search.lower() if search else None
            result: list[Task] = []
            for task in sorted(self._tasks.values(), key=lambda t: t.id):
                if status and task.status != str(status).lower():
                    continue
                if priority and task.priority != str(priority).lower():
                    continue
                if tag and str(tag).lower() not in task.tags:
                    continue
                if needle and needle not in task.title.lower() and needle not in task.description.lower():
                    continue
                result.append(task)
            return result

    def get_task(self, task_id: int) -> Task:
        with self._lock:
            task = self._tasks.get(int(task_id))
            if task is None:
                raise KeyError(f"tarea inexistente: {task_id}")
            return task

    def update_task(self, task_id: int, **changes: Any) -> Task:
        with self._lock:
            task = self.get_task(task_id)
            before = task.to_dict()
            applied: dict[str, Any] = {}
            for key, value in changes.items():
                if key in ("id", "created_at"):
                    continue
                if key in ("tags", "depends_on"):
                    value = list(value or [])
                elif value is not None and key in ("priority", "status", "recurrence"):
                    value = str(value).lower()
                setattr(task, key, value)
                applied[key] = value
            task.touch()
            self._record(task.id, "update", applied, before)
            self._persist()
            return task

    def set_status(self, task_id: int, status: str) -> Task:
        normalized = str(status).strip().lower()
        if normalized not in VALID_STATUSES:
            raise ValueError(
                f"status invalido: {status!r}; valido: {', '.join(VALID_STATUSES)}"
            )
        with self._lock:
            task = self.get_task(task_id)
            before = task.to_dict()
            task.status = normalized
            task.completed_at = now_iso() if normalized == "done" else None
            task.touch()
            self._record(task.id, "set_status", {"status": normalized}, before)
            self._persist()
            return task

    def complete_task(self, task_id: int) -> Task:
        with self._lock:
            task = self.get_task(task_id)
            blockers = self.blocked_by(task.id)
            if blockers:
                raise ValueError(
                    f"no se puede completar: dependencias no completadas {blockers}"
                )
            before = task.to_dict()
            task.status = "done"
            task.completed_at = now_iso()
            task.touch()
            self._record(task.id, "complete", {"status": "done"}, before)
            if task.recurrence:
                next_due = next_occurrence(task.due_date or now_iso(), task.recurrence)
                occurrence = Task(
                    id=self._next_id,
                    title=task.title,
                    description=task.description,
                    priority=task.priority,
                    status="todo",
                    tags=list(task.tags),
                    depends_on=list(task.depends_on),
                    recurrence=task.recurrence,
                    due_date=next_due,
                )
                self._next_id += 1
                self._tasks[occurrence.id] = occurrence
                self._record(occurrence.id, "recurrence", {"due_date": next_due}, None)
            self._persist()
            return task

    def reopen_task(self, task_id: int) -> Task:
        with self._lock:
            task = self.get_task(task_id)
            before = task.to_dict()
            task.status = "todo"
            task.completed_at = None
            task.touch()
            self._record(task.id, "reopen", {"status": "todo"}, before)
            self._persist()
            return task

    def cancel_task(self, task_id: int) -> Task:
        with self._lock:
            task = self.get_task(task_id)
            before = task.to_dict()
            task.status = "cancelled"
            task.completed_at = None
            task.touch()
            self._record(task.id, "cancel", {"status": "cancelled"}, before)
            self._persist()
            return task

    def delete_task(self, task_id: int) -> bool:
        with self._lock:
            task = self._tasks.get(int(task_id))
            if task is None:
                raise KeyError(f"tarea inexistente: {task_id}")
            before = task.to_dict()
            del self._tasks[task.id]
            for other in self._tasks.values():
                if task.id in other.depends_on:
                    other.depends_on.remove(task.id)
            self._record(task.id, "delete", before, before)
            self._persist()
            return True

    def add_dependency(self, task_id: int, depends_on_id: int) -> Task:
        with self._lock:
            task = self.get_task(task_id)
            dep_id = int(depends_on_id)
            if dep_id not in self._tasks:
                raise KeyError(f"dependencia inexistente: {dep_id}")
            if dep_id == task.id:
                raise ValueError("una tarea no puede depender de si misma")
            if dep_id in task.depends_on:
                return task
            candidate = list(task.depends_on) + [dep_id]
            self._check_cycles(candidate, task.id)
            before = task.to_dict()
            task.depends_on = candidate
            task.touch()
            self._record(task.id, "add_dependency", {"depends_on": candidate}, before)
            self._persist()
            return task

    def blocked_by(self, task_id: int) -> list[int]:
        with self._lock:
            task = self.get_task(task_id)
            return [
                dep_id
                for dep_id in task.depends_on
                if dep_id in self._tasks and self._tasks[dep_id].status != "done"
            ]

    def ready_tasks(self) -> list[Task]:
        with self._lock:
            return [
                task
                for task in sorted(self._tasks.values(), key=lambda t: t.id)
                if task.status == "todo" and not self.blocked_by(task.id)
            ]

    def history(self, task_id: int) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._history.get(int(task_id), []))

    def undo(self) -> bool:
        with self._lock:
            if not self._undo_stack:
                return False
            entry = self._undo_stack.pop()
            snapshot = entry["before"]
            task_id = entry["task_id"]
            if snapshot is None:
                # La tarea fue creada por esa mutacion: se elimina.
                self._tasks.pop(task_id, None)
            else:
                self._tasks[task_id] = Task.from_dict(snapshot)
            self._next_id = max([t.id for t in self._tasks.values()] + [0]) + 1
            self._persist()
            return True

    def summary(self) -> dict[str, Any]:
        with self._lock:
            by_status: dict[str, int] = {}
            by_priority: dict[str, int] = {}
            overdue = 0
            now = datetime.now()
            for task in self._tasks.values():
                by_status[task.status] = by_status.get(task.status, 0) + 1
                by_priority[task.priority] = by_priority.get(task.priority, 0) + 1
                if task.status not in ("done", "cancelled"):
                    due = parse_iso(task.due_date)
                    if due is not None and due.replace(tzinfo=None) < now:
                        overdue += 1
            return {
                "total": len(self._tasks),
                "by_status": by_status,
                "by_priority": by_priority,
                "overdue": overdue,
                "blocked": sum(1 for task in self._tasks.values() if self.blocked_by(task.id)),
                "ready": len(self.ready_tasks()),
            }

    def export_markdown(self, path: str) -> str:
        with self._lock:
            report = markdown_report(self.list_tasks(), self.summary())
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(report)
            return report

    def export_csv(self, path: str) -> str:
        with self._lock:
            tasks = self.list_tasks()
            fields = [
                "id", "title", "description", "priority", "status", "tags",
                "depends_on", "recurrence", "created_at", "updated_at",
                "due_date", "completed_at",
            ]
            with open(path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for task in tasks:
                    row = task.to_dict()
                    row["tags"] = ";".join(task.tags)
                    row["depends_on"] = ";".join(str(d) for d in task.depends_on)
                    writer.writerow(row)
            return path

    # --------------------------------------------------------------- internos

    def _check_cycles(self, depends_on: list[int], task_id: int) -> None:
        """Recorre las cadenas de dependencias hacia atras; si vuelve a task_id hay ciclo."""
        visited: set[int] = set()
        stack = list(depends_on)
        while stack:
            current = stack.pop()
            if current == task_id:
                raise ValueError(f"ciclo de dependencia detectado en tarea {task_id}")
            if current in visited:
                continue
            visited.add(current)
            node = self._tasks.get(current)
            if node is not None:
                stack.extend(node.depends_on)

    def _record(
        self,
        task_id: int,
        action: str,
        changes: dict[str, Any],
        before: Optional[dict[str, Any]],
    ) -> None:
        self._history.setdefault(task_id, []).append(
            {"timestamp": now_iso(), "task_id": task_id, "action": action, "changes": changes}
        )
        self._undo_stack.append({"task_id": task_id, "action": action, "before": before})

    def _persist(self) -> None:
        if self.storage is not None:
            self.storage.save(list(self._tasks.values()))
