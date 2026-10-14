"""Menu interactivo del gestor de tareas."""

from __future__ import annotations

from typing import Optional

from .models import Task
from .query import apply_query, parse_query
from .service import TaskService

MENU = """
Taskflow Ultra
  1) crear tarea
  2) listar
  3) ver tarea
  4) actualizar (campo=valor)
  5) dependencias (add)
  6) bloqueada por
  7) completar
  8) reabrir
  9) cancelar
  10) borrar
  11) filtrar por query
  12) resumen
  13) historial
  14) undo
  15) exportar markdown
  16) exportar csv
  17) salir
"""


def _ask_int(prompt: str) -> Optional[int]:
    raw = input(prompt).strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        print("  valor invalido (se esperaba un numero)")
        return None


def _show(tasks: list[Task]) -> None:
    if not tasks:
        print("  (sin resultados)")
        return
    for task in tasks:
        print(f"  #{task.id} [{task.status}/{task.priority}] {task.title} tags={task.tags}")


def run(service: TaskService) -> None:
    print(MENU)
    while True:
        try:
            choice = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAdios.")
            return
        if not choice:
            continue
        try:
            if choice == "17":
                print("Adios.")
                return
            if choice == "1":
                title = input("  title: ").strip()
                if not title:
                    print("  title vacio")
                    continue
                description = input("  description: ")
                priority = input("  priority [low|medium|high|urgent]: ").strip() or "medium"
                tags = [t for t in input("  tags (coma): ").split(",") if t.strip()]
                recurrence = input("  recurrence [daily|weekly|monthly|none]: ").strip() or None
                task = service.create_task(
                    title=title,
                    description=description,
                    priority=priority,
                    tags=tags,
                    recurrence=recurrence,
                )
                print(f"  creada #{task.id}")
            elif choice == "2":
                _show(service.list_tasks())
            elif choice == "3":
                task_id = _ask_int("  id: ")
                if task_id is not None:
                    print(f"  {service.get_task(task_id).to_dict()}")
            elif choice == "4":
                task_id = _ask_int("  id: ")
                if task_id is None:
                    continue
                raw = input("  campo=valor: ").strip()
                if "=" not in raw:
                    print("  formato: campo=valor")
                    continue
                key, _, value = raw.partition("=")
                changes = {key.strip(): value.strip()}
                updated = service.update_task(task_id, **changes)
                print(f"  {updated.to_dict()}")
            elif choice == "5":
                task_id = _ask_int("  id: ")
                dep_id = _ask_int("  depende de: ")
                if task_id is not None and dep_id is not None:
                    service.add_dependency(task_id, dep_id)
                    print("  dependencia agregada")
            elif choice == "6":
                task_id = _ask_int("  id: ")
                if task_id is not None:
                    print(f"  bloqueada por: {service.blocked_by(task_id)}")
            elif choice == "7":
                task_id = _ask_int("  id: ")
                if task_id is not None:
                    print(f"  completada #{service.complete_task(task_id).id}")
            elif choice == "8":
                task_id = _ask_int("  id: ")
                if task_id is not None:
                    print(f"  reabierta #{service.reopen_task(task_id).id}")
            elif choice == "9":
                task_id = _ask_int("  id: ")
                if task_id is not None:
                    print(f"  cancelada #{service.cancel_task(task_id).id}")
            elif choice == "10":
                task_id = _ask_int("  id: ")
                if task_id is not None:
                    service.delete_task(task_id)
                    print("  borrada")
            elif choice == "11":
                text = input("  query (status:todo priority:high tag:x search:y): ").strip()
                _show(apply_query(service.list_tasks(), parse_query(text)))
            elif choice == "12":
                print(f"  {service.summary()}")
            elif choice == "13":
                task_id = _ask_int("  id: ")
                if task_id is not None:
                    for entry in service.history(task_id):
                        print(f"  {entry['timestamp']} {entry['action']} {entry['changes']}")
            elif choice == "14":
                print("  deshecho" if service.undo() else "  nada para deshacer")
            elif choice in ("15", "16"):
                path = input("  path de salida: ").strip()
                if not path:
                    print("  path vacio")
                    continue
                if choice == "15":
                    service.export_markdown(path)
                else:
                    service.export_csv(path)
                print(f"  exportado a {path}")
            else:
                print("  opcion desconocida")
        except (ValueError, KeyError) as exc:
            print(f"  error: {exc}")
        except KeyboardInterrupt:
            print("\nAdios.")
            return



