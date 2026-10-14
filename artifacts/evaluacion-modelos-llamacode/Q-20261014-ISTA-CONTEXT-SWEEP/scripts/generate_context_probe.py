#!/usr/bin/env python3
"""Build a deterministic, synthetic long-context retrieval fixture for Strata."""
import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path


FACTS = [
    ("case-5172", "invoice_ref", "INV-Q7L4-92"),
    ("case-6803", "dock_code", "DOCK-N4-813"),
    ("case-1048", "sensor_value", "18.375 kPa"),
    ("case-9351", "release_tag", "rel-7f2c9b"),
    ("case-2264", "extension", "x-4816"),
    ("case-7490", "warehouse_bin", "B-19-R6"),
    ("case-3815", "contractor_ref", "CTR-008-AX"),
    ("case-8627", "batch_code", "BT-4M-7731"),
    ("case-2906", "incident_state", "awaiting-inspection"),
    ("case-4439", "checksum", "sha256:9c13a8d0e6f274b1"),
]

TEMPLATES = [
    "Dispatch note {n}: route {route} reached {site} at {hour}; operator {person} logged {status}. Ref {ref}.",
    "Maintenance record {n}: asset {asset} inspected by {person}; pressure {pressure}; outcome {status}; ticket {ref}.",
    "Archive entry {n}: department {dept}, owner {person}, priority {priority}, region {site}, tracking {ref}.",
    "Shipment {n}: carrier {carrier}, pallet {pallet}, destination {site}, seal {seal}, received {hour} UTC.",
    "Support summary {n}: service {service}, symptom {symptom}, assigned {person}, resolution {status}, case {ref}.",
    "Lab observation {n}: sample {sample}, instrument {asset}, reading {pressure}, quality flag {status}, note {ref}.",
]


def load_tokenizer(tokenizer_dir: Path):
    import strata_tokenizer as ST

    vocab = json.loads((tokenizer_dir / "vocab.json").read_text(encoding="utf-8"))
    tokens = [None] * len(vocab)
    for token, token_id in vocab.items():
        tokens[token_id] = token
    merges = (tokenizer_dir / "merges.txt").read_text(encoding="utf-8").split("\n")
    token_types = json.loads((tokenizer_dir / "token_type.json").read_text(encoding="utf-8"))
    return ST.Tokenizer(tokens, merges, token_types)


def filler_line(rng: random.Random, n: int) -> str:
    template = rng.choice(TEMPLATES)
    values = {
        "n": f"R-{n:06d}",
        "route": rng.choice(["north-4", "delta-8", "coastal-2", "inland-7", "meridian-5"]),
        "site": rng.choice(["Lujan", "Quilmes", "Bahia", "Rosario", "Mendoza", "Cordoba"]),
        "person": rng.choice(["M. Alvarez", "S. Pereira", "J. Ibarra", "L. Acosta", "R. Benitez"]),
        "status": rng.choice(["verified", "deferred", "queued", "closed", "review-required"]),
        "ref": f"{rng.choice(['AX','QZ','MP','TR'])}-{rng.randrange(100000,999999)}",
        "asset": f"{rng.choice(['pump','valve','meter','relay'])}-{rng.randrange(100,999)}",
        "pressure": f"{rng.randrange(100,9900)/100:.2f} {rng.choice(['kPa','bar','psi'])}",
        "dept": rng.choice(["logistics", "finance", "field-ops", "laboratory", "support"]),
        "priority": rng.choice(["low", "normal", "high", "urgent"]),
        "carrier": rng.choice(["Andes Freight", "Rio Cargo", "Pampa Transit", "Delta Parcel"]),
        "pallet": f"P-{rng.randrange(1000,9999)}-{rng.choice('ABCDEFGH')}",
        "seal": f"S{rng.randrange(1000000,9999999)}",
        "hour": f"{rng.randrange(24):02d}:{rng.randrange(60):02d}",
        "service": rng.choice(["catalog", "billing", "inventory", "identity", "telemetry"]),
        "symptom": rng.choice(["slow response", "duplicate event", "stale cache", "missing field", "late retry"]),
        "sample": f"LAB-{rng.randrange(10000,99999)}-{rng.choice('XYZ')}",
    }
    return template.format(**values)


def build_chunk(tokenizer, segment: int, target_tokens: int, line_base: int) -> str:
    rng = random.Random(4242 + segment * 100_003)
    n = max(1, target_tokens // 23)
    best = ""
    best_delta = math.inf
    for _ in range(8):
        rng = random.Random(4242 + segment * 100_003)
        lines = [filler_line(rng, line_base + i) for i in range(n)]
        candidate = "\n".join(lines) + "\n"
        count = len(tokenizer.encode(candidate))
        delta = abs(count - target_tokens)
        if delta < best_delta:
            best, best_delta = candidate, delta
        if delta <= 8:
            break
        next_n = max(1, int(n * target_tokens / max(1, count)))
        if next_n == n:
            next_n += 1 if count < target_tokens else -1
        n = max(1, next_n)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokenizer-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--target-tokens", type=int, default=115000)
    args = ap.parse_args()

    tokenizer = load_tokenizer(args.tokenizer_dir)
    header = (
        "Synthetic operations archive for an exact retrieval task. Treat each "
        "record as independent evidence; do not infer values from nearby rows. "
        "At the end, return only a JSON object mapping each requested case ID "
        "to the exact value of its named field. Preserve punctuation and units.\n\n"
    )
    records = []
    for i, (case_id, field, value) in enumerate(FACTS):
        records.append(
            f"[VERIFIED RECORD {i+1:02d}] case_id={case_id}; {field}={value}; "
            f"source=sealed-ledger-{i+1:02d}; status=verified.\n"
        )
    questions = "\nREQUESTS\n" + "\n".join(
        f"{i+1}. For {case_id}, return the exact {field}."
        for i, (case_id, field, _) in enumerate(FACTS)
    )
    fixed = header + "\n".join(records) + questions
    fixed_tokens = len(tokenizer.encode(fixed))
    filler_budget = max(1000, args.target_tokens - fixed_tokens)
    targets = [round(filler_budget * 0.05)] + [round(filler_budget * 0.10)] * 9 + [round(filler_budget * 0.05)]

    chunks = []
    for i, token_target in enumerate(targets):
        chunks.append(build_chunk(tokenizer, i, token_target, i * 100_000))

    parts = [header]
    fact_offsets = []
    # Facts at approximately 5%, 15%, ..., 95% of the full input.
    parts.append(chunks[0])
    for i, record in enumerate(records):
        fact_offsets.append(sum(len(tokenizer.encode(x)) for x in parts))
        parts.append(record)
        parts.append(chunks[i + 1])
    prompt = "\n".join(parts) + questions
    prompt_tokens = len(tokenizer.encode(prompt))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = args.out_dir / "probe-prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    expected = {case_id: value for case_id, _, value in FACTS}
    (args.out_dir / "probe-expected.json").write_text(
        json.dumps(expected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    metadata = {
        "suite": "context-retrieval-v1",
        "generatorSeed": 4242,
        "targetTokens": args.target_tokens,
        "tokenizerTextOnlyTokens": prompt_tokens,
        "factPositionsTextOnly": [
            {"caseId": case_id, "tokenOffset": offset, "fraction": round(offset / max(1, prompt_tokens), 4)}
            for offset, (case_id, _, _) in zip(fact_offsets, FACTS)
        ],
        "promptSha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "promptFileSha256": hashlib.sha256(prompt_path.read_bytes()).hexdigest(),
        "promptBytes": len(prompt.encode("utf-8")),
        "expectedSha256": hashlib.sha256(
            json.dumps(expected, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest(),
    }
    (args.out_dir / "probe-metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
