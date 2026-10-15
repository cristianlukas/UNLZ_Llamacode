#!/usr/bin/env python3
"""Add evaluation-only temperature/seed overrides to a native source mirror."""
import argparse
import hashlib
import json
import pathlib
import time


ORIGINAL = """    const double benchmarkTemp = temp < 0.0 ? 0.1 : qMin(temp, 0.1);
    const int benchmarkSeed = 4242;"""
REPLACEMENT = """    double benchmarkTemp = temp < 0.0 ? 0.1 : qMin(temp, 0.1);
    bool evalTemperatureOk = false;
    const double evalTemperature = qgetenv(\"LLAMACODE_EVAL_TEMPERATURE\").toDouble(&evalTemperatureOk);
    if (evalTemperatureOk && evalTemperature >= 0.0 && evalTemperature <= 2.0)
        benchmarkTemp = evalTemperature;
    bool evalSeedOk = false;
    const int evalSeed = qgetenv(\"LLAMACODE_EVAL_SEED\").toInt(&evalSeedOk);
    const int benchmarkSeed = evalSeedOk && evalSeed >= 0 ? evalSeed : 4242;"""


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=pathlib.Path)
    parser.add_argument("--receipt", required=True, type=pathlib.Path)
    args = parser.parse_args()
    source = args.source / "src/AppController.cpp"
    text = source.read_text(encoding="utf-8")
    if text.count(ORIGINAL) != 1:
        raise SystemExit("Expected one unchanged benchmark temperature/seed block")
    before_hash = sha256(source)
    source.write_text(text.replace(ORIGINAL, REPLACEMENT, 1), encoding="utf-8")
    after_hash = sha256(source)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps({
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_file": str(source),
        "sha256_before": before_hash,
        "sha256_after": after_hash,
        "scope": "native source mirror only; production checkout unchanged",
        "temperature_env": "LLAMACODE_EVAL_TEMPERATURE",
        "seed_env": "LLAMACODE_EVAL_SEED",
        "validation": "the exact original two-line block was found once and replaced",
    }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
