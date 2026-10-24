"""Small helpers for Q100's fail-fast, loopback tool guard."""
from __future__ import annotations

import json
from pathlib import Path


def clear_proxy_log(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("")


def first_blocked_tool_call(path: Path) -> list[str] | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return None
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue  # Ignore a partially written final line; the next poll retries.
        if row.get("blockedToolCall"):
            return [str(name) for name in row.get("observedToolNames", [])]
    return None
