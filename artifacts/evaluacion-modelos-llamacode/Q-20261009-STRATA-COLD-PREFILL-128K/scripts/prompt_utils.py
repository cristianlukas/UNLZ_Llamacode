#!/usr/bin/env python3
"""Helpers that use Strata's own tokenizer and Responses prompt renderer."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

TASK = Path(__file__).resolve().parents[1]
REPO = TASK.parents[2]
STRATA = Path("/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source")
sys.path.insert(0, str(STRATA))
sys.path.insert(0, str(STRATA / "serve"))
sys.path.insert(0, str(STRATA / "tools"))

import strata_tokenizer as ST  # noqa: E402
import serve.responses as responses  # noqa: E402
import serve.server as server  # noqa: E402
from serve.frontend import ChatTemplate  # noqa: E402


def load_prompt_renderer(config_path: Path):
    cfg = json.loads(config_path.read_text())
    tpath = Path(cfg["tokenizer"])
    vocab = json.loads((tpath / "vocab.json").read_text(encoding="utf-8"))
    tokens = [None] * len(vocab)
    for token, token_id in vocab.items():
        tokens[token_id] = token
    merges = (tpath / "merges.txt").read_text(encoding="utf-8").split("\n")
    types = json.loads((tpath / "token_type.json").read_text())
    tok = ST.Tokenizer(tokens, merges, types)
    template_path = tpath / "chat_template.jinja"
    svc = server.Service(None, tok, ChatTemplate(template_path), model_name=cfg["model_name"],
                         sampling_defaults=cfg.get("sampling", {}))
    return cfg, svc


def count_prompt(svc, req: dict, keep_compaction_tools: bool) -> tuple[int, list[int], list[dict] | None]:
    messages = responses.input_messages(req)
    tools, _names, _skipped = responses.request_tools(req)
    shown = tools
    if keep_compaction_tools:
        shown = responses.prompt_tools(req, tools)
    kwargs = responses.template_kwargs(req, svc.shared)
    ids = svc.encode_prompt(messages, shown, kwargs)
    if keep_compaction_tools:
        responses.prompt_made(req, shown)
    return len(ids), ids, shown


def codex_metadata(kind: str, session_id: str, thread_id: str) -> dict:
    return {
        "session_id": session_id,
        "thread_id": thread_id,
        "x-codex-turn-metadata": json.dumps({
            "session_id": session_id,
            "thread_id": thread_id,
            "request_kind": kind,
        }),
    }


def base_request(input_items: list[dict], kind: str, session_id: str, thread_id: str,
                 tools: list[dict] | None, max_output_tokens: int) -> dict:
    return {
        "model": "qwen3.8-flash-next-astra-iq3_s-calibrated",
        "instructions": "You are testing context handling. Follow the user's exact instruction.",
        "input": input_items,
        "tools": tools or [],
        "tool_choice": "auto",
        "parallel_tool_calls": False,
        "max_output_tokens": max_output_tokens,
        "reasoning": {"effort": "none"},
        "temperature": 0.6,
        "top_p": 0.95,
        "top_k": 20,
        "min_p": 0.0,
        "repetition_penalty": 1.0,
        "presence_penalty": 0.0,
        "seed": 42,
        "store": False,
        "client_metadata": codex_metadata(kind, session_id, thread_id),
    }


def load_scenario(path: Path | None = None) -> dict:
    p = path or TASK / "inputs" / "scenario.json"
    return json.loads(p.read_text())


def make_tools() -> list[dict]:
    return [{
        "type": "function",
        "name": "inspect_workspace",
        "description": "Read-only inspection helper for an isolated coding workspace.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Relative path to inspect."}},
            "required": ["path"],
            "additionalProperties": False,
        },
    }]


def messages_for_initial(scenario: dict) -> list[dict]:
    return [{"type": "message", "role": "user", "content": scenario["initial_user_message"]}]


def messages_for_compaction(scenario: dict, first_response: dict) -> list[dict]:
    items = [{"type": "message", "role": "user", "content": scenario["initial_user_message"]}]
    items.extend(first_response.get("output", []))
    for item in first_response.get("output", []):
        if item.get("type") in ("function_call", "custom_tool_call"):
            items.append({"type": "function_call_output", "call_id": item.get("call_id"),
                          "output": "Read-only evaluation stub: no external action was performed."})
    items.append({"type": "message", "role": "user", "content": scenario["compaction_user_message"]})
    return items
