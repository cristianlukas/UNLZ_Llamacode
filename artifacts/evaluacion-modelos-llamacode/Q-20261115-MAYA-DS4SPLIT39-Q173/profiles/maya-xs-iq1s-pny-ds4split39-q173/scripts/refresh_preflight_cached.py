#!/usr/bin/env python3
"""Refresh Q209 live gates without rereading the 276 GB model shards."""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_q173 as q  # noqa: E402


def main() -> int:
    q.check_lock()
    prereg = q.prereg()
    prior_path = q.RECEIPTS / "preflight.json"
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    if prior.get("status") != "PASS" or prior.get("lock_token") != q.TOKEN:
        raise RuntimeError("missing prior successful full-hash preflight")
    if prior.get("runner_sha256") != q.sha(pathlib.Path(q.__file__)):
        raise RuntimeError("runner changed since full-hash preflight")
    assets = prior.get("assets", {})
    if assets.get("full_shard_hashes_verified") is not True or assets.get("total_model_bytes") != 276626308260:
        raise RuntimeError("prior full-shard hash receipt is not suitable for cache reuse")

    shards = sorted(q.MODEL_ROOT.glob(q.MODEL_PREFIX + "*.gguf"))
    old_shards = assets.get("model_shards", [])
    if len(shards) != 5 or len(old_shards) != 5:
        raise RuntimeError("model shard count changed")
    current_shards = []
    identity_fields = ("path", "resolved_path", "bytes", "mtime_ns", "inode", "device")
    for index, (path, old) in enumerate(zip(shards, old_shards)):
        current = q.file_snapshot(path)
        if any(current.get(key) != old.get(key) for key in identity_fields):
            raise RuntimeError(f"shard identity changed since its verified full SHA-256: {path}")
        if old.get("sha256") != q.SHARD_HASHES[index]:
            raise RuntimeError(f"cached full-SHA receipt does not match pinned shard {index + 1}")
        current_shards.append({**current, "sha256_reused_from_verified_full_hash": old["sha256"]})

    expected_support = [
        (q.MAYA_ENGINE, "b4d00bcb0dc1b6680158749941601e79f669af6b1ae5c2d28c5feaa0cc72df17"),
        (q.MAYA_RUN, "95087759f61e581888fadbb3e9f84128197a7d908628658ccb65e3298e82748b"),
        (q.TOKENIZER, "c90dfa01249db1be4245780a052ede752e1361c612ac6d08e2bdada7d599476b"),
        (q.BENCHY, "e8a892fe937d5ae1b6a43c31e8cb286ce4774f70396f62ab71008c9ddb0a01a1"),
        (q.CONFIG, prereg["runtime"]["config_sha256"]),
    ]
    prior_support = assets.get("supporting_files", [])
    if len(prior_support) != len(expected_support):
        raise RuntimeError("supporting-asset receipt count changed")
    supporting = []
    for (path, expected), old in zip(expected_support, prior_support):
        if not path.is_file():
            raise RuntimeError(f"missing pinned supporting asset: {path}")
        current = {**q.file_snapshot(path), "sha256": q.sha(path)}
        if current["sha256"] != expected or old.get("sha256") != expected:
            raise RuntimeError(f"supporting asset hash mismatch: {path}")
        supporting.append(current)

    gates = q.live_gates()
    if not gates["port_free"] or gates["foreign_inference_servers"]:
        raise RuntimeError("inference server or occupied port found; no service was stopped")
    if gates["gpus"]["compute_apps"]:
        raise RuntimeError("GPU compute apps present; no process was stopped")
    gpu_by_uuid = {gpu["uuid"]: gpu for gpu in gates["gpus"]["gpus"]}
    if q.ASUS_UUID not in gpu_by_uuid or q.PNY_UUID not in gpu_by_uuid:
        raise RuntimeError("the preregistered ASUS and PNY 3090s are not both present")
    if gates["memory"]["mem_available_bytes"] < q.HOST_FLOOR_BYTES:
        raise RuntimeError("MemAvailable below registered 16 GiB floor")

    stat = __import__("os").statvfs(q.OUT.parent)
    free = stat.f_bavail * stat.f_frsize
    if free < 1_000_000_000:
        raise RuntimeError(f"insufficient output space: {free}")

    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    receipt = {
        "schema": "llamacode.q209-cached-preflight-refresh.v1",
        "status": "PASS",
        "timestamp_utc": now,
        "task": "Q209-MAYA-DS4SPLIT39-Q173",
        "lock_token": q.TOKEN,
        "purpose": "fresh live preflight for Q173 131072x1; no full 276 GB shard reread",
        "previous_full_hash_preflight_utc": prior.get("timestamp_utc"),
        "previous_runner_sha256": prior.get("runner_sha256"),
        "current_runner_sha256": q.sha(pathlib.Path(q.__file__)),
        "model_shard_validation": {
            "status": "PASS_IDENTITY_UNCHANGED_REUSED_PRIOR_FULL_SHA",
            "shards": current_shards,
            "verified_bytes": sum(item["bytes"] for item in current_shards),
        },
        "supporting_files_rehashed": supporting,
        "live_gates": gates,
        "no_other_compute_apps": True,
        "no_foreign_inference_servers": True,
        "port_free": True,
        "output_free_bytes": free,
        "next_context_tokens": 131072,
        "gpu_inference_started": False,
    }
    out = q.RECEIPTS / "preflight-cached-refresh-131072.json"
    q.write_json(out, receipt)
    # Keep the runner's cached-asset guard grounded in the previous full-SHA
    # receipt while updating the live gate snapshot it will use for this run.
    prior["cached_preflight_refresh"] = str(out)
    prior["cached_preflight_refresh_utc"] = now
    prior["live_gate_refresh"] = gates
    prior["output_free_bytes_refresh"] = free
    q.write_json(prior_path, prior)
    q.write_json(q.OUT / "receipts/preflight.json", prior)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
