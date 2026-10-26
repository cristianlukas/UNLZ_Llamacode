#!/usr/bin/env python3
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parent
questions = json.loads((root / "questions.json").read_text(encoding="utf-8"))["questions"]
oracle = json.loads((root / "oracle-results.json").read_text(encoding="utf-8"))["questions"]
errors = []
for question in questions:
    qid = question["id"]
    raw = oracle[qid]["stdout"]
    expected_value = int(raw, 0) if raw.lower().startswith("0x") else int(raw)
    options = re.findall(r"\b([A-D])=(-?(?:0x[0-9a-fA-F]+|[0-9]+))", question["prompt"])
    matches = [letter for letter, value in options if int(value, 0) == expected_value]
    if len(matches) != 1 or matches[0] != question["answer"]:
        errors.append({"id": qid, "oracle": raw, "matchingOptions": matches, "registeredAnswer": question["answer"]})
if errors:
    print(json.dumps({"status": "FAIL", "errors": errors}, indent=2))
    raise SystemExit(1)
print(json.dumps({"status": "PASS", "questionCount": len(questions), "oracleMatches": len(questions)}, indent=2))
