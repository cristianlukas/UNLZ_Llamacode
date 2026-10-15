import datetime
import json
import shutil
import socket
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def command(args):
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False).stdout.strip()


def read_meminfo():
    values = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key] = int(value.strip().split()[0]) * 1024
    return values


def pressure(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        parts = line.split()
        row = {k: float(v) for k, v in (item.split("=") for item in parts[1:])}
        result[parts[0]] = row
    return result


port = 8117
sock = socket.socket()
try:
    try:
        sock.bind(("127.0.0.1", port))
        port_free = True
    except OSError:
        port_free = False
finally:
    sock.close()

model_manifest = (ROOT / "receipts/sol-model-sha256-check.txt").read_text().splitlines()
model_hashes_ok = len(model_manifest) == 8 and all(line.endswith(": OK") for line in model_manifest)
wheel_hash = command(["sha256sum", str(ROOT / "receipts/anyjev-0.3.0-py3-none-any.whl")])
image_id = command(["docker", "image", "inspect", "--format", "{{.Id}}", "vllm/vllm-openai:v0.27.1"])
gpus = command(["nvidia-smi", "--query-gpu=index,name,memory.total,memory.used,utilization.gpu", "--format=csv,noheader"])
gpu_processes = command(["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader"])
running_containers = command(["docker", "ps", "--format", "{{.Names}} {{.Image}}"])
meminfo = read_meminfo()
swaps = Path("/proc/swaps").read_text().splitlines()[1:]
swap_used_bytes = sum(int(row.split()[3]) * 1024 for row in swaps)
psi = pressure("/proc/pressure/memory")

record = {
    "task_id": "Q-20261015-ANYJEV-EVAL",
    "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "model_hash_check": {"manifest": "Q-20261015-SOL-TASKFLOW-SAMPLING/receipts/sol-model-sha256.tsv", "checked_files": len(model_manifest), "all_ok": model_hashes_ok},
    "package": {"version": "anyjev==0.3.0", "wheel_sha256": wheel_hash.split()[0]},
    "runtime_image": {"tag": "vllm/vllm-openai:v0.27.1", "image_id": image_id},
    "gpu_query": gpus,
    "gpu_compute_processes": gpu_processes,
    "running_containers": running_containers,
    "mem_available_bytes": meminfo.get("MemAvailable"),
    "swap_used_bytes": swap_used_bytes,
    "memory_psi": psi,
    "candidate_port": port,
    "candidate_port_free": port_free,
    "disk_df": {
        "root": command(["df", "-B1", "--output=avail", "/"]).splitlines()[-1].strip(),
        "model_store": command(["df", "-B1", "--output=avail", "/media/cristian/Disco local"]).splitlines()[-1].strip(),
    },
    "decision": "pass" if model_hashes_ok and port_free and not gpu_processes and meminfo.get("MemAvailable", 0) > 32 * 1024**3 and psi.get("full", {}).get("avg10", 100) < 5 and not running_containers else "abort",
}
(ROOT / "receipts/preflight.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))
