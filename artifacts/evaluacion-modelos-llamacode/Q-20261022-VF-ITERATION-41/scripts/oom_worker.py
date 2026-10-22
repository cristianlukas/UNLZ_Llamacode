#!/usr/bin/env python3
"""Synthetic OOM worker; expected to die inside its systemd cgroup."""
import json
import os
import pathlib
import subprocess
import sys
import time

report_path = pathlib.Path(os.environ["Q41_WORKER_REPORT"])
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
cgroup = next(line.split(":", 2)[2] for line in pathlib.Path("/proc/self/cgroup").read_text().splitlines() if line.startswith("0::"))
cg = pathlib.Path("/sys/fs/cgroup") / cgroup.lstrip("/")
report = {
    "worker_pid": os.getpid(),
    "child_pid": child.pid,
    "cgroup": cgroup,
    "child_cgroup": pathlib.Path(f"/proc/{child.pid}/cgroup").read_text().strip(),
    "memory_high": (cg / "memory.high").read_text().strip(),
    "memory_max": (cg / "memory.max").read_text().strip(),
    "memory_swap_max": (cg / "memory.swap.max").read_text().strip(),
    "oom_group": (cg / "memory.oom.group").read_text().strip(),
    "oom_score_adjust": pathlib.Path("/proc/self/oom_score_adj").read_text().strip(),
}
tmp = report_path.with_suffix(".tmp")
tmp.write_text(json.dumps(report, indent=2) + "\n")
tmp.replace(report_path)
print("Q41-OOM-WORKER-READY", json.dumps(report, sort_keys=True), flush=True)
time.sleep(float(os.environ.get("Q41_OOM_DELAY_S", "0")))
# Touch every page so the cgroup, rather than virtual address reservation, is tested.
payload = bytearray(512 * 1024 * 1024)
for offset in range(0, len(payload), 4096):
    payload[offset] = 1
print("UNEXPECTED-ALLOC-SUCCESS", flush=True)
time.sleep(60)
