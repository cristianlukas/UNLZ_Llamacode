#!/usr/bin/env python3
"""Read-only structural/fingerprint check, run as root inside pinned image without GPU/network."""
import hashlib
import json
import os
import struct
from datetime import datetime, timezone
from pathlib import Path

MODEL = Path("/models")
DRAFTER = Path("/drafter")
DRAFTER_SHA = "ec26996e6a0745ab5edb857117220ce1e219ad524f71e6e149b703804947d8e7"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def header(path):
    size = path.stat().st_size
    with path.open("rb") as f:
        prefix = f.read(8)
        if len(prefix) != 8:
            raise ValueError(f"short safetensors prefix: {path.name}")
        n = struct.unpack("<Q", prefix)[0]
        if n > size - 8:
            raise ValueError(f"safetensors header exceeds file: {path.name}")
        data = json.loads(f.read(n))
    end = 0
    for name, meta in data.items():
        if name == "__metadata__":
            continue
        start, stop = meta["data_offsets"]
        if start < 0 or stop < start:
            raise ValueError(f"invalid tensor offset: {path.name}:{name}")
        end = max(end, stop)
    if 8 + n + end > size:
        raise ValueError(f"tensor payload exceeds file: {path.name}")
    return data


def main():
    config = json.loads((MODEL / "config.json").read_text())
    index = json.loads((MODEL / "model.safetensors.index.json").read_text())
    weights = index["weight_map"]
    if config.get("quantization_config", {}).get("quant_method") != "compressed-tensors":
        raise ValueError("unexpected prepared quantization config")
    required = [
        "lm_head.weight_packed",
        "model.language_model.embed_tokens.weight_packed",
        "mtp.layers.0.mlp.down_proj.weight_packed",
        "mtp.draft_lm_head.weight_packed",
    ]
    missing_keys = [key for key in required if key not in weights]
    if missing_keys:
        raise ValueError(f"prepared index missing required keys: {missing_keys}")

    shard_checks = []
    latest_mtime = 0.0
    for name in sorted(set(weights.values())):
        path = MODEL / name
        if not path.is_file():
            raise ValueError(f"index references missing shard: {name}")
        tensors = header(path)
        absent = [key for key, shard in weights.items() if shard == name and key not in tensors]
        if absent:
            raise ValueError(f"index keys absent from safetensors header: {name}: {absent[:4]}")
        st = path.stat()
        latest_mtime = max(latest_mtime, st.st_mtime)
        shard_checks.append({
            "path": str(path),
            "sizeBytes": st.st_size,
            "modeOctal": oct(st.st_mode & 0o777),
            "headerTensorCount": len(tensors),
            "sha256": sha256(path) if name in {
                "model-00006-of-00007.safetensors",
                "model-00007-of-00007.safetensors",
                "model_extra_tensors.safetensors",
            } else None,
        })

    checkpoint_files = [p for p in MODEL.iterdir() if p.is_file()]
    checkpoint_files.extend(p for p in DRAFTER.iterdir() if p.is_file())
    latest_mtime = max(latest_mtime, *(p.stat().st_mtime for p in checkpoint_files))

    draft_vocab = MODEL / "mtp_draft_vocab_ids.pt"
    if not draft_vocab.is_file() or draft_vocab.stat().st_size == 0:
        raise ValueError("prepared MTP draft vocabulary id map missing")
    drafter = DRAFTER / "model.safetensors"
    if not drafter.is_file() or sha256(drafter) != DRAFTER_SHA:
        raise ValueError("DFlash2 drafter hash mismatch")

    q85_verify = datetime.fromisoformat(os.environ["Q101_PREPARE_VERIFY_UTC"].replace("Z", "+00:00"))
    latest = datetime.fromtimestamp(latest_mtime, timezone.utc)
    if latest > q85_verify:
        raise ValueError(f"model shard changed after Q85 verification: {latest.isoformat()}")

    report = {
        "status": "pass",
        "containerUser": os.getuid(),
        "network": "none",
        "rootFilesystem": "read-only",
        "gpuDevicesPassed": False,
        "prepareRun": False,
        "quantMethod": config["quantization_config"]["quant_method"],
        "requiredPackedKeysPresent": required,
        "allIndexKeysPresentInHeaders": True,
        "allTensorOffsetsWithinFiles": True,
        "latestModelShardMtimeUtc": latest.isoformat().replace("+00:00", "Z"),
        "unchangedSinceQ85Verification": True,
        "modelShards": shard_checks,
        "draftVocabIdsBytes": draft_vocab.stat().st_size,
        "drafter": {"path": str(drafter), "sizeBytes": drafter.stat().st_size, "sha256": DRAFTER_SHA, "matchesPinned": True},
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
