#!/usr/bin/env python3
"""Detached, bounded Q173 8K screen for Speedy v0.4.0 / Flash-Next IQ3_S."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path("/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode")
BASE = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261116-Q225-SPEEDY040-IQ3S-Q173/profiles/speedy-iq3s"
SRC = pathlib.Path("/media/cristian/Disco local/Modelos-eval/Q225-Speedy-v0.4.0/source")
ENGINE = pathlib.Path("/media/cristian/Disco local/Modelos-eval/Q225-Speedy-v0.4.0/engine-v0.4.0/strata")
ARCHIVE = pathlib.Path("/media/cristian/Disco local/Modelos-eval/Q225-Speedy-v0.4.0/strata-linux-x64-rtx30.zip")
MODEL = pathlib.Path("/media/cristian/HDD extra/LlamaCode-evals/Q211-qwen38-iq3s-mtp/target/IQ3_S")
PACK = pathlib.Path("/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode/artifacts/evaluacion-modelos-llamacode/Q-20261116-Q225-SPEEDY040-IQ3S-Q173/profiles/speedy-iq3s/generated-pack/iq3_s")
MTP = pathlib.Path("/media/cristian/Disco local/Models/ASTRA-IQ3_S-calibrated-20261006/data/mtp/rt")
CONFIG = BASE / "config/speedy-iq3s-dual-q173-8k-a19-cache6000-spec2-pw0-mtp-off.json"
ENGINE_LOG = BASE / "logs/strata-engine-a19.log"
PACK_RECEIPT = BASE / "receipts/pack-build-a03.json"
EXPECTED_CONFIG_SHA256 = "bd2b2c9a3c9d47a8b5165fa649a04dc905b1e7265df2eadf8e4b1e8ec905819c"
EXPECTED_PACK_RECEIPT_SHA256 = "e8f0264b5ed77e9c18e5781b41a9678c47a57fad590ba144b499a2865fc0278b"
EXPECTED_PRIOR_ARTIFACT_RECEIPT_SHA256 = "51b75c64d871c34fd3cad997b44f7cca53ff7d53a5669195c9bf572fb078decf"
EXPECTED_ARTIFACT_STAT_SHA256 = "21e60517a80582a96e378f3918ce5d23e8b50464c12b8cdbae1e5569931205ff"
EXPECTED_PACK_FILES = {
    "dense.bin": (1538035200, "d2af3d8331e5c7a1985d1d589747230f9d56719a6d33c7cddc9ee6b81cde6b13"),
    "index.txt": (93685, "b2a014878c3b61d6a6f915e194055a5e68ede34f9465dd1cb13249d902f008ac"),
    "native_experts.txt": (3304, "d9ac2dfa3ee63c55c9c6a6db26f72da0cec0ee41733f007e5cbbbba71617aa5d"),
    "conversions.json": (306, "51df3cd6ffd0d38c2da8e2d3a95a604b4a96c20b06fc639a9bf477282a42b86a"),
    "tokenizer/vocab.json": (5737005, "4ba64f0332abcfb0b600b7df1537d1e836e68009d5fb7cdb77339738dc6365c4"),
    "tokenizer/chat_template.jinja": (9993, "12827f24b742ea4e80cdc12dbcf9622227056b9f797252a3149263d4f9aaadce"),
    "tokenizer/tokenizer.json": (541, "c0bd435efbc6c3b28964b47999afe16c4ad268c7c7c4e8cb3af410796a6f30bf"),
    "tokenizer/merges.txt": (3353258, "4ba698529766c7a2f5052083ea15cdf2485577f5237a332ee291054eb11e3332"),
    "tokenizer/token_type.json": (744960, "5088c8c298fc06af8382ddb3b76c888703ac2634e82263b97eedcc2ad202738b"),
}
BENCHY = pathlib.Path("/home/cristian/.cache/q173-llama-benchy-0.4.0/bin/llama-benchy")
PORT = 18489
HOST = "127.0.0.1"
UNIT = "q225-speedy-iq3s-q173-8k-a19.service"
SERVER_PYTHON = BASE / "venv/bin/python"
LOCK_TOKEN = "d9029f6b-c649-4291-b0be-f14d77dc737e"
HELPER = "vram-quarantine@GPU-af6de4b3-6497-b7f8-796d-6d69cba422e6.service"
CUDA_LIB = "/media/cristian/Disco local/LlamaCode-cache/relocated-home-cache/cuda-13.0.1/targets/x86_64-linux/lib"
UUIDS = {0: "GPU-af6de4b3-6497-b7f8-796d-6d69cba422e6", 1: "GPU-5b9f385f-6a8e-b802-f69c-e62a71c91049"}
EXPECTED = {
    "archive_sha256": "3827c0ca8ddd19dd757bd87c57426c01db63048c1b1574cba83edc3a8bac9fad",
    "model_shards": [
        ("Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf", 54817524224,
         "4c1eb2ceb4915e1192f4f386021897bde56a97f40a0bb78bb86465e0f7d2aca3"),
        ("Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00002-of-00002.gguf", 28800138432,
         "316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113"),
    ],
    "draft": {
        "dense.bin": (116099072, "c724dc0b0822ada5d2977bf5bde821605feabaa64ea2e0045b67ca656329070a"),
        "experts.bin": (707788800, "09398406be61f1f54c93861f449e48b8df0bfccbc9ec9b2b7636775a6ea9244f"),
        "draft_vocab.bin": (425196, "b1e1d3a7a9e4bf862dcd5923ce661fb59bbd07907e594df5cf86a62ac235cb91"),
    },
}
SERVER: subprocess.Popen | None = None


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path: pathlib.Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def run(argv: list[str], timeout: int = 20) -> str:
    return subprocess.run(argv, check=True, text=True, capture_output=True, timeout=timeout).stdout.strip()


def mem_available_kib() -> int:
    return next(int(x.split()[1]) for x in pathlib.Path("/proc/meminfo").read_text().splitlines()
                if x.startswith("MemAvailable:"))


def pressure_avg10() -> float:
    line = next(x for x in pathlib.Path("/proc/pressure/memory").read_text().splitlines()
                if x.startswith("some "))
    return float(next(x.split("=", 1)[1] for x in line.split() if x.startswith("avg10=")))


def gpu_snapshot() -> dict:
    raw = run(["nvidia-smi", "--query-gpu=index,uuid,name,memory.used,memory.total,temperature.gpu",
               "--format=csv,noheader,nounits"])
    gpus = {}
    for line in raw.splitlines():
        i, uuid, name, used, total, temp = [x.strip() for x in line.split(",")]
        gpus[int(i)] = {"uuid": uuid, "name": name, "memory_used_mib": int(used),
                        "memory_total_mib": int(total), "temperature_c": int(temp)}
    comp = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,gpu_uuid,used_gpu_memory",
                           "--format=csv,noheader,nounits"], text=True, capture_output=True, timeout=10)
    apps = {0: [], 1: []}
    if comp.returncode == 0 and comp.stdout.strip():
        for line in comp.stdout.splitlines():
            pid, uuid, used = [x.strip() for x in line.split(",")]
            idx = next((i for i, expected in UUIDS.items() if uuid == expected), None)
            if idx is not None:
                apps[idx].append({"pid": int(pid), "used_mib": int(used)})
    return {"gpus": gpus, "compute": apps, "mem_available_kib": mem_available_kib(),
            "memory_pressure_avg10": pressure_avg10()}


def owned_pid(pid: int) -> bool:
    try:
        cg = pathlib.Path(f"/proc/{pid}/cgroup").read_text()
        return UNIT in cg
    except OSError:
        return False


def foreign_servers() -> list[dict]:
    keywords = ("llama-server", "ninfer-serve", "vllm", "aphrodite", "sglang", "ollama",
                "koboldcpp", "xolotl", "strata", "lmstudio", "lm-studio")
    found = []
    for proc in pathlib.Path("/proc").iterdir():
        if not proc.name.isdigit() or owned_pid(int(proc.name)):
            continue
        try:
            argv = proc.joinpath("cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            comm = proc.joinpath("comm").read_text().strip()
        except OSError:
            continue
        if comm.lower() in {"bash", "sh", "dash", "zsh", "fish"}:
            continue
        lower = (comm + " " + argv).lower()
        python_server = comm.lower().startswith(("python", "pypy")) and any(
            marker in lower for marker in ("-m serve.server", "serve/server.py", "vllm.",
                "aphrodite.", "sglang.", "llama_cpp.server", "koboldcpp", "xolotl", "--engine strata"))
        if any(x in comm.lower() for x in keywords) or python_server:
            found.append({"pid": int(proc.name), "comm": comm, "argv": argv[:280]})
    return found


def preflight(allow_own: bool = False) -> dict:
    lock = json.loads((ROOT / "WORK_QUEUE.lock").read_text(encoding="utf-8"))
    if lock.get("token") != LOCK_TOKEN or lock.get("task") != "Q-20261103-VF-RESUME-202":
        raise RuntimeError("el WORK_QUEUE.lock cambió de propietario")
    snap = gpu_snapshot()
    if any(snap["gpus"].get(i, {}).get("uuid") != UUIDS[i] or "RTX 3090" not in snap["gpus"][i]["name"]
           for i in (0, 1)):
        raise RuntimeError("el par/orden de RTX 3090 no coincide con el preregistro")
    if any(snap["gpus"][i]["temperature_c"] >= 82 for i in (0, 1)):
        raise RuntimeError("temperatura de GPU >=82 C")
    if snap["mem_available_kib"] < 32 * 1024 * 1024 or snap["memory_pressure_avg10"] >= 10:
        raise RuntimeError("barrera de memoria (MemAvailable <32 GiB o PSI avg10 >=10%)")
    topo = run(["nvidia-smi", "topo", "-p2p", "r"])
    if topo.count("OK") < 2:
        raise RuntimeError("P2P bidireccional no está OK")
    cmdline = pathlib.Path("/proc/cmdline").read_text()
    target = "gpu_unlock.targets=0000:01:00.0,0000:03:00.0"
    if target not in cmdline:
        raise RuntimeError("gpu_unlock no apunta a ambas RTX 3090")
    helper = run(["systemctl", "show", "-p", "StatusText", HELPER])
    if run(["systemctl", "is-active", HELPER]) != "active" or "1636/1636 frames held, 0 pending" not in helper:
        raise RuntimeError("la cuarentena de VRAM de la ASUS no está completa/activa")
    journal = run(["journalctl", "-b", "-u", "3090-helper-verify-boot.service", "--no-pager", "-o", "cat"])
    if journal.rfind("PASS: reserva ASUS") < journal.rfind("FAIL:"):
        raise RuntimeError("3090 HELPER no tiene PASS en este arranque")
    foreign = foreign_servers()
    if foreign:
        raise RuntimeError("servidor de inferencia ajeno detectado: " + json.dumps(foreign))
    if not allow_own and any(snap["compute"][i] for i in (0, 1)):
        raise RuntimeError("hay CUDA compute ajeno antes del lanzamiento: " + json.dumps(snap["compute"]))
    return {"timestamp_utc": utc(), "snapshot": snap, "p2p": "OK bidireccional",
            "gpu_unlock": target, "asus_reservation": helper, "boot_helper": "PASS", "foreign_servers": foreign}


def verify_artifacts() -> dict:
    config_payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    configured_log = pathlib.Path(config_payload.get("log", ""))
    if not configured_log.is_absolute() or configured_log != ENGINE_LOG:
        raise RuntimeError("engine log path must be absolute and match ENGINE_LOG")
    args = config_payload.get("args", [])
    if "--expert-cache" not in args or args[args.index("--expert-cache") + 1] != "6000":
        raise RuntimeError("A19 requires --expert-cache 6000 slots")
    if "--spec" not in args or args[args.index("--spec") + 1] != "2":
        raise RuntimeError("A19 requires native-IQ-compatible --spec 2")
    if config_payload.get("mtp") is not False or config_payload.get("drafting") != "off":
        raise RuntimeError("A19 requires explicit MTP/draft off")
    if any(flag in args for flag in ("--mtp", "--spec-min-p", "--batch-mtp", "--draft", "--draft-model")):
        raise RuntimeError("A19 config still contains draft-layer flags")
    if "--spec" not in args:
        raise RuntimeError("A19 must preserve prompt-lookup --spec")
    config_hash = hashlib.sha256(CONFIG.read_bytes()).hexdigest()
    if config_hash != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"SHA256 mismatch del config: {CONFIG}")
    pack_receipt_hash = hashlib.sha256(PACK_RECEIPT.read_bytes()).hexdigest()
    if pack_receipt_hash != EXPECTED_PACK_RECEIPT_SHA256:
        raise RuntimeError("SHA256 mismatch del recibo de pack A03")
    pack_receipt = json.loads(PACK_RECEIPT.read_text(encoding="utf-8"))
    if pack_receipt.get("status") != "PASS":
        raise RuntimeError("el recibo de pack A03 no dice PASS")
    prior_path = BASE / "receipts/preflight-a04-artifacts.json"
    prior_hash = hashlib.sha256(prior_path.read_bytes()).hexdigest()
    if prior_hash != EXPECTED_PRIOR_ARTIFACT_RECEIPT_SHA256:
        raise RuntimeError("recibo de verificación de artefactos A04 cambió")
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    if prior.get("status") != "PASS":
        raise RuntimeError("la verificación de artefactos A04 no pasó")
    stat_path = BASE / "receipts/artifact-stat-snapshot-a04.json"
    stat_hash = hashlib.sha256(stat_path.read_bytes()).hexdigest()
    if stat_hash != EXPECTED_ARTIFACT_STAT_SHA256:
        raise RuntimeError("snapshot de identidad de archivos A04 cambió")
    stat_snapshot = json.loads(stat_path.read_text(encoding="utf-8"))
    checked = []
    for expected in stat_snapshot["files"]:
        path = pathlib.Path(expected["path"])
        st = path.stat()
        current = {"bytes": st.st_size, "device": st.st_dev, "inode": st.st_ino, "mtime_ns": st.st_mtime_ns}
        pinned = {key: expected[key] for key in current}
        if current != pinned:
            raise RuntimeError(f"identidad/metadata de artefacto cambió desde A04: {path}")
        checked.append({"path": str(path), "bytes": st.st_size, "sha256": expected["sha256"]})
    return {"verified": prior["verified"], "verified_pack": prior["verified_pack"],
            "artifact_hashes_reused_from": str(prior_path), "artifact_stat_identity_checked": checked,
            "artifact_receipt_sha256": prior_hash, "artifact_stat_snapshot_sha256": stat_hash,
            "pack_receipt_sha256": pack_receipt_hash, "config_sha256": config_hash,
            "runtime_executable_sha256": next(x["sha256"] for x in prior["verified"] if x["path"] == str(ENGINE))}


def health() -> dict:
    with urllib.request.urlopen(f"http://{HOST}:{PORT}/health", timeout=3) as response:
        return {"status": response.status, "body": response.read().decode(errors="replace")[:300]}


def bench(seed: int) -> tuple[dict, dict]:
    tag = f"seed-{seed}"
    result_path = BASE / f"runs/a19-q173-8k-{tag}.json"
    events_path = BASE / f"runs/a19-q173-8k-{tag}-events.jsonl"
    log_path = BASE / f"logs/a19-q173-8k-{tag}.log"
    argv = [str(BENCHY), "--base-url", f"http://{HOST}:{PORT}/v1", "--model", "qwen3.8-flash-next-iq3_s",
            "--tokenizer", str(PACK / "tokenizer"), "--pp", "8192", "--tg", "128", "--exact-tg",
            "--depth", "0", "--concurrency", "1", "--runs", "1", "--latency-mode", "generation",
            "--no-cache", "--no-adapt-prompt", "--no-warmup", "--skip-coherence", "--exit-on-first-fail",
            "--extra-body", f"temperature=0.6,top_p=0.95,top_k=20,min_p=0.0,repetition_penalty=1.0,presence_penalty=0.0,seed={seed}",
            "--format", "json", "--save-result", str(result_path), "--emit-progress", str(events_path)]
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(argv, cwd=SRC, stdout=log, stderr=subprocess.STDOUT, env=os.environ.copy())
        samples = []
        while proc.poll() is None:
            pre = preflight(allow_own=True)
            samples.append(pre["snapshot"])
            # Strata auto-reloads after a crashed engine. Stop the benchmark client and
            # unwind the parent server immediately on the known CUDA verify OOM.
            if ENGINE_LOG.is_file() and "verify: instantiate: out of memory" in ENGINE_LOG.read_text(encoding="utf-8", errors="replace"):
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
                raise RuntimeError(f"Strata verifier OOM detected; client stopped before auto-reload loop; see {ENGINE_LOG}")
            time.sleep(5)
    if proc.returncode != 0:
        raise RuntimeError(f"llama-benchy seed {seed} rc={proc.returncode}; revisar {log_path}")
    data = json.loads(result_path.read_text(encoding="utf-8"))
    bench_obj = data["benchmarks"][0]
    if int(bench_obj.get("prompt_size", -1)) != 8192 or int(bench_obj.get("response_size", -1)) != 128:
        raise RuntimeError(f"token count incorrecto en seed {seed}: {bench_obj}")
    return {"seed": seed, "benchmark": bench_obj, "raw_result": str(result_path),
            "events": str(events_path), "log": str(log_path), "samples": samples}, data


def stop_server() -> dict:
    global SERVER
    if SERVER is None:
        return {"status": "not_started"}
    pid = SERVER.pid
    if SERVER.poll() is None:
        SERVER.send_signal(signal.SIGINT)
        try:
            SERVER.wait(timeout=30)
        except subprocess.TimeoutExpired:
            SERVER.terminate()
            try:
                SERVER.wait(timeout=10)
            except subprocess.TimeoutExpired:
                SERVER.kill()
                SERVER.wait(timeout=5)
    time.sleep(2)
    return {"server_pid": pid, "server_rc": SERVER.returncode,
            "port_free": socket.socket().connect_ex((HOST, PORT)) != 0,
            "compute_after_stop": gpu_snapshot()["compute"]}


def main() -> int:
    global SERVER
    BASE.mkdir(parents=True, exist_ok=True)
    initial = preflight()
    hashes = verify_artifacts()
    write_json(BASE / "receipts/preflight-a19-artifacts.json", {"status": "PASS", "preflight": initial, **hashes})
    if not socket.socket().connect_ex((HOST, PORT)):
        raise RuntimeError(f"puerto {PORT} ocupado")
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = CUDA_LIB + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
    env.update(json.loads(CONFIG.read_text(encoding="utf-8"))["env"])
    if not SERVER_PYTHON.is_file():
        raise RuntimeError(f"falta el entorno Python aislado: {SERVER_PYTHON}")
    cmd = [str(SERVER_PYTHON), "-m", "serve.server", "--engine", "strata", "--config", str(CONFIG),
           "--host", HOST, "--port", str(PORT), "--gpu", "0,1", "--offline",
           "--ready-file", str(BASE / "receipts/server-ready-a19.json")]
    server_log = (BASE / "logs/server-a19.log").open("w", encoding="utf-8")
    SERVER = subprocess.Popen(cmd, cwd=SRC, env=env, stdout=server_log, stderr=subprocess.STDOUT)
    start = time.monotonic()
    started_utc = utc()
    readiness = None
    while time.monotonic() - start < 2700:
        preflight(allow_own=True)
        if SERVER.poll() is not None:
            raise RuntimeError(f"servidor propio terminó rc={SERVER.returncode}; log={BASE/'logs/server-a19.log'}")
        try:
            readiness = health()
            if readiness["status"] == 200:
                with urllib.request.urlopen(f"http://{HOST}:{PORT}/v1/models", timeout=10) as r:
                    readiness["models"] = json.loads(r.read())
                break
        except Exception:
            pass
        print(json.dumps({"event": "loading", "elapsed_s": round(time.monotonic()-start, 1),
                          "mem_available_gib": round(mem_available_kib()/1024/1024, 1),
                          "gpu": gpu_snapshot()}, ensure_ascii=False), flush=True)
        time.sleep(10)
    if not readiness or readiness.get("status") != 200:
        raise TimeoutError("el servidor no llegó a readiness en 2700 s")
    snap = gpu_snapshot()
    for idx in (0, 1):
        if not snap["compute"][idx] or not all(owned_pid(x["pid"]) for x in snap["compute"][idx]):
            raise RuntimeError(f"no se pudo atribuir compute propio en GPU{idx}: {snap['compute'][idx]}")
    init_s = round(time.monotonic()-start, 3)
    write_json(BASE / "receipts/server-ready-a19.json", {"status": "PASS", "ready_seconds": init_s,
                "health": readiness, "gpu": snap, "command": cmd, "config": str(CONFIG)})
    results = []
    for seed in (42, 43, 44):
        if SERVER.poll() is not None:
            raise RuntimeError("servidor se cerró antes de completar las tres corridas")
        item, _ = bench(seed)
        results.append(item)
        write_json(BASE / "runs/a19-progress.json", {"status": "RUNNING", "completed": len(results),
                    "expected": 3, "results": results, "timestamp_utc": utc()})
        print(json.dumps({"event": "run_complete", "seed": seed,
                          "result": item["benchmark"]}, ensure_ascii=False), flush=True)
    stop = stop_server()
    p_values = [float(x["benchmark"]["pp_throughput"]["mean"]) for x in results]
    d_values = [float(x["benchmark"]["tg_throughput"]["mean"]) for x in results]
    p_mean = sum(p_values) / len(p_values)
    d_mean = sum(d_values) / len(d_values)
    valid = len(results) == 3 and stop.get("port_free") and not any(stop.get("compute_after_stop", {}).values())
    continue_ladder = valid and p_mean >= 1000 and d_mean >= 90
    final = {"test_id": "Q225-SPEEDY040-IQ3S-Q173-8K-SCREEN", "status": "PASS" if valid else "FAIL_CLEANUP",
             "started_utc": started_utc,
             "finished_utc": utc(), "model": "Qwen3.8 Flash-Next RCO IQ3_S", "runtime": "Speedy v0.4.0 / Strata",
             "context_tokens": 8192, "output_tokens": 128, "gpu": snap, "server_ready_seconds_diagnostic": init_s,
             "results": results, "prefill_mean_tok_s": p_mean, "decode_mean_tok_s": d_mean,
             "worker_cleanup": stop,
             "decision_gate": {"continue_ladder": continue_ladder, "prefill_min_tok_s": 1000,
                               "decode_min_tok_s": 90, "reason": "screen gate only; not a superiority or adoption claim"},
             "note": "No Q172/quality measured. No superiority claim until an exact matched local Strata control is compared."}
    write_json(BASE / "RESULTS.json", final)
    with (BASE / "RESULTS.md").open("a", encoding="utf-8") as results_md:
        results_md.write("\n## A19 final — Speedy v0.4.0 / IQ3_S Q173-style 8K screen\n\n"
            "Preregistered three-seed throughput screen; quality is N/D. See `RESULTS.json` for raw values and receipts.\n\n"
            f"Status: **{final['status']}**. Server startup {init_s} s (diagnostic only, not a cold/hot pair).\n\n"
            "This screen is not a superiority claim; compare only after a same-quant Strata baseline with matching firmware/runtime and harness.\n")
    print(json.dumps({"event": "finished", "status": final["status"], "result": str(BASE/"RESULTS.json"),
                      "cleanup": stop}, ensure_ascii=False), flush=True)
    return 0 if valid else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BaseException as exc:
        info = {"test_id": "Q225-SPEEDY040-IQ3S-Q173-8K-SCREEN", "status": "FAIL_OR_ABORTED",
                "timestamp_utc": utc(), "error": f"{type(exc).__name__}: {exc}",
                "server_pid": SERVER.pid if SERVER else None,
                "log": str(BASE / "logs/server-a19.log")}
        try:
            if SERVER and SERVER.poll() is None:
                SERVER.send_signal(signal.SIGINT)
                try:
                    SERVER.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    SERVER.terminate()
                    SERVER.wait(timeout=10)
            write_json(BASE / "RESULTS.json", info)
        finally:
            print(json.dumps(info, ensure_ascii=False), flush=True)
        if isinstance(exc, SystemExit):
            raise
        raise
