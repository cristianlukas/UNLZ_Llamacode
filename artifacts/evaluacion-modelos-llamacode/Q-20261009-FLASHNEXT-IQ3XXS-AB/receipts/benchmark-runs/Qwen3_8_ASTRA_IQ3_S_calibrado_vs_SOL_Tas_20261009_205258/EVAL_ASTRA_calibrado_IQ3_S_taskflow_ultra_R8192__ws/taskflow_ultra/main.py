"""Punto de entrada: menú interactivo o self-test no interactivo.

Uso:
    python -m taskflow_ultra.main              # menú interactivo
    python -m taskflow_ultra.main --self-test  # prueba funcional, imprime SELF_TEST_OK
"""
from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timedelta, timezone

from .cli import run_interactive
from .query import apply_query, parse_query
from .scheduler import next_occurrence
from .service import TaskService
from .storage import JsonTaskStorage


def _self_test() -> int:
    try:
        with tempfile.TemporaryDirectory() as tmp:
            storage = JsonTaskStorage(f"{tmp}/tasks.json")
            service = TaskService(storage)

            a = service.create_task("A", tags=["Backend", "backend"], priority="high")
            assert a.tags == ["backend"], a.tags
            b = service.create_task("B", depends_on=[a.id])
            due = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
            c = service.create_task("C", due_date=due)

            # dependencias y ciclos
            try:
                service.add_dependency(a.id, b.id)
                raise AssertionError("cycle not detected")
            except ValueError:
                pass
            try:
                service.complete_task(b.id)
                raise AssertionError("completed despite open dependency")
            except ValueError:
                pass
            assert service.blocked_by(b.id) == [a.id]
            assert [t.id for t in service.ready_tasks()] == [a.id, c.id]

            # completar con recurrencia genera siguiente ocurrencia
            r = service.create_task("R", recurrence="monthly", due_date="2026-01-31T10:00:00+00:00")
            service.complete_task(r.id)
            occurrences = [t for t in service.list_tasks(search="R") if t.recurrence == "monthly"]
            assert len(occurrences) == 2, occurrences
            nxt = next(occurrence for occurrence in occurrences if occurrence.status == "todo")
            assert nxt.due_date is not None and nxt.due_date.startswith("2026-02-28"), nxt.due_date

            # undo
            before_total = service.summary()["total"]
            assert service.undo() is True
            assert service.summary()["total"] == before_total - 1

            # query
            filters = parse_query("status:todo priority:high tag:backend search:a bogus:x")
            assert filters == {"status": "todo", "priority": "high", "tag": "backend", "search": "a"}
            assert all(t.status == "todo" for t in apply_query(service.list_tasks(), filters))

            # summary / overdue
            summary = service.summary()
            assert summary["total"] >= 1 and summary["overdue"] >= 1

            # persistencia y ids crecientes tras recargar
            service.save()
            reloaded = TaskService(JsonTaskStorage(f"{tmp}/tasks.json"))
            ids = sorted(t.id for t in reloaded.list_tasks())
            assert ids and len(ids) == len(set(ids))
            new = reloaded.create_task("post-reload")
            assert new.id == max(ids) + 1

            # exports
            md = service.export_markdown(f"{tmp}/report.md")
            csv_path = service.export_csv(f"{tmp}/report.csv")
            with open(md, encoding="utf-8") as handle:
                assert "# TaskFlow Ultra Report" in handle.read()
            with open(csv_path, encoding="utf-8") as handle:
                assert "id,title" in handle.readline()

        print("SELF_TEST_OK")
        return 0
    except Exception as exc:  # noqa: BLE001 - self-test debe reportar cualquier fallo
        print(f"SELF_TEST_FAIL: {exc}")
        return 1


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if "--self-test" in argv:
        return _self_test()
    storage_path = None
    if "--taskflow-ultra-data" in argv:
        idx = argv.index("--taskflow-ultra-data")
        if idx + 1 < len(argv):
            storage_path = argv[idx + 1]
    storage = JsonTaskStorage(storage_path) if storage_path else None
    service = TaskService(storage)
    try:
        run_interactive(service)
    except KeyboardInterrupt:
        print("\nbye")
    return 0


if __name__ == "__main__":
    sys.exit(main())
