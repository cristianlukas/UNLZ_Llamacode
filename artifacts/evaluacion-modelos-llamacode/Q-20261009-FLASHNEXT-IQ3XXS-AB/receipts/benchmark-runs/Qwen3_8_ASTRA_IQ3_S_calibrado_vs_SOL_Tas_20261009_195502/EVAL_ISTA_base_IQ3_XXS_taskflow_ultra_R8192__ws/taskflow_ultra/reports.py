"""Reportes: Markdown a partir de tareas y summary."""
from __future__ import annotations

from typing import Any

from .models import Task, VALID_PRIORITIES, VALID_STATUSES


def _esc(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def markdown_report(tasks: list[Task], summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# TaskFlow Ultra Report")
    lines.append("")
    total = summary.get("total", len(tasks))
    lines.append(f"Total de tareas: **{total}**")
    lines.append("")

    lines.append("## Conteos por estado")
    lines.append("")
    lines.append("| Estado | Cantidad |")
    lines.append("| --- | ---: |")
    by_status = summary.get("by_status", {})
    for status in VALID_STATUSES:
        lines.append(f"| {status} | {by_status.get(status, 0)} |")
    lines.append("")

    lines.append("## Conteos por prioridad")
    lines.append("")
    lines.append("| Prioridad | Cantidad |")
    lines.append("| --- | ---: |")
    by_priority = summary.get("by_priority", {})
    for priority in VALID_PRIORITIES:
        lines.append(f"| {priority} | {by_priority.get(priority, 0)} |")
    lines.append("")

    lines.append("## Métricas")
    lines.append("")
    lines.append(f"- Overdue: {summary.get('overdue', 0)}")
    lines.append(f"- Blocked: {summary.get('blocked', 0)}")
    lines.append(f"- Ready: {summary.get('ready', 0)}")
    lines.append("")

    blocked = [t for t in tasks if t.status not in ("done", "cancelled") and t.depends_on]
    lines.append("## Tareas bloqueadas")
    lines.append("")
    if blocked:
        lines.append("| ID | Título | Deps pendientes |")
        lines.append("| --- | --- | --- |")
        for task in blocked:
            lines.append(
                f"| {task.id} | {_esc(task.title)} | {_esc(', '.join(str(d) for d in task.depends_on))} |"
            )
    else:
        lines.append("_Sin tareas bloqueadas._")
    lines.append("")

    lines.append("## Tareas")
    lines.append("")
    lines.append("| ID | Título | Estado | Prioridad | Tags | Due |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for task in tasks:
        lines.append(
            f"| {task.id} | {_esc(task.title)} | {task.status} | {task.priority} | "
            f"{_esc(', '.join(task.tags))} | {_esc(task.due_date)} |"
        )
    lines.append("")
    return "\n".join(lines)
