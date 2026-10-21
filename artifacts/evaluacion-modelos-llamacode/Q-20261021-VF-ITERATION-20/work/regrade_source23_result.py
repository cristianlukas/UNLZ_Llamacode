#!/usr/bin/env python3
"""Regrade saved S23 completions using the Q20-local isolated scorer; no model calls."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import time

TASK = pathlib.Path(__file__).resolve().parents[1]
SCORER = TASK / "work/source23-run-bcb.py"
FIXTURE = pathlib.Path(
    "/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode/"
    "artifacts/evaluacion-modelos-llamacode/Q-20261020-VF-20261019-01/"
    "fixtures/source23-bcb8-bilingual.json"
)


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite an existing regrade: {args.output}")
    spec = importlib.util.spec_from_file_location("q20_source23_scorer", SCORER)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load scorer: {SCORER}")
    scorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scorer)
    result = json.loads(args.input.read_text(encoding="utf-8"))
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    tests_by_id = {item["id"]: item["tests"] for item in fixture["items"]}
    if len(result.get("rows", [])) != 8 or len(tests_by_id) != 8:
        raise SystemExit("expected exactly eight saved responses and eight fixed tests")
    rows = []
    for old in result["rows"]:
        if old.get("id") not in tests_by_id or not old.get("transportOk"):
            raise SystemExit(f"missing or invalid saved response for {old.get('id')}")
        row = dict(old)
        row["previousGradeDetail"] = old.get("gradeDetail")
        row["code"] = scorer.candidate_code(old.get("rawContent", old["code"]))
        row["passed"], row["gradeDetail"] = scorer.grade(row["code"], tests_by_id[old["id"]])
        row["regradedWith"] = str(SCORER)
        rows.append(row)
        print(f"{len(rows)}/8 {row['id']} passed={row['passed']} detail={row['gradeDetail'][:180]}", flush=True)
    result["passed"] = sum(bool(row["passed"]) for row in rows)
    result["rows"] = rows
    result["regrade"] = {
        "recordedAtUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "modelRequestsSent": 0,
        "sourceResult": str(args.input),
        "sourceResultSha256": sha256(args.input),
        "fixture": str(FIXTURE),
        "fixtureSha256": sha256(FIXTURE),
        "scorer": str(SCORER),
        "scorerSha256": sha256(SCORER),
        "score": f"{result['passed']}/8",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["regrade"], ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
