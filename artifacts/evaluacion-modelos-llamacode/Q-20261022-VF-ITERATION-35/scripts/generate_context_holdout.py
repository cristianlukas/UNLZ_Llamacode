#!/usr/bin/env python3
"""Generate a new, deterministic long-context contradiction/rephrasing holdout."""
import argparse
import hashlib
import json
import math
import random
from pathlib import Path


FIELDS = [
    ("service_route", "routing code", ["NW-7314", "SE-2086", "CT-9942", "MX-6130"]),
    ("approved_limit", "signed-off ceiling", ["18.75 units", "42.10 units", "7.625 units", "93.50 units"]),
    ("shipment_seal", "seal identifier", ["SEAL-K8-114", "SEAL-P3-806", "SEAL-R6-552", "SEAL-T9-207"]),
    ("archive_ref", "archive reference", ["AR-2026-7D31", "AR-2026-4B08", "AR-2026-9F62", "AR-2026-1C45"]),
    ("inspection_date", "approved inspection date", ["2026-08-14", "2026-09-03", "2026-07-29", "2026-10-11"]),
    ("package_trace", "trace code", ["PKG-48-XQ", "PKG-13-MV", "PKG-72-LA", "PKG-06-RC"]),
    ("recovery_node", "designated recovery node", ["node-17", "node-42", "node-08", "node-31"]),
    ("checksum", "approved checksum", ["sha256:8c9e2a71", "sha256:3b6d0f42", "sha256:e14a97c3", "sha256:5f02bc86"]),
]

TEMPLATES = [
    "Dispatch file {n}: route {route} reached {site} at {hour}; operator {person} logged {status}. Reference {ref}.",
    "Maintenance note {n}: asset {asset} inspected by {person}; pressure {pressure}; outcome {status}; ticket {ref}.",
    "Archive entry {n}: department {dept}, owner {person}, priority {priority}, region {site}, tracking {ref}.",
    "Shipment {n}: carrier {carrier}, pallet {pallet}, destination {site}, seal {seal}, received {hour} UTC.",
    "Support digest {n}: service {service}, symptom {symptom}, assigned {person}, resolution {status}, case {ref}.",
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
        "n": f"ARCH-{n:07d}",
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


def build_chunk(tokenizer, seed: int, segment: int, target_tokens: int, line_base: int) -> str:
    rng_seed = seed + segment * 100_003
    n = max(1, target_tokens // 23)
    best = ""
    best_delta = math.inf
    for _ in range(8):
        rng = random.Random(rng_seed)
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
    ap.add_argument("--target-tokens", type=int, required=True)
    ap.add_argument("--seed", type=int, required=True)
    args = ap.parse_args()

    tokenizer = load_tokenizer(args.tokenizer_dir)
    rng = random.Random(args.seed)
    facts = []
    for index, (field, phrase, values) in enumerate(FIELDS):
        case_id = f"case-{args.seed % 10000:04d}-{index+1:02d}"
        correct = values[(args.seed + index * 7) % len(values)]
        wrong_pool = [value for value in values if value != correct]
        revoked = wrong_pool[(args.seed + index) % len(wrong_pool)]
        # Half the revoked records appear later in the text to test status selection,
        # not simply choosing the final mention.
        records = [
            ("FINAL_APPROVED", "revision=03", correct),
            ("REVOKED", "revision=04", revoked),
        ]
        rng.shuffle(records)
        for status, revision, value in records:
            line = (f"[SEALED CASE FILE] case_id={case_id}; field={field}; {revision}; "
                    f"status={status}; value={value}; audit=verified.\n")
            facts.append({"case_id": case_id, "field": field, "phrase": phrase,
                          "status": status, "value": value, "record": line})

    # Add plausible distractor records with a competing value under unrelated IDs.
    distractors = []
    for index, (field, _, values) in enumerate(FIELDS):
        other = values[(args.seed + index + 1) % len(values)]
        distractors.append(
            f"[SEALED CASE FILE] case_id=decoy-{args.seed % 10000:04d}-{index+1:02d}; "
            f"field={field}; revision=03; status=FINAL_APPROVED; value={other}; audit=verified.\n"
        )

    records = [fact["record"] for fact in facts] + distractors
    # Ensure target and revoked versions are spread through the full prompt, while
    # the record order varies independently for each holdout seed.
    rng.shuffle(records)
    header = (
        "Synthetic sealed case archive for a selective-retrieval holdout. Each case "
        "can have several revisions. Only records explicitly marked FINAL_APPROVED "
        "are authoritative; REVOKED records are not answers, even when their revision "
        "number is newer or their mention appears later. Records for other case IDs "
        "are distractors. Do not infer missing values.\n\n"
    )
    questions = "\nREQUESTS\n" + "\n".join(
        f"{i+1}. For {fact['case_id']}, return the {fact['phrase']} that survived formal approval. "
        f"Use its FINAL_APPROVED record and disregard any REVOKED revision."
        for i, fact in enumerate(facts[::2])
    )
    # Each case appears in two records; take one expected answer per case.
    expected = {}
    case_metadata = []
    for fact in facts:
        if fact["status"] == "FINAL_APPROVED":
            expected[fact["case_id"]] = fact["value"]
            case_metadata.append({"caseId": fact["case_id"], "field": fact["field"],
                                  "approved": fact["value"]})
    fixed_tokens = len(tokenizer.encode(header + "\n".join(records) + questions))
    filler_budget = max(1000, args.target_tokens - fixed_tokens)
    segments = len(records) + 1
    targets = [round(filler_budget / segments)] * segments
    targets[-1] += filler_budget - sum(targets)
    chunks = [build_chunk(tokenizer, args.seed, i, target, i * 100_000)
              for i, target in enumerate(targets)]

    parts = [header, chunks[0]]
    record_positions = []
    for i, record in enumerate(records):
        record_positions.append(sum(len(tokenizer.encode(x)) for x in parts))
        parts.extend([record, chunks[i+1]])
    prompt = "\n".join(parts) + questions
    prompt_tokens = len(tokenizer.encode(prompt))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = args.out_dir / "probe-prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    (args.out_dir / "probe-expected.json").write_text(
        json.dumps(expected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    metadata = {
        "suite": "context-retrieval-holdout-v1",
        "generatorSeed": args.seed,
        "targetTokens": args.target_tokens,
        "tokenizerTextOnlyTokens": prompt_tokens,
        "caseCount": len(expected),
        "cases": case_metadata,
        "recordPositionsTextOnly": record_positions,
        "recordStatuses": {"FINAL_APPROVED": 16, "REVOKED": 8, "distractor_case_ids": 8},
        "promptSha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "promptFileSha256": hashlib.sha256(prompt_path.read_bytes()).hexdigest(),
        "promptBytes": len(prompt.encode("utf-8")),
        "expectedSha256": hashlib.sha256(
            json.dumps(expected, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(),
    }
    (args.out_dir / "probe-metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
