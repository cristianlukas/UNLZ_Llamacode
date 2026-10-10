"""Servicio de dominio: TaskService thread-safe con historial y undo."""
from __future__ import annotations

import copy
import csv
import threading
from datetime import date, datetime, timezone
from typing import Any, Callable, Optional

from .models import (
    Task,
    VALID_PRIORITIES,
    VALID_RECURRENCES,
    VALID_STATUSES,
    normalize_depends_on,
    normalize_tags,
    _now_iso,
)
from .reports import markdown_report
from .scheduler import next_occurrence

_MUTABLE_FIELDS = {
    "title",
    "description",
    "priority",
    "status",
    "tags",
    "depends_on",
    "recurrence",
    "due_date",
}


def _parse_iso(value: str) -> datetime:
    text = str(value)
    if "T" in text:
        text = text.split("T", 1)[0]
    return datetime.combine(date.fromisoformat(text), datetime.min.time())


class TaskService:
    def __init__(self, storage: Any = None) -> None:
        self._lock = threading.RLock()
        self._tasks: dict[int, Task] = {}
        self._next_id = 1
        self._history: dict[int, list[dict[str, Any]]] = {}
        self._undo_stack: list[dict[str, Any]] = []
        self._storage = storage
        if storage is not None:
            self.load()

    # ---------- persistencia ----------
    def load(self) -> None:
        with self._lock:
            tasks = self._storage.load()
            self._tasks = {t.id: t for t in tasks}
            self._next_id = (max(self._tasks) + 1) if self._tasks else 1
            for tid in self._tasks:
                self._history.setdefault(tid, [])

    def save(self) -> None:
        with self._lock:
            if self._storage is not None:
                self._storage.save(self.sorted_tasks())

    # ---------- helpers internos ----------
    def sorted_tasks(self) -> list[Task]:
        with self._lock:
            return [self._tasks[k] for k in sorted(self._tasks)]

    def _snapshot(self) -> dict[str, Any]:
        return {
            "tasks": copy.deepcopy(self._tasks),
            "next_id": self._next_id,
        }

    def _push_undo(self) -> None:
        self._undo_stack.append(self._snapshot())

    def _record(self, task_id: int, action: str, changes: dict[str, Any]) -> None:
        entry = {
            "timestamp": _now_iso(),
            "task_id": task_id,
            "action": action,
            "changes": changes,
        }
        self._history.setdefault(task_id, []).append(entry)

    def _require(self, task_id: int) -> Task:
        try:
            common = int(task_id)
        except (TypeError, ValueError):
            raise KeyError(f"tarea inexistente: {task_id!r}")
        task = self._tasks.get(common)
        if task is None:
            raise KeyError(f"tarea inexistente: {common}")
        return task

    def _validate_common(self, common: str) -> None:
        if common not in VALID_PRIORITIES:
            raise ValueError(
                f"priority inválida: {common!r}. Válidas: {', '.join(VALID_PRIORITIES)}"
            )

    def _would_cycle(self, task_id: int, new_dep: int) -> bool:
        if task_id == new_dep:
            return True
        stack = [new_dep]
        seen: set[int] = set()
        while stack:
            current = stack.pop()
            if current == task_id:
                return True
            if current in seen:
                continue
            seen.add(current)
            common = self._tasks.get(current)
            if common is not None:
                stack.extend(common.depends_on)
        return False

    def _unmet_dependencies(self, task: Task) -> list[int]:
        unmet: list[int] = []
        for dep in task.depends_on:
            dep_task = self._tasks.get(dep)
            if dep_task is None or dep_task.status != "done":
                unmet.append(dep)
        return unmet

    # ---------- API pública ----------
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
        with self._lock:
            common = str(title).strip()
            if not common:
                raise ValueError("title no puede estar vacío")
            self._validate_common(priority)
            if recurrence is not None and recurrence not in VALID_RECURRENCES:
                raise ValueError(
                    f"recurrence inválida: {recurrence!r}. Válidas: {', '.join(VALID_RECURRENCES)}"
                )
            deps = normalize_depends_on(depends_on)
            for dep in deps:
                if dep not in self._tasks:
                    raise KeyError(f"dependencia inexistente: {dep}")
            self._push_undo()
            task = Task(
                id=self._next_id,
                title=common,
                description=str(description or ""),
                priority=priority,
                status="todo",
                tags=normalize_tags(tags),
                depends_on=deps,
                recurrence=recurrence,
                due_date=due_date,
            )
            self._next_id += 1
            self._tasks[task.id] = task
            self._record(task.id, "create", {"title": task.title})
            self.save()
            return task

    def list_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        tag: Optional[str] = None,
        search: Optional[str] = None,
    ) -> list[Task]:
        with self._lock:
            if status is not None and status not in VALID_STATUSES:
                raise ValueError(
                    f"status inválida: {status!r}. Válidas: {', '.join(VALID_STATUSES)}"
                )
            if priority is not None:
                self._validate_common(priority)
            needle = search.lower() if search else None
            wanted_tag = tag.strip().lower() if tag else None
            result: list[Task] = []
            for task in self.sorted_tasks():
                if status is not None and task.status != status:
                    continue
                if priority is not None and task.priority != priority:
                    continue
                if wanted_tag and wanted_tag not in task.tags:
                    continue
                if needle and needle not in task.title.lower() and needle not in task.description.lower():
                    continue
                result.append(task)
            return result

    def get_task(self, task_id: int) -> Task:
        with self._lock:
            return self._require(task_id)

    def update_task(self, task_id: int, **changes: Any) -> Task:
        with self._lock:
            task = self._require(task_id)
            unknown = set(changes) - _MUTABLE_FIELDS
            if unknown:
                raise ValueError(f"campos no actualizables: {', '.join(sorted(unknown))}")
            self._push_undo()
            applied: dict[str, Any] = {}
            if "title" in changes:
                new_title = str(changes["title"]).strip()
                if not new_title:
                    raise ValueError("title no puede estar vacío")
                applied["title"] = new_title
            if "priority" in changes:
                self._validate_common(changes["priority"])
                applied["priority"] = changes["priority"]
            if "status" in changes:
                new_status = changes["status"]
                if new_status not in VALID_STATUSES:
                    raise ValueError(
                        f"status inválida: {new_status!r}. Válidas: {', '.join(VALID_STATUSES)}"
                    )
                applied["status"] = new_status
            if "tags" in changes:
                applied["tags"] = normalize_tags(changes["tags"])
            if "depends_on" in changes:
                deps = normalize_depends_on(changes["depends_on"])
                for dep in deps:
                    if dep not in self._tasks:
                        raise KeyError(f"dependencia inexistente: {dep}")
                    if self._would_cycle(task.id, dep):
                        raise ValueError(
                            f"dependencia crearía ciclo: {task.id} -> {dep}"
                        )
                applied["depends_on"] = deps
            if "recurrence" in changes:
                rec = changes["recurrence"]
                if rec is not None and rec not in VALID_RECURRENCES:
                    raise ValueError(
                        f"recurrence inválida: {rec!r}. Válidas: {', '.join(VALID_RECURRENCES)}"
                    )
                applied["recurrence"] = rec
            if "description" in changes:
                applied["description"] = str(changes["description"] or "")
            if "due_date" in changes:
                applied["due_date"] = changes["due_date"]

            for key, value in applied.items():
                setattr(task, key, value)
            task.updated_at = _now_iso()
            self._record(task.id, "update", applied)
            self.save()
            return task

    def set_status(self, task_id: int, status: str) -> Task:
        with self._lock:
            if status not in VALID_STATUSES:
                raise ValueError(
                    f"status inválida: {status!r}. Válidas: {', '.join(VALID_STATUSES)}"
                )
            task = self._require(task_id)
            self._push_undo()
            old = task.status
            task.status = status
            task.updated_at = _now_iso()
            if status == "done":
                task.completed_at = _now_iso()
            self._record(task.id, "set_status", {"status": f"{old}->{status}"})
            self.save()
            return task

    def complete_task(self, task_id: int) -> Task:
        with self._lock:
            task = self._require(task_id)
            unmet = self._unmet_dependencies(task)
            if unmet:
                raise ValueError(
                    f"no se puede completar {task.id}: dependencias no completadas: {unmet}"
                )
            self._push_undo()
            task.status = "done"
            task.completed_at = _now_iso()
            task.updated_at = _now_iso()
            self._record(task.id, "complete", {"status": "done"})
            if task.recurrence is not None:
                self._spawn_recurrence(task)
            self.save()
            return task

    def _spawn_recurrence(self, task: Task) -> Task:
        base = task.due_date or _now_iso()
        try:
            new_due = next_occurrence(base, task.recurrence)
        except ValueError:
            new_due = None
        new_task = Task(
            id=self._next_id,
            title=task.title,
            description=task.description,
            priority=task.priority,
            status="todo",
            tags=list(task.tags),
            depends_on=[],
            recurrence=task.recurrence,
            due_date=new_due,
        )
        self._next_id += 1
        self._tasks[new_task.id] = new_task
        self._record(new_task.id, "recurrence", {"from": task.id, "due_date": new_due})
        return new_task

    def reopen_task(self, task_id: int) -> Task:
        with self._lock:
            task = self._require(task_id)
            self._push_undo()
            task.status = "todo"
            task.completed_at = None
            task.updated_at = _now_iso()
            self._record(task.id, "reopen", {"status": "todo"})
            self.save()
            return task

    def cancel_task(self, task_id: int) -> Task:
        with self._lock:
            task = self._require(task_id)
            self._push_undo()
            task.status = "cancelled"
            task.updated_at = _now_iso()
            self._record(task.id, "cancel", {"status": "cancelled"})
            self.save()
            return task

    def delete_task(self, task_id: int) -> bool:
        with self._lock:
            task = self._require(task_id)
            self._push_undo()
            del self._tasks[task.id]
            for other in self._tasks.values():
                if task.id in other.depends_on:
                    other.depends_on = [d for d in other.depends_on if d != task.id]
            self._record(task.id, "delete", {"deleted": True})
            self.save()
            return True

    def add_dependency(self, task_id: int, depends_on_id: int) -> Task:
        with self._lock:
            task = self._require(task_id)
            self._require(depends_on_id)
            if depends_on_id in task.depends_on:
                return task
            if self._would_cycle(task.id, depends_on_id):
                raise ValueError(
                    f"dependencia crearía ciclo: {task.id} -> {depends_on_id}"
                )
            self._push_undo()
            task.depends_on.append(depends_on_id)
            task.updated_at = _now_iso()
            self._record(task.id, "add_dependency", {"depends_on": depends_on_id})
            self.save()
            return task

    def blocked_by(self, task_id: int) -> list[int]:
        with self._lock:
            task = self._require(task_id)
            return self._unmet_dependencies(task)

    def ready_tasks(self) -> list[Task]:
        with self._lock:
            return [
                task
                for task in self.sorted_tasks()
                if task.status == "todo" and not self._unmet_dependencies(task)
            ]

    def history(self, task_id: int) -> list[dict[str, Any]]:
        with self._lock:
            self._require(task_id)
            return list(self._history.get(task_id, []))

    def undo(self) -> bool:
        with self._lock:
            if not self._undo_stack:
                return False
            snapshot = self._undo_stack.pop()
            self._tasks = snapshot["tasks"]
            self._next_id = snapshot["next_id"]
            self.save()
            return True

    def summary(self) -> dict[str, Any]:
        with self._lock:
            by_status = {s: 0 for s in VALID_STATUSES}
            by_priority = {p: 0 for p in VALID_PRIORITIES}
            overdue = 0
            blocked = 0
            ready = 0
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            for task in self._tasks.values():
                by_status[task.status] = by_status.get(task.status, 0) + 1
                by_priority[task.priority] = by_priority.get(task.priority, 0) + 1
                if task.status not in ("done", "cancelled"):
                    if task.due_date:
                        try:
                            if _parse_iso(task.due_date) < now:
                                overdue += 1
                        except ValueError:
                            pass
                    unmet = self._unmet_dependencies(task)
                    if unmet:
                        blocked += 1
                    elif task.status == "todo":
                        ready += 1
            return {
                "total": len(self._tasks),
                "by_status": by_status,
                "by_priority": by_priority,
                "overdue": overdue,
                "blocked": blocked,
                "ready": ready,
            }

    def export_markdown(self, path: str) -> str:
        with self._lock:
            text = markdown_report(self.sorted_tasks(), self.summary())
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
            return text

    def export_csv(self, path: str) -> str:
        with self._lock:
            fields = [
                "id",
                "title",
                "description",
                "priority",
                "status",
                "tags",
                "depends_on",
                "recurrence",
                "created_at",
                "updated_at",
                "due_date",
                "completed_at",
            ]
            with open(path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for task in self.sorted_tasks():
                    row = task.to_dict()
                    row["tags"] = ";".join(row["tags"])
                    row["depends_on"] = ";".join(str(d) for d in row["depends_on"])
                    writer.writerow(row)
            return path
