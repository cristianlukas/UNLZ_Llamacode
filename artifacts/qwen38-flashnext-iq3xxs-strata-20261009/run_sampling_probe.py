#!/usr/bin/env python3
"""Probe isolated sampling changes on HumanEval/0 through Strata's OpenAI API."""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


CONDITIONS = [
    ("baseline", 0.6, 0.95),
    ("temperature_only", 0.7, 0.95),
    ("top_p_only", 0.6, 0.8),
    ("post_recipe", 0.7, 0.8),
]


def grade_source(source, cwd):
    with tempfile.TemporaryDirectory(prefix="strata-sampling-grade-") as tmp:
        root = Path(tmp)
        fixture = root / "grader.py"
        fixture.write_text(source, encoding="utf-8")
        command = [
            "bwrap", "--unshare-all", "--die-with-parent",
            "--ro-bind", "/", "/", "--bind", tmp, tmp,
            "--dev", "/dev", "--proc", "/proc", "--chdir", tmp,
            sys.executable, "-I", "-S", "-B", str(fixture),
        ]
        result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=30)
        return {"exitCode": result.returncode, "stdout": result.stdout,
                "stderr": result.stderr[-4000:]}


def complete(base_url, model, prompt, temperature, top_p, seed):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "max_tokens": 1200,
        "temperature": temperature,
        "top_p": top_p,
        "top_k": 20,
        "min_p": 0.0,
        "repetition_penalty": 1.0,
        "presence_penalty": 0.0,
        "seed": seed,
    }
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    with urllib.request.urlopen(req, timeout=900) as response:
        result = json.load(response)
    elapsed = time.monotonic() - started
    content = result["choices"][0]["message"].get("content") or ""
    return content, result.get("usage", {}), elapsed


def code_only(text):
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()
    match = re.search(r"```(?:python)?\s*\n([\s\S]*?)\n```", text, flags=re.IGNORECASE)
    return match.group(1).strip() if match else text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8350/v1")
    parser.add_argument("--model", required=True)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=4242)
    args = parser.parse_args()

    if not shutil.which("bwrap"):
        raise RuntimeError("bubblewrap (bwrap) is required for isolated grading")
    suite = json.loads(args.suite.read_text(encoding="utf-8"))
    task = suite["prompts"][0]
    acceptance = task["acceptance"]
    rows = []
    for name, temperature, top_p in CONDITIONS:
        content, usage, elapsed = complete(args.base_url, args.model, task["prompt"],
                                           temperature, top_p, args.seed)
        code = code_only(content)
        source = acceptance["preamble"] + "\n\n" + code + "\n\n" + acceptance["tests"]
        grade = grade_source(source, args.suite.parent)
        rows.append({
            "condition": name,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": 20,
            "min_p": 0.0,
            "repetition_penalty": 1.0,
            "presence_penalty": 0.0,
            "seed": args.seed,
            "elapsedSec": round(elapsed, 4),
            "usage": usage,
            "pass": grade["exitCode"] == 0,
            "grade": grade,
            "response": content,
        })
    result = {
        "schemaVersion": 1,
        "suite": str(args.suite),
        "suiteId": task["id"],
        "suiteName": suite.get("name"),
        "model": args.model,
        "baseUrl": args.base_url,
        "conditions": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"saved": str(args.out), "scores": [
        {"condition": r["condition"], "pass": r["pass"], "elapsedSec": r["elapsedSec"]}
        for r in rows]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
