#!/usr/bin/env python3
"""Record llama.cpp slot progress while a benchmark runs."""
import argparse
import json
import pathlib
import time
import urllib.request
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:18112")
    parser.add_argument("--out", required=True)
    parser.add_argument("--interval", type=int, default=15)
    parser.add_argument("--max-seconds", type=int, default=2100)
    args = parser.parse_args()
    output = pathlib.Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + args.max_seconds
    while time.monotonic() < deadline:
        row = {"time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")}
        try:
            with urllib.request.urlopen(args.base + "/slots", timeout=10) as response:
                slots = json.loads(response.read().decode())
            row["slots"] = [{k: slot.get(k) for k in (
                "id", "is_processing", "id_task", "n_prompt_tokens",
                "n_prompt_tokens_processed", "n_prompt_tokens_cache", "next_token")}
                for slot in slots]
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
        with output.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(json.dumps(row, ensure_ascii=False), flush=True)
        time.sleep(max(1, args.interval))


if __name__ == "__main__":
    main()
