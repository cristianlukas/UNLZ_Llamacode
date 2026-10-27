#!/usr/bin/env python3
"""Sanitized single-seed BCB-Hard-8 runner for OpenAI-compatible local servers."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[4]
PACK = ROOT / "artifacts/bigcodebench-hard-ubuntu-8.json"
GRADER_IMAGE = "vllm/vllm-openai@sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967"

FENCE = re.compile(r"```(?:python|py)?\s*(.*?)```", re.I | re.S)
THINK = re.compile(r"<think>.*?</think>", re.I | re.S)


def load_api_key(path: str | None) -> str | None:
    if not path:
        return None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith("VLLM_API_KEY="):
            value = line.split("=", 1)[1].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            return value or None
    return None


def extract_code(text: str) -> str:
    text = THINK.sub("", text).strip()
    blocks = FENCE.findall(text)
    return max(blocks, key=len).strip() if blocks else text


def grade_code(code: str, tests: str) -> tuple[str, str]:
    if not code.strip():
        return "no_final_content", "empty_code"
    try:
        with tempfile.TemporaryDirectory(prefix="q167-bcb-") as directory:
            root = Path(directory)
            candidate = root / "candidate.py"
            candidate.write_text(code + "\n\n" + tests + "\n", encoding="utf-8")
            container_name = f"q167-grader-{os.getpid()}-{uuid.uuid4().hex[:10]}"
            cmd = [
                "docker", "run", "--rm", "--name", container_name,
                "--network", "none", "--read-only", "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges:true", "--pids-limit", "64",
                "--memory", "2g", "--cpus", "2",
                "--tmpfs", "/tmp:rw,nosuid,nodev,size=512m",
                "--tmpfs", "/mnt/work:rw,nosuid,nodev,size=64m",
                "--user", f"{os.getuid()}:{os.getgid()}",
                "--mount", f"type=bind,source={directory},target=/mnt/input,readonly",
                "--workdir", "/mnt/work", "--env", "HOME=/tmp",
                "--env", "PYTHONDONTWRITEBYTECODE=1", "--entrypoint", "python3",
                GRADER_IMAGE, "-I", "/mnt/input/candidate.py",
            ]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            except subprocess.TimeoutExpired:
                subprocess.run(["docker", "rm", "-f", container_name], capture_output=True,
                               text=True, timeout=15, check=False)
                return "test_timeout", "grader_container_timeout_45s"
        if result.returncode == 0:
            return "passed", "container_exit_0"
        if result.returncode >= 125:
            return "sandbox_error", f"grader_container_exit_{result.returncode}"
        return "test_failed", f"python_exit_{result.returncode}"
    except Exception as exc:
        return "sandbox_error", f"grader_exception_{type(exc).__name__}"


def request_one(url: str, model: str, prompt: str, seed: int, max_tokens: int,
                reasoning_effort: str, api_key: str | None) -> dict:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Solve the programming task. Return only a complete Python implementation; do not explain."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.6,
        "top_p": 0.95,
        "top_k": 20,
        "min_p": 0.0,
        "repetition_penalty": 1.0,
        "presence_penalty": 0.0,
        "max_tokens": max_tokens,
        "seed": seed,
        "stream": True,
        "stream_options": {"include_usage": True},
        "reasoning_effort": reasoning_effort,
        "chat_template_kwargs": {"enable_thinking": True, "reasoning_effort": reasoning_effort},
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    req = Request(url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), headers=headers)
    started = time.perf_counter()
    first_token = None
    content_parts: list[str] = []
    usage: dict = {}
    finish_reason = None
    status = None
    saw_done = False
    try:
        with urlopen(req, timeout=900) as response:
            status = response.status
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    saw_done = True
                    break
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if isinstance(event.get("usage"), dict):
                    usage = event["usage"]
                choices = event.get("choices") or []
                if not choices:
                    continue
                choice = choices[0]
                delta = choice.get("delta") or {}
                fragment = delta.get("content")
                reasoning = delta.get("reasoning") or delta.get("reasoning_content")
                if (isinstance(fragment, str) and fragment) or (isinstance(reasoning, str) and reasoning):
                    if first_token is None:
                        first_token = time.perf_counter()
                if isinstance(fragment, str) and fragment:
                    content_parts.append(fragment)
                if choice.get("finish_reason"):
                    finish_reason = choice["finish_reason"]
        ended = time.perf_counter()
        text = "".join(content_parts)
        wall_seconds = max(ended - started, 1e-9)
        ttft_seconds = max(first_token - started, 1e-9) if first_token else None
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        prefill_proxy = (round(prompt_tokens / ttft_seconds, 2)
                        if isinstance(prompt_tokens, int) and ttft_seconds else None)
        decode_proxy = (round(max(completion_tokens - 1, 0) / max(wall_seconds - ttft_seconds, 1e-9), 2)
                       if isinstance(completion_tokens, int) and ttft_seconds else None)
        return {
            "transportOk": status == 200 and saw_done,
            "httpStatus": status,
            "wallMs": round(wall_seconds * 1000, 2),
            "ttftMs": round(ttft_seconds * 1000, 2) if ttft_seconds else None,
            "promptTokens": prompt_tokens,
            "completionTokens": completion_tokens,
            "reasoningTokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
            "prefillClientProxyTokPerSec": prefill_proxy,
            "decodeClientProxyTokPerSec": decode_proxy,
            "completionClientProxyTokPerSec": (round(completion_tokens / wall_seconds, 2)
                                                 if isinstance(completion_tokens, int) else None),
            "finishReason": finish_reason,
            "code": extract_code(text),
            "contentChars": len(text),
            "errorType": None if saw_done else "incomplete_stream",
        }
    except HTTPError as exc:
        return {"transportOk": False, "httpStatus": exc.code,
                "wallMs": round((time.perf_counter() - started) * 1000, 2),
                "ttftMs": None, "promptTokens": None, "completionTokens": None,
                "finishReason": None, "code": "", "contentChars": 0,
                "errorType": "http_error"}
    except (URLError, TimeoutError, OSError) as exc:
        return {"transportOk": False, "httpStatus": status,
                "wallMs": round((time.perf_counter() - started) * 1000, 2),
                "ttftMs": None, "promptTokens": None, "completionTokens": None,
                "finishReason": None, "code": "", "contentChars": 0,
                "errorType": type(exc).__name__}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--arm", choices=("sol", "hyperqwen"), required=True)
    parser.add_argument("--seed", type=int, default=4242)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--api-key-file")
    parser.add_argument("--reverse", action="store_true")
    parser.add_argument("--max-tokens", type=int, default=6144)
    args = parser.parse_args()

    pack_bytes = PACK.read_bytes()
    pack_sha = hashlib.sha256(pack_bytes).hexdigest()
    expected_sha = "11279cde14113fc8527f141c53e14cb5ccf0dba65749081a4f914408e391c268"
    if pack_sha != expected_sha:
        raise SystemExit("BCB-Hard-8 fixture hash changed; refusing to score")
    corpus = json.loads(pack_bytes)
    items = list(corpus["items"])
    if len(items) != 8:
        raise SystemExit("fixture task count changed; refusing to score")
    if args.reverse:
        items.reverse()
    api_key = load_api_key(args.api_key_file)

    warmup = request_one(
        args.url, args.model,
        "Write a Python function named warmup_identity(x) that returns x. Return only code.",
        args.seed, 32, "medium", api_key,
    )
    warmup.pop("code", None)
    if not warmup.get("transportOk"):
        raise SystemExit("warmup request failed; refusing to score this arm")

    rows = []
    for index, item in enumerate(items, 1):
        response = request_one(args.url, args.model, item["prompt"], args.seed,
                               args.max_tokens, "medium", api_key)
        if response["transportOk"]:
            status, grade_diagnostic = grade_code(response.pop("code"), item["tests"])
        else:
            status, grade_diagnostic = "transport_error", "not_graded_transport_error"
        row = {"id": item["id"], **response, "gradeStatus": status,
               "gradeDiagnostic": grade_diagnostic, "passed": status == "passed"}
        rows.append(row)
        print(f"{args.arm} {index}/8 id={item['id']} pass={row['passed']} "
              f"grade={status} wallMs={row['wallMs']} tokens={row['completionTokens']}", flush=True)

    out = {
        "taskId": "Q-20261027-VF-ITERATION-167",
        "arm": args.arm,
        "model": args.model,
        "endpoint": args.url,
        "fixtureSha256": pack_sha,
        "seed": args.seed,
        "reasoningEffort": "medium",
        "thinking": True,
        "temperature": 0.6,
        "topP": 0.95,
        "topK": 20,
        "minP": 0.0,
        "repetitionPenalty": 1.0,
        "presencePenalty": 0.0,
        "maxTokens": args.max_tokens,
        "warmup": {key: value for key, value in warmup.items() if key != "contentChars"},
        "order": "reverse" if args.reverse else "fixture",
        "runs": len(rows),
        "transportOk": sum(bool(row["transportOk"]) for row in rows),
        "passed": sum(bool(row["passed"]) for row in rows),
        "sandboxErrors": sum(row["gradeStatus"] == "sandbox_error" for row in rows),
        "emptyFinals": sum(row["gradeStatus"] == "no_final_content" for row in rows),
        "rows": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if out["transportOk"] == 8 and out["sandboxErrors"] == 0 and out["emptyFinals"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
