#!/usr/bin/env python3
"""Extract NVIDIA's block-FP8 MTP experts into Strata's BF16 MTP input layout.

The Qwen3.8 NVFP4 checkpoint stores the dense MTP tensors as BF16 and its 512
routed draft experts as E4M3 FP8 with a BF16 inverse scale for each 128x128
block. Strata's mtp_pack.py accepts BF16 tensors and expects gate/up fused on
the output axis. This script applies the checkpoint's inverse scales, rounds
the recovered FP8 values to BF16, and writes the expected fused expert files.

It does not modify the downloaded checkpoint. The resulting BF16 files are an
intermediate for mtp_pack.py; they preserve the checkpoint's FP8 weights after
dequantization, rounded to BF16.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch
from safetensors import safe_open

EXPERTS = 512
BLOCK = 128
DENSE_SHARDS = ("model-00009-of-00010.safetensors", "model-00010-of-00010.safetensors")
AUX_SHARD = "model-fp8-mtp-ple.safetensors"
EXPERT_ROOT = "mtp.layers.0.mlp.experts"


def tensor_bytes(t: torch.Tensor) -> bytes:
    if t.dtype != torch.bfloat16:
        raise TypeError(f"expected BF16, got {t.dtype}")
    return t.contiguous().view(torch.int16).cpu().numpy().astype("<i2", copy=False).tobytes()


def dequant_block_fp8(weight: torch.Tensor, scale_inv: torch.Tensor) -> torch.Tensor:
    if weight.dtype != torch.float8_e4m3fn:
        raise TypeError(f"expected float8_e4m3fn, got {weight.dtype}")
    if scale_inv.dtype != torch.bfloat16:
        raise TypeError(f"expected BF16 weight_scale_inv, got {scale_inv.dtype}")
    rows, cols = weight.shape
    if rows % BLOCK or cols % BLOCK or tuple(scale_inv.shape) != (rows // BLOCK, cols // BLOCK):
        raise ValueError(f"unexpected FP8 block shape {tuple(weight.shape)} / {tuple(scale_inv.shape)}")
    scales = scale_inv.float().repeat_interleave(BLOCK, 0).repeat_interleave(BLOCK, 1)
    out = (weight.float() * scales).to(torch.bfloat16)
    if not torch.isfinite(out.float()).all():
        raise ValueError("non-finite value after FP8 block dequantization")
    return out


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 24), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", type=Path, required=True, help="completed NVIDIA checkpoint directory")
    ap.add_argument("--out", type=Path, required=True, help="BF16 tensor directory for tools/mtp_pack.py")
    ap.add_argument("--revision", default="fc694b5", help="source revision recorded in the receipt")
    args = ap.parse_args()
    index = json.loads((args.model / "model.safetensors.index.json").read_text())["weight_map"]
    names = sorted(k for k in index if k.startswith("mtp."))
    expert_names = [k for k in names if k.startswith(EXPERT_ROOT + ".")]
    dense_names = [k for k in names if k not in expert_names and not k.endswith("weight_scale_inv")]
    if len(expert_names) != EXPERTS * 6:
        raise ValueError(f"expected 6 checkpoint tensors for each of {EXPERTS} experts; found {len(expert_names)}")

    out = args.out
    tensors = out / "tensors"
    tensors.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    with (safe_open(args.model / DENSE_SHARDS[0], framework="pt") as shard9,
          safe_open(args.model / DENSE_SHARDS[1], framework="pt") as shard10,
          safe_open(args.model / AUX_SHARD, framework="pt") as aux):
        dense_by_file = {DENSE_SHARDS[0]: shard9, DENSE_SHARDS[1]: shard10}
        for name in dense_names:
            source_shard = index[name]
            if source_shard not in dense_by_file:
                raise ValueError(f"unexpected dense MTP shard for {name}: {source_shard}")
            raw = tensor_bytes(dense_by_file[source_shard].get_tensor(name))
            path = tensors / f"{name}.bin"
            path.write_bytes(raw)
            manifest.append(dict(name=name, shard=source_shard, dtype="BF16",
                                 shape=list(dense_by_file[source_shard].get_slice(name).get_shape()),
                                 bytes=len(raw), file=str(path.relative_to(out)), sha256=hashlib.sha256(raw).hexdigest()))

        gate_path = tensors / f"{EXPERT_ROOT}.gate_up_proj.bin"
        down_path = tensors / f"{EXPERT_ROOT}.down_proj.bin"
        with gate_path.open("wb") as gate_file, down_path.open("wb") as down_file:
            for expert in range(EXPERTS):
                prefix = f"{EXPERT_ROOT}.{expert}."
                gate = dequant_block_fp8(aux.get_tensor(prefix + "gate_proj.weight"),
                                         aux.get_tensor(prefix + "gate_proj.weight_scale_inv"))
                up = dequant_block_fp8(aux.get_tensor(prefix + "up_proj.weight"),
                                       aux.get_tensor(prefix + "up_proj.weight_scale_inv"))
                down = dequant_block_fp8(aux.get_tensor(prefix + "down_proj.weight"),
                                         aux.get_tensor(prefix + "down_proj.weight_scale_inv"))
                if tuple(gate.shape) != (640, 2560) or tuple(up.shape) != (640, 2560) or tuple(down.shape) != (2560, 640):
                    raise ValueError(f"unexpected MTP expert {expert} projection shapes")
                gate_file.write(tensor_bytes(torch.cat((gate, up), dim=0)))
                down_file.write(tensor_bytes(down))
                if (expert + 1) % 64 == 0:
                    print(f"dequantized MTP experts {expert + 1}/{EXPERTS}", flush=True)

    manifest.extend([
        dict(name=f"{EXPERT_ROOT}.gate_up_proj", shard=AUX_SHARD, dtype="BF16",
             shape=[EXPERTS, 1280, 2560], bytes=gate_path.stat().st_size,
             file=str(gate_path.relative_to(out)), sha256=sha256(gate_path)),
        dict(name=f"{EXPERT_ROOT}.down_proj", shard=AUX_SHARD, dtype="BF16",
             shape=[EXPERTS, 2560, 640], bytes=down_path.stat().st_size,
             file=str(down_path.relative_to(out)), sha256=sha256(down_path)),
    ])
    manifest.sort(key=lambda x: x["name"])
    (out / "mtp-manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    receipt = {"source": "nvidia/Qwen3.8-Flash-Next-NVFP4", "revision": args.revision,
               "source_aux": AUX_SHARD, "mtp_source_experts": "E4M3 FP8, BF16 inverse scales, 128x128 blocks",
               "conversion": "multiply each FP8 value by its block weight_scale_inv; round to BF16; concatenate gate then up on output axis",
               "experts": EXPERTS, "block": BLOCK, "mtp_tensor_count_packed": len(manifest)}
    (out / "mtp-source.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"wrote {len(manifest)} Strata MTP tensors to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
