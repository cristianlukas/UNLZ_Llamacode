"""Entry point: menú interactivo o --self-test."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from .cli import run_cli
from .service import TaskService
from .storage import JsonTaskStorage


def _self_test() -> int:
    try:
        with tempfile.TemporaryDirectory() as tmp:
            storage = JsonTaskStorage(Path(tmp) / "tasks.json")
            service = TaskService(storage)

            a = service.create_task("Diseñar API", "spec", "high", ["Backend", "backend"])
            b = service.create_task("Implementar API", "api impl", "medium", ["backend"],
                                    depends_on=[a.id])
            assert a.tags == ["backend"], a.tags

            # bloqueo por dependencia
            try:
                service.complete_task(b.id)
                return 1
            except ValueError:
                pass

            service.complete_task(a.id)
            service.complete_task(b.id)
            assert service.get_task(b.id).status == "done"
            assert service.get_task(b.id).completed_at

            # recurrencia
            c = service.create_task("Daily standup", "", "medium", ["team"],
                                    due_date="2026-01-31", recurrence="monthly")
            service.complete_task(c.id)
            nxt = service.get_task(c.id + 1)
            assert nxt.title == "Daily standup" and nxt.status == "todo"
            assert nxt.due_date == "2026-02-28", nxt.due_date

            # ciclos
            d = service.create_task("Tarea D")
            e = service.create_task("Tarea E")
            service.add_dependency(d.id, e.id)
            try:
                service.add_dependency(e.id, d.id)
                return 1
            except ValueError:
                pass

            # undo
            before = service.get_task(d.id).status
            assert service.undo() is True
            assert service.get_task(d.id).status == before

            # ready / blocked
            f = service.create_task("Bloqueada", "", "low", [], depends_on=[e.id])
            assert service.blocked_by(f.id) == [e.id]
            assert f.id not in [t.id for t in service.ready_tasks()]

            # persistencia + ids crecientes
            common = TaskService(JsonTaskStorage(Path(tmp) / "tasks.json"))
            assert common.get_task(a.id).title == "Diseñar API"
            g = common.create_task("Nueva")
            assert g.id > max(t.id for t in common.sorted_tasks() if t.id != g.id)

            # JSON corrupto
            (Path(tmp) / "bad.json").write_text("{no es json", encoding="utf-8")
            assert JsonTaskStorage(Path(tmp) / "bad.json").load() == []

            # export
            service.export_markdown(Path(tmp) / "report.md")
            service.export_csv(Path(tmp) / "tasks.csv")
            assert (Path(tmp) / "report.md").read_text(encoding="utf-8").startswith("# TaskFlow")
            assert "id,title" in (Path(tmp) / "tasks.csv").read_text(encoding="utf-8")

            summary = service.summary()
            for key in ("total", "by_status", "by_priority", "overdue", "blocked", "ready"):
                assert key in summary
    except Exception as exc:  # noqa: BLE001 - self-test debe reportar
        print(f"SELF_TEST_FAIL: {exc}", file=sys.stderr)
        return 1
    print("SELF_TEST_OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--self-test" in argv:
        return _self_test()
    storage_path = argv[0] if argv else "taskflow_data.json"
    service = TaskService(JsonTaskStorage(storage_path))
    try:
        run_cli(service)
    except KeyboardInterrupt:
        print("\nSalida cancelada.")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
