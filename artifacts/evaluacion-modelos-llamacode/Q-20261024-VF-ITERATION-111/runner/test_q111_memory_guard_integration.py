#!/usr/bin/env python3
"""Q111 CPU-only regression for actual Q97/Q100 guard integration."""
from __future__ import annotations
import ast, hashlib, importlib.util, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-111"
PREREG = TASK / "receipts/preregistration.json"
RESULT = TASK / "receipts/q111-integration-audit.json"
TOKEN = "b680a96eba14d849b2a46f80cffb89a2"
FILES = {
    "q97Launcher": ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-97/scripts/q97_supervised_bcb.py",
    "q100Launcher": ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-100/scripts/q100_supervised_fanout.py",
    "q108Core": ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-108/runner/q108_guard_core.py",
    "q110Wrapper": ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-110/runner/q110_warning_policy.py",
}
prereg = json.loads(PREREG.read_text(encoding="utf-8"))
lock = json.loads((ROOT / "WORK_QUEUE.lock").read_text(encoding="utf-8"))
if lock.get("task_id") != "Q-20261024-VF-ITERATION-111" or lock.get("token") != TOKEN:
    raise SystemExit("Q111 lock mismatch; refusing test")
actual_hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in FILES.items()}
if actual_hashes != prereg.get("sha256"):
    raise SystemExit("A preregistered launcher/core changed; refusing test")

def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module

q97 = load_module("q97_supervised_bcb_q111", FILES["q97Launcher"])
q108 = load_module("q108_guard_core_q111", FILES["q108Core"])
q110 = load_module("q110_warning_policy_q111", FILES["q110Wrapper"])
checks=[]
def check(name, fn):
    try:
        fn(); checks.append({"name":name,"passed":True})
    except Exception as exc:
        checks.append({"name":name,"passed":False,"error":f"{type(exc).__name__}: {exc}"})
def ok(value, msg):
    if not value: raise AssertionError(msg)
def psi(full=0.0,some=0.0): return {"some":some,"full":full}

def moderate_warning_starts_at_30():
    state={}
    for i in range(1,30):
        state,warn,stop=q97.pressure_gate_transition(psi(full=20.0),state)
        ok(not warn and stop is None,f"warning/stop too early at {i}")
    state,warn,stop=q97.pressure_gate_transition(psi(full=20.0),state)
    ok(warn and stop is None,"warning absent at sample 30")
check("Q97 actual launcher: moderate full PSI warns at sample 30",moderate_warning_starts_at_30)

def recovery_resets():
    state={}
    for _ in range(29): state,_,_=q97.pressure_gate_transition(psi(some=70.0),state)
    state,warn,stop=q97.pressure_gate_transition(psi(),state)
    ok(not warn and stop is None and all(v==0 for v in state.values()),"recovery did not reset all PSI streaks")
    state,warn,stop=q97.pressure_gate_transition(psi(some=70.0),state)
    ok(not warn and stop is None and state["warning_some70"]==1,"new episode did not start at one")
check("Q97 actual launcher: recovery resets consecutive PSI warnings",recovery_resets)

def severe_full_boundary():
    state={}
    for i in range(1,15):
        state,warn,stop=q97.pressure_gate_transition(psi(full=60.0),state)
        ok(stop is None,f"full severe stopped at {i}")
    state,_,stop=q97.pressure_gate_transition(psi(full=60.0),state)
    ok(stop is not None and "15 consecutive" in stop,"full severe did not stop at 15")
check("Q97 actual launcher: full PSI hard stop boundary is sample 15",severe_full_boundary)

def severe_some_boundary():
    state={}
    for i in range(1,15):
        state,warn,stop=q97.pressure_gate_transition(psi(some=80.0),state)
        ok(stop is None,f"some severe stopped at {i}")
    state,_,stop=q97.pressure_gate_transition(psi(some=80.0),state)
    ok(stop is not None and "15 consecutive" in stop,"some severe did not stop at 15")
check("Q97 actual launcher: some PSI hard stop boundary is sample 15",severe_some_boundary)

def q100_delegates_to_q97():
    path=FILES["q100Launcher"]
    tree=ast.parse(path.read_text(encoding="utf-8"))
    text=path.read_text(encoding="utf-8")
    ok('Q97_HELPER' in text and 'q97_supervised_bcb.py' in text,"Q100 no longer points at Q97 guard")
    ok('"q97_memory_supervision"' in text and 'guard = importlib.util.module_from_spec(spec)' in text,"Q100 no longer loads Q97 helper")
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="run_monitored")
    calls=[n for n in ast.walk(fn) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=="guard" and n.func.attr=="check_gates"]
    ok(bool(calls),"Q100 monitored loop does not delegate gates to Q97 helper")
check("Q100 active supervisor delegates monitored gate to Q97",q100_delegates_to_q97)

def candidate_boundary_is_distinct():
    sample={"memAvailableGiB":80.0,"memoryPsiAvg10Pct":psi(full=34.72,some=34.72),"oomKill":0}
    reason,_,raw_warning=q108.evaluate_sample(sample,0,0)
    ok(reason is None and raw_warning,"Q108 candidate one-sample behavior changed")
    state=0
    for i in range(1,30):
        reason,_,state,warn=q110.evaluate_policy(sample,0,0,state)
        ok(reason is None and not warn,f"Q110 candidate wrapper warned at {i}")
    reason,_,state,warn=q110.evaluate_policy(sample,0,0,state)
    ok(reason is None and state==30 and warn,"Q110 candidate wrapper did not warn at 30")
check("Q108/Q110 candidate warning distinction matches the audited code",candidate_boundary_is_distinct)

def historical_runs_completed_under_moderate_pressure():
    q97_result=json.loads((ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-97/receipts/q97-final-result.json").read_text())
    q97_guard=json.loads((ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-97/receipts/q97-memory-guard-review.json").read_text())
    q100_result=json.loads((ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-100/receipts/q100-final-result.json").read_text())
    astra=q97_result["results"]["astra"]
    sample97=q97_guard["currentRun"]
    guard100=q100_result["memoryGuard"]
    ok(astra["runs"]==8 and astra["transportOk"]==8,"Q97 ASTRA arm not fully transported")
    ok(20.0 < sample97["globalPsiFullAvg10PeakPct"] < 60.0 and sample97["warningSamples"]>0 and sample97["globalOomKillMax"]==0,"Q97 moderate-PSI evidence changed")
    ok(guard100["allSixRunsCompleted"] and not guard100["guardAborted"] and 20.0<guard100["peakGlobalPsiFullAvg10Pct"]<60.0 and guard100["globalOomKills"]==0,"Q100 moderate-PSI control failed")
check("Q97/Q100 actual runs completed through moderate PSI without OOM or guard abort",historical_runs_completed_under_moderate_pressure)

def prereg_hash_and_lock_stable():
    current=json.loads((ROOT/"WORK_QUEUE.lock").read_text())
    ok(current.get("task_id")=="Q-20261024-VF-ITERATION-111" and current.get("token")==TOKEN,"lock ownership changed mid-test")
    ok(actual_hashes==prereg["sha256"],"pre-registered helper fingerprints mismatch")
check("exclusive lock and preregistered code fingerprints remained valid",prereg_hash_and_lock_stable)

passed=sum(x["passed"] for x in checks)
result={"schemaVersion":1,"taskId":"Q-20261024-VF-ITERATION-111","experimentId":"Q111-A1","recordedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),"status":"pass" if passed==len(checks) else "fail","checksPassed":passed,"checksTotal":len(checks),"gpuUsed":False,"modelOrServerStarted":False,"buildRun":False,"downloadRun":False,"artificialMemoryGiB":0,"productionChanged":False,"sourceSha256":actual_hashes,"checks":checks}
RESULT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print(json.dumps(result,indent=2,ensure_ascii=False))
if passed != len(checks): raise SystemExit(1)
