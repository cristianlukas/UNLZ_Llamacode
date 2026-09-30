#!/usr/bin/env python3
"""Repeat a fixed coding prompt and save llama-server timing metrics."""
import argparse
import json
import statistics
import time
from pathlib import Path
from urllib.request import Request, urlopen


PROMPT = "Escribí una función Python llamada add(a, b) que devuelva a + b. Incluí una docstring breve y un ejemplo de uso."
SYSTEM = "Sos un asistente de programación. Respondé sólo con la función pedida."


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", default="http://127.0.0.1:8130/v1/chat/completions")
    p.add_argument("--model", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--passes", type=int, default=5)
    a = p.parse_args()
    rows = []
    for i in range(a.passes):
        payload = {
            "model": a.model,
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": PROMPT}],
            "temperature": 0.6, "top_p": 0.95, "top_k": 20, "min_p": 0.0,
            "seed": 42, "max_tokens": 128,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        req = Request(a.url, data=json.dumps(payload, ensure_ascii=False).encode(), headers={"Content-Type": "application/json"})
        start = time.perf_counter()
        try:
            with urlopen(req, timeout=180) as response:
                result = json.load(response)
            rows.append({"pass": i + 1, "transportOk": True, "wallMs": round((time.perf_counter() - start) * 1000, 2),
                         "timings": result.get("timings", {}), "usage": result.get("usage", {}),
                         "content": result["choices"][0]["message"].get("content", "")})
        except Exception as exc:
            rows.append({"pass": i + 1, "transportOk": False, "error": f"{type(exc).__name__}: {exc}"})
        print(f"{i + 1}/{a.passes}: {rows[-1].get('timings', {}).get('predicted_per_second')} tok/s", flush=True)
    good = [r["timings"]["predicted_per_second"] for r in rows if r["transportOk"] and "predicted_per_second" in r["timings"]]
    report = {"benchmark": "fixed_short_coding_decode", "model": a.model, "prompt": PROMPT,
              "temperature": 0.6, "topP": 0.95, "topK": 20, "minP": 0.0, "seed": 42,
              "reasoning": "off", "passes": a.passes,
              "medianDecodeTps": statistics.median(good) if good else None, "rows": rows}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if len(good) == a.passes else 2


if __name__ == "__main__":
    raise SystemExit(main())
