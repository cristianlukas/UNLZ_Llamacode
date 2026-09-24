#!/usr/bin/env python3
"""Measure prompt cost of retained versus stale multimodal history.

The runner mirrors LlamaAgentBackend::trimStaleImages for benchmark purposes.
It does not claim visual quality when the endpoint is text-only; reports mark
that dimension as unavailable instead of converting it to a zero.
"""

from __future__ import annotations

import argparse
import base64
import json
import statistics
import struct
import time
import zlib
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def png_data_uri(red: int, green: int, blue: int) -> str:
    raw = bytes([0, red, green, blue, 255])
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def has_image(message: Mapping[str, Any]) -> bool:
    return any(part.get("type") == "image_url" for part in message.get("content", []) or []
               if isinstance(part, Mapping))


def trim_stale_images(messages: Sequence[Mapping[str, Any]], keep_last: int) -> list[dict[str, Any]]:
    image_indices = [index for index in range(len(messages) - 1, -1, -1) if has_image(messages[index])]
    rank = {index: position for position, index in enumerate(image_indices)}
    output: list[dict[str, Any]] = []
    for index, original in enumerate(messages):
        message = json.loads(json.dumps(original))
        if index not in rank or rank[index] < keep_last:
            output.append(message)
            continue
        parts = [part for part in message.get("content", []) if part.get("type") != "image_url"]
        parts.append({"type": "text", "text": "[captura de pantalla omitida: desactualizada]"})
        message["content"] = parts
        output.append(message)
    return output


def request(url: str, payload: Mapping[str, Any], timeout: float) -> tuple[dict[str, Any] | None, str, float]:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    req = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    started = time.perf_counter()
    try:
        with urlopen(req, timeout=timeout) as reply:
            return json.loads(reply.read().decode("utf-8")), "", (time.perf_counter() - started) * 1000
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return None, f"{type(exc).__name__}: {exc}", (time.perf_counter() - started) * 1000


def usage(data: Mapping[str, Any] | None, key: str) -> int | None:
    try:
        value = (data or {}).get("usage", {}).get(key)
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8080/v1/chat/completions")
    parser.add_argument("--model", default="")
    parser.add_argument("--histories", default="1,2,5,10")
    parser.add_argument("--keep-last", default="0,1,2")
    parser.add_argument("--passes", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    histories = [int(item) for item in args.histories.split(",") if item.strip()]
    keeps = [int(item) for item in args.keep_last.split(",") if item.strip()]
    if args.passes < 1 or any(value < 0 for value in histories + keeps):
        parser.error("historias/keep-last/passes inválidos")
    rows: list[dict[str, Any]] = []
    for history in histories:
        messages: list[dict[str, Any]] = [{"role": "system", "content": "Describí sólo la última captura."}]
        for index in range(history):
            messages.append({"role": "user", "content": [
                {"type": "text", "text": f"Captura histórica {index + 1}."},
                {"type": "image_url", "image_url": {"url": png_data_uri(index * 17 % 255, 40, 220)}},
            ]})
        for keep in keeps:
            wire = trim_stale_images(messages, keep)
            for pass_number in range(1, args.passes + 1):
                payload: dict[str, Any] = {"messages": wire, "temperature": 0.0, "max_tokens": 32, "stream": False}
                if args.model:
                    payload["model"] = args.model
                data, error, wall = request(args.url, payload, args.timeout)
                rows.append({
                    "historyImages": history, "keepLastImages": keep, "pass": pass_number,
                    "transportOk": data is not None, "wallMs": round(wall, 2),
                    "wireBytes": len(json.dumps(wire, ensure_ascii=False, separators=(",", ":")).encode()),
                    "imageMessagesOnWire": sum(has_image(item) for item in wire),
                    "promptTokens": usage(data, "prompt_tokens"), "error": error,
                })
    summary: dict[str, Any] = {}
    for history in histories:
        for keep in keeps:
            sample = [row for row in rows if row["historyImages"] == history and row["keepLastImages"] == keep]
            ok = [row for row in sample if row["transportOk"]]
            summary[f"history={history};keep={keep}"] = {
                "historyImages": history, "keepLastImages": keep, "runs": len(sample),
                "transportPct": 100.0 * len(ok) / len(sample) if sample else 0.0,
                "medianWireBytes": statistics.median(row["wireBytes"] for row in ok) if ok else None,
                "medianPromptTokens": statistics.median(row["promptTokens"] for row in ok if row["promptTokens"] is not None) if any(row["promptTokens"] is not None for row in ok) else None,
                "medianWallMs": statistics.median(row["wallMs"] for row in ok) if ok else None,
                "imageMessagesOnWire": sorted({row["imageMessagesOnWire"] for row in sample}),
            }
    report = {"schema": "llamacode-image-history-benchmark-v1", "url": args.url,
              "model": args.model, "passes": args.passes, "summary": summary, "rows": rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("history keep transport median_bytes median_prompt median_ms images_on_wire")
    for item in summary.values():
        print(f"{item['historyImages']:>7} {item['keepLastImages']:>4} {item['transportPct']:>9.2f}% "
              f"{str(item['medianWireBytes']):>13} {str(item['medianPromptTokens']):>13} "
              f"{str(item['medianWallMs']):>10} {item['imageMessagesOnWire']}")
    print(f"reporte={args.out}")
    return 0 if all(item["transportPct"] == 100.0 for item in summary.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
