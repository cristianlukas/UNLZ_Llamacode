#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path


CASES = {
    "Q1": ["classify", "0x10", "64", "0"],
    "Q2": ["classify", "0x10", "65", "0"],
    "Q3": ["classify", "0x10", "0", "1"],
    "Q4": ["classify", "0x20", "2", "1"],
    "Q5": ["classify", "0x20", "1", "0"],
    "Q6": ["classify", "0x20", "120", "3"],
    "Q7": ["classify", "0x30", "10", "0"],
    "Q8": ["next", "1", "3"],
    "Q9": ["next", "2", "4"],
    "Q10": ["next", "0", "2"],
    "Q11": ["transform", "0x41", "0"],
    "Q12": ["crc", "0102"],
}


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: run_oracle.py <fixture-binary>")
    binary = Path(sys.argv[1]).resolve()
    root = Path(__file__).resolve().parent
    questions = json.loads((root / "questions.json").read_text(encoding="utf-8"))
    answers = {}
    for question in questions["questions"]:
        qid = question["id"]
        args = [str(binary), *CASES[qid]]
        completed = subprocess.run(args, check=True, capture_output=True, text=True, timeout=2)
        answers[qid] = {
            "argv": args[1:],
            "stdout": completed.stdout.strip(),
            "returncode": completed.returncode,
        }
    result = {
        "status": "oracle_calls_passed",
        "binary": str(binary),
        "questions": answers,
        "cases": len(answers),
    }
    (root / "oracle-results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
