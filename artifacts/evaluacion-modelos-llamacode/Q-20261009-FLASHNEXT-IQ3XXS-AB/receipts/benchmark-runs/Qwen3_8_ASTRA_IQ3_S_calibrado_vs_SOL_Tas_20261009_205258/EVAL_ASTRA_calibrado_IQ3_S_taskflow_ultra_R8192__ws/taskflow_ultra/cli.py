"""CLI interactiva: menú de tareas sobre TaskService."""
from __future__ import annotations

from typing import Callable

from .models import PRIORITIES, STATUSES
from .query import apply_query, parse_query
from .service import TaskService

MENU = """
TaskFlow Ultra menu
  1) create          2) list            3) get
  4) update          5) status          6) complete
  7) reopen          8) cancel          9) delete
 10) add-dep        11) blocked-by     12) ready
 13) history        14) query          15) summary
 16) undo           17) export-md      18) export-csv
 19) save           q) quit
"""


def _ask(input_fn: Callable[[str], str], prompt: str) -> str:
    return input_fn(prompt).strip()


def _ask_int(input_fn: Callable[[str], str], prompt: str) -> int | None:
    raw = _ask(input_fn, prompt)
    try:
        return int(raw)
    except ValueError:
        print(f"invalid integer: {raw!r}")
        return None


def _print_task(task: object) -> None:
    d = task.to_dict()  # type: ignore[attr-defined]
    print(
        f"#{d['id']} [{d['status']}/{d['priority']}] {d['title']}"
        + (f" tags={d['tags']}" if d["tags"] else "")
        + (f" deps={d['depends_on']}" if d["depends_on"] else "")
        + (f" due={d['due_date']}" if d["due_date"] else "")
        + (f" rec={d['recurrence']}" if d["recurrence"] else "")
    )


def run_interactive(service: TaskService, input_fn: Callable[[str], str] = input) -> None:
    print(MENU)
    while True:
        try:
            choice = _ask(input_fn, "> ").lower()
        except EOFError:
            print()
            break
        if choice in ("q", "quit", "exit"):
            break
        try:
            if choice == "1":
                title = _ask(input_fn, "title: ")
                description = _ask(input_fn, "description: ")
                priority = _ask(input_fn, "priority [medium]: ") or "medium"
                tags_raw = _ask(input_fn, "tags (comma): ")
                tags = [t for t in tags_raw.split(",") if t.strip()] if tags_raw else None
                due = _ask(input_fn, "due date ISO (blank=none): ") or None
                recurrence = _ask(input_fn, "recurrence daily/weekly/monthly (blank=none): ") or None
                _print_task(service.create_task(title, description, priority, tags, due, None, recurrence))
            elif choice == "2":
                status = _ask(input_fn, "status filter (blank=all): ") or None
                priority = _ask(input_fn, "priority filter (blank=all): ") or None
                tag = _ask(input_fn, "tag filter (blank=all): ") or None
                search = _ask(input_fn, "search (blank=all): ") or None
                tasks = service.list_tasks(status, priority, tag, search)
                if not tasks:
                    print("no tasks")
                for task in tasks:
                    _print_task(task)
            elif choice == "3":
                task_id = _ask_int(input_fn, "id: ")
                if task_id is not None:
                    _print_task(service.get_task(task_id))
            elif choice == "4":
                task_id = _ask_int(input_fn, "id: ")
                if task_id is not None:
                    changes: dict[str, object] = {}
                    title = _ask(input_fn, "new title (blank=keep): ")
                    if title:
                        changes["title"] = title
                    priority = _ask(input_fn, f"priority {PRIORITIES} (blank=keep): ")
                    if priority:
                        changes["priority"] = priority
                    due = _ask(input_fn, "due date ISO (blank=keep): ")
                    if due:
                        changes["due_date"] = due
                    if changes:
                        _print_task(service.update_task(task_id, **changes))
                    else:
                        print("nothing to update")
            elif choice == "5":
                task_id = _ask_int(input_fn, "id: ")
                status = _ask(input_fn, f"status {STATUSES}: ")
                if task_id is not None:
                    _print_task(service.set_status(task_id, status))
            elif choice == "6":
                task_id = _ask_int(input_fn, "id: ")
                if task_id is not None:
                    _print_task(service.complete_task(task_id))
            elif choice == "7":
                task_id = _ask_int(input_fn, "id: ")
                if task_id is not None:
                    _print_task(service.reopen_task(task_id))
            elif choice == "8":
                task_id = _ask_int(input_fn, "id: ")
                if task_id is not None:
                    _print_task(service.cancel_task(task_id))
            elif choice == "9":
                task_id = _ask_int(input_fn, "id: ")
                if task_id is not None:
                    print("deleted" if service.delete_task(task_id) else "not found")
            elif choice == "10":
                task_id = _ask_int(input_fn, "task id: ")
                dep_id = _ask_int(input_fn, "depends-on id: ")
                if task_id is not None and dep_id is not None:
                    _print_task(service.add_dependency(task_id, dep_id))
            elif choice == "11":
                task_id = _ask_int(input_fn, "id: ")
                if task_id is not None:
                    print("blocked by:", service.blocked_by(task_id))
            elif choice == "12":
                tasks = service.ready_tasks()
                if not tasks:
                    print("no ready tasks")
                for task in tasks:
                    _print_task(task)
            elif choice == "13":
                task_id = _ask_int(input_fn, "id: ")
                if task_id is not None:
                    for entry in service.history(task_id):
                        print(entry["timestamp"], entry["action"], entry["changes"])
            elif choice == "14":
                text = _ask(input_fn, "query (status:todo priority:high tag:x search:y): ")
                filters = parse_query(text)
                print("filters:", filters)
                for task in apply_query(service.list_tasks(), filters):
                    _print_task(task)
            elif choice == "15":
                print(service.summary())
            elif choice == "16":
                print("undone" if service.undo() else "nothing to undo")
            elif choice == "17":
                path = _ask(input_fn, "markdown path: ")
                if path:
                    print("exported:", service.export_markdown(path))
            elif choice == "18":
                path = _ask(input_fn, "csv path: ")
                if path:
                    print("exported:", service.export_csv(path))
            elif choice == "19":
                service.save()
                print("saved")
            elif choice:
                print("unknown option")
        except (ValueError, KeyError) as exc:
            print(f"error: {exc}")
        except KeyboardInterrupt:
            print("\ninterrupted; type q to quit")


def run_cli(argv: list[str] | None = None) -> int:
    """Punto de entrada no interactivo simple: taskflow-ultra <comando> [args]."""
    argv = list(argv or [])
    service = TaskService()
    if not argv:
        return 0
    command, *args = argv
    try:
        if command == "create":
            if not args:
                print("usage: create <title> [priority]")
                return 2
            priority = args[1] if len(args) > 1 else "medium"
            _print_task(service.create_task(args[0], priority=priority))
        elif command == "list":
            for task in service.list_tasks():
                _print_task(task)
        else:
            print(f"unknown command: {command}")
            return 2
    except (ValueError, KeyError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


__all__ = ["run_interactive", "run_cli", "MENU"]
