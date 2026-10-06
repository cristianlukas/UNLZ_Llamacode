#!/usr/bin/env python3
"""Independent fixed acceptance checks for TaskFlow ULTRA benchmark runs."""
from __future__ import annotations
import csv, importlib.util, io, json, os, sys, tempfile, threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

GROUPS = {}

def check(name):
    def deco(fn):
        GROUPS[name] = fn
        return fn
    return deco

def require(condition, message):
    if not condition:
        raise AssertionError(message)

def modules(root):
    source = Path(root) / 'solution_taskflow_fixed_gold.py'
    spec = importlib.util.spec_from_file_location('solution_taskflow_fixed_gold', source)
    require(spec is not None and spec.loader is not None, 'solution file missing')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return (module, module, module, module, module, module)

@check('model_validation')
def model_validation(root):
    models, *_ = modules(root)
    t = models.Task(id=7, title=' example ', tags=['Backend','backend',' UI '], depends_on=[2,2])
    require(t.tags == ['backend','ui'], f'tags normalization: {t.tags!r}')
    require(t.depends_on == [2], f'dependency normalization: {t.depends_on!r}')
    for kw in ({'priority':'critical'}, {'status':'waiting'}, {'recurrence':'yearly'}):
        try: models.Task(id=8, title='x', **kw)
        except ValueError: pass
        else: raise AssertionError(f'invalid field accepted: {kw}')

@check('serialization')
def serialization(root):
    models, *_ = modules(root)
    original = models.Task(id=19, title='deadline', priority='urgent', tags=['Ops'],
                           depends_on=[4], recurrence='weekly',
                           created_at='2026-02-03T04:05:06+00:00',
                           updated_at='2026-02-04T04:05:06+00:00',
                           due_date='2026-03-01T09:30:00+00:00')
    restored = models.Task.from_dict(original.to_dict())
    require(restored.to_dict() == original.to_dict(), 'to_dict/from_dict are not symmetric')

@check('service_basics')
def service_basics(root):
    _, service, *_ = modules(root)
    s = service.TaskService()
    a = s.create_task('API migration', description='public api', priority='high', tags=['Backend'])
    b = s.create_task('UI polish', priority='low')
    require(a.id < b.id and s.get_task(a.id).title == 'API migration', 'IDs/get_task')
    require([x.id for x in s.list_tasks(priority='high', tag='backend', search='API')] == [a.id], 'combined list filters')
    try: s.create_task(' ')
    except ValueError: pass
    else: raise AssertionError('empty title accepted')
    try: s.get_task(987654)
    except KeyError: pass
    else: raise AssertionError('unknown id did not raise KeyError')

@check('dependency_graph')
def dependency_graph(root):
    _, service, *_ = modules(root)
    s = service.TaskService(); a=s.create_task('A'); b=s.create_task('B', depends_on=[a.id])
    require(s.blocked_by(b.id) == [a.id], 'blocked_by did not report open dependency')
    require([x.id for x in s.ready_tasks()] == [a.id], 'ready_tasks before dependency completion')
    try: s.add_dependency(a.id,b.id)
    except ValueError: pass
    else: raise AssertionError('cycle accepted')
    try: s.create_task('missing dep', depends_on=[98765])
    except KeyError: pass
    else: raise AssertionError('missing dependency accepted')

@check('completion_gate')
def completion_gate(root):
    _, service, *_ = modules(root)
    s=service.TaskService(); a=s.create_task('prerequisite'); b=s.create_task('dependent',depends_on=[a.id])
    try: s.complete_task(b.id)
    except ValueError: pass
    else: raise AssertionError('dependent completed before prerequisite')
    s.complete_task(a.id); s.complete_task(b.id)
    require(s.get_task(b.id).status=='done' and s.get_task(b.id).completed_at, 'completion state/timestamp')

@check('recurrence')
def recurrence(root):
    _, service, _, scheduler, *_ = modules(root)
    require(scheduler.next_occurrence('2024-01-31','monthly')[:10]=='2024-02-29', 'leap month clamp')
    require(scheduler.next_occurrence('2023-01-31','monthly')[:10]=='2023-02-28', 'non-leap month clamp')
    s=service.TaskService(); t=s.create_task('monthly', due_date='2024-01-31', recurrence='monthly')
    s.complete_task(t.id)
    tasks=s.list_tasks()
    nexts=[x for x in tasks if x.id != t.id]
    require(len(nexts)==1 and nexts[0].status=='todo' and nexts[0].due_date[:10]=='2024-02-29', 'completion did not create clamped next occurrence')

@check('undo_mutation')
def undo_mutation(root):
    _, service, *_ = modules(root)
    s=service.TaskService(); t=s.create_task('before'); s.update_task(t.id,title='after')
    require(s.undo() is True and s.get_task(t.id).title=='before', 'undo did not revert final update')

@check('undo_completion')
def undo_completion(root):
    _, service, *_ = modules(root)
    s=service.TaskService(); t=s.create_task('undo completed task'); s.complete_task(t.id)
    require(s.get_task(t.id).status=='done', 'precondition: completion failed')
    require(s.undo() is True, 'undo returned false after complete_task')
    restored=s.get_task(t.id)
    require(restored.status=='todo' and restored.completed_at is None, 'undo did not restore completion fields')

@check('storage_roundtrip')
def storage_roundtrip(root):
    models, _, storage, *_ = modules(root)
    with tempfile.TemporaryDirectory() as td:
        path=Path(td)/'tasks.json'; original=[models.Task(id=10,title='persist',tags=['A'],due_date='2026-08-01')]
        store=storage.JsonTaskStorage(str(path)); store.save(original); loaded=store.load()
        require(len(loaded)==1 and loaded[0].id==10 and loaded[0].tags==['a'], 'roundtrip lost data')
        require(not list(Path(td).glob('*.tmp')) and not list(Path(td).glob('.taskflow_*.tmp')), 'atomic-save temp file left behind')

@check('storage_tolerance')
def storage_tolerance(root):
    _, _, storage, *_ = modules(root)
    with tempfile.TemporaryDirectory() as td:
        path=Path(td)/'bad.json'; store=storage.JsonTaskStorage(str(path))
        require(store.load()==[], 'missing file must load as empty')
        path.write_text('{broken',encoding='utf-8'); require(store.load()==[], 'corrupt json must load as empty')
        path.write_text('[{"id":1,"title":"ok"},{"id":2}]',encoding='utf-8')
        loaded=store.load(); require(len(loaded)==1 and loaded[0].id==1, 'malformed row should not poison valid rows')

@check('concurrency')
def concurrency(root):
    _, service, *_ = modules(root)
    s=service.TaskService()
    with ThreadPoolExecutor(max_workers=16) as pool:
        items=list(pool.map(lambda i:s.create_task(f'task-{i}'),range(40)))
    ids=[t.id for t in items]
    require(len(set(ids))==40 and sorted(ids)==list(range(1,41)), 'concurrent IDs duplicated or skipped')

@check('query_filters')
def query_filters(root):
    _, service, _, _, query, _ = modules(root)
    s=service.TaskService()
    expected=s.create_task('API backend',description='deploy api',priority='urgent',tags=['Backend'])
    s.create_task('API docs',priority='low',tags=['docs']); s.create_task('backend deploy',priority='urgent',tags=['backend'])
    parsed=query.parse_query('status:todo priority:urgent tag:backend search:api invalid:value')
    got=query.apply_query(s.list_tasks(),parsed)
    require([x.id for x in got]==[expected.id], f'combined query result mismatch: {[x.id for x in got]}')

@check('exports')
def exports(root):
    _, service, *_ = modules(root)
    with tempfile.TemporaryDirectory() as td:
        s=service.TaskService(); t=s.create_task('Export row',priority='high',tags=['ops'])
        md=Path(td)/'report.md'; csvp=Path(td)/'report.csv'
        s.export_markdown(str(md)); s.export_csv(str(csvp))
        m=md.read_text(encoding='utf-8'); rows=list(csv.DictReader(io.StringIO(csvp.read_text(encoding='utf-8'))))
        require('Export row' in m and 'By Status' in m, 'markdown report content missing')
        require(len(rows)==1 and 'Export row' in rows[0].values(), 'CSV row missing')

def main():
    if len(sys.argv)!=3 or sys.argv[2] not in GROUPS:
        print('USAGE: fixed_grader.py WORKSPACE TEST_ID',file=sys.stderr); return 2
    name=sys.argv[2]
    try:
        GROUPS[name](Path(sys.argv[1]).resolve())
    except Exception as e:
        print(f'FAIL: {name}: {type(e).__name__}: {e}',file=sys.stderr); return 1
    print(f'PASS: {name}'); return 0
if __name__=='__main__': raise SystemExit(main())
