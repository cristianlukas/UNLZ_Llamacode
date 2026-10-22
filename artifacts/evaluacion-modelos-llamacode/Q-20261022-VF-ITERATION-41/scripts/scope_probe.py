#!/usr/bin/env python3
import json
import os
import pathlib
import sys
import time

report = pathlib.Path(sys.argv[1])
payload = {
    "pid": os.getpid(),
    "uid": os.getuid(),
    "gid": os.getgid(),
    "cwd": os.getcwd(),
    "envMarker": os.environ.get("Q41_SCOPE_MARK"),
    "cgroup": pathlib.Path("/proc/self/cgroup").read_text().strip(),
}
rel = next(line.split(":", 2)[2] for line in payload["cgroup"].splitlines() if line.startswith("0::"))
cg = pathlib.Path("/sys/fs/cgroup") / rel.lstrip("/")
for key, filename in (("memoryHigh", "memory.high"), ("memoryMax", "memory.max"), ("memorySwapMax", "memory.swap.max"), ("oomGroup", "memory.oom.group")):
    payload[key] = (cg / filename).read_text().strip()
report.write_text(json.dumps(payload, indent=2) + "\n")
print("Q41-SCOPE-START", json.dumps(payload, sort_keys=True), flush=True)
time.sleep(4)
print("Q41-SCOPE-END 23", flush=True)
raise SystemExit(23)
