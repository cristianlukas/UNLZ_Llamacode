#!/usr/bin/env python3
"""Sweep per-request reasoning budgets against an OpenAI-compatible server.

This is an opt-in benchmark. It deliberately scores only versioned acceptance
markers from the corpus; it never treats a long answer or a non-empty answer as
quality. The report keeps transport failures separate from model failures.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT / "assets" / "benchmarks" / "custom" / "reasoning_budget_v2.json"


def load_corpus(path: Path) -> list[dict[str, Any]]:
    source = json.loads(path.read_text(encoding="utf-8"))
    tasks = source.get("tasks", [])
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("el corpus debe tener tasks no vacías")
    result = []
    seen: set[str] = set()
    for raw in tasks:
        if not isinstance(raw, dict):
            raise ValueError("cada task debe ser un objeto")
        task_id = str(raw.get("id", "")).strip()
        prompt = str(raw.get("prompt", "")).strip()
        if not task_id or not prompt or task_id in seen:
            raise ValueError("cada task necesita id único y prompt")
        seen.add(task_id)
        acceptance = raw.get("acceptance", {})
        if not isinstance(acceptance, dict):
            raise ValueError(f"acceptance inválido en {task_id}")
        result.append({"id": task_id, "category": raw.get("category", "other"),
                      "prompt": prompt, "acceptance": acceptance})
    return result


def response_text(response: Mapping[str, Any]) -> str:
    choices = response.get("choices", [])
    if not choices or not isinstance(choices[0], Mapping):
        return ""
    message = choices[0].get("message", {}) or {}
    return str(message.get("content", ""))


def score_text(text: str, acceptance: Mapping[str, Any]) -> dict[str, Any]:
    folded = text.casefold()
    required = [str(item).casefold() for item in acceptance.get("contains", [])]
    forbidden = [str(item).casefold() for item in acceptance.get("forbid", [])]
    missing = [item for item in required if item not in folded]
    found_forbidden = [item for item in forbidden if item in folded]
    return {
        "passed": not missing and not found_forbidden,
        "missing": missing,
        "forbidden": found_forbidden,
        "chars": len(text),
    }


def request(url: str, payload: Mapping[str, Any], timeout: float) -> tuple[dict[str, Any] | None, str, float]:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    req = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    started = time.perf_counter()
    try:
        with urlopen(req, timeout=timeout) as reply:
            return json.loads(reply.read().decode("utf-8")), "", (time.perf_counter() - started) * 1000
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return None, f"{type(exc).__name__}: {exc}", (time.perf_counter() - started) * 1000


def metric(response: Mapping[str, Any] | None, key: str, *nested: str) -> float | None:
    value: Any = response or {}
    for part in (key,) + nested:
        if not isinstance(value, Mapping):
            return None
        value = value.get(part)
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def summarize(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    budgets = sorted({int(row["budget"]) for row in rows})
    output: dict[str, Any] = {}
    for budget in budgets:
        sample = [row for row in rows if int(row["budget"]) == budget]
        completed = [row for row in sample if row.get("transportOk")]
        wall = [float(row["wallMs"]) for row in completed]
        prompt = [float(row["promptTokens"]) for row in completed if row.get("promptTokens") is not None]
        generated = [float(row["generatedTokens"]) for row in completed if row.get("generatedTokens") is not None]
        reasoning = [float(row["reasoningTokens"]) for row in completed if row.get("reasoningTokens") is not None]
        output[str(budget)] = {
            "budget": budget,
            "runs": len(sample),
            "transportOk": len(completed),
            "transportPct": 100.0 * len(completed) / len(sample) if sample else 0.0,
            "passed": sum(bool(row.get("score", {}).get("passed")) for row in sample),
            "successPct": 100.0 * sum(bool(row.get("score", {}).get("passed")) for row in sample) / len(sample) if sample else 0.0,
            "medianWallMs": statistics.median(wall) if wall else None,
            "medianPromptTokens": statistics.median(prompt) if prompt else None,
            "medianGeneratedTokens": statistics.median(generated) if generated else None,
            "medianReasoningTokens": statistics.median(reasoning) if reasoning else None,
        }
    return output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8080/v1/chat/completions")
    parser.add_argument("--model", default="")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--budgets", default="0,512,1024,2048,4096,8192")
    parser.add_argument("--passes", type=int, default=3)
    parser.add_argument("--max-tokens", type=int, default=1024,
                        help="techo de tokens visibles + reasoning por request")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.passes < 1 or args.max_tokens < 16:
        parser.error("--passes debe ser >= 1")
    try:
        budgets = [int(item.strip()) for item in args.budgets.split(",") if item.strip()]
    except ValueError as exc:
        parser.error(f"--budgets inválido: {exc}")
    if not budgets or any(item < 0 for item in budgets):
        parser.error("--budgets debe contener enteros >= 0")
    tasks = load_corpus(args.corpus)
    rows: list[dict[str, Any]] = []
    for pass_number in range(1, args.passes + 1):
        for budget in budgets:
            for task in tasks:
                payload: dict[str, Any] = {
                    "messages": [
                        {"role": "system", "content": "Respondé de forma verificable y conservadora."},
                        {"role": "user", "content": task["prompt"]},
                    ],
                    "reasoning_budget": budget,
                    "chat_template_kwargs": {"enable_thinking": budget > 0},
                    "temperature": 0.0,
                    "top_p": 0.95,
                    "top_k": 20,
                    "max_tokens": args.max_tokens,
                    "stream": False,
                }
                if args.model:
                    payload["model"] = args.model
                data, error, wall = request(args.url, payload, args.timeout)
                text = response_text(data) if data else ""
                score = score_text(text, task["acceptance"])
                rows.append({
                    "pass": pass_number, "budget": budget, "task": task["id"],
                    "category": task["category"], "transportOk": data is not None,
                    "wallMs": round(wall, 2), "score": score,
                    "promptTokens": metric(data, "usage", "prompt_tokens"),
                    "generatedTokens": metric(data, "usage", "completion_tokens"),
                    "reasoningTokens": metric(data, "usage", "completion_tokens_details", "reasoning_tokens"),
                    "error": error, "response": text[:4000],
                })
    report = {
        "schema": "llamacode-reasoning-budget-benchmark-v1",
        "model": args.model, "url": args.url, "budgets": budgets,
        "passes": args.passes, "taskCount": len(tasks),
        "summary": summarize(rows), "rows": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("budget  success  transport  median_ms  prompt_tok  generated_tok  reasoning_tok")
    for item in report["summary"].values():
        print(f"{item['budget']:>6} {item['successPct']:>7.2f}% {item['transportPct']:>9.2f}% "
              f"{str(item['medianWallMs']):>10} {str(item['medianPromptTokens']):>11} "
              f"{str(item['medianGeneratedTokens']):>14} {str(item['medianReasoningTokens']):>14}")
    print(f"reporte={args.out}")
    return 0 if all(item["transportPct"] == 100.0 for item in report["summary"].values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
