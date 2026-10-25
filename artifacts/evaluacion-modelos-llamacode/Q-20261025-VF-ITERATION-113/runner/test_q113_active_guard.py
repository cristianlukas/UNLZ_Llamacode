#!/usr/bin/env python3
"""CPU fixture replay against the actual Q97 guard functions; no GPU/model."""
from __future__ import annotations
import hashlib, importlib.util, inspect, json, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
TASK=ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-113"
TOKEN="6cc30fdfb03eb1a873be27b0bfec160b"
PREREG=TASK/"receipts/preregistration.json"
RESULT=TASK/"receipts/q113-active-guard-audit.json"
Q97=ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-97/scripts/q97_supervised_bcb.py"
Q100=ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-100/scripts/q100_supervised_fanout.py"
SOURCE_FILES={
    "q97":Q97,
    "q100":Q100,
    "q102Replay":ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-102/runner/q102_memory_guard.py",
    "q102ReplayTests":ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-102/runner/test_q102_memory_guard.py",
    "q108Candidate":ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-108/runner/q108_guard_core.py",
    "q110Candidate":ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-110/runner/q110_warning_policy.py",
    "q97Review":ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-97/receipts/q97-memory-guard-review.json",
    "q102Result":ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-102/receipts/q102-final-result.json",
}
pre=json.loads(PREREG.read_text())
lock=json.loads((ROOT/"WORK_QUEUE.lock").read_text())
if lock.get("task_id")!="Q-20261025-VF-ITERATION-113" or lock.get("token")!=TOKEN:
    raise SystemExit("Q113 lock mismatch")
hashes={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in SOURCE_FILES.items()}
if hashes!=pre["sourceSha256"]: raise SystemExit("preregistered source fingerprint mismatch")
spec=importlib.util.spec_from_file_location("q97_q113",Q97)
q97=importlib.util.module_from_spec(spec);spec.loader.exec_module(q97)
checks=[]
def check(name,fn):
    try: fn();checks.append({"name":name,"passed":True})
    except Exception as e: checks.append({"name":name,"passed":False,"error":f"{type(e).__name__}: {e}"})
def reset(): q97.record_sample.psi_counts={"warning_full20":0,"warning_some70":0,"severe_full60":0,"severe_some80":0}
def env(mem=100.0,some=0.0,full=0.0,global_oom=0,cg_oom=0,cg_oom_kill=0):
    q97.mem_available_gib=lambda:mem
    q97.psi_avg10=lambda:{"some":some,"full":full}
    q97.service_cgroup_memory_psi_avg10=lambda:{"some":0.0,"full":0.0}
    q97.oom_snapshot=lambda:{"global":{"oom_kill":global_oom},"cgroup":{"oom":cg_oom,"oom_kill":cg_oom_kill}}
    q97.gpu_snapshot=lambda:[{"index":0,"name":"fixture RTX 3090","uuid":"fixture0"},{"index":1,"name":"fixture RTX 3090","uuid":"fixture1"}]
def base():return {"global":{"oom_kill":0},"cgroup":{"oom":0,"oom_kill":0}}

def run_sample(mem=100.0,some=0.0,full=0.0,global_oom=0,cg_oom=0,cg_oom_kill=0,baseline=False):
    env(mem,some,full,global_oom,cg_oom,cg_oom_kill)
    return q97.check_gates("q113-fixture",base(),baseline=baseline)
def must_stop(reason,**kwargs):
    try:run_sample(**kwargs)
    except q97.GateStop as e:
        if reason not in str(e):raise AssertionError(f"wrong stop reason: {e}")
        return
    raise AssertionError(f"expected GateStop containing {reason!r}")

with tempfile.TemporaryDirectory(prefix="q113-guard-") as tmp:
    q97.SAMPLES=Path(tmp)/"samples.jsonl"
    def astra_high_rss_history():
        q102=json.loads((ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-102/receipts/q102-final-result.json").read_text())
        astra=q102["historicalControls"]["astraDefault1M"]
        assert "RSS tree max 51.14 GiB" in astra and "MemAvailable min 55.728 GiB" in astra
        assert "10/10" in astra and "OOM 0" in astra
        review=json.loads((ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-97/receipts/q97-memory-guard-review.json").read_text())
        q14=next(x for x in review["historicalEvidence"] if x["id"].startswith("Q14 ASTRA DEFAULT"))
        assert q14["processTreeRssGiB"]==51.14 and q14["minMemAvailableGiB"]==55.64 and q14["oomKill"]==0
        reset();row=run_sample(mem=55.728)
        assert row["memAvailableGiB"]==55.728 and not row["memoryPsiWarning"]
        assert "rss" not in inspect.getsource(q97.record_sample).lower()
        assert "rss" not in inspect.getsource(q97.check_gates).lower()
    check("actual Q97 guard continues at ASTRA 1M recorded MemAvailable despite 51.14 GiB RSS metadata",astra_high_rss_history)
    def moderate_q100_history():
        reset()
        for i in range(29):
            row=run_sample(mem=69.386,full=46.52)
            assert not row["memoryPsiWarning"]
        row=run_sample(mem=69.386,full=46.52)
        assert row["memoryPsiWarning"]
        assert q97.record_sample.psi_counts["severe_full60"]==0
    check("actual Q97 policy warns on sustained Q100 moderate PSI without stopping",moderate_q100_history)
    def available_boundary():
        reset();assert run_sample(mem=32.0)["memAvailableGiB"]==32.0
        must_stop("MemAvailable fell below 32 GiB",mem=31.99)
    check("actual Q97 hard stop is strict below 32 GiB, equality continues",available_boundary)
    def oom_boundaries():
        reset();must_stop("global oom_kill counter increased",global_oom=1)
        reset();must_stop("service cgroup memory.events oom counter increased",cg_oom=1)
        reset();must_stop("service cgroup memory.events oom_kill counter increased",cg_oom_kill=1)
    check("actual Q97 hard stop detects global and service-cgroup OOM counters",oom_boundaries)
    def severe_boundaries():
        reset()
        for _ in range(14):run_sample(mem=100,some=80,full=60)
        assert q97.record_sample.psi_counts["severe_full60"]==14
        must_stop("global memory PSI full avg10 >=60% for 15 consecutive",mem=100,some=80,full=60)
    check("actual Q97 severe PSI stops at sample 15, not 14",severe_boundaries)
    def recovery():
        reset()
        for _ in range(14):run_sample(mem=100,full=60)
        run_sample(mem=100)
        assert q97.record_sample.psi_counts["severe_full60"]==0
        for _ in range(14):run_sample(mem=100,some=80)
        must_stop("global memory PSI some avg10 >=80% for 15 consecutive",mem=100,some=80)
    check("actual Q97 recovery resets severe streak and some>=80% stops at 15",recovery)
    def historical_sol_limitation():
        final=json.loads((ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-102/receipts/q102-final-result.json").read_text())
        s=final["historicalControls"]["SOL_Q34"]
        assert "completed without OOM" in s and "PSI series unavailable" in s
    check("SOL TP=2 history is retained as no-OOM control, not a PSI series",historical_sol_limitation)

result={"taskId":"Q-20261025-VF-ITERATION-113","experimentId":"Q113-A1","status":"pass" if all(x["passed"] for x in checks) else "fail","checksPassed":sum(x["passed"] for x in checks),"checksTotal":len(checks),"checks":checks,"sourceSha256":hashes,"gpuUsed":False,"gpuSnapshotMocked":True,"modelOrServerStarted":False,"networkUsed":False,"buildRun":False,"artificialMemoryGiB":0,"largeMemoryAllocation":False,"productionChanged":False}
RESULT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
for item in checks:print(("PASS" if item["passed"] else "FAIL"),item["name"],item.get("error",""))
print(f"Q113 active Q97 guard audit: {result['checksPassed']}/{result['checksTotal']} PASS")
if not all(x["passed"] for x in checks):raise SystemExit(1)
