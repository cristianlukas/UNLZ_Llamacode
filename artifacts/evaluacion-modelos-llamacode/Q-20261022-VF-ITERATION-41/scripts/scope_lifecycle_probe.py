#!/usr/bin/env python3
"""CPU-only process-tree probe for the Linux evaluation scope helper."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

report_path = Path(sys.argv[1])
mode = sys.argv[2]
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
report = {
    "pid": os.getpid(),
    "childPid": child.pid,
    "cwd": os.getcwd(),
    "marker": os.environ.get("Q41_SCOPE_MARK"),
    "oomScoreAdj": Path("/proc/self/oom_score_adj").read_text().strip(),
    "childOomScoreAdj": Path(f"/proc/{child.pid}/oom_score_adj").read_text().strip(),
    "cgroup": Path("/proc/self/cgroup").read_text().strip(),
    "childCgroup": Path(f"/proc/{child.pid}/cgroup").read_text().strip(),
}
tmp = report_path.with_suffix(".tmp")
tmp.write_text(json.dumps(report, indent=2) + "\n")
tmp.replace(report_path)
print("Q41-LIFECYCLE-START", json.dumps(report, sort_keys=True), flush=True)
if mode == "short":
    child.terminate()
    child.wait(timeout=3)
    print("Q41-LIFECYCLE-END 23", flush=True)
    raise SystemExit(23)
while True:
    time.sleep(1)
