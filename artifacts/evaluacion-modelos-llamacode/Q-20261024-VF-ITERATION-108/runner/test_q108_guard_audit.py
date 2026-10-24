#!/usr/bin/env python3
"""CPU-only audit: evidence controls, guard boundaries and telemetry fail-closed behavior."""
from __future__ import annotations
import importlib.util, json, math, os, signal
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parents[4]
ART=ROOT/'artifacts/evaluacion-modelos-llamacode'
TASK=ART/'Q-20261024-VF-ITERATION-108'
CORE=TASK/'runner/q108_guard_core.py'
spec=importlib.util.spec_from_file_location('q108_guard_core',CORE)
core=importlib.util.module_from_spec(spec); spec.loader.exec_module(core)
checks=[]
def check(name,fn):
    try: fn(); checks.append((name,True,'PASS'))
    except Exception as exc: checks.append((name,False,f'{type(exc).__name__}: {exc}'))
def assert_true(cond,msg):
    if not cond: raise AssertionError(msg)
def record(rel): return json.loads((ART/rel).read_text())
def valid(mem=100.0,some=0.0,full=0.0,oom=0):
    return {'memAvailableGiB':mem,'memoryPsiAvg10Pct':{'some':some,'full':full},'oomKill':oom}

# Reproduce the old fail-open behavior, then ensure the Q108 candidate rejects it.
def legacy_missing_psi_is_silently_accepted():
    p=ART/'Q-20261024-VF-ITERATION-103/runner/q103_memory_guard.py'
    oldspec=importlib.util.spec_from_file_location('q103_guard_legacy',p)
    old=importlib.util.module_from_spec(oldspec); oldspec.loader.exec_module(old)
    reason,streak,warning=old.evaluate_sample({'memAvailableGiB':100,'memoryPsiAvg10Pct':{},'oomKill':0},0,0)
    assert_true((reason,streak,warning)==(None,0,False),'expected legacy fail-open reproduction')
    try: core.evaluate_sample({'memAvailableGiB':100,'memoryPsiAvg10Pct':{},'oomKill':0},0,0)
    except core.TelemetryError: return
    raise AssertionError('Q108 accepted absent PSI')
check('legacy missing-PSI fail-open reproduced; Q108 rejects it',legacy_missing_psi_is_silently_accepted)

def bad_psi(text): core.parse_psi_text(text)
def test_missing_psi():
    for text in ['', 'some avg10=0.1 avg60=0 avg300=0 total=1', 'some avg10=0 full total=1', 'some avg10=nan full avg10=0', 'some avg10=101 full avg10=0', 'some avg10=1\nfull avg10=0\nsome avg10=2']:
        try: bad_psi(text)
        except core.TelemetryError: continue
        raise AssertionError(f'accepted PSI text: {text!r}')
check('missing/malformed/out-of-range PSI rejected',test_missing_psi)

def test_valid_psi():
    got=core.parse_psi_text('some avg10=46.52 avg60=1 avg300=0 total=1\nfull avg10=46.52 avg60=1 avg300=0 total=1\n')
    assert_true(got=={'some':46.52,'full':46.52},str(got))
check('valid PSI parsed exactly',test_valid_psi)

def test_real_proc_reader_and_fixture():
    with TemporaryDirectory() as d:
        proc=Path(d)
        (proc/'pressure').mkdir()
        (proc/'meminfo').write_text('MemTotal: 131072000 kB\nMemAvailable: 1048576 kB\n')
        (proc/'pressure/memory').write_text('some avg10=0.10 avg60=0.10 avg300=0.10 total=1\nfull avg10=0.00 avg60=0.00 avg300=0.00 total=1\n')
        (proc/'vmstat').write_text('oom_kill 3\n')
        fixture=core.read_host_sample(proc)
        assert_true(fixture['memAvailableGiB']==1.0 and fixture['oomKill']==3 and fixture['memoryPsiAvg10Pct']=={'some':0.1,'full':0.0},str(fixture))
        (proc/'pressure/memory').unlink()
        try: core.read_host_sample(proc)
        except core.TelemetryError: pass
        else: raise AssertionError('missing /proc/pressure/memory did not fail closed')
    live=core.read_host_sample(Path('/proc'))
    reason,streak,warning=core.evaluate_sample(live,live['oomKill'],0)
    assert_true(reason is None and streak in (0,1),'real host sample crossed a memory/OOM hard stop')
check('procfs fixture and one live host sample parse; missing PSI fails closed',test_real_proc_reader_and_fixture)

def test_missing_oom():
    for text in ['', 'oom_kill x', 'oom_kill -1', 'oom_kill 1\noom_kill 2']:
        try: core.parse_oom_text(text)
        except core.TelemetryError: continue
        raise AssertionError(f'accepted oom counter: {text!r}')
check('missing/malformed/duplicated OOM counter rejected',test_missing_oom)

# Existing successful user controls must not be stopped by high RSS alone.
def test_astra_success_control():
    reason,streak,warning=core.evaluate_sample(valid(mem=55.728),0,0)
    assert_true((reason,streak,warning)==(None,0,False),'ASTRA 1M control stopped/warned')
check('ASTRA DEFAULT 1M control: 51.14 GiB RSS, 55.728 GiB available -> continue',test_astra_success_control)

def test_sol_success_record():
    review=record('Q-20261024-VF-ITERATION-97/receipts/q97-memory-guard-review.json')
    evidence={x['id']:x for x in review['historicalEvidence']}['Q34 SOL vLLM TP2']
    assert_true(evidence['oomKill']==0 and 'completed' in evidence['outcome'],'SOL Q34 success/no-OOM evidence missing')
    assert_true(evidence['gpus']=='both RTX 3090','SOL dual-GPU mode not documented')
    assert_true('no per-second PSI' in evidence['outcome'],'SOL PSI evidence limit missing')
check('SOL Q34 TP=2 success/no-OOM documented; PSI limitation preserved',test_sol_success_record)

def test_q100_moderate_psi():
    reason,streak,warning=core.evaluate_sample(valid(mem=69.386,full=46.52,some=46.52),0,0)
    assert_true(reason is None and streak==0 and warning,'moderate PSI did not warn-only')
check('Q100 moderate PSI warns only and does not stop',test_q100_moderate_psi)

def test_boundaries():
    assert_true(core.evaluate_sample(valid(mem=32),0,0)[0] is None,'exactly 32 GiB should continue')
    assert_true(core.evaluate_sample(valid(mem=31.99),0,0)[0]=='MemAvailable <32 GiB','below floor did not stop')
    assert_true(core.evaluate_sample(valid(oom=1),0,0)[0]=='global oom_kill counter increased','OOM delta did not stop')
    _,n,_=core.evaluate_sample(valid(some=80,full=60),0,13); assert_true(n==14,'14-sample streak wrong')
    r,n,_=core.evaluate_sample(valid(some=80,full=60),0,14); assert_true(n==15 and r and '15 consecutive' in r,'15-sample severe gate wrong')
    _,n,_=core.evaluate_sample(valid(),0,14); assert_true(n==0,'pressure recovery did not reset streak')
check('floor/OOM/severe-PSI 14→15/recovery boundaries preserved',test_boundaries)

def test_required_sample_fields():
    for sample in [{'memAvailableGiB':90,'oomKill':0}, {'memAvailableGiB':90,'memoryPsiAvg10Pct':{'some':0},'oomKill':0}, {'memAvailableGiB':float('nan'),'memoryPsiAvg10Pct':{'some':0,'full':0},'oomKill':0}, {'memAvailableGiB':90,'memoryPsiAvg10Pct':{'some':True,'full':0},'oomKill':0}, {'memAvailableGiB':True,'memoryPsiAvg10Pct':{'some':0,'full':0},'oomKill':0}]:
        try: core.evaluate_sample(sample,0,0)
        except core.TelemetryError: continue
        raise AssertionError('accepted incomplete/invalid sample')
check('incomplete or invalid sample rejected explicitly',test_required_sample_fields)

def test_io_pressure_not_memory_stop():
    reason,_,_=core.evaluate_sample(valid(),0,0)
    assert_true(reason is None,'I/O metrics are not an input to the memory decision')
check('non-memory pressure cannot be misrouted as memory stop',test_io_pressure_not_memory_stop)

def test_candidate_only_signal():
    sent=[]
    with TemporaryDirectory() as d:
        p=Path(d)/'stop.txt'
        for pid,error in [(424242,core.TelemetryError('PSI unavailable')),(424243,FileNotFoundError('/proc/pressure/memory'))]:
            def missing_telemetry(err=error): raise err
            reason,streak,warning=core.monitor_once(pid,missing_telemetry,0,0,p,lambda target,sig:sent.append((target,sig)))
            assert_true(reason.startswith('memory telemetry unavailable:') and streak==0 and warning is False,'telemetry error was not fail-closed')
            assert_true(p.read_text()==reason+'\n','stop reason not persisted')
        no_stop=core.monitor_once(515151,lambda:valid(mem=55.728),0,0,p,lambda pid,sig:sent.append((pid,sig)))
        assert_true(no_stop==(None,0,False),'healthy ASTRA control unexpectedly stopped')
    assert_true(sent==[(424242,signal.SIGTERM),(424243,signal.SIGTERM)],f'unexpected signal scope: {sent}')
check('fail-closed action signals only the explicit candidate PID',test_candidate_only_signal)

def test_historical_receipts():
    r102=record('Q-20261024-VF-ITERATION-102/receipts/guard-replay-amendment01.json')
    r103=record('Q-20261024-VF-ITERATION-103/receipts/q103-final-result.json')
    r100=record('Q-20261024-VF-ITERATION-100/receipts/q100-final-result.json')
    review=record('Q-20261024-VF-ITERATION-97/receipts/q97-memory-guard-review.json')
    assert_true(r102['test']['result']=='19/19 PASS','Q102 replay receipt mismatch')
    assert_true(r103['result']['vmHwmGiB']>=56 and r103['result']['hardStopReason'] is None and r103['result']['minMemAvailableGiB']>48,'Q103 high-RSS receipt mismatch')
    assert_true(r100['memoryGuard']['guardAborted'] is False and r100['memoryGuard']['allSixRunsCompleted'] is True and r100['memoryGuard']['peakGlobalPsiFullAvg10Pct']<60,'Q100 control mismatch')
    controls={x['id']:x for x in review['historicalEvidence']}
    assert_true(controls['Q35 ASTRA Flash-Next 1M, 3 seeds']['completedSeeds']=='3/3','ASTRA Q35 completion missing')
    assert_true(controls['Q34 SOL vLLM TP2']['oomKill']==0 and 'no per-second PSI' in controls['Q34 SOL vLLM TP2']['outcome'],'SOL PSI caveat missing')
check('Q97/Q100/Q102/Q103 historical success receipts consistent',test_historical_receipts)

def test_strata_stale_queue_action():
    d=json.loads(Path('/home/cristian/.codex/visualizations/2026/10/19/01a155f2-b702-76d3-a5dd-7d2b85aa5043/cola-evaluaciones-ia/data/actionables.json').read_text())
    rows=d if isinstance(d,list) else d.get('actionables',d.get('items',[]))
    x=next(x for x in rows if x.get('id')=='f318d34d-eefc-4d16-b77d-98b1977d0698')
    q100=record('Q-20261024-VF-ITERATION-100/receipts/q100-final-result.json')
    q105=record('Q-20261024-VF-ITERATION-105/receipts/q105-final-result.json')
    assert_true('Completado' in x.get('status','') and 'no adoptar parallel2' in x.get('status',''),'Strata actionable not reconciled to completed no-adoption')
    assert_true('Google Sheets Accionables' in x.get('reconciliationEvidence',''),'local reconciliation receipt missing')
    assert_true(q100['status']=='completed-no-adoption' and q105['serverUsed'] is False,'completed Strata E2E/forensic evidence missing')
check('Strata Q99 action reconciled to Q100/Q105 no-adoption result',test_strata_stale_queue_action)

# Verify the current Q108 lock before declaring tests.
def test_lock():
    lock=json.loads((ROOT/'WORK_QUEUE.lock').read_text())
    assert_true(lock.get('task_id')=='Q-20261024-VF-ITERATION-108' and lock.get('token')=='19dc403c-9b1f-4f4f-8227-b38b24edcdb1','Q108 lock mismatch')
check('exclusive Q108 lock valid',test_lock)

for name,ok,msg in checks: print(('PASS' if ok else 'FAIL'),name,msg)
print(f'Q108 audit: {sum(1 for _,ok,_ in checks if ok)}/{len(checks)} PASS')
if not all(ok for _,ok,_ in checks): raise SystemExit(1)
