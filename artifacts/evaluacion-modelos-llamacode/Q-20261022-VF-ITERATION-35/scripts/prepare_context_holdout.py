#!/usr/bin/env python3
"""Prepare reproducible fixtures and isolated per-run config copies for Q35."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261022-VF-ITERATION-35"
BASE = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261014-ISTA-NEEDLE-HAYSTACK"
TOKENIZER_DIR = Path("/media/cristian/Disco local/Models/FlashNext-IQ2XS-ISTA-Strata-eval-20261012/strata-data/packs/iq2_xs/tokenizer")
PYTHON = Path("/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source/.venv/bin/python")
PYTHONPATH = "/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source/tools"
GENERATOR = TASK / "scripts/generate_context_holdout.py"
CONTEXTS = [131072, 262144, 524288, 1048576]
SEEDS = [2026101, 2026102, 2026103]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    env = os.environ.copy()
    env["PYTHONPATH"] = PYTHONPATH
    rows = []
    for context in CONTEXTS:
        base_config = json.loads((BASE / f"receipts/configs/context-{context}.json").read_text())
        for seed in SEEDS:
            fixture = TASK / f"fixtures/{context}/{seed}"
            run_dir = TASK / f"runs/{context}/{seed}"
            config = TASK / f"receipts/configs/context-{context}-seed-{seed}.json"
            config.parent.mkdir(parents=True, exist_ok=True)
            run_dir.mkdir(parents=True, exist_ok=True)
            generated = subprocess.run([
                str(PYTHON), str(GENERATOR), "--tokenizer-dir", str(TOKENIZER_DIR),
                "--out-dir", str(fixture), "--target-tokens", str(round(context * 0.955)),
                "--seed", str(seed),
            ], env=env, text=True, capture_output=True, check=True)
            metadata = json.loads(generated.stdout)
            run_config = dict(base_config)
            run_config["args"] = list(base_config["args"])
            run_config["env"] = dict(base_config.get("env", {}))
            run_config["log"] = str((run_dir / "engine.log").resolve())
            config.write_text(json.dumps(run_config, ensure_ascii=False, indent=2) + "\n")
            rows.append({
                "context": context, "seed": seed, "target_tokens": round(context * 0.955),
                "fixture_dir": str(fixture.resolve()),
                "prompt_sha256": metadata["promptSha256"],
                "expected_sha256": metadata["expectedSha256"],
                "prompt_text_tokens": metadata["tokenizerTextOnlyTokens"],
                "config_path": str(config.resolve()), "config_sha256": sha256(config),
                "run_dir": str(run_dir.resolve()),
            })
    tokenizer_files = {name: sha256(TOKENIZER_DIR / name)
                       for name in ("vocab.json", "merges.txt", "token_type.json")}
    result = {
        "task": "Q-20261022-VF-ITERATION-35",
        "suite": "context-retrieval-holdout-v1",
        "prepared_at_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "tokenizer_files_sha256": tokenizer_files,
        "runs": rows,
    }
    out = TASK / "receipts/fixtures-manifest.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"fixture_count": len(rows), "tokenizer_files_sha256": tokenizer_files,
                      "runs": [{k: r[k] for k in ("context", "seed", "prompt_text_tokens", "prompt_sha256")}
                               for r in rows]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
