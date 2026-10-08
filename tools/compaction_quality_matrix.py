#!/usr/bin/env python3
"""Measure repeated context compaction against an uncompressed control.

This is an opt-in experiment, not a product benchmark.  It uses the same
summary contract as ``LlamaAgentBackend::startCompaction`` and an
OpenAI-compatible llama-server.  The workload carries durable markers through
several rounds, then checks whether the first response after each reset and the
final response still preserve them.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


COMPACTION_SYSTEM = (
    "Sos un compactador de memoria de trabajo. Convertí el tramo en UN objeto JSON "
    "válido y compacto con estas claves: goal:string, completed:string[], "
    "decisions:string[], artifacts:[{path:string,change:string,verified:bool}], "
    "failed_approaches:string[], open_questions:string[], next_action:string, "
    "evidence:string[]. Preservá restricciones del usuario, rutas, cambios no "
    "verificados, resultados de tests/build y errores todavía relevantes. Omití "
    "salidas repetidas y detalles ya cerrados. No inventes. Respondé sólo JSON."
)

MARKERS = [
    "KEEP-01: no editar config/production.env",
    "KEEP-02: conservar la firma de API calc_total",
    "KEEP-03: ejecutar tests/test_alpha.py",
    "KEEP-04: no borrar migraciones",
    "KEEP-05: entregar src/report.md",
]


def post_json(url: str, payload: dict[str, Any]) -> tuple[dict[str, Any], float]:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    request = Request(
        url.rstrip("/") + "/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=900) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"request failed: {exc}") from exc
    result["_wallMs"] = (time.perf_counter() - started) * 1000.0
    return result, result["_wallMs"]


def content(response: dict[str, Any]) -> str:
    choices = response.get("choices", [])
    if not choices:
        return ""
    return str(choices[0].get("message", {}).get("content", ""))


def timings(response: dict[str, Any]) -> dict[str, Any]:
    usage = response.get("usage", {})
    raw = response.get("timings", {})
    return {
        "promptTokens": int(usage.get("prompt_tokens", raw.get("prompt_n", 0)) or 0),
        "promptMs": float(raw.get("prompt_ms", 0.0) or 0.0),
        "generatedTokens": int(usage.get("completion_tokens", raw.get("predicted_n", 0)) or 0),
        "generatedMs": float(raw.get("predicted_ms", 0.0) or 0.0),
        "cachedTokens": int(
            usage.get("prompt_tokens_details", {}).get("cached_tokens", raw.get("cache_n", 0)) or 0
        ),
        "wallMs": float(response.get("_wallMs", 0.0) or 0.0),
    }


def serialize_for_summary(message: dict[str, Any]) -> str:
    return f"{message.get('role', '')}: {message.get('content', '')}\n"


def marker_hits(text: str) -> list[str]:
    folded = text.casefold()
    return [marker for marker in MARKERS if marker.casefold() in folded]


def filler(round_number: int, chars: int) -> str:
    line = (
        f"tool_result round={round_number}: output is informational and must not replace "
        "the durable constraints above. Inspect only the requested files; repeated log "
        "lines are intentionally noisy to model a real coding harness.\n"
    )
    repeated = (line * ((chars // len(line)) + 1))[:chars]
    return repeated


def make_round_messages(round_number: int, filler_chars: int) -> tuple[dict[str, str], dict[str, str]]:
    marker = MARKERS[round_number - 1]
    user = {
        "role": "user",
        "content": (
            f"Round {round_number}: continue the coding task. Record this durable fact exactly: "
            f"{marker}. Also keep the original objective and do not claim verification without evidence."
        ),
    }
    assistant = {
        "role": "assistant",
        "content": (
            f"I inspected the requested area for round {round_number}.\n{marker}\n"
            f"{filler(round_number, filler_chars)}"
        ),
    }
    return user, assistant


def action_prompt(round_number: int) -> str:
    return (
        f"After reset {round_number}, state the single next action. Include exactly "
        f"ACTION-{round_number}: verify the requested diff, and do not invent completed tests."
    )


def run_once(base_url: str, rounds: int, filler_chars: int, compact: bool) -> dict[str, Any]:
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "You are a conservative coding agent. Preserve durable constraints and answer "
                "only from the supplied transcript. The original objective is to inspect a "
                "small repository change and report the next safe action."
            ),
        },
        {
            "role": "user",
            "content": "Original objective: inspect the repository change, preserve every durable constraint, and verify before editing.",
        },
    ]
    resets: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []

    for round_number in range(1, rounds + 1):
        user, assistant = make_round_messages(round_number, filler_chars)
        messages.extend([user, assistant])
        compaction = None
        if compact:
            convo = "".join(serialize_for_summary(message) for message in messages[2:])
            response, _ = post_json(
                base_url,
                {
                    "model": "local",
                    "messages": [
                        {"role": "system", "content": COMPACTION_SYSTEM},
                        {"role": "user", "content": convo},
                    ],
                    "stream": False,
                    "temperature": 0.2,
                    "max_tokens": 2048,
                    "cache_prompt": True,
                },
            )
            summary = content(response).strip()
            if not summary:
                summary = f"[summary unavailable after reset {round_number}]"
            messages = messages[:2] + [
                {
                    "role": "user",
                    "content": (
                        f"[Resumen del contexto previo ({round_number} round(s) compactados)]:\n{summary}"
                    ),
                }
            ]
            compaction = {
                "round": round_number,
                "summaryChars": len(summary),
                "summaryMarkers": marker_hits(summary),
                "timing": timings(response),
            }
            resets.append(compaction)

        response, _ = post_json(
            base_url,
            {
                "model": "local",
                "messages": messages + [{"role": "user", "content": action_prompt(round_number)}],
                "stream": False,
                "temperature": 0.0,
                "max_tokens": 96,
                "cache_prompt": True,
            },
        )
        answer = content(response)
        action = {
            "round": round_number,
            "ok": f"ACTION-{round_number}:" in answer,
            "markers": marker_hits(answer),
            "content": answer[:1000],
            "timing": timings(response),
        }
        actions.append(action)
        messages.append({"role": "user", "content": action_prompt(round_number)})
        messages.append({"role": "assistant", "content": answer})

    response, _ = post_json(
        base_url,
        {
            "model": "local",
            "messages": messages + [
                {
                    "role": "user",
                    "content": (
                        "Final audit. List every KEEP marker that remains in the transcript and "
                        "state ACTION-FINAL: inspect the diff. Include the markers literally."
                    ),
                }
            ],
            "stream": False,
            "temperature": 0.0,
            "max_tokens": 256,
            "cache_prompt": True,
        },
    )
    final_answer = content(response)
    return {
        "mode": "compaction" if compact else "raw",
        "rounds": rounds,
        "fillerChars": filler_chars,
        "compactions": resets,
        "actions": actions,
        "final": {
            "ok": "ACTION-FINAL:" in final_answer and len(marker_hits(final_answer)) == len(MARKERS),
            "markers": marker_hits(final_answer),
            "content": final_answer[:2000],
            "timing": timings(response),
        },
    }


def summarize(runs: list[dict[str, Any]]) -> dict[str, Any]:
    compact_runs = [run for run in runs if run["mode"] == "compaction"]
    raw_runs = [run for run in runs if run["mode"] == "raw"]

    def action_rate(items: list[dict[str, Any]]) -> float:
        values = [action["ok"] for run in items for action in run["actions"]]
        return sum(values) / len(values) * 100.0 if values else 0.0

    def final_rate(items: list[dict[str, Any]]) -> float:
        return sum(run["final"]["ok"] for run in items) / len(items) * 100.0 if items else 0.0

    def med(items: list[dict[str, Any]], path: tuple[str, ...]) -> float:
        values: list[float] = []
        for run in items:
            for item in run["actions"] if path[0] == "actions" else [run["final"]]:
                value: Any = item
                for key in path[1:]:
                    value = value[key]
                values.append(float(value))
        return statistics.median(values) if values else 0.0

    return {
        "runs": len(runs),
        "compactionRuns": len(compact_runs),
        "rawRuns": len(raw_runs),
        "compactionActionRatePct": action_rate(compact_runs),
        "rawActionRatePct": action_rate(raw_runs),
        "compactionFinalRatePct": final_rate(compact_runs),
        "rawFinalRatePct": final_rate(raw_runs),
        "compactionActionWallMsP50": med(compact_runs, ("actions", "timing", "wallMs")),
        "rawActionWallMsP50": med(raw_runs, ("actions", "timing", "wallMs")),
        "compactionFinalWallMsP50": med(compact_runs, ("final", "timing", "wallMs")),
        "rawFinalWallMsP50": med(raw_runs, ("final", "timing", "wallMs")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8134")
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--filler-chars", type=int, default=2500)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.rounds <= len(MARKERS):
        parser.error(f"--rounds debe estar entre 1 y {len(MARKERS)}")
    if not 0 <= args.filler_chars <= 50000 or not 1 <= args.repeats <= 10:
        parser.error("filler/repeats fuera de rango")

    runs: list[dict[str, Any]] = []
    for _ in range(args.repeats):
        runs.append(run_once(args.url, args.rounds, args.filler_chars, compact=False))
        runs.append(run_once(args.url, args.rounds, args.filler_chars, compact=True))
    report = {
        "schema": "llamacode-compaction-quality-v1",
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "url": args.url,
        "rounds": args.rounds,
        "fillerChars": args.filler_chars,
        "repeats": args.repeats,
        "summary": summarize(runs),
        "runs": runs,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
