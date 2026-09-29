"""Summarize LlamaCode benchmark-runs dirs: python3 lch1_summary.py RUNDIR..."""
import glob, json, os, sys
for d in sys.argv[1:]:
    for f in glob.glob(os.path.join(d, '*.json')):
        if os.path.basename(f) in ('metadata.json', 'comparison.json'): continue
        r = json.load(open(f)); q = r.get('toolCallQuality') or {}
        print(json.dumps(dict(run=os.path.basename(d.rstrip('/')), profile=r.get('profileName'),
            first=f"{r.get('firstAttemptScore')}/{r.get('firstAttemptTotal')}", final=f"{r.get('finalScore')}/{r.get('finalTotal')}",
            repairs=r.get('repairAttempts'), timedOut=r.get('timedOut'), failureKind=r.get('failureKind'),
            elapsedSec=r.get('elapsedSec'), firstAttemptSec=r.get('timeToFirstAttempt'), avgTps=round(r.get('avgTps') or 0, 2),
            tools=f"{q.get('successfulCalls')}/{q.get('totalCalls')}", thinking=r.get('thinkingEnabled')), ensure_ascii=False))
