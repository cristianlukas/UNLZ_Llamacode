"""taskflow_ultra: gestor de tareas de nivel producción (modelo, storage, servicio, scheduler, query, reportes, CLI)."""
from __future__ import annotations

from .models import Task
from .query import apply_query, parse_query
from .reports import markdown_report
from .scheduler import next_occurrence
from .service import TaskService
from .storage import JsonTaskStorage

__version__ = "1.0.0"

__all__ = [
    "Task",
    "TaskService",
    "JsonTaskStorage",
    "parse_query",
    "apply_query",
    "next_occurrence",
    "markdown_report",
    "__version__",
]
