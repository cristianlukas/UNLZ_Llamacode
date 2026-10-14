"""Punto de entrada: menu interactivo o self-test no interactivo."""

from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timedelta

from .models import Task
from .query import apply_query, parse_query
from .scheduler import next_occurrence
from .service import TaskService
from .storage import JsonTaskStorage


def _self_test() -> int:
    try:
        directory = tempfile.mkdtemp(prefix="taskflow_selftest_")
        storage = JsonTaskStorage(f"{directory}/tasks.json")
        service = TaskService(storage)

        a = service.create_task("API", tags=["Backend", "backend"], priority="high")
        b = service.create_task("Docs", depends_on=[a.id], recurrence="monthly",
                                due_date=(datetime.now() - timedelta(days=1)).date().isoformat())
        assert a.tags == ["backend"], a.tags
        assert service.blocked_by(b.id) == [a.id]
        assert service.ready_tasks() == [a]

        try:
            service.complete_task(b.id)
            raise AssertionError("complete no deberia permitir dependencias abiertas")
        except ValueError:
            pass

        # clave invalida ignorada: ambos siguen en todo
        assert apply_query(service.list_tasks(), parse_query("status:todo bogus:x")) == [a, b]
        assert service.summary()["overdue"] >= 1

        service.complete_task(a.id)
        assert a.status == "done" and a.completed_at
        service.complete_task(b.id)  # b tiene recurrence: genera ocurrencia
        occurrences = [t for t in service.list_tasks() if t.id not in (a.id, b.id)]
        assert len(occurrences) == 1 and occurrences[0].status == "todo"
        assert occurrences[0].due_date == next_occurrence(b.due_date, "monthly")
        assert next_occurrence("2026-01-31", "monthly") == "2026-02-28"

        service.undo()  # deshace la creacion de la ocurrencia
        assert len(service.list_tasks()) == 2

        reloaded = TaskService(JsonTaskStorage(storage.path))
        assert [t.id for t in reloaded.list_tasks()] == [a.id, b.id]
        assert reloaded.create_task("Next").id == b.id + 1

        service.export_markdown(f"{directory}/report.md")
        service.export_csv(f"{directory}/report.csv")
        print("SELF_TEST_OK")
        return 0
    except Exception as exc:
        print(f"SELF_TEST_FAIL: {type(exc).__name__}: {exc}")
        return 1


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--self-test" in argv:
        return _self_test()

    from .cli import run

    path = argv[0] if argv else "tasks.json"
    service = TaskService(JsonTaskStorage(path))
    try:
        run(service)
    except KeyboardInterrupt:
        print("\nAdios.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
