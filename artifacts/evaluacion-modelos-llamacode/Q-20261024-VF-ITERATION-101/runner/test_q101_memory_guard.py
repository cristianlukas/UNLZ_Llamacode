#!/usr/bin/env python3
import importlib.util
from pathlib import Path
p=Path(__file__).with_name("q101_memory_guard.py")
s=importlib.util.spec_from_file_location("q101_memory_guard",p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
checks=[]
def check(name,sample,prev,streak,expected_reason,expected_streak,expected_warning):
 r,n,w=m.evaluate_sample(sample,prev,streak); checks.append((name,r==expected_reason and n==expected_streak and w==expected_warning,r,n,w))
check("moderate PSI warns only",{"memAvailableGiB":100,"memoryPsiAvg10Pct":{"some":10,"full":45},"oomKill":5},5,0,None,0,True)
check("severe streak not early",{"memAvailableGiB":100,"memoryPsiAvg10Pct":{"some":80,"full":60},"oomKill":5},5,13,None,14,True)
check("severe at sample 15",{"memAvailableGiB":100,"memoryPsiAvg10Pct":{"some":80,"full":60},"oomKill":5},5,14,"global PSI severe threshold persisted for 15 consecutive 1-second samples",15,True)
check("recovery resets streak",{"memAvailableGiB":100,"memoryPsiAvg10Pct":{"some":0,"full":0},"oomKill":5},5,14,None,0,False)
check("MemAvailable floor",{"memAvailableGiB":31.99,"memoryPsiAvg10Pct":{"some":0,"full":0},"oomKill":5},5,0,"MemAvailable <32 GiB",0,False)
check("OOM counter increase",{"memAvailableGiB":100,"memoryPsiAvg10Pct":{"some":0,"full":0},"oomKill":6},5,0,"global oom_kill counter increased",0,False)
for n,ok,r,s,w in checks: print(("PASS" if ok else "FAIL"),n,r or "",s,w)
if not all(x[1] for x in checks): raise SystemExit(1)
print(f"Q101 memory guard tests: {sum(x[1] for x in checks)}/{len(checks)} PASS")
