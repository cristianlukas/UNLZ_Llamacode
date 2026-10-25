#!/usr/bin/env python3
"""Read-only Q110 host/inference-server preflight; launches or signals nothing."""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-110"
OUT = TASK / "receipts/q110-host-preflight.json"
LOCK = json.loads((ROOT / "WORK_QUEUE.lock").read_text(encoding="utf-8"))
if LOCK.get("task_id") != "Q-20261024-VF-ITERATION-110" or LOCK.get("token") != "549f3a3b-673a-4d3a-9046-1122a67c04a2":
    raise SystemExit("Q110 lock mismatch; refusing preflight")


def run(args):
    p = subprocess.run(args, capture_output=True, text=True, check=False)
    return {"argv": args, "returnCode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}


def memavailable():
    fields = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith(("MemTotal:", "MemAvailable:", "SwapTotal:", "SwapFree:")):
            key, val, *_ = line.split()
            fields[key.rstrip(":")] = int(val) * 1024
    return fields


def oomkill():
    for line in Path("/proc/vmstat").read_text().splitlines():
        if line.startswith("oom_kill "):
            return int(line.split()[1])
    raise RuntimeError("oom_kill missing")


def psi():
    out = {}
    for line in Path("/proc/pressure/memory").read_text().splitlines():
        parts = line.split()
        if parts and parts[0] in {"some", "full"}:
            out[parts[0]] = {k: float(v) for k, v in (f.split("=", 1) for f in parts[1:] if "=" in f) if k.startswith("avg")}
    if set(out) != {"some", "full"}:
        raise RuntimeError("memory PSI records incomplete")
    return out


def inference_processes():
    pattern = re.compile(r"llama-server|ollama|vllm|sglang|aphrodite|lmdeploy|mlx_lm|exllama|text-generation-launcher|tritonserver|xinference|localai", re.I)
    excluded = {str(os.getpid())}
    pid = os.getppid()
    for _ in range(8):
        if str(pid) in excluded:
            break
        excluded.add(str(pid))
        try:
            raw = Path(f"/proc/{pid}/stat").read_text()
            rest = raw[raw.rfind(")") + 2:].split()
            pid = int(rest[1])
        except (OSError, ValueError, IndexError):
            break
    matches = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit() or proc.name in excluded:
            continue
        try:
            cmd = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
            comm = (proc / "comm").read_text().strip()
            if pattern.search(comm) or pattern.search(cmd):
                matches.append({"pid": int(proc.name), "comm": comm, "cmdline": cmd[:350]})
        except (OSError, ProcessLookupError):
            pass
    return matches


def parse_apps(raw):
    apps = []
    for line in raw.splitlines():
        parts = [part.strip() for part in line.split(",", 2)]
        if len(parts) == 3:
            apps.append({"pid": parts[0], "processName": parts[1], "usedGpuMemory": parts[2]})
    return apps


def main():
    gpu = run(["nvidia-smi", "--query-gpu=index,name,driver_version,memory.total,memory.used,utilization.gpu", "--format=csv,noheader"])
    apps_run = run(["nvidia-smi", "--query-compute-apps=pid,process_name,used_gpu_memory", "--format=csv,noheader"])
    listeners = run(["ss", "-ltnp"])
    process_matches = inference_processes()
    port_pattern = re.compile(r":(?:11434|1234|5000|5001|7860|8000|8001|8002|8080|8081|8088|8501|30000)(?:\s|$)")
    port_matches = [line for line in listeners["stdout"].splitlines() if port_pattern.search(line)]
    mem = memavailable()
    current_oom = oomkill()
    base = Path("/proc/driver/nvidia/version").read_text(errors="replace") if Path("/proc/driver/nvidia/version").exists() else ""
    mod = run(["modinfo", "-F", "version", "nvidia"])
    value = {
        "schemaVersion": 1,
        "taskId": "Q-20261024-VF-ITERATION-110",
        "capturedAtUtc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "host": socket.gethostname(),
        "platform": run(["uname", "-a"])["stdout"],
        "nvidiaSmi": gpu,
        "nvidiaComputeApps": parse_apps(apps_run["stdout"]),
        "nvidiaComputeAppsCommand": apps_run,
        "nvidiaProcDriverVersion": base.strip(),
        "nvidiaModuleVersion": mod["stdout"],
        "meminfoBytes": mem,
        "memAvailableGiB": round(mem["MemAvailable"] / (1024 ** 3), 3),
        "memoryPsiAvg10Pct": psi(),
        "globalOomKill": current_oom,
        "inferenceProcessMatches": process_matches,
        "listenerScan": listeners,
        "knownInferencePortMatches": port_matches,
        "knownInferenceServerActive": bool(process_matches or port_matches),
        "windowsNativeTools": {name: bool(subprocess.run(["bash", "-lc", f"command -v {name}"], capture_output=True).returncode == 0) for name in ["powershell.exe", "pwsh", "powershell", "cmd.exe", "cmd"]},
        "modelOrServerStarted": False,
        "gpuWorkloadStarted": False,
        "foreignProcessesSignaled": 0,
        "notes": "nvidia-smi was queried read-only. The listed ArtCraft process is preserved and is not identified as an inference server by process/port scan.",
    }
    if OUT.exists():
        raise SystemExit(f"refusing to overwrite {OUT}")
    OUT.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: value[k] for k in ["capturedAtUtc", "nvidiaSmi", "nvidiaComputeApps", "nvidiaModuleVersion", "memAvailableGiB", "memoryPsiAvg10Pct", "globalOomKill", "inferenceProcessMatches", "knownInferencePortMatches", "knownInferenceServerActive", "windowsNativeTools", "modelOrServerStarted", "gpuWorkloadStarted", "foreignProcessesSignaled"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
