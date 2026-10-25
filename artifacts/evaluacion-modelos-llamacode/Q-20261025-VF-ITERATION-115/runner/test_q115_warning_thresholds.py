#!/usr/bin/env python3
"""CPU fixtures for exact Q97 global moderate-PSI warning boundaries."""
from __future__ import annotations
import hashlib,importlib.util,json,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
TASK=ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-115"
TOKEN="cf7d4c4b389d4518b6e84503564bee05"
PRE=TASK/"receipts/preregistration.json"
OUT=TASK/"receipts/q115-warning-boundaries.json"
Q97=ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-97/scripts/q97_supervised_bcb.py"
Q100=ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-100/scripts/q100_supervised_fanout.py"
REVIEW=ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-97/receipts/q97-memory-guard-review.json"
pre=json.loads(PRE.read_text());lock=json.loads((ROOT/"WORK_QUEUE.lock").read_text())
if lock.get("task_id")!="Q-20261025-VF-ITERATION-115" or lock.get("token")!=TOKEN:raise SystemExit("Q115 lock mismatch")
files={"q97":Q97,"q100":Q100,"q97Review":REVIEW};hashes={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()}
if hashes!=pre["sourceSha256"]:raise SystemExit("Q115 source fingerprint mismatch")
spec=importlib.util.spec_from_file_location("q97_q115",Q97);q97=importlib.util.module_from_spec(spec);spec.loader.exec_module(q97)
checks=[]
def check(name,fn):
 try:fn();checks.append({"name":name,"passed":True})
 except Exception as e:checks.append({"name":name,"passed":False,"error":f"{type(e).__name__}: {e}"})
def reset():q97.record_sample.psi_counts={"warning_full20":0,"warning_some70":0,"severe_full60":0,"severe_some80":0}
def configure(some,full):
 q97.mem_available_gib=lambda:71.864
 q97.psi_avg10=lambda:{"some":some,"full":full}
 q97.service_cgroup_memory_psi_avg10=lambda:{"some":0.0,"full":0.0}
 q97.oom_snapshot=lambda:{"global":{"oom_kill":0},"cgroup":{"oom":0,"oom_kill":0}}
 q97.gpu_snapshot=lambda:[{"index":0,"name":"fixture RTX 3090"},{"index":1,"name":"fixture RTX 3090"}]
base={"global":{"oom_kill":0},"cgroup":{"oom":0,"oom_kill":0}}
def verify_boundary(some,full,expected):
 reset();configure(some,full)
 with tempfile.TemporaryDirectory(prefix="q115-warning-") as tmp:
  q97.SAMPLES=Path(tmp)/"samples.jsonl"
  for i in range(29):
   row=q97.check_gates("q115-warning-boundary",base)
   assert not row["memoryPsiWarning"],f"unexpected warning sample {i+1} at some={some}, full={full}"
  row=q97.check_gates("q115-warning-boundary",base)
  assert row["memoryPsiWarning"] is expected,f"expected warning={expected} at 30, got {row['memoryPsiWarning']} for some={some}, full={full}"
  assert q97.record_sample.psi_counts["severe_full60"]==0 and q97.record_sample.psi_counts["severe_some80"]==0
check("global PSI full exactly 20% warns at sample 30; 19.99% does not",lambda:(verify_boundary(0.0,20.0,True),verify_boundary(0.0,19.99,False)))
check("global PSI some exactly 70% warns at sample 30; 69.99% does not",lambda:(verify_boundary(70.0,0.0,True),verify_boundary(69.99,0.0,False)))
review=json.loads(REVIEW.read_text());policy=review["currentPolicy"];assert "full avg10 >=20%" in policy["moderateWarning"] and "some avg10 >=70%" in policy["moderateWarning"]
result={"taskId":"Q-20261025-VF-ITERATION-115","experimentId":"Q115-A1","status":"pass" if all(x["passed"] for x in checks) else "fail","checksPassed":sum(x["passed"] for x in checks),"checksTotal":len(checks),"checks":checks,"sourceSha256":hashes,"policyReceiptCrossChecked":True,"gpuUsed":False,"twoRtx3090Fixture":True,"modelOrServerStarted":False,"networkUsed":False,"buildRun":False,"artificialMemoryGiB":0,"productionChanged":False}
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
for x in checks:print(("PASS" if x["passed"] else "FAIL"),x["name"],x.get("error",""))
print(f"Q115 exact warning-boundary replay: {result['checksPassed']}/{result['checksTotal']} PASS")
if result["status"]!="pass":raise SystemExit(1)
