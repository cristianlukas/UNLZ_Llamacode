#!/usr/bin/env python3
"""Run one preregistered seed of the fixed BigCodeBench-Hard-8 screen."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parents[4]
PACK = REPO / "artifacts/evaluacion-modelos-llamacode/Q-20261020-VF-20261019-01/fixtures/source23-bcb8-bilingual.json"
GRADER_PYTHON = Path("/home/cristian/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12")
GRADER_ROOT = GRADER_PYTHON.resolve().parents[1]
USER_SITE = Path("/home/cristian/.local/lib/python3.12/site-packages")
THINK = re.compile(r"<think>.*?</think>", re.I | re.S)
FENCE = re.compile(r"```(?:python|py)?\s*(.*?)```", re.I | re.S)


def request_json(url: str, payload: dict, timeout: int):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    start = time.perf_counter()
    with urlopen(Request(url, data=data, headers={"Content-Type": "application/json"}), timeout=timeout) as response:
        body = json.loads(response.read())
    return body, (time.perf_counter() - start) * 1000


def candidate_code(text: str) -> str:
    text = THINK.sub("", text).strip()
    blocks = FENCE.findall(text)
    if blocks:
        return max(blocks, key=len).strip()
    lines = text.splitlines()
    if lines and lines[0].lstrip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def grade(code: str, tests: str) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="lc-s43-bcb-") as temp:
        directory = Path(temp)
        script = directory / "candidate.py"
        script.write_text(code + "\n\n" + tests + "\n", encoding="utf-8")
        if not GRADER_PYTHON.is_file() or not GRADER_ROOT.is_dir() or not USER_SITE.is_dir():
            return False, "pinned grader Python or its read-only data packages are unavailable"
        command = [
            "bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc",
            "--tmpfs", "/tmp", "--tmpfs", "/home", "--tmpfs", "/media", "--tmpfs", "/mnt",
        ]
        home = Path.home()
        for part in (home, home / ".cache", home / ".cache/codex-runtimes",
                     home / ".cache/codex-runtimes/codex-primary-runtime",
                     home / ".cache/codex-runtimes/codex-primary-runtime/dependencies",
                     GRADER_ROOT, USER_SITE.parents[2], USER_SITE.parents[1],
                     USER_SITE.parents[0], USER_SITE):
            command.extend(["--dir", str(part)])
        command += [
            "--ro-bind", str(GRADER_ROOT), str(GRADER_ROOT),
            "--ro-bind", str(USER_SITE), str(USER_SITE),
            "--dir", "/mnt/work", "--bind", temp, "/mnt/work", "--chdir", "/mnt/work",
            "--unshare-net", "--unshare-pid", "--die-with-parent",
            str(GRADER_PYTHON), "-E", "/mnt/work/candidate.py",
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=45)
            return result.returncode == 0, (result.stderr or result.stdout).strip()[-1200:]
        except subprocess.TimeoutExpired:
            return False, "grader timed out after 45s"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8353/v1/chat/completions")
    parser.add_argument("--model", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-tokens", type=int, default=6144)
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()

    if args.seed <= 0:
        parser.error("--seed must be a positive integer")
    corpus = json.loads(PACK.read_text(encoding="utf-8"))
    rows = []
    for index, item in enumerate(corpus["items"], 1):
        payload = {
            "model": args.model,
            "messages": [
                {"role": "system", "content": ("Resuelve la tarea de programación. Devuelve únicamente una implementación completa en Python; no expliques." if item.get("language") == "es" else "Solve the programming task. Return only a complete Python implementation; do not explain.")},
                {"role": "user", "content": item["prompt"]},
            ],
            "temperature": 0.6,
            "top_p": 0.95,
            "top_k": 20,
            "min_p": 0.0,
            "repetition_penalty": 1.0,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
            "seed": args.seed,
            "max_tokens": args.max_tokens,
            "chat_template_kwargs": {"enable_thinking": False},
            "stream": False,
        }
        start = time.perf_counter()
        try:
            response, wall_ms = request_json(args.url, payload, args.timeout)
            message = response.get("choices", [{}])[0].get("message", {})
            content = str(message.get("content", ""))
            code = candidate_code(content)
            passed, detail = grade(code, item["tests"])
            rows.append({
                "id": item["id"], "language": item.get("language", "en"), "seed": args.seed, "transportOk": True,
                "wallMs": round(wall_ms, 2), "passed": passed,
                "completionTokens": response.get("usage", {}).get("completion_tokens"),
                "promptTokens": response.get("usage", {}).get("prompt_tokens"),
                "reasoningTokens": response.get("usage", {}).get("completion_tokens_details", {}).get("reasoning_tokens"),
                "timings": response.get("timings"),
                "code": code, "gradeDetail": detail, "rawContent": content[:12000],
            })
        except Exception as error:
            rows.append({
                "id": item["id"], "language": item.get("language", "en"), "seed": args.seed, "transportOk": False,
                "wallMs": round((time.perf_counter() - start) * 1000, 2), "passed": False,
                "error": f"{type(error).__name__}: {error}",
            })
        print(f"{index}/{len(corpus['items'])} seed={args.seed} {item['id']} passed={rows[-1]['passed']} wallMs={rows[-1]['wallMs']}", flush=True)

    output = {
        "experiment": "VF-20261019-01-S23-PLE-FP8-AB",
        "benchmark": "BigCodeBench-Hard-8", "pack": str(PACK.relative_to(REPO)),
        "model": args.model, "url": args.url, "seed": args.seed,
        "reasoning": "off", "temperature": 0.6, "topP": 0.95, "topK": 20,
        "minP": 0.0, "repetitionPenalty": 1.0, "presencePenalty": 0.0,
        "frequencyPenalty": 0.0, "maxTokens": args.max_tokens,
        "runs": len(rows), "transportOk": sum(row["transportOk"] for row in rows),
        "passed": sum(row["passed"] for row in rows), "rows": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"score={output['passed']}/{output['runs']} transport={output['transportOk']}/{output['runs']} out={args.out}")
    return 0 if output["transportOk"] == output["runs"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
