"""Tests de taskflow_ultra (unittest, sin dependencias externas)."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from datetime import datetime, timedelta

from taskflow_ultra.models import Task
from taskflow_ultra.query import apply_query, parse_query
from taskflow_ultra.reports import markdown_report
from taskflow_ultra.scheduler import next_occurrence
from taskflow_ultra.service import TaskService
from taskflow_ultra.storage import JsonTaskStorage


def past_date() -> str:
    return (datetime.now() - timedelta(days=2)).date().isoformat()


class BaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="taskflow_test_")
        self.path = os.path.join(self.tmpdir, "tasks.json")
        self.service = TaskService(JsonTaskStorage(self.path))

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except OSError:
            pass
        try:
            os.rmdir(self.tmpdir)
        except OSError:
            pass


class TestModel(BaseTest):
    def test_create_task_basic(self) -> None:
        task = self.service.create_task("Alpha")
        self.assertEqual(task.id, 1)
        self.assertEqual(task.status, "todo")
        self.assertEqual(task.priority, "medium")
        self.assertTrue(task.created_at)

    def test_tags_normalized_case_insensitive_dedup(self) -> None:
        task = self.service.create_task("Beta", tags=["Backend", "backend", " QA ", "qa"])
        self.assertEqual(task.tags, ["backend", "qa"])

    def test_depends_on_normalized_no_duplicates(self) -> None:
        a = self.service.create_task("A")
        b = self.service.create_task("B", depends_on=[a.id, str(a.id), a.id])
        self.assertEqual(b.depends_on, [a.id])

    def test_invalid_priority_and_recurrence_raise(self) -> None:
        with self.assertRaises(ValueError):
            self.service.create_task("X", priority="critical")
        with self.assertRaises(ValueError):
            self.service.create_task("X", recurrence="yearly")

    def test_empty_title_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.service.create_task("   ")

    def test_to_dict_from_dict_symmetric(self) -> None:
        task = self.service.create_task("Gamma", tags=["x"], depends_on=[], recurrence="daily")
        data = task.to_dict()
        clone = Task.from_dict(data)
        self.assertEqual(clone.to_dict(), data)
        with self.assertRaises(ValueError):
            Task.from_dict({"id": "abc", "title": "ok"})
        with self.assertRaises(ValueError):
            Task.from_dict("no es dict")

    def test_get_task_missing_raises_keyerror(self) -> None:
        with self.assertRaises(KeyError):
            self.service.get_task(999)


class TestDependencies(BaseTest):
    def test_cycle_detection(self) -> None:
        a = self.service.create_task("A")
        b = self.service.create_task("B", depends_on=[a.id])
        with self.assertRaises(ValueError):
            self.service.add_dependency(a.id, b.id)
        with self.assertRaises(ValueError):
            self.service.add_dependency(b.id, b.id)

    def test_dependency_missing_raises_keyerror(self) -> None:
        a = self.service.create_task("A")
        with self.assertRaises(KeyError):
            self.service.add_dependency(a.id, 42)

    def test_complete_blocked_by_dependencies(self) -> None:
        a = self.service.create_task("A")
        b = self.service.create_task("B", depends_on=[a.id])
        with self.assertRaises(ValueError):
            self.service.complete_task(b.id)
        self.service.complete_task(a.id)
        self.service.complete_task(b.id)
        self.assertEqual(b.status, "done")
        self.assertTrue(b.completed_at)
        self.assertEqual(self.blocked_or_empty(b), [])

    def blocked_or_empty(self, task: Task) -> list[int]:
        return self.service.blocked_by(task.id)

    def test_ready_and_blocked(self) -> None:
        a = self.service.create_task("A")
        b = self.service.create_task("B", depends_on=[a.id])
        self.assertEqual(self.service.ready_tasks(), [a])
        self.assertEqual(self.service.blocked_by(b.id), [a.id])
        self.service.complete_task(a.id)
        self.assertEqual(self.service.ready_tasks(), [b])
        self.assertEqual(self.service.blocked_by(b.id), [])

    def test_reopen_and_cancel(self) -> None:
        task = self.service.create_task("R")
        self.service.complete_task(task.id)
        self.service.reopen_task(task.id)
        self.assertEqual(task.status, "todo")
        self.assertIsNone(task.completed_at)
        self.service.cancel_task(task.id)
        self.assertEqual(task.status, "cancelled")
        self.assertIsNone(task.completed_at)

    def test_update_task_and_history(self) -> None:
        task = self.service.create_task("H")
        self.service.update_task(task.id, priority="urgent", description="nota")
        self.assertEqual(task.priority, "urgent")
        entries = self.service.history(task.id)
        self.assertGreaterEqual(len(entries), 2)
        self.assertTrue(all("timestamp" in e and "action" in e for e in entries))

    def test_delete_task_removes_references(self) -> None:
        a = self.service.create_task("A")
        b = self.service.create_task("B", depends_on=[a.id])
        self.service.delete_task(a.id)
        self.assertEqual(b.depends_on, [])
        with self.assertRaises(KeyError):
            self.service.delete_task(a.id)


class TestRecurrence(BaseTest):
    def test_recurrence_creates_next_occurrence(self) -> None:
        task = self.service.create_task("Daily", recurrence="daily", due_date="2026-01-05")
        self.service.complete_task(task.id)
        occurrences = [t for t in self.service.list_tasks() if t.id != task.id]
        self.assertEqual(len(occurrences), 1)
        nxt = occurrences[0]
        self.assertEqual(nxt.status, "todo")
        self.assertEqual(nxt.due_date, "2026-01-06")
        self.assertGreater(nxt.id, task.id)

    def test_next_occurrence_month_end_clamp(self) -> None:
        self.assertEqual(next_occurrence("2026-01-31", "monthly"), "2026-02-28")
        self.assertEqual(next_occurrence("2024-01-31", "monthly"), "2024-02-29")
        self.assertEqual(next_occurrence("2026-01-01", "weekly"), "2026-01-08")
        self.assertEqual(next_occurrence("2026-12-31", "monthly"), "2027-01-31")
        with self.assertRaises(ValueError):
            next_occurrence("2026-01-01", "biweekly")


class TestUndo(BaseTest):
    def test_undo_reverts_last_mutation(self) -> None:
        task = self.service.create_task("U")
        self.service.complete_task(task.id)
        self.assertEqual(self.service.get_task(task.id).status, "done")
        self.assertTrue(self.service.undo())
        self.assertEqual(self.service.get_task(task.id).status, "todo")
        self.assertTrue(self.service.undo())  # undo de la creacion
        self.assertEqual(self.service.list_tasks(), [])
        self.assertFalse(self.service.undo())

    def test_undo_returns_false_when_empty(self) -> None:
        self.assertFalse(self.service.undo())


class TestQuery(BaseTest):
    def test_parse_query_and_invalid_keys_ignored(self) -> None:
        parsed = parse_query("status:todo priority:high tag:backend search:api bogus:x")
        self.assertEqual(parsed, {"status": "todo", "priority": "high", "tag": "backend", "search": "api"})
        self.assertEqual(parse_query("sin claves"), {})

    def test_apply_query_combined_filters(self) -> None:
        self.service.create_task("Api gateway", tags=["backend"], priority="high")
        self.service.create_task("Docs", tags=["docs"], priority="low")
        done = self.service.create_task("Api done", tags=["backend"])
        self.service.complete_task(done.id)
        hits = apply_query(self.service.list_tasks(), "status:todo tag:backend search:api")
        self.assertEqual([t.title for t in hits], ["Api gateway"])
        self.assertEqual(apply_query(self.service.list_tasks(), "status:done"), [done])
        # combinacion valida: todo + low -> solo Docs
        self.assertEqual([t.title for t in apply_query(self.service.list_tasks(), "status:todo priority:low")], ["Docs"])
        # combinacion imposible: todo + high + tag docs -> vacio
        self.assertEqual(apply_query(self.service.list_tasks(), "status:todo priority:high tag:docs"), [])


class TestSummary(BaseTest):
    def test_summary_fields_and_overdue(self) -> None:
        overdue = self.service.create_task("Late", due_date=past_date())
        self.service.create_task("Done", due_date=past_date())
        self.service.complete_task(2)
        summary = self.service.summary()
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["overdue"], 1)
        self.assertEqual(summary["by_status"]["done"], 1)
        self.assertEqual(summary["by_status"]["todo"], 1)
        self.assertIn("ready", summary)
        self.assertIn("blocked", summary)


class TestStorage(BaseTest):
    def test_persistence_roundtrip_and_ids_preserved(self) -> None:
        a = self.service.create_task("P1")
        b = self.service.create_task("P2", tags=["x"])
        self.service.set_status(b.id, "doing")
        reloaded = TaskService(JsonTaskStorage(self.path))
        self.assertEqual([t.id for t in reloaded.list_tasks()], [a.id, b.id])
        self.assertEqual(reloaded.get_task(b.id).status, "doing")
        self.assertEqual(reloaded.create_task("P3").id, 3)

    def test_load_missing_file_returns_empty(self) -> None:
        missing = os.path.join(self.tmpdir, "no-existe.json")
        self.assertEqual(JsonTaskStorage(missing).load(), [])

    def test_corrupt_json_returns_empty(self) -> None:
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("{ esto no es json ]")
        self.assertEqual(JsonTaskStorage(self.path).load(), [])

    def test_malformed_entries_are_skipped(self) -> None:
        payload = [
            {"id": 1, "title": "ok"},
            {"id": "xx", "title": "bad id"},
            {"id": 3, "title": ""},
            "no es dict",
            {"id": 4, "title": "ok2", "status": "invalido"},
        ]
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        tasks = JsonTaskStorage(self.path).load()
        self.assertEqual([t.id for t in tasks], [1])

    def test_atomic_save_uses_temp_file(self) -> None:
        self.service.create_task("Atomic")
        leftovers = [f for f in os.listdir(self.tmpdir) if f.endswith(".tmp")]
        self.assertEqual(leftovers, [])
        self.assertTrue(os.path.exists(self.path))

    def test_concurrent_save_load(self) -> None:
        storage = JsonTaskStorage(self.path)
        tasks = [Task(id=1, title="T")]
        storage.save(tasks)
        errors: list[Exception] = []

        def worker() -> None:
            try:
                for _ in range(20):
                    storage.save(tasks)
                    storage.load()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual([t.id for t in storage.load()], [1])


class TestConcurrency(BaseTest):
    def test_concurrent_create_no_duplicate_ids(self) -> None:
        errors: list[Exception] = []

        def worker() -> None:
            try:
                for i in range(20):
                    self.service.create_task(f"H{i}")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        ids = [t.id for t in self.service.list_tasks()]
        self.assertEqual(len(ids), 200)
        self.assertEqual(len(set(ids)), 200)

    def test_ids_increase_after_reload(self) -> None:
        self.service.create_task("A")
        self.service.create_task("B")
        reloaded = TaskService(JsonTaskStorage(self.path))
        new = reloaded.create_task("C")
        self.assertEqual(new.id, 3)
        self.assertEqual([t.id for t in reloaded.list_tasks()], [1, 2, 3])


class TestExports(BaseTest):
    def test_export_markdown(self) -> None:
        self.service.create_task("M1", tags=["backend"], priority="high")
        blocked = self.service.create_task("M2", depends_on=[1])
        path = os.path.join(self.tmpdir, "report.md")
        report = self.service.export_markdown(path)
        self.assertTrue(os.path.exists(path))
        self.assertIn("# Taskflow Ultra Report", report)
        self.assertIn("## Conteos por estado", report)
        self.assertIn("## Bloqueadas", report)
        self.assertIn("| ID | Title |", report)
        self.assertIn("M2", report)
        self.assertIn("## Tareas", report)
        self.assertTrue(blocked.depends_on)

    def test_export_csv(self) -> None:
        self.service.create_task("C1", tags=["a", "b"])
        path = os.path.join(self.tmpdir, "report.csv")
        self.service.export_csv(path)
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        self.assertTrue(content.startswith("id,title,description,priority,status,tags"))
        self.assertIn("C1", content)
        rows = [line for line in content.splitlines() if line]
        self.assertEqual(len(rows), 2)


if __name__ == "__main__":
    unittest.main()
