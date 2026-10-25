#!/usr/bin/env python3
"""CPU fixture replay: high cgroup PSI is diagnostic, not an active Q97 gate."""
from __future__ import annotations
import hashlib, importlib.util, json, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
TASK=ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-114"
TOKEN="1d72ff558d30406c80c6dc7ce33e5a26"
PRE=TASK/"receipts/preregistration.json"
OUT=TASK/"receipts/q114-cgroup-psi-replay.json"
Q97=ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-97/scripts/q97_supervised_bcb.py"
Q100=ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-100/scripts/q100_supervised_fanout.py"
REVIEW=ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-97/receipts/q97-memory-guard-review.json"
pre=json.loads(PRE.read_text());lock=json.loads((ROOT/"WORK_QUEUE.lock").read_text())
if lock.get("task_id")!="Q-20261025-VF-ITERATION-114" or lock.get("token")!=TOKEN: raise SystemExit("Q114 lock mismatch")
files={"q97":Q97,"q100":Q100,"q97Review":REVIEW}
hashes={k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in files.items()}
if hashes!=pre["sourceSha256"]: raise SystemExit("Q114 source fingerprint mismatch")
spec=importlib.util.spec_from_file_location("q97_q114",Q97);q97=importlib.util.module_from_spec(spec);spec.loader.exec_module(q97)
checks=[]
def check(name,fn):
 try:fn();checks.append({"name":name,"passed":True})
 except Exception as e:checks.append({"name":name,"passed":False,"error":f"{type(e).__name__}: {e}"})
def reset():q97.record_sample.psi_counts={"warning_full20":0,"warning_some70":0,"severe_full60":0,"severe_some80":0}
def set_signals():
 q97.mem_available_gib=lambda:71.864
 q97.psi_avg10=lambda:{"some":34.72,"full":34.72}
 q97.service_cgroup_memory_psi_avg10=lambda:{"some":81.53,"full":81.53}
 q97.oom_snapshot=lambda:{"global":{"oom_kill":0},"cgroup":{"oom":0,"oom_kill":0}}
 q97.gpu_snapshot=lambda:[{"index":0,"name":"fixture RTX 3090"},{"index":1,"name":"fixture RTX 3090"}]
base={"global":{"oom_kill":0},"cgroup":{"oom":0,"oom_kill":0}}
with tempfile.TemporaryDirectory(prefix="q114-cgroup-psi-") as tmp:
 q97.SAMPLES=Path(tmp)/"samples.jsonl"
 def cgroup_high_is_diagnostic():
  reset();set_signals();q97.psi_avg10=lambda:{"some":0.0,"full":0.0}
  for i in range(30):
   row=q97.check_gates("q114-cgroup-only-pressure",base)
   assert not row["memoryPsiWarning"],f"warning at cgroup-only sample {i+1}"
   assert row["serviceCgroupMemoryPsiAvg10Pct"]=={"some":81.53,"full":81.53}
   assert row["memAvailableGiB"]==71.864
  assert q97.record_sample.psi_counts["severe_full60"]==0 and q97.record_sample.psi_counts["severe_some80"]==0
 check("81.53% cgroup PSI alone across 30 samples is diagnostic, not a warning/stop gate",cgroup_high_is_diagnostic)
 def global_warning_at_30_without_hard_stop():
  reset();set_signals()
  for i in range(29):
   row=q97.check_gates("q114-moderate-global",base)
   assert not row["memoryPsiWarning"] and q97.record_sample.psi_counts["severe_full60"]==0
  row=q97.check_gates("q114-moderate-global",base)
  assert row["memoryPsiWarning"] and q97.record_sample.psi_counts["severe_full60"]==0
  assert row["serviceCgroupMemoryPsiAvg10Pct"]["full"]==81.53
 check("moderate global PSI warns at sample 30 while cgroup PSI stays diagnostic and hard-stop remains clear",global_warning_at_30_without_hard_stop)
review=json.loads(REVIEW.read_text());hist=review["currentRun"]
assert hist["cgroupPsiFullAvg10PeakPct"]==81.53 and hist["globalPsiFullAvg10PeakPct"]==34.72
result={"taskId":"Q-20261025-VF-ITERATION-114","experimentId":"Q114-A1","status":"pass" if all(x["passed"] for x in checks) else "fail","checksPassed":sum(x["passed"] for x in checks),"checksTotal":len(checks),"checks":checks,"sourceSha256":hashes,"historicalQ97PeaksCrossChecked":True,"historicalPeaksAreNotAssumedSimultaneous":True,"gpuUsed":False,"gpuSnapshotMockedTwoRtx3090":True,"modelOrServerStarted":False,"networkUsed":False,"buildRun":False,"artificialMemoryGiB":0,"productionChanged":False}
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
for x in checks:print(("PASS" if x["passed"] else "FAIL"),x["name"],x.get("error",""))
print(f"Q114 cgroup PSI diagnostic replay: {result['checksPassed']}/{result['checksTotal']} PASS")
if result["status"]!="pass":raise SystemExit(1)
