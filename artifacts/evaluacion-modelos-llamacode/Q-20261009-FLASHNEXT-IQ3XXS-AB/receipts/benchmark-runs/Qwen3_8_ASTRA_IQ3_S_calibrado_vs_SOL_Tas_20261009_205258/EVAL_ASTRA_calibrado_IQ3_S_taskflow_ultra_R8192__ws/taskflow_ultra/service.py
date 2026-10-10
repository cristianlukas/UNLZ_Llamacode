"""Servicio de aplicación: CRUD, dependencias, recurrencia, historial, undo, resumen y exports.

Toda la mutación de estado está protegida por un RLock: seguro para múltiples hilos.
"""
from __future__ import annotations

import copy
import csv
import threading
from datetime import datetime, timezone
from typing import Any

from .models import PRIORITIES, STATUSES, Task, now_iso, parse_iso_datetime
from .scheduler import next_occurrence
from .storage import JsonTaskStorage

_MUTABLE_FIELDS = (
    "title",
    "description",
    "priority",
    "status",
    "tags",
    "depends_on",
    "recurrence",
    "due_date",
    "completed_at",
)


def _is_overdue(task: Task, now: datetime) -> bool:
    if task.status in ("done", "cancelled") or not task.due_date:
        return False
    try:
        due = parse_iso_datetime(task.due_date)
    except ValueError:
        return False
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    return due < now


class TaskService:
    def __init__(self, storage: JsonTaskStorage | None = None) -> None:
        self._lock = threading.RLock()
        self._tasks: dict[int, Task] = {}
        self._next_id: int = 1
        self._history: dict[int, list[dict[str, Any]]] = {}
        self._undo_stack: list[dict[str, Any]] = []
        if storage is not None:
            self._storage: JsonTaskStorage | None = storage
            self.reload()
        else:
            self._storage = None

    # ------------------------------------------------------------------ carga

    def reload(self) -> None:
        """Recarga el estado desde el storage (si existe)."""
        if self._storage is None:
            return
        with self._lock:
            tasks = self._storage.load()
            self._tasks = {task.id: task for task in tasks}
            self._next_id = (max(self._tasks) + 1) if self._tasks else 1

    def save(self) -> None:
        if self._storage is not None:
            with self._lock:
                self._storage.save(self._tasks.values())

    # ------------------------------------------------------------- snapshots

    def _snapshot(self) -> dict[str, Any]:
        return {
            "tasks": {tid: copy.deepcopy(t) for tid, t in self._tasks.items()},
            "next_id": self._next_id,
        }

    def _record_history(self, task_id: int, action: str, changes: dict[str, Any]) -> None:
        self._history.setdefault(task_id, []).append(
            {"timestamp": now_iso(), "task_id": task_id, "action": action, "changes": changes}
        )

    def _touch(self, task: Task) -> None:
        task.updated_at = now_iso()

    # ------------------------------------------------------------- creación

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        tags: list[str] | None = None,
        due_date: str | None = None,
        depends_on: list[int] | None = None,
        recurrence: str | None = None,
    ) -> Task:
        with self._lock:
            snapshot = self._snapshot()
            task = Task(
                id=self._next_id,
                title=title,
                description=description,
                priority=priority,
                tags=tags,
                due_date=due_date,
                depends_on=depends_on,
                recurrence=recurrence,
            )
            if depends_on:
                self._tasks[task.id] = task
                try:
                    self._check_dependencies(task.id, task.depends_on)
                except (ValueError, KeyError):
                    del self._tasks[task.id]
                    raise
            self._tasks[task.id] = task
            self._next_id += 1
            self._record_history(task.id, "create", {"new": task.to_dict()})
            self._undo_stack.append(snapshot)
            self.save()
            return task

    # --------------------------------------------------------------- lectura

    def list_tasks(
        self,
        status: str | None = None,
        priority: str | None = None,
        tag: str | None = None,
        search: str | None = None,
    ) -> list[Task]:
        with self._lock:
            tasks = sorted(self._tasks.values(), key=lambda t: t.id)
        if status is not None:
            if status not in STATUSES:
                raise ValueError(f"invalid status {status!r}; expected one of: {', '.join(STATUSES)}")
            tasks = [t for t in tasks if t.status == status]
        if priority is not None:
            if priority not in PRIORITIES:
                raise ValueError(
                    f"invalid priority {priority!r}; expected one of: {', '.join(PRIORITIES)}"
                )
            tasks = [t for t in tasks if t.priority == priority]
        if tag is not None:
            needle = str(tag).strip().lower()
            tasks = [t for t in tasks if needle in t.tags]
        if search is not None:
            needle = str(search).strip().lower()
            tasks = [
                t
                for t in tasks
                if needle in t.title.lower() or needle in t.description.lower()
            ]
        return tasks

    def get_task(self, task_id: int) -> Task:
        with self._lock:
            task = self._tasks.get(int(task_id))
        if task is None:
            raise KeyError(f"task {task_id} not found")
        return task

    # ------------------------------------------------------------- mutación

    def update_task(self, task_id: int, **changes: Any) -> Task:
        with self._lock:
            task = self.get_task(task_id)
            unknown = set(changes) - set(_MUTABLE_FIELDS)
            if unknown:
                raise ValueError(f"unknown fields: {', '.join(sorted(unknown))}")
            snapshot = self._snapshot()
            before = task.to_dict()
            for field_name, value in changes.items():
                setattr(task, field_name, value)
            task.__post_init__()
            if "depends_on" in changes:
                self._check_dependencies(task.id, task.depends_on)
            self._touch(task)
            self._record_history(
                task.id, "update",
                {"old": before, "new": task.to_dict()},
            )
            self._undo_stack.append(snapshot)
            self.save()
            return task

    def set_status(self, task_id: int, status: str) -> Task:
        if status not in STATUSES:
            raise ValueError(f"invalid status {status!r}; expected one of: {', '.join(STATUSES)}")
        with self._lock:
            task = self.get_task(task_id)
            if status == "done":
                return self.complete_task(task_id)
            snapshot = self._snapshot()
            old_status = task.status
            task.status = status
            if status in ("todo", "doing", "blocked"):
                task.completed_at = None
            self._touch(task)
            self._record_history(task.id, "update", {"old": {"status": old_status}, "new": {"status": status}})
            self._undo_stack.append(snapshot)
            self.save()
            return task

    def complete_task(self, task_id: int) -> Task:
        with self._lock:
            task = self.get_task(task_id)
            blockers = self._blocked_by(task)
            if blockers:
                raise ValueError(
                    f"cannot complete task {task_id}: unfinished dependencies: {blockers}"
                )
            snapshot = self._snapshot()
            old_status = task.status
            task.status = "done"
            task.completed_at = now_iso()
            self._touch(task)
            self._record_history(
                task.id, "update", {"old": {"status": old_status}, "new": {"status": "done"}}
            )
            if task.recurrence:
                next_due = next_occurrence(task.due_date, task.recurrence)
                self._tasks[self._next_id] = Task(
                    id=self._next_id,
                    title=task.title,
                    description=task.description,
                    priority=task.priority,
                    status="todo",
                    tags=list(task.tags),
                    recurrence=task.recurrence,
                    due_date=next_due,
                )
                self._record_history(
                    self._next_id,
                    "create",
                    {"new": {"id": self._next_id, "title": task.title, "due_date": next_due,
                              "reason": f"recurrence {task.recurrence} of task {task.id}"}},
                )
                self._next_id += 1
            self._undo_stack.append(snapshot)
            self.save()
            return task

    def reopen_task(self, task_id: int) -> Task:
        with self._lock:
            task = self.get_task(task_id)
            snapshot = self._snapshot()
            old_status = task.status
            task.status = "todo"
            task.completed_at = None
            self._touch(task)
            self._record_history(
                task.id, "update", {"old": {"status": old_status}, "new": {"status": "todo"}}
            )
            self._undo_stack.append(snapshot)
            self.save()
            return task

    def cancel_task(self, task_id: int) -> Task:
        with self._lock:
            task = self.get_task(task_id)
            snapshot = self._snapshot()
            old_status = task.status
            task.status = "cancelled"
            self._touch(task)
            self._record_history(
                task.id, "update", {"old": {"status": old_status}, "new": {"status": "cancelled"}}
            )
            self._undo_stack.append(snapshot)
            self.save()
            return task

    def delete_task(self, task_id: int) -> bool:
        with self._lock:
            task = self.get_task(task_id)
            snapshot = self._snapshot()
            del self._tasks[task.id]
            for other in self._tasks.values():
                if task.id in other.depends_on:
                    other.depends_on = [d for d in other.depends_on if d != task.id]
            self._record_history(task.id, "delete", {"old": task.to_dict()})
            self._undo_stack.append(snapshot)
            self.save()
            return True

    def add_dependency(self, task_id: int, depends_on_id: int) -> Task:
        with self._lock:
            task = self.get_task(task_id)
            if int(depends_on_id) not in self._tasks:
                raise KeyError(f"dependency task {depends_on_id} not found")
            if depends_on_id == task.id:
                raise ValueError(f"task {task.id} cannot depend on itself")
            if depends_on_id in task.depends_on:
                return task
            snapshot = self._snapshot()
            if self._would_create_cycle(task.id, int(depends_on_id)):
                raise ValueError(
                    f"adding dependency {task.id} -> {depends_on_id} would create a cycle"
                )
            task.depends_on.append(int(depends_on_id))
            self._touch(task)
            self._record_history(
                task.id, "update",
                {"old": {"depends_on": snapshot["tasks"][task.id].depends_on},
                 "new": {"depends_on": list(task.depends_on)}},
            )
            self._undo_stack.append(snapshot)
            self.save()
            return task

    # --------------------------------------------------------- dependencias

    def _check_dependencies(self, task_id: int, depends_on: list[int]) -> None:
        for dep in depends_on:
            if dep == task_id:
                raise ValueError(f"task {task_id} cannot depend on itself")
            if dep not in self._tasks:
                raise KeyError(f"dependency task {dep} not found")
        for dep in depends_on:
            if self._would_create_cycle(task_id, dep):
                raise ValueError(
                    f"dependency {task_id} -> {dep} would create a cycle"
                )

    def _would_create_cycle(self, task_id: int, depends_on_id: int) -> bool:
        """True si task_id ya es alcanzable desde depends_on_id (cierre del ciclo)."""
        if task_id == depends_on_id:
            return True
        stack = [depends_on_id]
        visited: set[int] = set()
        while stack:
            current = stack.pop()
            if current == task_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            node = self._tasks.get(current)
            if node:
                stack.extend(node.depends_on)
        return False

    def _blocked_by(self, task: Task) -> list[int]:
        return [
            dep
            for dep in task.depends_on
            if dep not in self._tasks or self._tasks[dep].status != "done"
        ]

    def blocked_by(self, task_id: int) -> list[int]:
        with self._lock:
            task = self.get_task(task_id)
            return self._blocked_by(task)

    def ready_tasks(self) -> list[Task]:
        with self._lock:
            return [
                task
                for task in sorted(self._tasks.values(), key=lambda t: t.id)
                if task.status == "todo" and not self._blocked_by(task)
            ]

    # ------------------------------------------------- historial y undo

    def history(self, task_id: int) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._history.get(int(task_id), []))

    def undo(self) -> bool:
        with self._lock:
            if not self._undo_stack:
                return False
            snapshot = self._undo_stack.pop()
            self._tasks = snapshot["tasks"]
            self._next_id = snapshot["next_id"]
            self.save()
            return True

    # ------------------------------------------------------------- resumen

    def summary(self) -> dict[str, Any]:
        with self._lock:
            tasks = list(self._tasks.values())
            now = datetime.now(timezone.utc)
            by_status: dict[str, int] = {s: 0 for s in STATUSES}
            by_priority: dict[str, int] = {p: 0 for p in PRIORITIES}
            for task in tasks:
                by_status[task.status] = by_status.get(task.status, 0) + 1
                by_priority[task.priority] = by_priority.get(task.priority, 0) + 1
            return {
                "total": len(tasks),
                "by_status": by_status,
                "by_priority": by_priority,
                "overdue": sum(1 for t in tasks if _is_overdue(t, now)),
                "blocked": sum(1 for t in tasks if t.status == "blocked"),
                "ready": sum(1 for t in tasks if t.status == "todo" and not self._blocked_by(t)),
            }

    # -------------------------------------------------------------- exports

    def export_markdown(self, path: str) -> str:
        from .reports import markdown_report

        with self._lock:
            report = markdown_report(self.list_tasks(), self.summary())
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(report)
        return path

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
                row["tags"] = ";".join(row["tags"])
                row["depends_on"] = ";".join(str(d) for d in row["depends_on"])
                writer.writerow(row)
        return path
