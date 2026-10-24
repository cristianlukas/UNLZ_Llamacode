#!/usr/bin/env python3
"""Read-only verification of the already-prepared HyperQwen checkpoint."""
from __future__ import annotations
import hashlib
import json
import os
import struct
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode")
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-101"
Q85 = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-85/receipts"
LOCK_TOKEN = "f5f2021d-5cbf-4ae2-a0c9-878f53871914"
MODEL = Path("/media/cristian/HDD extra/Modelos-eval/Q85-HyperQwen/models/Qwen3.8-27B-W4A16-AutoRound")
DRAFTER = Path("/media/cristian/HDD extra/Modelos-eval/Q85-HyperQwen/models/Qwen3.8-27B-DFlash2-W4A16")
IMAGE = "ghcr.io/syv-ai/hyperqwen@sha256:0acd4b9625473e51c9bab56406c30814bc0d0d7e0a38deb408c62664b5a77669"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def safetensors_header(path: Path) -> dict:
    size = path.stat().st_size
    with path.open("rb") as f:
        prefix = f.read(8)
        if len(prefix) != 8:
            raise ValueError(f"short safetensors prefix: {path.name}")
        header_len = struct.unpack("<Q", prefix)[0]
        if header_len > size - 8:
            raise ValueError(f"header exceeds file: {path.name}")
        header = json.loads(f.read(header_len))
    end = 0
    for name, meta in header.items():
        if name == "__metadata__":
            continue
        start, stop = meta["data_offsets"]
        if start < 0 or stop < start:
            raise ValueError(f"invalid data offsets: {path.name}:{name}")
        end = max(end, stop)
    if 8 + header_len + end > size:
        raise ValueError(f"tensor data exceeds file: {path.name}")
    return header


def main() -> int:
    lock = json.loads((ROOT / "WORK_QUEUE.lock").read_text())
    if lock.get("task_id") != "Q-20261024-VF-ITERATION-101" or lock.get("token") != LOCK_TOKEN:
        raise SystemExit("Q101 lock mismatch")

    raw = json.loads((Q85 / "base-model-hash-verification.json").read_text())
    post = json.loads((Q85 / "q85-dual-gpu-runtime-preflight.json").read_text())
    drafter_pin = json.loads((Q85 / "drafter-hash-and-tmp-bind.json").read_text())
    if post["candidate"].get("verifyNoServer") != "verify: OK (0 failures)":
        raise SystemExit("prior pinned post-prepare verifier is not a pass")

    # These three files are intentionally rewritten by prepare/; check the
    # preserved source bytes and fingerprint the live prepared outputs separately.
    backups = {
        "model-00006-of-00007.safetensors": ".bak_embed",
        "model-00007-of-00007.safetensors": ".bak",
        "model_extra_tensors.safetensors": ".bak-mtp",
    }
    checks = []
    for item in raw["fileChecks"]:
        name = item["path"]
        live = MODEL / name
        source = live if name not in backups else Path(str(live) + backups[name])
        print("ASSET_HASH_START", source.name, flush=True)
        if not source.is_file() or source.stat().st_size != item["sizeBytes"]:
            raise SystemExit(f"pinned source size mismatch: {source}")
        got = sha256(source)
        if got != item["sha256"]:
            raise SystemExit(f"pinned source SHA mismatch: {source}")
        record = {
            "sourcePath": str(source),
            "sourceSizeBytes": source.stat().st_size,
            "sourceSha256": got,
            "matchesPinnedRawSource": True,
        }
        if name in backups:
            if not live.is_file():
                raise SystemExit(f"prepared model file missing: {live}")
            st = live.stat()
            record["preparedPath"] = str(live)
            record["preparedSizeBytes"] = st.st_size
            record["preparedModeOctal"] = oct(st.st_mode & 0o777)
            record["preparedReadableByHostUser"] = os.access(live, os.R_OK)
            record["preparedMtimeUtc"] = datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat().replace("+00:00", "Z")
        checks.append({"pinnedFile": name, **record})

    dr = drafter_pin["file"]
    dr_path = DRAFTER / dr["path"]
    print("ASSET_HASH_START", dr_path.name, flush=True)
    if dr_path.stat().st_size != dr["sizeBytes"] or sha256(dr_path) != dr["sha256"]:
        raise SystemExit("pinned DFlash2 drafter fingerprint mismatch")

    helper = TASK / "runner/q101_verify_prepared_checkpoint_container.py"
    command = [
        "ionice", "-c", "3", "docker", "run", "--rm", "--pull=never",
        "--network=none", "--read-only", "--pids-limit=64",
        "-v", f"{MODEL}:/models:ro", "-v", f"{DRAFTER}:/drafter:ro",
        "-v", f"{helper}:/verify.py:ro", "-e", "Q101_PREPARE_VERIFY_UTC=2026-10-24T15:07:30Z",
        "--entrypoint=/app/venv/bin/python", IMAGE, "-B", "/verify.py",
    ]
    container = subprocess.run(command, check=True, capture_output=True, text=True)
    structural = json.loads(container.stdout)

    report = {
        "taskId": "Q-20261024-VF-ITERATION-101",
        "capturedAtUtc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "pass",
        "lockOwned": True,
        "method": "read-only source fingerprint check; preserved .bak* files are used only for HyperQwen's three documented in-place rewrites; prepared shard reads are delegated to a root-in-container read-only check because prepare outputs are root-owned",
        "rawModelRevision": raw["revision"],
        "rawSourceChecks": checks,
        "q85PostPrepareVerificationReceipt": str(Q85 / "q85-dual-gpu-runtime-preflight.json"),
        "priorPostPrepareVerification": post["candidate"]["verifyNoServer"],
        "preparedCheckpointStructuralVerification": structural,
        "drafter": {"path": str(dr_path), "sizeBytes": dr_path.stat().st_size, "sha256": dr["sha256"], "matchesPinned": True},
        "gpuInferenceStarted": False,
        "modelFilesModified": False,
    }
    out = TASK / "receipts/q101-attempt10-source-fingerprint-verification.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
