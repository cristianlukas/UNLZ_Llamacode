"""Tests del proyecto taskflow_ultra (unittest, sin dependencias externas)."""
from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest

from taskflow_ultra.models import Task
from taskflow_ultra.query import apply_query, parse_query
from taskflow_ultra.reports import markdown_report
from taskflow_ultra.scheduler import next_occurrence
from taskflow_ultra.service import TaskService
from taskflow_ultra.storage import JsonTaskStorage


class TempDirTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.path = os.path.join(self.tmp, "tasks.json")

    def tearDown(self) -> None:
        self._tmp.cleanup()


class TestModels(unittest.TestCase):
    def test_tag_normalization_dedup_case_insensitive(self) -> None:
        task = Task(id=1, title="T", tags=["Backend", "backend", " API ", ""])
        self.assertEqual(task.tags, ["backend", "api"])

    def test_depends_on_dedup_and_int(self) -> None:
        task = Task(id=1, title="T", depends_on=[2, "2", 3])
        self.assertEqual(task.depends_on, [2, 3])

    def test_invalid_priority_status_recurrence_raise(self) -> None:
        with self.assertRaises(ValueError):
            Task(id=1, title="T", priority="critical")
        with self.assertRaises(ValueError):
            Task(id=1, title="T", status="x")
        with self.assertRaises(ValueError):
            Task(id=1, title="T", recurrence="yearly")

    def test_empty_title_raises(self) -> None:
        with self.assertRaises(ValueError):
            Task(id=1, title="   ")

    def test_to_dict_from_dict_symmetric(self) -> None:
        task = Task(
            id=7, title="T", description="d", priority="urgent", status="doing",
            tags=["a", "B"], depends_on=[1, 2], recurrence="weekly",
            due_date="2026-03-01T09:00:00+00:00",
        )
        restored = Task.from_dict(task.to_dict())
        self.assertEqual(restored.to_dict(), task.to_dict())


class TestScheduler(unittest.TestCase):
    def test_daily_weekly(self) -> None:
        self.assertEqual(next_occurrence("2026-01-31T10:00:00", "daily"), "2026-02-01T10:00:00")
        self.assertEqual(next_occurrence("2026-02-25T10:00:00", "weekly"), "2026-03-04T10:00:00")

    def test_monthly_end_of_month_clamp(self) -> None:
        self.assertEqual(next_occurrence("2026-01-31T10:00:00", "monthly"), "2026-02-28T10:00:00")
        self.assertEqual(next_occurrence("2024-01-31T10:00:00", "monthly"), "2024-02-29T10:00:00")
        self.assertEqual(next_occurrence("2026-12-15T00:00:00", "monthly"),
                         "2027-01-15T00:00:00")

    def test_invalid_recurrence_returns_none(self) -> None:
        self.assertIsNone(next_occurrence("2026-01-01T00:00:00", None))
        self.assertIsNone(next_occurrence("2026-01-01T00:00:00", "yearly"))


class TestService(TempDirTestCase):
    def test_create_and_get_and_keyerror(self) -> None:
        service = TaskService()
        task = service.create_task("Alpha", description="desc")
        self.assertEqual(task.id, 1)
        self.assertEqual(service.get_task(1).title, "Alpha")
        with self.assertRaises(KeyError):
            service.get_task(999)

    def test_empty_title_valueerror(self) -> None:
        service = TaskService()
        with self.assertRaises(ValueError):
            service.create_task("   ")

    def test_dependency_cycle_detection(self) -> None:
        service = TaskService()
        a = service.create_task("A")
        b = service.create_task("B", depends_on=[a.id])
        with self.assertRaises(ValueError):
            service.add_dependency(a.id, b.id)
        with self.assertRaises(ValueError):
            service.add_dependency(b.id, b.id)  # auto-dependencia = ciclo

    def test_dependency_missing_id_keyerror(self) -> None:
        service = TaskService()
        service.create_task("A")
        with self.assertRaises(KeyError):
            service.add_dependency(1, 42)

    def test_complete_blocked_by_dependencies(self) -> None:
        service = TaskService()
        a = service.create_task("A")
        b = service.create_task("B", depends_on=[a.id])
        with self.assertRaises(ValueError):
            service.complete_task(b.id)
        service.complete_task(a.id)
        done = service.complete_task(b.id)
        self.assertEqual(done.status, "done")
        self.assertIsNotNone(done.completed_at)

    def test_recurrence_creates_next_occurrence(self) -> None:
        service = TaskService()
        task = service.create_task("Daily standup", recurrence="daily",
                                   due_date="2026-05-01T09:00:00+00:00")
        service.complete_task(task.id)
        pending = [t for t in service.list_tasks(status="todo") if t.recurrence == "daily"]
        self.assertEqual(len(pending), 1)
        self.assertGreater(pending[0].id, task.id)
        self.assertEqual(pending[0].due_date, "2026-05-02T09:00:00+00:00")

    def test_reopen_cancel(self) -> None:
        service = TaskService()
        task = service.create_task("X")
        service.complete_task(task.id)
        reopened = service.reopen_task(task.id)
        self.assertEqual(reopened.status, "todo")
        self.assertIsNone(reopened.completed_at)
        cancelled = service.cancel_task(task.id)
        self.assertEqual(cancelled.status, "cancelled")

    def test_ready_and_blocked_by(self) -> None:
        service = TaskService()
        a = service.create_task("A")
        b = service.create_task("B", depends_on=[a.id])
        service.create_task("C")
        self.assertEqual([t.id for t in service.ready_tasks()], [a.id, 3])
        self.assertEqual(service.blocked_by(b.id), [a.id])
        service.complete_task(a.id)
        self.assertEqual(service.blocked_by(b.id), [])
        self.assertIn(b.id, [t.id for t in service.ready_tasks()])

    def test_history_records_mutations(self) -> None:
        service = TaskService()
        task = service.create_task("H")
        service.update_task(task.id, priority="high")
        service.cancel_task(task.id)
        entries = service.history(task.id)
        self.assertEqual([e["action"] for e in entries], ["create", "update", "update"])
        self.assertIn("timestamp", entries[0])

    def test_undo_restores_state(self) -> None:
        service = TaskService()
        service.create_task("A")
        service.create_task("B")
        self.assertTrue(service.undo())
        self.assertEqual(service.summary()["total"], 1)
        self.assertTrue(service.undo())
        self.assertEqual(service.summary()["total"], 0)
        self.assertFalse(service.undo())

    def test_summary_counts(self) -> None:
        service = TaskService()
        service.create_task("A", priority="high")
        service.create_task("B", due_date="2000-01-01T00:00:00+00:00")
        service.create_task("C", depends_on=[1])
        service.set_status(3, "blocked")
        summary = service.summary()
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["by_status"]["blocked"], 1)
        self.assertEqual(summary["by_priority"]["high"], 1)
        self.assertEqual(summary["overdue"], 1)
        self.assertEqual(summary["blocked"], 1)
        self.assertEqual(summary["ready"], 2)

    def test_filters_combinable_and_search(self) -> None:
        service = TaskService()
        service.create_task("API gateway", tags=["Backend"], priority="high",
                            description="connects services")
        service.create_task("UI polish", tags=["frontend"], priority="low")
        hits = service.list_tasks(tag="backend", search="connects")
        self.assertEqual([t.title for t in hits], ["API gateway"])
        hits = service.list_tasks(search="API")  # case-insensitive en title
        self.assertEqual(len(hits), 1)
        hits = service.list_tasks(status="done")
        self.assertEqual(hits, [])

    def test_delete_task_removes_refs(self) -> None:
        service = TaskService()
        a = service.create_task("A")
        b = service.create_task("B", depends_on=[a.id])
        self.assertTrue(service.delete_task(a.id))
        self.assertEqual(service.get_task(b.id).depends_on, [])
        with self.assertRaises(KeyError):
            service.get_task(a.id)

    def test_concurrent_create_unique_ids(self) -> None:
        service = TaskService()
        ids: list[int] = []
        lock = threading.Lock()

        def worker() -> None:
            task = service.create_task("concurrent")
            with lock:
                ids.append(task.id)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(ids), 10)
        self.assertEqual(len(set(ids)), 10)
        self.assertEqual(service.summary()["total"], 10)


class TestQuery(unittest.TestCase):
    def test_parse_query_valid_and_invalid_keys_ignored(self) -> None:
        filters = parse_query("status:todo priority:high tag:backend search:api bogus:1 status:bad")
        self.assertEqual(filters, {"status": "todo", "priority": "high",
                                   "tag": "backend", "search": "api"})

    def test_apply_query_filters(self) -> None:
        tasks = [
            Task(id=1, title="fix api bug", tags=["backend"], priority="high"),
            Task(id=2, title="docs", tags=["frontend"], priority="low", status="doing"),
        ]
        result = apply_query(tasks, "status:todo tag:backend search:api")
        self.assertEqual([t.id for t in result], [1])
        result = apply_query(tasks, "nonsense:xyz")  # no rompe
        self.assertEqual([t.id for t in result], [1, 2])


class TestStorage(TempDirTestCase):
    def test_missing_file_returns_empty(self) -> None:
        self.assertEqual(JsonTaskStorage(self.path).load(), [])

    def test_corrupt_json_returns_empty(self) -> None:
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("{not json at all")
        self.assertEqual(JsonTaskStorage(self.path).load(), [])

    def test_malformed_entries_skipped(self) -> None:
        payload = [
            {"id": 1, "title": "ok"},
            {"id": "not-an-int", "title": "bad id"},
            {"title": "no id"},
            "not-a-dict",
            {"id": 2, "title": "also ok"},
        ]
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        tasks = JsonTaskStorage(self.path).load()
        self.assertEqual([t.id for t in tasks], [1, 2])

    def test_save_load_roundtrip_and_atomic(self) -> None:
        storage = JsonTaskStorage(self.path)
        tasks = [Task(id=5, title="Persisted", tags=["a"])]
        storage.save(tasks)
        loaded = JsonTaskStorage(self.path).load()
        self.assertEqual(loaded[0].to_dict(), tasks[0].to_dict())
        self.assertEqual(
            [f for f in os.listdir(self.tmp) if f.startswith(".taskflow-")],
            [],
        )  # sin temporales huérfanos tras replace
        self.assertTrue(os.path.exists(self.path))

    def test_ids_preserved_and_grow_after_reload(self) -> None:
        service = TaskService(JsonTaskStorage(self.path))
        a = service.create_task("A")
        service.create_task("B")
        reloaded = TaskService(JsonTaskStorage(self.path))
        self.assertEqual([t.id for t in reloaded.list_tasks()], [a.id, 2])
        c = reloaded.create_task("C")
        self.assertEqual(c.id, 3)

    def test_concurrent_save_load_no_crash(self) -> None:
        storage = JsonTaskStorage(self.path)
        errors: list[Exception] = []

        def saver() -> None:
            try:
                for _ in range(20):
                    storage.save([Task(id=1, title="concurrent")])
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        def loader() -> None:
            try:
                for _ in range(20):
                    storage.load()
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=saver) for _ in range(3)]
        threads += [threading.Thread(target=loader) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])


class TestReports(TempDirTestCase):
    def test_markdown_report_sections(self) -> None:
        service = TaskService()
        a = service.create_task("A", tags=["x"])
        b = service.create_task("B", depends_on=[a.id])
        service.set_status(b.id, "blocked")
        report = markdown_report(service.list_tasks(), service.summary())
        self.assertIn("# TaskFlow Ultra Report", report)
        self.assertIn("## Counts by status", report)
        self.assertIn("## Counts by priority", report)
        self.assertIn("## Blocked tasks", report)
        self.assertIn("#2 B", report)
        self.assertIn("| ID | Title | Status |", report)
        self.assertIn("| 1 | A |", report)

    def test_export_markdown_and_csv_files(self) -> None:
        service = TaskService()
        service.create_task("Export me", tags=["t1", "t2"], due_date="2026-01-01T00:00:00+00:00")
        md_path = os.path.join(self.tmp, "report.md")
        csv_path = os.path.join(self.tmp, "report.csv")
        service.export_markdown(md_path)
        service.export_csv(csv_path)
        with open(md_path, encoding="utf-8") as handle:
            self.assertIn("Export me", handle.read())
        with open(csv_path, encoding="utf-8") as handle:
            content = handle.read()
        self.assertIn("id,title", content)
        self.assertIn("Export me", content)
        self.assertIn("t1;t2", content)


if __name__ == "__main__":
    unittest.main()
