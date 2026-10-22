#!/usr/bin/env python3
import json
import os
import pathlib
import sys
import time

receipt = pathlib.Path(sys.argv[1])
exit_code = int(sys.argv[2])
sleep_seconds = float(sys.argv[3])
cgroup = pathlib.Path('/proc/self/cgroup').read_text().strip()
receipt.write_text(json.dumps({
    'pid': os.getpid(),
    'uid': os.getuid(),
    'gid': os.getgid(),
    'cgroup': cgroup,
}, indent=2) + '\n')
print('Q41-CANARY-START', os.getpid(), cgroup, flush=True)
time.sleep(sleep_seconds)
print('Q41-CANARY-END', exit_code, flush=True)
raise SystemExit(exit_code)
