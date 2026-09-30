#!/usr/bin/env python3
"""Run the existing Computer Use order benchmark with thinking disabled."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import benchmark_computer_use_prompt_order as benchmark  # noqa: E402

request_json = benchmark.request_json


def request_without_thinking(url: str, payload: dict, timeout: float):
    payload["chat_template_kwargs"] = {"enable_thinking": False}
    return request_json(url, payload, timeout)


def main() -> int:
    benchmark.request_json = request_without_thinking
    result = benchmark.main()
    # The report path is the argument supplied to the underlying CLI.
    for index, value in enumerate(sys.argv[:-1]):
        if value == "--out":
            report_path = Path(sys.argv[index + 1])
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["chatTemplateKwargs"] = {"enable_thinking": False}
            report["reasoningMode"] = "disabled for parity with the tool contract run"
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            break
    return result


if __name__ == "__main__":
    raise SystemExit(main())
