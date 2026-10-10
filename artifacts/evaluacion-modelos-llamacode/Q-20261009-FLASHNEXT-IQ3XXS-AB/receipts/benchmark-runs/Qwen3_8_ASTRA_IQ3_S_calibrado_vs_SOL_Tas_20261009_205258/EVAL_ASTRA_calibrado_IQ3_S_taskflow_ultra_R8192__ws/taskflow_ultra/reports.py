"""Reportes: Markdown con conteos por estado/prioridad, bloqueadas y tabla de tareas."""
from __future__ import annotations

from typing import Any

from .models import PRIORITIES, STATUSES, Task


def _escape(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def markdown_report(tasks: list[Task], summary: dict[str, Any] | None = None) -> str:
    summary = summary or {}
    by_status = summary.get("by_status") or {
        s: sum(1 for t in tasks if t.status == s) for s in STATUSES
    }
    by_priority = summary.get("by_priority") or {
        p: sum(1 for t in tasks if t.priority == p) for p in PRIORITIES
    }
    lines: list[str] = []
    lines.append("# TaskFlow Ultra Report")
    lines.append("")
    lines.append(f"Total tasks: {summary.get('total', len(tasks))}")
    lines.append("")
    lines.append("## Counts by status")
    lines.append("")
    for status in STATUSES:
        lines.append(f"- {status}: {by_status.get(status, 0)}")
    lines.append("")
    lines.append("## Counts by priority")
    lines.append("")
    for priority in PRIORITIES:
        lines.append(f"- {priority}: {by_priority.get(priority, 0)}")
    lines.append("")
    lines.append("## Blocked tasks")
    lines.append("")
    blocked = [t for t in tasks if t.status == "blocked"]
    if blocked:
        for task in blocked:
            deps = ", ".join(str(d) for d in task.depends_on) or "-"
            lines.append(f"- #{task.id} {task.title} (depends on: {deps})")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Tasks")
    lines.append("")
    lines.append("| ID | Title | Status | Priority | Tags | Depends on | Due date |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for task in tasks:
        lines.append(
            "| {id} | {title} | {status} | {priority} | {tags} | {deps} | {due} |".format(
                id=task.id,
                title=_escape(task.title),
                status=task.status,
                priority=task.priority,
                tags=_escape(", ".join(task.tags)),
                deps=", ".join(str(d) for d in task.depends_on) or "-",
                due=task.due_date or "-",
            )
        )
    lines.append("")
    return "\n".join(lines)
