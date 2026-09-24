#!/usr/bin/env python3
"""Measure append-only tool-loop prefix reuse on an OpenAI-compatible server.

The ``rolling-tool`` variant is the current LlamaCode wire contract: tool
history is appended and schemas stay canonical. ``unstable-prefix`` deliberately
changes a tool-schema key order each turn. If the server does not report cache
usage, the report says ``cacheMetricsAvailable=false`` and does not claim a
rolling-tool win.
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


def tool_schema(unstable: bool) -> list[dict[str, Any]]:
    function: dict[str, Any] = {"name": "read_file", "description": "read a file",
                                "parameters": {"type": "object", "properties": {
                                    "path": {"type": "string"}}, "required": ["path"]}}
    if unstable:
        function = {"parameters": function["parameters"], "description": function["description"],
                    "name": function["name"]}
    return [{"type": "function", "function": function}]


def request(url: str, payload: Mapping[str, Any], timeout: float) -> tuple[dict[str, Any] | None, str, float]:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    req = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    started = time.perf_counter()
    try:
        with urlopen(req, timeout=timeout) as reply:
            return json.loads(reply.read().decode("utf-8")), "", (time.perf_counter() - started) * 1000
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return None, f"{type(exc).__name__}: {exc}", (time.perf_counter() - started) * 1000


def number(data: Mapping[str, Any] | None, *path: str) -> float | None:
    value: Any = data or {}
    for item in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(item)
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8080/v1/chat/completions")
    parser.add_argument("--model", default="")
    parser.add_argument("--turns", type=int, default=6)
    parser.add_argument("--passes", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.turns < 1 or args.passes < 1:
        parser.error("turns y passes deben ser >= 1")
    rows: list[dict[str, Any]] = []
    for variant, unstable in (("rolling-tool", False), ("unstable-prefix", True)):
        for pass_number in range(1, args.passes + 1):
            messages: list[dict[str, Any]] = [{"role": "system", "content": "Conservá el marcador de cada ronda."}]
            for turn in range(1, args.turns + 1):
                messages.extend([
                    {"role": "user", "content": f"Ronda {turn}: leé el archivo y conservá MARK-{turn}."},
                    {"role": "assistant", "content": "", "tool_calls":[{"id":f"call-{turn}", "type":"function", "function":{"name":"read_file", "arguments":json.dumps({"path":f"src/file{turn}.txt"})}}]},
                    {"role": "tool", "tool_call_id":f"call-{turn}", "content":f"tool result MARK-{turn}: contenido verificado"},
                ])
                payload: dict[str, Any] = {
                    "messages": messages + [{"role": "user", "content": f"Confirmá sólo que recordás MARK-{turn}."}],
                    "tools": tool_schema(unstable), "tool_choice": "none",
                    "cache_prompt": True, "temperature": 0.0, "max_tokens": 32, "stream": False,
                }
                if args.model:
                    payload["model"] = args.model
                data, error, wall = request(args.url, payload, args.timeout)
                rows.append({
                    "variant": variant, "pass": pass_number, "turn": turn,
                    "transportOk": data is not None, "wallMs": round(wall, 2),
                    "promptTokens": number(data, "usage", "prompt_tokens"),
                    "cachedTokens": number(data, "usage", "prompt_tokens_details", "cached_tokens"),
                    "cacheN": number(data, "timings", "cache_n"),
                    "error": error,
                })
    summary: dict[str, Any] = {}
    for variant in ("rolling-tool", "unstable-prefix"):
        sample = [row for row in rows if row["variant"] == variant]
        ok = [row for row in sample if row["transportOk"]]
        cache = [row for row in ok if row["cachedTokens"] is not None or row["cacheN"] is not None]
        values = [row["cachedTokens"] if row["cachedTokens"] is not None else row["cacheN"] for row in cache]
        summary[variant] = {
            "runs": len(sample), "transportPct": 100.0 * len(ok) / len(sample) if sample else 0.0,
            "medianWallMs": statistics.median(row["wallMs"] for row in ok) if ok else None,
            "medianPromptTokens": statistics.median(row["promptTokens"] for row in ok if row["promptTokens"] is not None) if any(row["promptTokens"] is not None for row in ok) else None,
            "medianCachedTokens": statistics.median(values) if values else None,
            "cacheMetricsAvailable": bool(cache),
        }
    report = {"schema": "llamacode-prefix-loop-benchmark-v1", "url": args.url,
              "model": args.model, "turns": args.turns, "passes": args.passes,
              "cacheMetricsAvailable": any(item["cacheMetricsAvailable"] for item in summary.values()),
              "summary": summary, "rows": rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("variant          transport  median_ms  prompt_tok  cached_tok  cache_metrics")
    for variant, item in summary.items():
        print(f"{variant:16} {item['transportPct']:>9.2f}% {str(item['medianWallMs']):>10} "
              f"{str(item['medianPromptTokens']):>11} {str(item['medianCachedTokens']):>10} "
              f"{item['cacheMetricsAvailable']}")
    print(f"cache_metrics_available={report['cacheMetricsAvailable']}")
    print(f"reporte={args.out}")
    return 0 if all(item["transportPct"] == 100.0 for item in summary.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
