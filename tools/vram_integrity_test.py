"""On-device VRAM integrity test for NVIDIA GPUs (Windows and Linux).

Fills almost all free VRAM of each GPU with known data, reads it back and
counts words that changed. Everything is generated and compared on the GPU,
so PCIe/risers/bifurcation are NOT involved: a failure here is the GPU's own
memory (or its memory controller).

Also prints the fault fingerprint used in
docs/gpu0-asus-3090-vram-fault-20260927.md:
  - bad words per pattern (a stuck-at-1 fault passes the all-ones pattern),
  - histogram of stuck bits on the all-zeros pattern,
  - most common stride between bad words.

Requirements: Python 3.10+ and a CUDA build of PyTorch, e.g.
  pip install torch --index-url https://download.pytorch.org/whl/cu126

usage:
  python tools/vram_integrity_test.py              # every GPU
  python tools/vram_integrity_test.py --gpu 0      # one GPU (PCI bus order)
  python tools/vram_integrity_test.py --reserve-mib 3072 --json out.json

Close games/browsers/LLM servers first: only free VRAM is tested.
"""
import argparse
import collections
import json
import os
import platform
import time

# nvidia-smi numbers GPUs by PCI bus; CUDA's default order is "fastest first".
os.environ.setdefault("CUDA_DEVICE_ORDER", "PCI_BUS_ID")

import torch  # noqa: E402

WORDS = 64 * 2**20  # int32 words per block = 256 MiB
PATTERNS = [("random_a", None), ("random_b", None), ("0x55AA55AA", 0x55AA55AA),
            ("0x2A55AA55", 0x2A55AA55), ("all_ones", -1), ("all_zeros", 0)]


def fill(block, pattern, value, seed):
    if value is None:
        gen = torch.Generator(device=block.device).manual_seed(seed)
        block.random_(generator=gen)
    else:
        block.fill_(value)


def test_gpu(dev, reserve_mib):
    torch.cuda.set_device(dev)
    props = torch.cuda.get_device_properties(dev)
    bus = getattr(props, "pci_bus_id", None)
    free = torch.cuda.mem_get_info(dev)[0] - reserve_mib * 2**20
    nblk = max(0, free // (WORDS * 4) - 1)
    blocks = [torch.empty(WORDS, dtype=torch.int32, device=dev) for _ in range(nblk)]
    scratch = torch.empty(WORDS, dtype=torch.int32, device=dev)
    per_pattern = collections.Counter()
    blocks_hit = set()
    stuck_bits = collections.Counter()
    bad_offsets = []
    t0 = time.time()
    for p, (name, value) in enumerate(PATTERNS):
        for i, b in enumerate(blocks):
            fill(b, name, value, i * 7 + p)
        torch.cuda.synchronize(dev)
        for i, b in enumerate(blocks):
            fill(scratch, name, value, i * 7 + p)
            mask = b != scratch
            n = int(mask.sum())
            if not n:
                continue
            per_pattern[name] += n
            blocks_hit.add(i)
            if name == "all_zeros":
                idx = mask.nonzero().flatten()
                bad_offsets.extend((i * WORDS + int(o)) for o in idx.tolist())
                for v in b[idx].tolist():
                    v &= 0xFFFFFFFF
                    for k in range(32):
                        if v >> k & 1:
                            stuck_bits[k] += 1
    bad_offsets.sort()
    strides = collections.Counter(b - a for a, b in zip(bad_offsets, bad_offsets[1:])).most_common(3)
    mask = 0
    for k in stuck_bits:
        mask |= 1 << k
    result = dict(
        gpu=dev, name=props.name, pci_bus_id=bus,
        tested_gib=round(nblk * WORDS * 4 / 2**30, 2), seconds=round(time.time() - t0, 1),
        bad_words_total=sum(per_pattern.values()), bad_words_per_pattern=dict(per_pattern),
        blocks_hit=len(blocks_hit), stuck_bits_on_zeros=dict(sorted(stuck_bits.items())),
        stuck_mask=hex(mask) if mask else None,
        common_strides_words=strides,
    )
    del blocks, scratch
    torch.cuda.empty_cache()
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpu", type=int, action="append", help="GPU index in PCI bus order (repeatable)")
    ap.add_argument("--reserve-mib", type=int, default=2048, help="VRAM left free for the desktop/driver")
    ap.add_argument("--json", help="write results to this file")
    args = ap.parse_args()
    if not torch.cuda.is_available():
        raise SystemExit("PyTorch has no CUDA: install a CUDA build (see the docstring).")
    gpus = args.gpu if args.gpu is not None else list(range(torch.cuda.device_count()))
    print(f"host={platform.node()} os={platform.platform()} torch={torch.__version__} cuda={torch.version.cuda}")
    results = []
    for dev in gpus:
        r = test_gpu(dev, args.reserve_mib)
        results.append(r)
        verdict = "PASS" if r["bad_words_total"] == 0 else "FAIL"
        print(f"[{verdict}] GPU{dev} {r['name']} bus={r['pci_bus_id']} tested={r['tested_gib']} GiB x6 "
              f"bad_words={r['bad_words_total']} per_pattern={r['bad_words_per_pattern']} "
              f"stuck_mask={r['stuck_mask']} stuck_bits={r['stuck_bits_on_zeros']} "
              f"strides={r['common_strides_words']} ({r['seconds']} s)", flush=True)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(dict(host=platform.node(), os=platform.platform(), results=results), f, indent=1)
    raise SystemExit(1 if any(r["bad_words_total"] for r in results) else 0)


if __name__ == "__main__":
    main()
