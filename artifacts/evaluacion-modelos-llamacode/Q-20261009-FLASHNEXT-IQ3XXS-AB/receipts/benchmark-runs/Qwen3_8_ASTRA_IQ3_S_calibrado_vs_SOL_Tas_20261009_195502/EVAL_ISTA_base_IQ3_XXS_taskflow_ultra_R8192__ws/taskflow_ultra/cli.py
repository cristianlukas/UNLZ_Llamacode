"""CLI interactiva para TaskFlow Ultra."""
from __future__ import annotations

import shlex
from typing import Optional

from .models import Task
from .query import apply_query, parse_query
from .service import TaskService


def _read_int(prompt: str) -> Optional[int]:
    raw = input(prompt).strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        print("  -> número inválido")
        return None


def _read_list(prompt: str) -> list[str]:
    raw = input(prompt).strip()
    if not raw:
        return []
    try:
        return shlex.split(raw)
    except ValueError:
        return [part for part in raw.replace(",", " ").split() if part]


def _print_task(task: Task) -> None:
    deps = ", ".join(str(d) for d in task.depends_on) or "-"
    tags = ", ".join(task.tags) or "-"
    print(
        f"  #{task.id} [{task.status}] ({task.priority}) {task.title} "
        f"tags={tags} deps={deps} due={task.due_date or '-'}"
    )


def run_cli(service: TaskService) -> None:
    print("TaskFlow Ultra — gestor de tareas")
    while True:
        print(
            "\nOpciones: 1=crear 2=listar 3=ver 4=update 5=status 6=completar "
            "7=reabrir 8=cancelar 9=borrar 10=dependencia 11=blocked 12=ready "
            "13=historial 14=undo 15=summary 16=query 17=export_md 18=export_csv 0=salir"
        )
        try:
            choice = input("> ").strip()
        except EOFError:
            break
        if choice in ("0", "q", "salir"):
            break
        try:
            if choice == "1":
                title = input("título: ")
                description = input("descripción: ")
                priority = input("priority (low/medium/high/urgent): ") or "medium"
                tags = _read_list("tags (espacio/coma): ")
                due = input("due_date YYYY-MM-DD: ").strip() or None
                recurrence = input("recurrence (daily/weekly/monthly): ").strip() or None
                deps = [int(x) for x in _read_list("depends_on ids: ") if x.isdigit()]
                task = service.create_task(
                    title=title,
                    description=description,
                    priority=priority,
                    tags=tags,
                    due_date=due,
                    depends_on=deps,
                    recurrence=recurrence,
                )
                _print_task(task)
            elif choice == "2":
                status = input("status filtro: ").strip() or None
                priority = input("priority filtro: ").strip() or None
                tag = input("tag filtro: ").strip() or None
                search = input("search: ").strip() or None
                tasks = service.list_tasks(
                    status=status, priority=priority, tag=tag, search=search
                )
                if not tasks:
                    print("  (sin resultados)")
                for task in tasks:
                    _print_task(task)
            elif choice == "3":
                task_id = _read_int("id: ")
                if task_id is not None:
                    _print_task(service.get_task(task_id))
            elif choice == "4":
                task_id = _read_int("id: ")
                if task_id is not None:
                    changes: dict = {}
                    title = input("nuevo título: ").strip()
                    if title:
                        changes["title"] = title
                    priority = input("priority: ").strip()
                    if priority:
                        changes["priority"] = priority
                    status = input("status: ").strip()
                    if status:
                        changes["status"] = status
                    _print_task(service.update_task(task_id, **changes))
            elif choice == "5":
                task_id = _read_int("id: ")
                status = input("status: ").strip()
                if task_id is not None:
                    _print_task(service.set_status(task_id, status))
            elif choice == "6":
                task_id = _read_int("id: ")
                if task_id is not None:
                    _print_task(service.complete_task(task_id))
            elif choice == "7":
                task_id = _read_int("id: ")
                if task_id is not None:
                    _print_task(service.reopen_task(task_id))
            elif choice == "8":
                task_id = _read_int("id: ")
                if task_id is not None:
                    _print_task(service.cancel_task(task_id))
            elif choice == "9":
                task_id = _read_int("id: ")
                if task_id is not None:
                    service.delete_task(task_id)
                    print("  eliminada")
            elif choice == "10":
                task_id = _read_int("id: ")
                dep_id = _read_int("depends_on_id: ")
                if task_id is not None and dep_id is not None:
                    _print_task(service.add_dependency(task_id, dep_id))
            elif choice == "11":
                task_id = _read_int("id: ")
                if task_id is not None:
                    print(f"  blocked_by: {service.blocked_by(task_id)}")
            elif choice == "12":
                for task in service.ready_tasks():
                    _print_task(task)
            elif choice == "13":
                task_id = _read_int("id: ")
                if task_id is not None:
                    for entry in service.history(task_id):
                        print(f"  {entry['timestamp']} {entry['action']} {entry['changes']}")
            elif choice == "14":
                print(f"  undo: {service.undo()}")
            elif choice == "15":
                print(f"  summary: {service.summary()}")
            elif choice == "16":
                text = input("query (status:todo priority:high tag:backend search:api): ")
                parsed = parse_query(text)
                for task in apply_query(service.sorted_tasks(), parsed):
                    _print_task(task)
            elif choice == "17":
                path = input("ruta markdown: ").strip() or "report.md"
                service.export_markdown(path)
                print(f"  exportado a {path}")
            elif choice == "18":
                path = input("ruta csv: ").strip() or "tasks.csv"
                service.export_csv(path)
                print(f"  exportado a {path}")
            else:
                print("  opción desconocida")
        except (ValueError, KeyError) as exc:
            print(f"  error: {exc}")
