#!/usr/bin/env python3
"""Restore only the pinned HyperQwen checkpoint into the Q85 evaluation folder."""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
TASK = Path(__file__).resolve().parents[1]
LOCK_TASK = "Q146 resume justified VF-20261019-01 tests"
LOCK_TOKEN = "2242863e-c78e-4fa9-9649-c1d1541f3919"
MODEL_DIR = Path("/media/cristian/HDD extra/Modelos-eval/Q85-HyperQwen/models/Qwen3.8-27B-W4A16-AutoRound")
HF_HOME = Path("/media/cristian/HDD extra/Modelos-eval/Q-20261027-VF-ITERATION-167/hf-home")
HASH_RECEIPT = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-85/receipts/base-model-hash-verification.json"
PROGRESS = TASK / "receipts/download-progress.json"
REPO = "dbirks/Qwen3.8-27B-W4A16-AutoRound"
REVISION = "1f05c441c4e64ae0549de44fa9ea5a6d43610314"
MIN_HDD_FREE = 40 * 1024**3
MIN_ROOT_FREE = 8 * 1024**3


def utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(data: dict) -> None:
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    temporary = PROGRESS.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with temporary.open("rb") as stream:
        os.fsync(stream.fileno())
    temporary.replace(PROGRESS)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    lock = json.loads((ROOT / "WORK_QUEUE.lock").read_text(encoding="utf-8"))
    if lock.get("task") != LOCK_TASK or lock.get("token") != LOCK_TOKEN:
        raise SystemExit("evaluation umbrella lock ownership changed; refusing download")
    source = json.loads(HASH_RECEIPT.read_text(encoding="utf-8"))
    if source.get("revision") != REVISION or source.get("repo") != REPO:
        raise SystemExit("pinned Q85 source receipt differs")
    checks = source.get("fileChecks", [])
    expected_total = sum(int(row["sizeBytes"]) for row in checks)
    disk = {"/": shutil.disk_usage("/").free,
            "/media/cristian/HDD extra": shutil.disk_usage("/media/cristian/HDD extra").free}
    if disk["/"] < MIN_ROOT_FREE or disk["/media/cristian/HDD extra"] - expected_total < MIN_HDD_FREE:
        raise SystemExit("storage preflight failed; refusing candidate download")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    HF_HOME.mkdir(parents=True, exist_ok=True)
    state = {"taskId": "Q-20261027-VF-ITERATION-167", "atUtc": utc(), "status": "DOWNLOADING",
             "repo": REPO, "revision": REVISION, "destination": str(MODEL_DIR),
             "expectedFiles": len(checks), "expectedBytes": expected_total,
             "diskFreeBeforeBytes": disk, "hashesVerified": False}
    write_json(state)

    env = os.environ.copy()
    for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        env.pop(name, None)
    env.update({"HF_HOME": str(HF_HOME), "HF_HUB_CACHE": str(HF_HOME / "hub"),
                "HF_XET_CACHE": str(HF_HOME / "xet"), "HF_HUB_DISABLE_TELEMETRY": "1",
                "HF_HUB_DISABLE_IMPLICIT_TOKEN": "1", "PYTHONUNBUFFERED": "1"})
    command = ["/home/cristian/.local/bin/hf", "download", REPO,
               "--revision", REVISION, "--local-dir", str(MODEL_DIR), "--max-workers", "3"]
    process = subprocess.run(command, env=env, check=False)
    state.update({"atUtc": utc(), "downloadExitCode": process.returncode})
    if process.returncode:
        state["status"] = "DOWNLOAD_FAILED"
        write_json(state)
        return process.returncode

    verified = []
    for row in checks:
        path = MODEL_DIR / row["path"]
        if not path.is_file():
            state.update({"atUtc": utc(), "status": "VERIFY_FAILED", "missingFile": row["path"]})
            write_json(state)
            return 2
        actual_size = path.stat().st_size
        actual_hash = sha256(path)
        verified.append({"path": row["path"], "sizeBytes": actual_size, "sha256": actual_hash,
                         "sizeMatches": actual_size == int(row["sizeBytes"]),
                         "sha256Matches": actual_hash == row["sha256"]})
        if not verified[-1]["sizeMatches"] or not verified[-1]["sha256Matches"]:
            state.update({"atUtc": utc(), "status": "VERIFY_FAILED", "fileChecks": verified})
            write_json(state)
            return 3
    disk_after = {"/": shutil.disk_usage("/").free,
                  "/media/cristian/HDD extra": shutil.disk_usage("/media/cristian/HDD extra").free}
    if disk_after["/media/cristian/HDD extra"] < MIN_HDD_FREE:
        state.update({"atUtc": utc(), "status": "POST_DOWNLOAD_STORAGE_FAILED",
                      "diskFreeAfterBytes": disk_after, "fileChecks": verified})
        write_json(state)
        return 4
    state.update({"atUtc": utc(), "status": "DOWNLOADED_AND_HASH_VERIFIED",
                  "diskFreeAfterBytes": disk_after, "fileChecks": verified,
                  "actualBytes": sum(row["sizeBytes"] for row in verified), "hashesVerified": True})
    write_json(state)
    print(json.dumps({"status": state["status"], "fileCount": len(verified),
                      "actualBytes": state["actualBytes"], "destination": str(MODEL_DIR)}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
