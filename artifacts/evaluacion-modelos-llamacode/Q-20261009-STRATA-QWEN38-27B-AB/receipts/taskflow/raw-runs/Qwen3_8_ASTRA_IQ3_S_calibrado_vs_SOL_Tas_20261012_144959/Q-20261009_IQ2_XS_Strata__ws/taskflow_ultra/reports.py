"""Reportes en Markdown."""

from __future__ import annotations

from typing import Any, Callable, Optional

from .models import Task


def markdown_report(
    tasks: list[Task],
    summary: dict[str, Any],
    blocked_by: Optional[Callable[[int], list[int]]] = None,
) -> str:
    """Markdown con titulo, conteos por estado/prioridad, bloqueadas y tabla."""
    lines: list[str] = ["# Taskflow Ultra Report", ""]
    lines.append(f"Total: {summary.get('total', len(tasks))}")
    lines.append("")

    lines.append("## Conteos por estado")
    lines.append("")
    for status, count in sorted((summary.get("by_status") or {}).items()):
        lines.append(f"- {status}: {count}")
    lines.append("")

    lines.append("## Conteos por prioridad")
    lines.append("")
    for priority, count in sorted((summary.get("by_priority") or {}).items()):
        lines.append(f"- {priority}: {count}")
    lines.append("")

    lines.append(f"Overdue: {summary.get('overdue', 0)}")
    lines.append(f"Ready: {summary.get('ready', 0)}")
    lines.append("")

    lines.append("## Bloqueadas")
    lines.append("")
    if blocked_by is not None:
        blocked = [task for task in tasks if blocked_by(task.id)]
    else:
        done_ids = {task.id for task in tasks if task.status == "done"}
        blocked = [task for task in tasks if any(d not in done_ids for d in task.depends_on)]
    if not blocked:
        lines.append("- (ninguna)")
    for task in blocked:
        deps = ", ".join(str(d) for d in task.depends_on) or "-"
        lines.append(f"- #{task.id} {task.title} (depende de: {deps})")
    lines.append("")

    lines.append("## Tareas")
    lines.append("")
    lines.append("| ID | Title | Priority | Status | Tags | Due | Completed |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for task in tasks:
        tags = ", ".join(task.tags) or "-"
        due = task.due_date or "-"
        completed = task.completed_at or "-"
        lines.append(
            f"| {task.id} | {task.title} | {task.priority} | {task.status} | {tags} | {due} | {completed} |"
        )
    return "\n".join(lines) + "\n"
