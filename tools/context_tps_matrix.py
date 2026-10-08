"""Measure short-prompt generation TPS at several server context sizes."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.kv_cache_ab import (
    _join_url,
    normalize_server_args,
    start_server,
    wait_for_server,
)
from tools.long_context_matrix import parse_contexts, render_context_args, validate_config


def request_completion(base_url: str, n_predict: int, timeout: float) -> Dict[str, Any]:
    payload = {
        "model": "benchmark",
        "messages": [{
            "role": "user",
            "content": "Write a short Python function named add(a, b) that returns a + b.",
        }],
        "max_tokens": n_predict,
        "temperature": 0.0,
        "top_p": 1.0,
        "top_k": 20,
        "seed": 4242,
        "cache_prompt": False,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    request = Request(
        f"{base_url}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    timings: Dict[str, Any] = {}
    content: List[str] = []
    usage: Dict[str, Any] = {}
    with urlopen(request, timeout=timeout) as response:
        for raw_line in response:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line.startswith("data: "):
                continue
            data = line[6:]
            if data == "[DONE]":
                continue
            item = json.loads(data)
            if isinstance(item.get("timings"), dict):
                timings.update(item["timings"])
            if isinstance(item.get("usage"), dict):
                usage.update(item["usage"])
            choices = item.get("choices") or []
            if choices and isinstance(choices[0], dict):
                delta = choices[0].get("delta") or {}
                if isinstance(delta, dict):
                    content.append(str(delta.get("content") or ""))
    return {"timings": timings, "usage": usage, "content": "".join(content)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--contexts", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--log-dir", required=True, type=Path)
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--startup-timeout", type=float, default=300.0)
    parser.add_argument("--request-timeout", type=float, default=180.0)
    parser.add_argument("--n-predict", type=int, default=64)
    args = parser.parse_args()

    config = validate_config(json.loads(args.config.read_text(encoding="utf-8")))
    contexts = parse_contexts(args.contexts)
    args.log_dir.mkdir(parents=True, exist_ok=True)
    base_args = config["commonArgs"] + config["variant"]["args"]
    rows: List[Dict[str, Any]] = []
    started = time.time()

    for context in contexts:
        log_path = args.log_dir / f"context-{context}.log"
        rendered = render_context_args(base_args, context)
        command = normalize_server_args(
            rendered, config["modelPath"], "127.0.0.1", args.port, add_metrics=True
        )
        row: Dict[str, Any] = {
            "contextTokens": context,
            "variant": config["variant"]["id"],
            "command": [config["serverExe"], *command],
            "logPath": str(log_path),
            "passed": False,
        }
        server = None
        try:
            server = start_server(
                Path(config["serverExe"]), command, config["variant"]["env"],
                log_path, config["launcher"]
            )
            wait_for_server(_join_url("127.0.0.1", args.port), args.startup_timeout, server.process)
            response = request_completion(
                _join_url("127.0.0.1", args.port), args.n_predict, args.request_timeout
            )
            timings = response.get("timings", {})
            row.update({
                "passed": True,
                "promptTokens": timings.get("prompt_n"),
                "predictedTokens": timings.get("predicted_n"),
                "promptTps": timings.get("prompt_per_second"),
                "genTps": timings.get("predicted_per_second"),
                "promptMs": timings.get("prompt_ms"),
                "predictedMs": timings.get("predicted_ms"),
                "contentPreview": str(response.get("content", ""))[:160],
            })
        except Exception as error:  # noqa: BLE001 - preserve per-context failures
            row["error"] = str(error)
        finally:
            if server is not None:
                row["serverExitCode"] = server.stop()
        rows.append(row)
        print(f"[context-tps] {context}: {'PASS' if row['passed'] else 'FAIL'}", flush=True)

    report = {
        "schema": "llamacode-context-tps-matrix-v1",
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsedSec": time.time() - started,
        "configPath": str(args.config.resolve()),
        "variant": config["variant"]["id"],
        "modelPath": config["modelPath"],
        "contexts": contexts,
        "nPredict": args.n_predict,
        "rows": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0 if all(row["passed"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
