#!/usr/bin/env python3
"""Run one Q154 throughput arm with serial requests and memory/cleanup guards."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import signal
import socket
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
TASK = Path(__file__).resolve().parents[1]
LOCK_TOKEN = "2242863e-c78e-4fa9-9649-c1d1541f3919"
STRATA = Path("/media/cristian/Disco local/Models-eval/Q153-huihui-v2/runtime/control-0.1.51/bin/strata")
BASE_URL = "http://127.0.0.1:8350"
SIZES = (4096, 16384, 32512)
REPEATS = (1, 2, 3)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def lock_check() -> None:
    lock = json.loads((REPO / "WORK_QUEUE.lock").read_text(encoding="utf-8"))
    if lock.get("token") != LOCK_TOKEN or lock.get("task") != "Q146 resume justified VF-20261019-01 tests":
        raise RuntimeError("WORK_QUEUE.lock is no longer owned by this evaluation; stopping before inference")


def ancestor_pids() -> set[int]:
    out = {os.getpid()}
    pid = os.getppid()
    while pid > 1 and pid not in out:
        out.add(pid)
        try:
            stat = Path(f"/proc/{pid}/stat").read_text().split()
            pid = int(stat[3])
        except (OSError, ValueError, IndexError):
            break
    return out


def inference_processes() -> list[dict]:
    ignored = ancestor_pids()
    found = []
    proc = Path("/proc")
    for entry in proc.iterdir():
        if not entry.name.isdigit() or int(entry.name) in ignored:
            continue
        try:
            args = [x.decode(errors="replace") for x in (entry / "cmdline").read_bytes().split(b"\0") if x]
            if not args:
                continue
            joined = " ".join(args).casefold()
            executable = Path(args[0]).name.casefold()
            engine_runtime = "/runtime/components/engine/" in joined and executable == "strata"
            if "peritosoft" in joined or "perito-soft" in joined or "llama-server" in executable \
                    or engine_runtime or (executable == "strata" and len(args) > 1 and args[1] == "serve"):
                found.append({"pid": int(entry.name), "ppid": int((entry / "status").read_text().split("PPid:")[1].splitlines()[0]),
                              "argv": args})
        except (OSError, ValueError, IndexError):
            continue
    return found


def gpu_rows() -> list[dict]:
    cmd = ["nvidia-smi", "--query-gpu=index,name,memory.used,memory.free,temperature.gpu,utilization.gpu",
           "--format=csv,noheader,nounits"]
    raw = subprocess.check_output(cmd, text=True, timeout=10)
    rows = []
    for line in raw.splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) == 6:
            rows.append({"index": int(parts[0]), "name": parts[1], "memory_used_mib": int(parts[2]),
                         "memory_free_mib": int(parts[3]), "temperature_c": None if parts[4] == "[N/A]" else int(parts[4]),
                         "utilization_percent": None if parts[5] == "[N/A]" else int(parts[5])})
    return rows


def memory_snapshot() -> dict:
    mem = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith(("MemAvailable:", "SwapFree:")):
            key, value = line.split(":", 1)
            mem[key] = int(value.strip().split()[0])
    psi = {}
    for line in Path("/proc/pressure/memory").read_text().splitlines():
        fields = line.split()
        if fields:
            vals = dict(item.split("=", 1) for item in fields[1:] if "=" in item)
            psi[fields[0]] = {k: float(v) for k, v in vals.items() if k in ("avg10", "avg60", "avg300")}
    vm = {}
    for line in Path("/proc/vmstat").read_text().splitlines():
        k, _, v = line.partition(" ")
        if k in ("oom_kill", "pswpin", "pswpout"):
            vm[k] = int(v)
    return {"meminfo_kib": mem, "psi_memory_percent": psi, "vmstat_pages": vm}


def read_json(url: str, timeout: float = 5) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read())


def post_json(path: Path, timeout: float = 1800) -> tuple[int, dict, float]:
    payload = path.read_bytes()
    req = urllib.request.Request(BASE_URL + "/v1/chat/completions", data=payload,
                                 headers={"Content-Type": "application/json"}, method="POST")
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            code = response.status
            body = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        code, body = exc.code, {"error": exc.read().decode(errors="replace")}
    return code, body, time.perf_counter() - start


def oom_count(snapshot: dict) -> int:
    return snapshot.get("vmstat_pages", {}).get("oom_kill", 0)


class Guard:
    def __init__(self, out: Path, proc: subprocess.Popen, baseline_oom: int):
        self.out, self.proc, self.baseline_oom = out, proc, baseline_oom
        self.stop = threading.Event()
        self.abort_reason = None
        self.warning_noted = False
        self.samples = 0
        self.warn_streak = 0
        self.hard_streak = 0
        self.thread = threading.Thread(target=self.run, name="q154-memory-guard", daemon=True)
        self.file = (out / "memory-samples.jsonl").open("a", encoding="utf-8")

    def start(self):
        self.thread.start()

    def run(self):
        deadline = time.monotonic()
        while not self.stop.is_set():
            snap = memory_snapshot()
            gpus = gpu_rows()
            full = snap.get("psi_memory_percent", {}).get("full", {}).get("avg10", 0.0)
            some = snap.get("psi_memory_percent", {}).get("some", {}).get("avg10", 0.0)
            self.warn_streak = self.warn_streak + 1 if (full >= 20.0 or some >= 70.0) else 0
            self.hard_streak = self.hard_streak + 1 if (full >= 60.0 or some >= 80.0) else 0
            temps = [g["temperature_c"] for g in gpus if g["temperature_c"] is not None]
            sample = {"recorded_utc": utc_now(), "elapsed_s": round(time.monotonic() - START_MONOTONIC, 3),
                      "memory": snap, "gpus": gpus, "warning_streak": self.warn_streak,
                      "hard_stop_streak": self.hard_streak}
            self.file.write(json.dumps(sample, separators=(",", ":")) + "\n")
            self.file.flush()
            self.samples += 1
            if self.warn_streak >= 30 and not self.warning_noted:
                self.warning_noted = True
                print("MEMORY_GUARD_WARNING: 30 consecutive PSI warning samples; continuing under preregistered hard-stop rule.", flush=True)
            if self.hard_streak >= 15:
                self.abort_reason = "memory PSI hard stop sustained for 15 consecutive 10-second samples"
            elif oom_count(snap) > self.baseline_oom:
                self.abort_reason = "host oom_kill counter increased during the experiment"
            elif temps and max(temps) >= 85:
                self.abort_reason = "GPU temperature reached preregistered 85 C stop"
            if self.abort_reason:
                print("SAFETY_STOP: " + self.abort_reason, flush=True)
                try:
                    os.killpg(self.proc.pid, signal.SIGINT)
                except ProcessLookupError:
                    pass
                return
            deadline += 10
            self.stop.wait(max(0.0, deadline - time.monotonic()))
        self.file.close()

    def close(self):
        self.stop.set()
        self.thread.join(timeout=15)
        if not self.file.closed:
            self.file.close()


START_MONOTONIC = time.monotonic()


def assert_port_free() -> None:
    with socket.socket() as sock:
        sock.settimeout(0.3)
        if sock.connect_ex(("127.0.0.1", 8350)) == 0:
            raise RuntimeError("127.0.0.1:8350 already has a listener; refusing to share or replace it")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=("control", "candidate"), required=True)
    args = ap.parse_args()
    arm = args.arm
    config = TASK / "configs" / ("astra-rco-iq2xs-32k.json" if arm == "control" else "huihui-v2-32k.json")
    model = json.loads(config.read_text(encoding="utf-8"))["model_name"]
    input_root = TASK / "inputs/throughput"
    manifest = json.loads((input_root / "manifest.json").read_text(encoding="utf-8"))
    output = TASK / "runs" / arm / "throughput"
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError(f"refusing to overwrite existing run evidence: {output}")

    lock_check()
    existing = inference_processes()
    if existing:
        raise RuntimeError("unreviewed PeritoSoft/inference processes present; refusing to start: " + json.dumps(existing))
    assert_port_free()
    gpu_before = gpu_rows()
    if len(gpu_before) != 2 or any("3090" not in row["name"] for row in gpu_before):
        raise RuntimeError(f"dual RTX 3090 preflight failed: {gpu_before}")
    mem_before = memory_snapshot()
    oom_before = oom_count(mem_before)
    (output / "preflight.json").write_text(json.dumps({"recorded_utc": utc_now(), "lock_token": LOCK_TOKEN,
        "processes": existing, "port_free": True, "gpu": gpu_before, "memory": mem_before}, indent=2) + "\n")

    plan = subprocess.run([str(STRATA), "serve", "--profile", str(config), "--host", "127.0.0.1",
                           "--port", "8350", "--offline", "--plan", "--output", "json"],
                          cwd=str(STRATA.parent.parent), capture_output=True, text=True, timeout=45)
    (output / "offline-plan.json").write_text(json.dumps({"exit_code": plan.returncode,
        "stdout": plan.stdout, "stderr": plan.stderr}, indent=2) + "\n")
    if plan.returncode != 0 or "--gpu" not in plan.stdout or "0,1" not in plan.stdout:
        raise RuntimeError("offline serve plan failed or did not explicitly select both GPUs")

    private = Path(tempfile.mkdtemp(prefix=f"q154-{arm}-"))
    os.chmod(private, 0o700)
    ready = private / "ready.json"
    log_path = output / "server.log"
    env = os.environ.copy()
    env["STRATA_PREFILL_CPU_SHARE"] = "0"
    start = time.perf_counter()
    log = log_path.open("wb")
    proc = subprocess.Popen([str(STRATA), "serve", "--profile", str(config), "--host", "127.0.0.1",
                             "--port", "8350", "--offline", "--ready-file", str(ready),
                             "--shutdown-timeout", "90"], cwd=str(STRATA.parent.parent), env=env,
                            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    guard = Guard(output, proc, oom_before)
    guard.start()
    measurements = []
    cleanup = {}
    try:
        deadline = time.monotonic() + 1200
        ready_payload = None
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(f"server exited before ready with status {proc.returncode}")
            if guard.abort_reason:
                raise RuntimeError(guard.abort_reason)
            try:
                ready_payload = json.loads(ready.read_text(encoding="utf-8"))
                models = read_json(BASE_URL + "/v1/models")
                break
            except (OSError, urllib.error.URLError, json.JSONDecodeError):
                time.sleep(3)
        if ready_payload is None:
            raise TimeoutError("server did not publish its owned ready file within 20 minutes")
        gpu_loaded = gpu_rows()
        deltas = [after["memory_used_mib"] - before["memory_used_mib"]
                  for before, after in zip(gpu_before, gpu_loaded)]
        if len(deltas) != 2 or min(deltas) < 1024:
            raise RuntimeError(f"dual-GPU allocation gate failed (<1 GiB per card): {deltas}")
        print(json.dumps({"event":"READY","arm":arm,"load_s":round(time.perf_counter()-start,3),
                          "gpu_allocation_delta_mib":deltas,"ready":ready_payload},separators=(",",":")),flush=True)
        (output / "ready.json").write_text(json.dumps({"recorded_utc":utc_now(),"load_s":time.perf_counter()-start,
            "ready":ready_payload,"models":models,"gpu_before":gpu_before,"gpu_loaded":gpu_loaded,
            "gpu_allocation_delta_mib":deltas},indent=2)+"\n")

        warmup = input_root / manifest["warmup"][f"request_{arm}"]
        code, body, wall = post_json(warmup, timeout=300)
        (output / "warmup-response.json").write_text(json.dumps({"http_status":code,"wall_s":wall,"body":body},indent=2)+"\n")
        if code != 200:
            raise RuntimeError(f"warmup request failed HTTP {code}: {body}")

        sizes = SIZES if arm == "control" else tuple(reversed(SIZES))
        for size in sizes:
            for rep in REPEATS:
                item = next(x for x in manifest["fixtures"] if x["prompt_tokens_expected"] == size
                            and x["key"] == f"{size}-rep{rep}")
                variant = item["variants"][0]
                primary = input_root / variant[f"request_{arm}"]
                attempts = []
                chosen = None
                for attempt, request_path in enumerate((primary, input_root / item["variants"][1][f"request_{arm}"]), start=1):
                    code, body, wall = post_json(request_path)
                    metrics = read_json(BASE_URL + "/metrics?requests=all")
                    latest = metrics.get("requests", [{}])[0] if metrics.get("requests") else {}
                    usage = body.get("usage", {}) if isinstance(body, dict) else {}
                    cached = usage.get("prompt_tokens_details", {}).get("cached_tokens")
                    timing = body.get("timings", {}) if isinstance(body, dict) else {}
                    prompt_actual = usage.get("prompt_tokens")
                    is_valid = (code == 200 and prompt_actual == size and cached == 0
                                and timing.get("cache_n") == 0 and latest.get("reused") == 0
                                and latest.get("prompt_total") == size)
                    record = {"attempt":attempt,"request":str(request_path.relative_to(TASK)),
                              "http_status":code,"wall_s":round(wall,4),"body":body,
                              "server_history_latest":latest,"valid":is_valid}
                    attempts.append(record)
                    if is_valid:
                        chosen = {"size":size,"replicate":rep,"recorded_utc":utc_now(),"attempts":attempts,
                                  "ttft_s":latest.get("first_engine_token_s"),
                                  "prefill_tok_s":timing.get("prompt_per_second"),"prefill_ms":timing.get("prompt_ms"),
                                  "decode_tok_s":timing.get("predicted_per_second"),"decode_ms":timing.get("predicted_ms"),
                                  "prompt_tokens":prompt_actual,"cached_tokens":cached,
                                  "completion_tokens":usage.get("completion_tokens"),
                                  "finish_reason":body.get("choices",[{}])[0].get("finish_reason"),
                                  "e2e_wall_s":round(wall,4),"valid":True}
                        break
                    if attempt == 1:
                        print(f"INVALID_PRIMARY {arm} {size} rep{rep}: cache/count gate failed; using preregistered fresh-nonce fallback",flush=True)
                if chosen is None:
                    chosen = {"size":size,"replicate":rep,"recorded_utc":utc_now(),"attempts":attempts,
                              "valid":False,"failure":"both preregistered request variants failed token/cache validity"}
                measurements.append(chosen)
                path = output / f"{size}-rep{rep}.json"
                path.write_text(json.dumps(chosen,indent=2)+"\n")
                with (output / "progress.jsonl").open("a",encoding="utf-8") as stream:
                    stream.write(json.dumps(chosen,separators=(",",":"))+"\n")
                print(json.dumps({"event":"REQUEST","arm":arm,"size":size,"replicate":rep,
                                  "valid":chosen["valid"],"ttft_s":chosen.get("ttft_s"),
                                  "prefill_tok_s":chosen.get("prefill_tok_s"),"decode_tok_s":chosen.get("decode_tok_s"),
                                  "e2e_wall_s":chosen.get("e2e_wall_s"),"completion_tokens":chosen.get("completion_tokens")},
                                 separators=(",",":")),flush=True)
                if guard.abort_reason:
                    raise RuntimeError(guard.abort_reason)
        result={"iteration":"Q154","arm":arm,"model":model,"recorded_utc":utc_now(),
                "load_s":round(time.perf_counter()-start,3),"warmup":"PASS_UNSCORED",
                "measurements":measurements,"valid_cells":sum(bool(m.get("valid")) for m in measurements),
                "guard_warning":guard.warning_noted,"guard_samples":guard.samples,
                "abort_reason":guard.abort_reason}
        (output/"summary.json").write_text(json.dumps(result,indent=2)+"\n")
        print(json.dumps({"event":"ARM_COMPLETE","arm":arm,"valid_cells":result["valid_cells"],
                          "guard_warning":result["guard_warning"]},separators=(",",":")),flush=True)
    finally:
        try:
            os.killpg(proc.pid, signal.SIGINT)
            try:
                proc.wait(timeout=100)
                cleanup["sigint_exit_code"] = proc.returncode
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=15)
                    cleanup["sigterm_exit_code"] = proc.returncode
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait(timeout=10)
                    cleanup["sigkill_exit_code"] = proc.returncode
        except ProcessLookupError:
            cleanup["already_exited"] = True
        guard.close()
        log.close()
        time.sleep(2)
        with socket.socket() as sock:
            sock.settimeout(0.3)
            port_free = sock.connect_ex(("127.0.0.1",8350)) != 0
        cleanup.update({"port_free": port_free,
                        "remaining_inference_processes": inference_processes(),
                        "gpu_after": gpu_rows(),"memory_after":memory_snapshot(),"ready_file_removed":not ready.exists()})
        (output/"cleanup.json").write_text(json.dumps({"recorded_utc":utc_now(),**cleanup},indent=2)+"\n")
        if cleanup.get("remaining_inference_processes") or not cleanup.get("port_free"):
            raise RuntimeError("cleanup gate failed; do not load the next model")
    print(json.dumps({"event":"CLEANUP_COMPLETE","arm":arm,"cleanup":cleanup},separators=(",",":")),flush=True)


if __name__ == "__main__":
    main()
