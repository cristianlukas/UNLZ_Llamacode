import datetime
import json
import shutil
import socket
import subprocess
from pathlib import Path


def command(args):
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False).stdout.strip()


def pressure(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        parts = line.split()
        result[parts[0]] = {k: float(v) for k, v in (item.split("=") for item in parts[1:])}
    return result


sock = socket.socket()
try:
    try:
        sock.bind(("127.0.0.1", 8117))
        port_free = True
    except OSError:
        port_free = False
finally:
    sock.close()

meminfo = {}
for line in Path("/proc/meminfo").read_text().splitlines():
    if ":" in line:
        key, value = line.split(":", 1)
        meminfo[key] = int(value.strip().split()[0]) * 1024
swaps = Path("/proc/swaps").read_text().splitlines()[1:]
swap_used = sum(int(row.split()[3]) * 1024 for row in swaps)
compute_processes = command(["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader"])
containers = command(["docker", "ps", "--format", "{{.Names}} {{.Image}}"])
psi = pressure("/proc/pressure/memory")
record = {
    "task_id": "Q-20261015-ANYJEV-EVAL",
    "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "gpu_compute_processes": compute_processes,
    "running_containers": containers,
    "mem_available_bytes": meminfo.get("MemAvailable"),
    "swap_used_bytes": swap_used,
    "memory_psi": psi,
    "candidate_port": 8117,
    "candidate_port_free": port_free,
    "disk_available_bytes": {
        "root": shutil.disk_usage("/").free,
        "model_store": shutil.disk_usage("/media/cristian/Disco local").free,
    },
    "decision": "pass" if not compute_processes and not containers and port_free and psi.get("full", {}).get("avg10", 100) < 5 else "abort",
}
target = Path(__file__).resolve().parent / "postflight.json"
target.write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))
