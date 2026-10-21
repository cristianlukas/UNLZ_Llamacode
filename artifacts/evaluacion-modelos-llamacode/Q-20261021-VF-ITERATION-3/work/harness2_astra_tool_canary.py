#!/usr/bin/env python3
"""One local ASTRA function-call canary, resource-guarded and isolated from egress."""
from __future__ import annotations

import datetime as dt
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

RUNNER_PATH = Path(__file__).resolve()
INNER_EXEC = RUNNER_PATH == Path("/tmp/h2probe.py")
REPO = Path(__file__).resolve().parents[4] if not INNER_EXEC else Path("/")
ITER = Path(__file__).resolve().parents[1] if not INNER_EXEC else Path("/tmp")
TASK_ID = "Q-20261021-VF-ITERATION-3"
TOKEN = "5db89d6f-d896-45d7-8238-02bf8e7d61a7"
PORT = 8354
MODEL = "qwen3.8-flash-next-iq2_xs"
SAMPLE_S = 5
MEM_MIN = 64 * 1024**3
MEM_ABORT = 48 * 1024**3
MEM_HIGH = 64 * 1024**3
MEM_MAX = 72 * 1024**3
GRADER_MEMORY_HIGH = 1 * 1024**3
GRADER_MEMORY_MAX = 2 * 1024**3
SWAP_GROWTH_MAX = 1 * 1024**3
GPU_FREE_MIN_MIB = 20 * 1024
GPU_TEMP_MAX_C = 85
PSI_PREFLIGHT_MAX = 10.0
PSI_ABORT = 25.0
PSI_ABORT_SAMPLES = 4
READY_TIMEOUT = 600
REQUEST_TIMEOUT = 180
MAX_OUTPUT_TOKENS = 2048
CANARY_CONTEXT = 8192
API_KEY = "local-only-no-secret"
STRATA_ROOT = Path("/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source")
MODEL_ROOT = Path("/media/cristian/Disco local/Models/FlashNext-IQ2XS-ISTA-Strata-eval-20261012")
MTP_ROOT = Path("/media/cristian/Disco local/Models/FlashNext-IQ3XXS-ISTA-Strata-eval-20261009/strata-data/mtp/rt")
BASE_CONFIG = REPO / "artifacts/evaluacion-modelos-llamacode/Q-20261020-VF-20261019-01/configs/source43-qwen-iq2xs-32k.json"
WEIGHT_MANIFEST = REPO / "artifacts/evaluacion-modelos-llamacode/Q-20261014-STRATA-IQ2XXS-SAMPLING/receipts/iq2xs-weights-sha256.txt"
RUNTIME_MANIFEST = REPO / "artifacts/evaluacion-modelos-llamacode/Q-20261014-STRATA-IQ2XXS-SAMPLING/receipts/runtime-sha256.txt"
RUN_DIR = ITER / "work/astra-tool-canary-run"
RECEIPT = ITER / "receipts/harness2-astra-tool-canary-result.json"
PREFLIGHT_RECEIPT = ITER / "receipts/harness2-astra-tool-canary-preflight.json"


def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def atomic_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def command(argv: list[str], timeout: int = 15) -> str:
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=True).stdout.strip()


def memavailable() -> int:
    line = next(x for x in Path("/proc/meminfo").read_text().splitlines() if x.startswith("MemAvailable:"))
    return int(line.split()[1]) * 1024


def swapfree() -> int:
    line = next(x for x in Path("/proc/meminfo").read_text().splitlines() if x.startswith("SwapFree:"))
    return int(line.split()[1]) * 1024


def psi_full_avg10() -> float:
    m = re.search(r"^full avg10=([0-9.]+)", Path("/proc/pressure/memory").read_text(), re.M)
    return float(m.group(1)) if m else 0.0


def gpu_snapshot() -> list[dict]:
    raw = command([
        "nvidia-smi", "--query-gpu=index,name,memory.free,temperature.gpu,utilization.gpu",
        "--format=csv,noheader,nounits",
    ])
    out = []
    for line in raw.splitlines():
        c = [p.strip() for p in line.split(",")]
        out.append({"index": int(c[0]), "name": c[1], "free_mib": int(c[2]),
                    "temperature_c": int(c[3]), "utilization_percent": int(c[4])})
    return out


def process_rows() -> list[dict]:
    raw = command(["ps", "-eo", "pid=,ppid=,comm=,args="], timeout=10)
    out = []
    for line in raw.splitlines():
        p = line.strip().split(None, 3)
        if len(p) == 4:
            out.append({"pid": int(p[0]), "ppid": int(p[1]), "comm": p[2], "cmd": p[3]})
    return out


INFER_RE = re.compile(r"(^|[/ ])(llama-server|strata|vllm|ollama|sglang|openjet-engine|"
                       r"text-generation-launcher|aphrodite-engine)([/ :]|$)", re.I)


def inference_processes(rows: list[dict] | None = None) -> list[dict]:
    rows = rows or process_rows()
    found = []
    for r in rows:
        try:
            argv = shlex.split(r["cmd"])
        except ValueError:
            argv = []
        if argv and Path(argv[0]).name.lower() == "git":
            continue
        if INFER_RE.search(r["cmd"]):
            found.append(r)
    return found


def listener_pids() -> dict[int, str]:
    raw = command(["ss", "-ltnpH"], timeout=10)
    out: dict[int, str] = {}
    for line in raw.splitlines():
        m = re.search(r"(?:\]|:)(\d+)\s+\S+\s+users:\(\(\"([^\"]+)", line)
        if not m:
            m = re.search(r":(\d+)\s+.*users:\(\(\"([^\"]+)", line)
        if m:
            out[int(m.group(1))] = m.group(2)
    return out


def listener_ports() -> list[int]:
    """Read listening local ports even when ss cannot resolve a process owner."""
    raw = command(["ss", "-ltnH"], timeout=10)
    ports = set()
    for line in raw.splitlines():
        fields = line.split()
        if len(fields) >= 4:
            m = re.search(r":(\d+)$", fields[3])
            if m:
                ports.add(int(m.group(1)))
    return sorted(ports)


def current_lock() -> dict:
    return json.loads((REPO / "WORK_QUEUE.lock").read_text(encoding="utf-8"))


def require_lock() -> None:
    d = current_lock()
    if d.get("task_id") != TASK_ID or d.get("token") != TOKEN:
        raise RuntimeError("WORK_QUEUE.lock no longer belongs to this test")


def runtime_fingerprint() -> dict:
    expected = {}
    for line in RUNTIME_MANIFEST.read_text().splitlines():
        sha, sep, path = line.partition("  ")
        if sep:
            expected[path.strip()] = sha
    checked = []
    for p in [STRATA_ROOT / "engine/strata", STRATA_ROOT / "serve/server.py", STRATA_ROOT / ".venv/bin/python"]:
        want = expected.get(str(p))
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        if not want or got != want:
            raise RuntimeError(f"Pinned Strata runtime hash mismatch: {p}")
        checked.append({"path": str(p), "sha256": got, "size_bytes": p.stat().st_size})
    weights = {}
    for line in WEIGHT_MANIFEST.read_text().splitlines():
        sha, sep, path = line.partition("  ")
        if sep:
            weights[path.strip()] = sha
    actual = []
    for p, expected_size in [
        (MODEL_ROOT / "IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf", 39225954592),
        (MODEL_ROOT / "IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00002-of-00002.gguf", 28800138432),
    ]:
        st = p.stat()
        want = weights.get(str(p))
        if st.st_size != expected_size or not want:
            raise RuntimeError(f"Pinned ASTRA weight manifest/size mismatch: {p}")
        actual.append({"path": str(p), "pinned_sha256": want, "size_bytes": st.st_size,
                       "mtime_ns": st.st_mtime_ns, "sha256_recomputed": False})
    if not STRATA_ROOT.is_dir() or not MTP_ROOT.is_dir() or not (MODEL_ROOT / "strata-data/packs/iq2_xs/tokenizer").is_dir():
        raise RuntimeError("ASTRA/Strata/MTP/tokenizer path is unavailable")
    return {"runtime_files_verified_sha256": checked,
            "model_files_verified_against_pinned_manifest_and_size": actual,
            "model_sha_policy": "reuse previously pinned SHA; compare current size/mtime to avoid an extra full 68 GB read"}


def namespace_canary() -> dict:
    code = (
        "import errno,http.server,json,socket,subprocess,threading,urllib.request;"
        "links=subprocess.run(['ip','-o','link','show'],check=True,capture_output=True,text=True).stdout;"
        "routes=subprocess.run(['ip','route','show'],check=True,capture_output=True,text=True).stdout;"
        "assert 'lo:' in links and len(links.splitlines())==1,links;"
        "assert not any(x.split()[:1]==['default'] for x in routes.splitlines()),routes;"
        "H=type('H',(http.server.BaseHTTPRequestHandler,),{'do_GET':lambda s:(s.send_response(200),s.end_headers(),s.wfile.write(b'OK')),'log_message':lambda *a:None});"
        "srv=http.server.HTTPServer(('127.0.0.1',0),H);t=threading.Thread(target=srv.serve_forever);t.start();"
        "body=urllib.request.urlopen('http://127.0.0.1:%d'%srv.server_port,timeout=2).read();"
        "s=socket.socket();s.settimeout(1);rc=s.connect_ex(('192.0.2.1',443));s.close();"
        "srv.shutdown();srv.server_close();t.join();"
        "assert body==b'OK' and rc==errno.ENETUNREACH,(body,rc);print(json.dumps({'interfaces':['lo'],'routes':routes.splitlines(),'loopback_http':200,'test_net_errno':rc,'test_net_errno_name':'ENETUNREACH'}))"
    )
    b = ["/usr/bin/bwrap", "--die-with-parent", "--new-session", "--unshare-user", "--uid", "0", "--gid", "0",
         "--unshare-net", "--unshare-pid", "--ro-bind", "/", "/", "--proc", "/proc", "--dev", "/dev",
         "--tmpfs", "/tmp", "--", "/usr/bin/python3", "-c", code]
    out = command(b, timeout=15)
    return json.loads(out)


def preflight() -> dict:
    require_lock()
    procs = inference_processes()
    if procs:
        raise RuntimeError(f"External inference process active: {procs}")
    listen = listener_pids()
    ports = listener_ports()
    if PORT in ports:
        raise RuntimeError(f"Canary port {PORT} is occupied (ss owners: {listen.get(PORT, 'unresolved')})")
    mem = memavailable()
    if mem < MEM_MIN:
        raise RuntimeError(f"MemAvailable {mem} below {MEM_MIN}")
    psi = psi_full_avg10()
    if psi > PSI_PREFLIGHT_MAX:
        raise RuntimeError(f"Memory PSI full avg10 {psi} exceeds {PSI_PREFLIGHT_MAX}")
    gpus = gpu_snapshot()
    if len(gpus) < 2 or any(g["free_mib"] < GPU_FREE_MIN_MIB or g["temperature_c"] >= GPU_TEMP_MAX_C for g in gpus[:2]):
        raise RuntimeError(f"GPU resource gate failed: {gpus}")
    free = shutil.disk_usage(ITER).free
    if free < 20 * 1024**3:
        raise RuntimeError(f"Scratch filesystem has only {free} free bytes")
    if not shutil.which("bwrap") or not shutil.which("systemd-run"):
        raise RuntimeError("bubblewrap or systemd-run is unavailable")
    # Verify that this user session can apply a private memory ceiling before any model load.
    subprocess.run(["systemd-run", "--user", "--scope", "--quiet", "-p", f"MemoryHigh={MEM_HIGH}",
                    "-p", f"MemoryMax={MEM_MAX}", "-p", "TasksMax=512", "--", "/usr/bin/true"],
                   check=True, timeout=15)
    subprocess.run(["systemd-run", "--user", "--scope", "--quiet", "-p",
                    f"MemoryHigh={GRADER_MEMORY_HIGH}", "-p", f"MemoryMax={GRADER_MEMORY_MAX}",
                    "-p", "TasksMax=64", "--", "/usr/bin/true"], check=True, timeout=15)
    ns = namespace_canary()
    fp = runtime_fingerprint()
    return {"at_utc": utc(), "lock_token": TOKEN, "external_inference_processes": procs,
            "evaluation_port_listener": None, "listener_snapshot": listen,
            "listening_ports_snapshot": ports,
            "memavailable_bytes": mem, "memory_psi_full_avg10_percent": psi,
            "swapfree_bytes": swapfree(), "gpus": gpus, "scratch_free_bytes": free,
            "memory_scope_smoke": "pass", "grader_scope_smoke": "pass",
            "network_namespace_canary": ns, "runtime_fingerprint": fp,
            "gui_allowed_left_running": True}


def make_isolated_config() -> tuple[Path, str]:
    cfg = json.loads(BASE_CONFIG.read_text(encoding="utf-8"))
    replacements = {
        str(MODEL_ROOT / "strata-data/packs/iq2_xs"): "/media/models/astra/strata-data/packs/iq2_xs",
        str(MODEL_ROOT / "IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf"): "/media/models/astra/IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf",
        str(MODEL_ROOT / "IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00002-of-00002.gguf"): "/media/models/astra/IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00002-of-00002.gguf",
        str(MTP_ROOT): "/media/models/mtp",
    }
    cfg["args"] = [replacements.get(x, x) for x in cfg["args"]]
    for flag in ("--max-context", "--kv-resident"):
        positions = [i for i, value in enumerate(cfg["args"][:-1]) if value == flag]
        if len(positions) != 1:
            raise RuntimeError(f"Expected one {flag} setting in isolated config, found {len(positions)}")
        cfg["args"][positions[0] + 1] = str(CANARY_CONTEXT)
    cfg["tokenizer"] = "/media/models/astra/strata-data/packs/iq2_xs/tokenizer"
    cfg["log"] = "/tmp/work/server.log"
    cfg["port"] = PORT
    p = RUN_DIR / "strata-isolated.json"
    p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p, hashlib.sha256(p.read_bytes()).hexdigest()


def systemd_scope_cgroup(unit: str) -> Path | None:
    try:
        cg = command(["systemctl", "--user", "show", unit, "--property=ControlGroup", "--value"], timeout=5)
    except Exception:
        return None
    p = Path("/sys/fs/cgroup") / cg.lstrip("/")
    return p if cg and p.is_dir() else None


def cgroup_pids(root: Path | None) -> set[int]:
    out: set[int] = set()
    if root and root.is_dir():
        for d, _dirs, files in os.walk(root):
            if "cgroup.procs" in files:
                try:
                    out.update(int(x) for x in (Path(d) / "cgroup.procs").read_text().split())
                except (OSError, ValueError):
                    pass
    return out


def descendants(pid: int) -> set[int]:
    rows = process_rows()
    by_parent: dict[int, list[int]] = {}
    for r in rows:
        by_parent.setdefault(r["ppid"], []).append(r["pid"])
    seen = {pid}
    stack = [pid]
    while stack:
        for child in by_parent.get(stack.pop(), []):
            if child not in seen:
                seen.add(child)
                stack.append(child)
    return seen


def guard_snapshot(baseline: dict, own: set[int]) -> dict:
    require_lock()
    rows = process_rows()
    ext = [p for p in inference_processes(rows) if p["pid"] not in own]
    if ext:
        raise RuntimeError(f"External inference process appeared: {ext}")
    listeners = listener_pids()
    if PORT in listeners and not any(p["pid"] in own and INFER_RE.search(p["cmd"]) for p in rows):
        raise RuntimeError(f"Port {PORT} acquired by a non-owned process: {listeners[PORT]}")
    mem = memavailable()
    psi = psi_full_avg10()
    sw = swapfree()
    gpus = gpu_snapshot()
    if mem < MEM_ABORT:
        raise RuntimeError(f"MemAvailable fell below guard: {mem}")
    if sw < baseline["swapfree_bytes"] - SWAP_GROWTH_MAX:
        raise RuntimeError(f"Swap grew more than 1 GiB: baseline={baseline['swapfree_bytes']} now={sw}")
    if any(g["temperature_c"] >= GPU_TEMP_MAX_C for g in gpus[:2]):
        raise RuntimeError(f"GPU reached abort temperature: {gpus}")
    return {"at_utc": utc(), "memavailable_bytes": mem,
            "memory_psi_full_avg10_percent": psi, "swapfree_bytes": sw,
            "gpus": gpus, "owned_inference_pids": sorted(own),
            "external_inference_processes": ext}


def sandbox_only() -> int:
    """Verify the exact model/runtime mount view without starting inference."""
    links = command(["ip", "-o", "link", "show"])
    routes = command(["ip", "route", "show"])
    if len(links.splitlines()) != 1 or "lo:" not in links or any(
            row.split()[:1] == ["default"] for row in routes.splitlines()):
        raise RuntimeError(f"Unexpected sandbox network: interfaces={links} routes={routes}")
    probe = socket.socket()
    probe.settimeout(1)
    egress = probe.connect_ex(("192.0.2.1", 443))
    probe.close()
    if egress != errno.ENETUNREACH:
        raise RuntimeError(f"TEST-NET expected ENETUNREACH, got {errno.errorcode.get(egress, egress)}")

    expected_files = [
        ("/media/models/astra/IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf", 39225954592),
        ("/media/models/astra/IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00002-of-00002.gguf", 28800138432),
    ]
    visible = []
    for name, size in expected_files:
        p = Path(name)
        st = p.stat()
        if st.st_size != size:
            raise RuntimeError(f"Mounted ASTRA shard size mismatch: {name}: {st.st_size}")
        # Open without writing to prove the bind mount rejects write access.
        try:
            fd = os.open(name, os.O_WRONLY | getattr(os, "O_CLOEXEC", 0))
        except OSError as exc:
            if exc.errno not in (errno.EROFS, errno.EACCES, errno.EPERM):
                raise
            write_probe = "rejected"
        else:
            os.close(fd)
            raise RuntimeError(f"ASTRA model bind unexpectedly permits write access: {name}")
        visible.append({"path": name, "size_bytes": st.st_size, "write_open": write_probe})
    tokenizer = Path("/media/models/astra/strata-data/packs/iq2_xs/tokenizer")
    mtp = Path("/media/models/mtp")
    source = Path(str(STRATA_ROOT))
    if not tokenizer.is_dir() or not mtp.is_dir() or not (source / "serve/server.py").is_file():
        raise RuntimeError("ASTRA tokenizer, MTP, or Strata server is not visible in the sandbox")
    config = json.loads(Path("/tmp/work/strata-isolated.json").read_text(encoding="utf-8"))
    config_text = json.dumps(config)
    if config.get("tokenizer") != str(tokenizer) or config.get("log") != "/tmp/work/server.log":
        raise RuntimeError("Isolated config tokenizer/log target does not match the private mounts")
    if str(MODEL_ROOT) in config_text or str(MTP_ROOT) in config_text:
        raise RuntimeError("An original host model path leaked into the isolated config")
    args = config.get("args", [])
    contexts = [args[i + 1] for i, value in enumerate(args[:-1]) if value == "--max-context"]
    kv_residents = [args[i + 1] for i, value in enumerate(args[:-1]) if value == "--kv-resident"]
    if contexts != [str(CANARY_CONTEXT)] or kv_residents != [str(CANARY_CONTEXT)]:
        raise RuntimeError(f"Isolated context settings do not match preregistration: {contexts}, {kv_residents}")
    hidden_profile = Path("/home/cristian/.config/LlamaCode/astra-iq2xs-strata.json")
    if hidden_profile.exists():
        raise RuntimeError("The user's real ASTRA profile leaked into the isolated home")
    gpu = command(["nvidia-smi", "--query-gpu=index,name,memory.free,temperature.gpu", "--format=csv,noheader,nounits"])
    result = {"status": "sandbox_mounts_network_and_gpu_pass", "interfaces": ["lo"],
              "default_route": False, "test_net_errno": egress,
              "test_net_errno_name": errno.errorcode.get(egress), "model_files": visible,
              "tokenizer_visible": True, "mtp_visible": True, "strata_server_visible": True,
              "production_profile_hidden": True, "canary_context_tokens": CANARY_CONTEXT,
              "kv_resident_tokens": CANARY_CONTEXT, "gpu_query": gpu, "inference_started": False,
              "at_utc": utc()}
    atomic_json(Path("/tmp/work/sandbox-smoke.json"), result)
    print(json.dumps(result, ensure_ascii=False))
    return 0


def make_bwrap_command(config_path: Path, sandbox: bool = False) -> list[str]:
    source = str(STRATA_ROOT)
    model_root = str(MODEL_ROOT)
    mtp_root = str(MTP_ROOT)
    py = str(STRATA_ROOT / ".venv/bin/python")
    return [
        "/usr/bin/bwrap", "--die-with-parent", "--new-session", "--unshare-user", "--uid", "0", "--gid", "0",
        "--unshare-net", "--unshare-pid", "--ro-bind", "/", "/", "--proc", "/proc", "--dev", "/dev",
        "--dev-bind", "/dev/nvidia0", "/dev/nvidia0", "--dev-bind", "/dev/nvidia1", "/dev/nvidia1",
        "--dev-bind", "/dev/nvidiactl", "/dev/nvidiactl", "--dev-bind", "/dev/nvidia-uvm", "/dev/nvidia-uvm",
        "--dev-bind", "/dev/nvidia-uvm-tools", "/dev/nvidia-uvm-tools", "--dev-bind", "/dev/nvidia-modeset", "/dev/nvidia-modeset",
        "--tmpfs", "/home", "--dir", "/home/cristian", "--dir", "/home/cristian/.cache",
        "--dir", "/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009", "--ro-bind", source, source,
        "--tmpfs", "/media", "--dir", "/media/models", "--dir", "/media/models/astra",
        "--dir", "/media/models/mtp", "--ro-bind", model_root, "/media/models/astra",
        "--ro-bind", mtp_root, "/media/models/mtp", "--tmpfs", "/run", "--tmpfs", "/tmp",
        "--dir", "/tmp/work", "--bind", str(RUN_DIR), "/tmp/work",
        "--ro-bind", str(RUNNER_PATH), "/tmp/h2probe.py",
        "--chdir", source, "--setenv", "HOME", "/tmp", "--setenv", "PATH",
        f"{STRATA_ROOT / '.venv/bin'}:/usr/local/cuda-12.8/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "--setenv", "LD_LIBRARY_PATH", "/usr/local/cuda-12.8/lib64", "--setenv", "PYTHONUNBUFFERED", "1",
        "--", py, "/tmp/h2probe.py", "--inner", "--port", str(PORT), "--config", "/tmp/work/strata-isolated.json",
        *( ["--sandbox-only"] if sandbox else [] ),
    ]


def run_inner(args: list[str]) -> int:
    port = int(args[args.index("--port") + 1])
    config_path = args[args.index("--config") + 1]
    model = MODEL
    server_log = open("/tmp/work/server.log", "w", encoding="utf-8")
    server = subprocess.Popen(
        [str(STRATA_ROOT / ".venv/bin/python"), str(STRATA_ROOT / "serve/server.py"),
         "--engine", "strata", "--config", config_path, "--host", "127.0.0.1", "--port", str(port),
         "--gpu", "0,1", "--api-key", API_KEY],
        cwd=STRATA_ROOT, stdout=server_log,
        stderr=subprocess.STDOUT, start_new_session=True,
        env={"HOME": "/tmp", "PATH": f"{STRATA_ROOT / '.venv/bin'}:/usr/local/cuda-12.8/bin:/usr/sbin:/usr/bin:/sbin:/bin",
             "LD_LIBRARY_PATH": "/usr/local/cuda-12.8/lib64", "PYTHONUNBUFFERED": "1",
             "STRATA_PREFILL_CPU_SHARE": "0"},
    )
    result = {"status": "starting", "model": model, "port": port, "server_pid_in_namespace": server.pid,
              "started_at_utc": utc(), "network": {}}
    try:
        links = command(["ip", "-o", "link", "show"])
        routes = command(["ip", "route", "show"])
        if len(links.splitlines()) != 1 or "lo:" not in links or any(x.split()[:1] == ["default"] for x in routes.splitlines()):
            raise RuntimeError(f"Unexpected network namespace: interfaces={links} routes={routes}")
        probe = socket.socket(); probe.settimeout(1)
        egress = probe.connect_ex(("192.0.2.1", 443)); probe.close()
        if egress != errno.ENETUNREACH:
            raise RuntimeError(f"TEST-NET expected ENETUNREACH, got {errno.errorcode.get(egress, egress)}")
        result["network"] = {"interfaces": ["lo"], "default_route": False,
                             "test_net_errno": egress, "test_net_errno_name": "ENETUNREACH"}
        deadline = time.monotonic() + READY_TIMEOUT
        health = None
        headers = {"Authorization": f"Bearer {API_KEY}"}
        while time.monotonic() < deadline:
            if server.poll() is not None:
                raise RuntimeError(f"Strata server exited during startup: {server.returncode}")
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{port}/health", headers=headers)
                with urllib.request.urlopen(req, timeout=3) as res:
                    health = json.loads(res.read())
                if health.get("status") == "ok" and health.get("loaded") is True:
                    break
            except Exception:
                time.sleep(5)
        if not health or health.get("status") != "ok" or health.get("loaded") is not True:
            raise TimeoutError("ASTRA did not reach loaded /health within 600 seconds")
        req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/models", headers=headers)
        with urllib.request.urlopen(req, timeout=5) as res:
            models = json.loads(res.read())
        ids = [row.get("id") for row in models.get("data", [])]
        if model not in ids:
            raise RuntimeError(f"Unexpected model response: {ids}")
        result["health"] = health
        result["models"] = ids
        result["request_started_at_utc"] = utc()
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a coding agent. Implement the requested Python function. Use the write_file tool exactly once to create solution.py with complete standalone Python source. Do not attempt any other tool and do not answer with prose."},
                {"role": "user", "content": "Implement covered_duration(intervals) for half-open integer intervals [start, end). Return the number of integer time units covered by their union. Empty intervals contribute 0. If any start > end, raise ValueError. Do not mutate input. Define the function in solution.py. Only the write_file(path='solution.py', content='...') tool call counts as delivery."},
            ],
            "tools": [{"type": "function", "function": {
                "name": "write_file", "description": "Write one UTF-8 Python source file into the canary workspace.",
                "parameters": {"type": "object", "properties": {
                    "path": {"type": "string", "enum": ["solution.py"]},
                    "content": {"type": "string"}}, "required": ["path", "content"], "additionalProperties": False}}}],
            "tool_choice": "auto", "max_tokens": MAX_OUTPUT_TOKENS,
            "temperature": 0.6, "top_p": 0.95, "top_k": 20, "min_p": 0.0,
            "repeat_penalty": 1.0, "presence_penalty": 0.0, "stream": False,
        }
        prompt_hash = hashlib.sha256(json.dumps(payload["messages"], sort_keys=True).encode()).hexdigest()
        schema_hash = hashlib.sha256(json.dumps(payload["tools"], sort_keys=True).encode()).hexdigest()
        body = json.dumps(payload, separators=(",", ":")).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=body,
                                     headers={**headers, "Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as res:
                answer = json.loads(res.read())
                http_status = res.status
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"ASTRA API returned HTTP {exc.code}: {exc.read(2000).decode(errors='replace')}") from exc
        choices = answer.get("choices") or []
        message = choices[0].get("message", {}) if choices else {}
        calls = message.get("tool_calls") or []
        result["api_http_status"] = http_status
        result["prompt_sha256"] = prompt_hash
        result["tool_schema_sha256"] = schema_hash
        result["usage"] = answer.get("usage")
        result["finish_reason"] = choices[0].get("finish_reason") if choices else None
        result["tool_call_count"] = len(calls)
        if len(calls) != 1:
            result.update({"status": "no_single_tool_call", "assistant_text_characters": len(message.get("content") or ""),
                           "assistant_text_sha256": hashlib.sha256(str(message.get("content") or "").encode()).hexdigest()})
        else:
            call = calls[0]
            fn = call.get("function", {})
            try:
                arguments = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Model emitted non-JSON tool arguments: {exc}") from exc
            path, content = arguments.get("path"), arguments.get("content")
            if fn.get("name") != "write_file" or path != "solution.py" or not isinstance(content, str):
                raise RuntimeError("Model tool call failed the fixed name/path/argument gate")
            if len(content.encode("utf-8")) > 30000:
                raise RuntimeError("Generated solution exceeds 30 KB")
            Path("/tmp/work/solution.py").write_text(content, encoding="utf-8")
            result.update({"status": "tool_call_written", "tool_name": fn.get("name"), "tool_path": path,
                           "solution_bytes": len(content.encode("utf-8")),
                           "solution_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()})
        result["completed_at_utc"] = utc()
        atomic_json(Path("/tmp/work/probe.json"), result)
        return 0
    except BaseException as exc:
        result.update({"status": "inner_error", "error": f"{type(exc).__name__}: {exc}", "completed_at_utc": utc()})
        atomic_json(Path("/tmp/work/probe.json"), result)
        return 1
    finally:
        if server.poll() is None:
            try:
                os.killpg(server.pid, signal.SIGTERM)
                server.wait(timeout=20)
            except Exception:
                try:
                    os.killpg(server.pid, signal.SIGKILL)
                except OSError:
                    pass
                try:
                    server.wait(timeout=10)
                except Exception:
                    pass
        server_log.close()


def grader_bwrap(workspace: Path = RUN_DIR) -> list[str]:
    return ["/usr/bin/bwrap", "--die-with-parent", "--new-session", "--unshare-user", "--uid", "0", "--gid", "0",
            "--unshare-net", "--unshare-pid", "--ro-bind", "/", "/", "--proc", "/proc", "--dev", "/dev",
            "--tmpfs", "/home", "--tmpfs", "/root", "--tmpfs", "/media", "--tmpfs", "/mnt",
            "--tmpfs", "/run", "--tmpfs", "/tmp", "--dir", "/tmp/workspace",
            "--ro-bind", str(workspace), "/tmp/workspace",
            "--chdir", "/tmp/workspace", "--setenv", "PYTHONDONTWRITEBYTECODE", "1", "--",
            "/usr/bin/python3", "-I", "-B", "/tmp/workspace/test_interval_union.py"]


def run_scoped_grader(timeout: int = 40, workspace: Path = RUN_DIR) -> subprocess.CompletedProcess:
    require_lock()
    if inference_processes():
        raise RuntimeError("An external inference process appeared before grading")
    unit = f"vf-h2-grader-{int(time.time())}"
    cmd = ["systemd-run", "--user", "--scope", "--quiet", "--unit", unit,
           "-p", f"MemoryHigh={GRADER_MEMORY_HIGH}", "-p", f"MemoryMax={GRADER_MEMORY_MAX}",
           "-p", "TasksMax=64", "--", *grader_bwrap(workspace)]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, start_new_session=True)
    deadline = time.monotonic() + timeout
    out = err = ""
    while True:
        require_lock()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            out, err = proc.communicate(timeout=min(1.0, remaining))
            break
        except subprocess.TimeoutExpired:
            continue
    if proc.poll() is None:
        subprocess.run(["systemctl", "--user", "stop", f"{unit}.scope"],
                       capture_output=True, timeout=15, check=False)
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except OSError:
            pass
        try:
            out, err = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
            out, err = proc.communicate(timeout=5)
        return subprocess.CompletedProcess(cmd, 124, out, err)
    require_lock()
    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)


def grader_smoke_only() -> int:
    """Check the fixed holdout and constrained grader with a known reference solution."""
    require_lock()
    if inference_processes():
        raise RuntimeError("An inference server is active; do not overlap the grader smoke")
    workspace = ITER / "work/interval-union-grader-smoke"
    workspace.mkdir(parents=True, exist_ok=True)
    solution = (
        "def covered_duration(intervals):\n"
        "    pairs = list(intervals)\n"
        "    if any(start > end for start, end in pairs):\n"
        "        raise ValueError('reversed interval')\n"
        "    pairs = sorted((start, end) for start, end in pairs if start < end)\n"
        "    total = 0\n"
        "    if not pairs:\n"
        "        return total\n"
        "    left, right = pairs[0]\n"
        "    for start, end in pairs[1:]:\n"
        "        if start > right:\n"
        "            total += right - left\n"
        "            left, right = start, end\n"
        "        else:\n"
        "            right = max(right, end)\n"
        "    return total + right - left\n"
    )
    (workspace / "solution.py").write_text(solution, encoding="utf-8")
    (workspace / "test_interval_union.py").write_bytes((ITER / "work/test_interval_union.py").read_bytes())
    receipt = {"test_id": "Q-20261021-H2-INTERVAL-UNION-GRADER-SELFTEST", "status": "running",
               "at_utc": utc(), "lock_token": TOKEN, "model_inference": False,
               "fixture": "fixed correct reference solution; not model output",
               "grader_memory_high_bytes": GRADER_MEMORY_HIGH,
               "grader_memory_max_bytes": GRADER_MEMORY_MAX, "grader_tasks_max": 64,
               "timeout_seconds": 40}
    rc = 1
    try:
        run = run_scoped_grader(timeout=40, workspace=workspace)
        receipt["grader"] = {"exit_code": run.returncode, "stdout": run.stdout[-4000:],
                             "stderr": run.stderr[-4000:], "sandbox": "bubblewrap read-only root, hidden home/media, private network namespace"}
        if run.returncode != 0 or "PASS: 10 interval-union holdout cases" not in run.stdout:
            raise RuntimeError("Known-answer holdout grader self-test did not pass 10/10")
        receipt["status"] = "grader_selftest_pass_10_of_10"
        rc = 0
    except BaseException as exc:
        receipt["status"] = "grader_selftest_failed"
        receipt["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        receipt["completed_at_utc"] = utc()
        atomic_json(ITER / "receipts/harness2-interval-union-grader-selftest.json", receipt)
    print(json.dumps({"test_id": receipt["test_id"], "status": receipt["status"],
                      "model_inference": False,
                      "receipt": str(ITER / "receipts/harness2-interval-union-grader-selftest.json")},
                     ensure_ascii=False))
    return rc


def preflight_only() -> int:
    """Exercise the final sandbox mounts and network boundary without model load."""
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    receipt = {"test_id": "Q-20261021-H2-ASTRA-LOCAL-TOOL-CANARY-PREFLIGHT",
               "status": "preflight", "started_at_utc": utc(), "lock_token": TOKEN,
               "gui_policy": "allowed and left running", "model": MODEL,
               "inference_started": False}
    rc = 1
    try:
        receipt["preflight"] = preflight()
        config_path, config_hash = make_isolated_config()
        receipt["isolated_config_sha256"] = config_hash
        receipt["canary_context_tokens"] = CANARY_CONTEXT
        receipt["runner_sha256"] = hashlib.sha256(RUNNER_PATH.read_bytes()).hexdigest()
        cmd = ["systemd-run", "--user", "--scope", "--quiet", "--unit",
               f"vf-h2-astra-preflight-{int(time.time())}", "-p", f"MemoryHigh={MEM_HIGH}",
               "-p", f"MemoryMax={MEM_MAX}", "-p", "TasksMax=512", "--",
               *make_bwrap_command(config_path, sandbox=True)]
        smoke = subprocess.run(cmd, capture_output=True, text=True, timeout=45, check=False)
        (RUN_DIR / "sandbox-preflight.log").write_text(
            "STDOUT\n" + smoke.stdout[-8000:] + "\nSTDERR\n" + smoke.stderr[-8000:], encoding="utf-8")
        receipt["sandbox_command_exit"] = smoke.returncode
        sandbox_path = RUN_DIR / "sandbox-smoke.json"
        if smoke.returncode != 0 or not sandbox_path.is_file():
            raise RuntimeError(f"Read-only isolated sandbox smoke failed (rc={smoke.returncode})")
        receipt["sandbox"] = json.loads(sandbox_path.read_text(encoding="utf-8"))
        require_lock()
        post_procs = inference_processes()
        post_ports = listener_ports()
        receipt["post_sandbox_external_inference_processes"] = post_procs
        receipt["post_sandbox_listening_ports"] = post_ports
        if post_procs or PORT in post_ports:
            raise RuntimeError("Inference process or canary port appeared during the no-inference preflight")
        receipt["status"] = "preflight_passed_no_inference"
        rc = 0
    except BaseException as exc:
        receipt["status"] = "preflight_failed_no_inference"
        receipt["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        receipt["completed_at_utc"] = utc()
        try:
            receipt["postflight"] = {"inference_processes": inference_processes(),
                                     "listeners": listener_pids(), "listening_ports": listener_ports(),
                                     "memavailable_bytes": memavailable(),
                                     "memory_psi_full_avg10_percent": psi_full_avg10(),
                                     "swapfree_bytes": swapfree(), "gpus": gpu_snapshot()}
        except Exception as exc:
            receipt["postflight_error"] = f"{type(exc).__name__}: {exc}"
        atomic_json(PREFLIGHT_RECEIPT, receipt)
    print(json.dumps({"test_id": receipt["test_id"], "status": receipt["status"],
                      "inference_started": False, "error": receipt.get("error"),
                      "receipt": str(PREFLIGHT_RECEIPT)}, ensure_ascii=False))
    return rc


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--inner":
        if "--sandbox-only" in sys.argv:
            return sandbox_only()
        return run_inner(sys.argv)
    if len(sys.argv) > 1 and sys.argv[1] == "--preflight-only":
        return preflight_only()
    if len(sys.argv) > 1 and sys.argv[1] == "--grader-smoke-only":
        return grader_smoke_only()
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    receipt = {"test_id": "Q-20261021-H2-ASTRA-LOCAL-TOOL-CANARY", "status": "preflight", "started_at_utc": utc(),
               "lock_token": TOKEN, "gui_policy": "allowed and left running", "model": MODEL,
               "inference_started": False}
    proc = None
    log_handle = None
    return_code = 1
    psi_streak = 0
    samples = []
    try:
        receipt["preflight"] = preflight()
        config_path, config_hash = make_isolated_config()
        receipt["isolated_config"] = str(config_path)
        receipt["isolated_config_sha256"] = config_hash
        receipt["canary_context_tokens"] = CANARY_CONTEXT
        receipt["runner_sha256"] = hashlib.sha256(RUNNER_PATH.read_bytes()).hexdigest()
        receipt["holdout_sha256"] = hashlib.sha256((ITER / "work/test_interval_union.py").read_bytes()).hexdigest()
        receipt["server_command"] = [str(STRATA_ROOT / ".venv/bin/python"), str(STRATA_ROOT / "serve/server.py"),
                                     "--engine", "strata", "--config", "/tmp/work/strata-isolated.json",
                                     "--host", "127.0.0.1", "--port", str(PORT), "--gpu", "0,1",
                                     "--api-key", "<local placeholder redacted>"]
        receipt["status"] = "starting"
        atomic_json(RECEIPT, receipt)
        unit = f"vf-h2-astra-canary-{int(time.time())}"
        bcmd = make_bwrap_command(config_path)
        cmd = ["systemd-run", "--user", "--scope", "--unit", unit,
               "-p", f"MemoryHigh={MEM_HIGH}", "-p", f"MemoryMax={MEM_MAX}",
               "-p", "TasksMax=512", "--", *bcmd]
        log_handle = (RUN_DIR / "orchestrator.log").open("w", encoding="utf-8")
        proc = subprocess.Popen(cmd, stdout=log_handle, stderr=subprocess.STDOUT, start_new_session=True)
        receipt["scope_unit"] = f"{unit}.scope"
        receipt["host_supervisor_pid"] = proc.pid
        receipt["inference_started"] = True
        receipt["server_started_at_utc"] = utc()
        atomic_json(RECEIPT, receipt)
        baseline = {"swapfree_bytes": receipt["preflight"]["swapfree_bytes"]}
        overall_started = time.monotonic()
        while proc.poll() is None:
            require_lock()
            own = descendants(proc.pid)
            cg = systemd_scope_cgroup(f"{unit}.scope")
            own |= cgroup_pids(cg)
            snapshot = guard_snapshot(baseline, own)
            samples.append(snapshot)
            psi_streak = psi_streak + 1 if snapshot["memory_psi_full_avg10_percent"] > PSI_ABORT else 0
            if psi_streak >= PSI_ABORT_SAMPLES:
                raise RuntimeError(f"Memory PSI exceeded {PSI_ABORT}% for {PSI_ABORT_SAMPLES} consecutive samples")
            if time.monotonic() - overall_started > READY_TIMEOUT + REQUEST_TIMEOUT + 60:
                raise TimeoutError("Canary exceeded 840-second overall guard")
            time.sleep(SAMPLE_S)
        receipt["host_supervisor_exit"] = proc.returncode
        receipt["guard_samples"] = samples
        if proc.returncode != 0:
            raise RuntimeError(f"Isolated ASTRA probe scope exited with rc={proc.returncode}; inspect orchestrator/server logs")
        probe_path = RUN_DIR / "probe.json"
        if not probe_path.is_file():
            raise RuntimeError("Isolated probe returned without its result receipt")
        probe = json.loads(probe_path.read_text())
        receipt["probe"] = probe
        if probe.get("status") != "tool_call_written":
            receipt["status"] = "canary_failed_no_tool_call"
            raise RuntimeError(f"Local ASTRA did not emit one valid file tool call: {probe.get('status')}")
        test = run_scoped_grader(timeout=40)
        receipt["holdout"] = {"exit_code": test.returncode, "stdout": test.stdout[-4000:],
                              "stderr": test.stderr[-4000:], "cases_expected": 10,
                              "sandbox": "bubblewrap read-only root, hidden home/media, private network namespace",
                              "systemd_scope_memory_high_bytes": GRADER_MEMORY_HIGH,
                              "systemd_scope_memory_max_bytes": GRADER_MEMORY_MAX,
                              "systemd_scope_tasks_max": 64}
        if test.returncode != 0:
            receipt["status"] = "canary_failed_holdout"
            raise RuntimeError("ASTRA-generated solution failed the fixed 10-case holdout")
        receipt["status"] = "canary_passed_tool_and_holdout"
        receipt["completed_at_utc"] = utc()
        return_code = 0
    except BaseException as exc:
        receipt["guard_samples"] = samples
        if receipt.get("status") not in ("canary_failed_no_tool_call", "canary_failed_holdout"):
            receipt["status"] = "aborted_or_failed"
        receipt["error"] = f"{type(exc).__name__}: {exc}"
        receipt["completed_at_utc"] = utc()
        return_code = 1
    finally:
        if proc is not None and proc.poll() is None:
            unit_name = receipt.get("scope_unit")
            if unit_name:
                subprocess.run(["systemctl", "--user", "stop", unit_name], capture_output=True, timeout=30)
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=15)
            except Exception:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except OSError:
                    pass
                try:
                    proc.wait(timeout=10)
                except Exception:
                    pass
        if proc is not None:
            receipt["host_supervisor_exit_after_cleanup"] = proc.poll()
        receipt["guard_samples"] = samples
        if log_handle is not None:
            log_handle.close()
        try:
            receipt["postflight"] = {"at_utc": utc(), "inference_processes": inference_processes(),
                                     "listeners": listener_pids(), "memavailable_bytes": memavailable(),
                                     "memory_psi_full_avg10_percent": psi_full_avg10(),
                                     "swapfree_bytes": swapfree(), "gpus": gpu_snapshot()}
        except Exception as exc:
            receipt["postflight_error"] = f"{type(exc).__name__}: {exc}"
        atomic_json(RECEIPT, receipt)
    print(json.dumps({"test_id": receipt["test_id"], "status": receipt["status"],
                      "error": receipt.get("error"), "receipt": str(RECEIPT)}, ensure_ascii=False))
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
