#!/usr/bin/env python3
"""CPU-only replay of the exact historical Q97 guard over ASTRA 1M telemetry."""
from __future__ import annotations
import hashlib, importlib.util, json, sys
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-128"
Q97 = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-97/scripts/q97_supervised_bcb.py"
TRACE = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-117/runs/astra-1m-seed-2026103-attempt05/memory-monitor.jsonl"
Q117 = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-117/receipts/q117-amd05-result.json"
AMD05 = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-117/scripts/q117_pressure_guard_attempt05.py"
Q118 = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-118/receipts/q118-amd05-live-trace-replay.json"
EXPECTED = {
    Q97: "663a2762ba8e5433b566c1fa2dbbe692cd8d4272619361c477a339da52c6904a",
    TRACE: "fb369806324110e6bb20a2a2a681af3cdf9b36583a6e1ccfc02b9e0eba1d6dd1",
    Q117: "7735a41285f36344bcac2278c39666e96e44f3e06890949bfd94bf5fbb37c5ee",
    AMD05: "b4d42302e7d405abd5c59df5aa86bb7de6ef3bb91aef487b49acbebd1d24270e",
    Q118: "68769dca479da3d40e48873a77fefb3852f449fcc4f700b56de30a414de0e160",
}
GIB=1024**3

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load_module(path):
    spec=importlib.util.spec_from_file_location("q97_historical_guard_q128",path)
    if spec is None or spec.loader is None: raise RuntimeError("cannot import pinned Q97 helper")
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

def main():
    fingerprint={str(p.relative_to(ROOT)):digest(p) for p in EXPECTED}
    fingerprints_match=all(digest(p)==sha for p,sha in EXPECTED.items())
    if not fingerprints_match: raise RuntimeError("input fingerprint mismatch")
    q97_text=Q97.read_text(encoding="utf-8")
    import_match=("counts, warning, psi_stop = pressure_gate_transition(psi, record_sample.psi_counts)" in q97_text and "if __name__ == \"__main__\":" in q97_text)
    if not import_match: raise RuntimeError("Q97 source no longer matches expected transition wiring")
    guard=load_module(Q97)
    rows=[json.loads(line) for line in TRACE.read_text(encoding="utf-8").splitlines() if line.strip()]
    q117=json.loads(Q117.read_text(encoding="utf-8")); q118=json.loads(Q118.read_text(encoding="utf-8"))
    if not rows: raise RuntimeError("empty ASTRA telemetry")
    expected=q117["memory"]
    counts={"warning_full20":0,"warning_some70":0,"severe_full60":0,"severe_some80":0}
    psi_stops=[]; hard_stops=[]; warnings=[]
    min_avail=float("inf"); max_rss=0; max_psi={"some":0.0,"full":0.0}
    global_oom=[]; worker_oom=[]; worker_swap=[]
    baseline_global=int(rows[0]["oomKill"])
    baseline_worker={k:int(v) for k,v in rows[0]["cgroup_memory"]["run"]["memory_events"].items()}
    for i,row in enumerate(rows,1):
        psi=row["memoryPsiAvg10Pct"]
        counts,warning,stop=guard.pressure_gate_transition(psi,counts)
        if stop: psi_stops.append({"sample":i,"reason":stop})
        if warning: warnings.append(i)
        available=float(row["memAvailableGiB"]); min_avail=min(min_avail,available)
        if available < 32: hard_stops.append({"sample":i,"reason":"MemAvailable<32 GiB"})
        oom=int(row["oomKill"]); global_oom.append(oom)
        if oom>baseline_global: hard_stops.append({"sample":i,"reason":"global oom_kill increased"})
        run=row["cgroup_memory"]["run"]
        events={k:int(v) for k,v in run["memory_events"].items()}
        for key in ("oom","oom_kill"):
            if events.get(key,0)>baseline_worker.get(key,0): hard_stops.append({"sample":i,"reason":f"worker cgroup {key} increased"})
        worker_oom.append(events); worker_swap.append(int(run["memory_swap_current_bytes"]))
        for metric in ("some","full"): max_psi[metric]=max(max_psi[metric],float(psi[metric]))
        max_rss=max(max_rss,int(row.get("process_tree_rss_bytes",0)))
    max_rss_gib=max_rss/GIB
    checks={
      "fingerprintsMatch":fingerprints_match,
      "exactQ97TransitionWiring":import_match,
      "sampleCountMatchesQ117":len(rows)==expected["sampleCount"]==707,
      "minMemAvailableMatchesQ117":abs(min_avail-expected["minMemAvailableGiB"])<1e-6,
      "maxProcessTreeRssMatchesQ117":abs(max_rss_gib-expected["peakProcessTreeRssGiB"])<1e-6,
      "maxHostPsiMatchesQ117":abs(max(max_psi.values())-expected["peakGlobalPsiAvg10Pct"])<1e-6,
      "noQ97PsiStop":len(psi_stops)==0,
      "noHardStop":len(hard_stops)==0,
      "globalOomRemainedZero":min(global_oom)==max(global_oom)==baseline_global==0,
      "workerOomAndSwapRemainedZero":all(not any(e.get(k,0)>baseline_worker.get(k,0) for k in ("oom","oom_kill")) for e in worker_oom) and max(worker_swap)==0,
      "priorAMD05ReplayPass":q118["status"]=="pass" and q118["checksPassed"]==12 and q118["checksTotal"]==12,
    }
    result={"taskId":"Q-20261025-VF-ITERATION-128","status":"PASS" if all(checks.values()) else "FAIL","checks":checks,"checksPassed":sum(checks.values()),"checksTotal":len(checks),"inputFingerprints":fingerprint,"trace":{"samples":len(rows),"minMemAvailableGiB":min_avail,"maxProcessTreeRssGiB":max_rss_gib,"maxHostPsiAvg10Pct":max_psi,"warningSamples":len(warnings),"firstWarningSample":warnings[0] if warnings else None,"q97PsiStops":psi_stops,"hardStops":hard_stops,"firstAndLastGlobalOomKill":[global_oom[0],global_oom[-1]],"workerOomEventsFinal":worker_oom[-1],"workerSwapPeakBytes":max(worker_swap)},"interpretation":{"rssWasNotAPressureSignal":True,"Q97WouldContinueThroughThisASTRA1MTrace":not psi_stops and not hard_stops,"AMD05PriorReplay":"PASS 12/12 in Q118; comparator only, not re-executed","SOLQ34":"completed on dual RTX 3090 without OOM; no continuous PSI trace, not replayable"},"scopeLimits":["Offline replay only; Q117 live run used AMD05, so this is a counterfactual Q97 replay, not a Q97 live run.","No actual severe PSI plus low-headroom event was observed.","SOL Q34 has no continuous PSI series.","This does not attribute Codex crashes or change any guard/profile/model/context/RAM/swap setting."]}
    out=TASK/"receipts/q128-q97-astra1m-replay.json"; out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"checks":checks,"trace":result["trace"]},ensure_ascii=False,indent=2))
    return 0 if result["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
