#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import os
import pathlib
import shutil
import time

ROOT = pathlib.Path("/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode")
ATTEMPT = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261022-VF-ITERATION-30/attempts/flashnext-bcb2-outputcap-01"
SOURCE_RUNTIME = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261021-VF-ITERATION-26/attempts/bcb-01/work/isolated-runtime"
RUNTIME = ATTEMPT / "work/isolated-runtime"
SOURCE_SUITE = SOURCE_RUNTIME / "data/LlamaCode/LlamaCode/benchmarks/custom/05c28394-11d0-41fe-a55f-b3cb69db9c15.json"
SUITE_ID = "vf-q30-bcb2-token-cap-diagnostic"
SUITE_NAME = "VF focused code-output-cap diagnostic"
LOCK_TOKEN = "4c3101a9-2bca-4b9d-9ab9-acc1024075a5"
SOURCE_SHA256 = "42771136b447b7b5619e04a1ea211f663222cd6752ca38d995083b5a4d207574"
PROMPT_ID = "BigCodeBench/765"


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    lock = json.loads((ROOT / "WORK_QUEUE.lock").read_text())
    if lock.get("token") != LOCK_TOKEN:
        raise SystemExit("Lock token changed; no runtime preparation performed")
    if not SOURCE_SUITE.is_file() or not SOURCE_RUNTIME.is_dir():
        raise SystemExit("Pinned BCB8 source runtime/suite missing")
    if RUNTIME.exists():
        raise SystemExit(f"Refusing to overwrite existing diagnostic runtime: {RUNTIME}")
    if sha(SOURCE_SUITE) != SOURCE_SHA256:
        raise SystemExit("Pinned BCB8 suite hash changed")

    suite = json.loads(SOURCE_SUITE.read_text(encoding="utf-8"))
    original = next((p for p in suite.get("prompts", []) if p.get("id") == PROMPT_ID), None)
    if original is None or original.get("maxTokens") != 1200:
        raise SystemExit("Pinned prompt missing or its original maxTokens is not 1200")

    shutil.copytree(SOURCE_RUNTIME, RUNTIME, copy_function=shutil.copy2)
    variant = {
        "id": SUITE_ID,
        "name": SUITE_NAME,
        "description": "Single-item diagnostic cloned from the pinned BCB8 task; only maxTokens changes from 1200 to 2400. This is not a full BCB stage.",
        "source": "VF-20261019-01 / Q30 focused diagnostic; derived from pinned local BCB8 fixture; no external download",
        "prompts": [copy.deepcopy(original)],
    }
    variant["prompts"][0]["maxTokens"] = 2400
    payload = (json.dumps(variant, ensure_ascii=False, indent=2) + "\n").encode()
    custom_dir = RUNTIME / "data/LlamaCode/LlamaCode/benchmarks/custom"
    custom_dir.mkdir(parents=True, exist_ok=True)
    (custom_dir / f"{SUITE_ID}.json").write_bytes(payload)
    (ATTEMPT / "work/diagnostic-suite.json").write_bytes(payload)

    receipt = {
        "prepared_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "prepared_no_inference",
        "lock_token": LOCK_TOKEN,
        "source_suite": str(SOURCE_SUITE),
        "source_suite_sha256": sha(SOURCE_SUITE),
        "source_prompt_id": PROMPT_ID,
        "source_max_tokens": original["maxTokens"],
        "variant_suite_id": SUITE_ID,
        "variant_suite_name": SUITE_NAME,
        "variant_max_tokens": variant["prompts"][0]["maxTokens"],
        "variant_suite_sha256": hashlib.sha256(payload).hexdigest(),
        "original_acceptance_preserved": variant["prompts"][0].get("acceptance") == original.get("acceptance"),
        "model_runtime_profile_unchanged": True,
        "runtime_copy_source": str(SOURCE_RUNTIME),
        "runtime_copy": str(RUNTIME),
        "downloaded": False,
        "server_started": False,
        "model_requests": 0,
        "gpu_used": False,
    }
    out = ATTEMPT / "receipts/preparation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
