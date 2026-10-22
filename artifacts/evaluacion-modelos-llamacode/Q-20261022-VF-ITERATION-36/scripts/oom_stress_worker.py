#!/usr/bin/env python3
"""Disposable worker that must be killed by its own 128 MiB cgroup."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

cg_rel = next(line.split(":", 2)[2] for line in Path("/proc/self/cgroup").read_text().splitlines()
              if line.startswith("0::"))
cg = Path("/sys/fs/cgroup") / cg_rel.lstrip("/")
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
report = {
    "worker_pid": os.getpid(),
    "child_pid": child.pid,
    "cgroup": cg_rel,
    "memory_high": (cg / "memory.high").read_text().strip(),
    "memory_max": (cg / "memory.max").read_text().strip(),
    "memory_swap_max": (cg / "memory.swap.max").read_text().strip(),
    "oom_group": (cg / "memory.oom.group").read_text().strip(),
    "oom_score_adjust": Path("/proc/self/oom_score_adj").read_text().strip(),
}
report_path = Path(os.environ["Q36_WORKER_REPORT"])
tmp = report_path.with_suffix(".tmp")
tmp.write_text(json.dumps(report, indent=2) + "\n")
tmp.replace(report_path)
print(json.dumps(report, sort_keys=True), flush=True)
time.sleep(0.2)
payload = bytearray(512 * 1024 * 1024)
for offset in range(0, len(payload), 4096):
    payload[offset] = 1
raise SystemExit("unexpectedly allocated 512 MiB under a 128 MiB cgroup limit")
