#!/usr/bin/env python3
"""Bounded read-then-write tool-call canary for the pinned TP=2 candidate."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


ARTIFACTS = Path(__file__).resolve().parents[1]
COMPOSE_DIR = Path("/media/cristian/HDD extra/Modelos-eval/Q85-HyperQwen/HyperQwen")
TEMP_ROOT = Path("/media/cristian/HDD extra/Modelos-eval/Q85-HyperQwen/tmp")
BASE_URL = "http://127.0.0.1:18142"
SOURCE_TEXT = "Q85-CANARY-READ-THEN-WRITE-314159"
CANARY_TOOL_CHOICE_MODE = os.getenv("Q101_CANARY_TOOL_CHOICE_MODE", "auto").strip().lower()
_enable_thinking_env = os.getenv("Q101_CANARY_ENABLE_THINKING")
CANARY_ENABLE_THINKING = (
    None if _enable_thinking_env is None else _enable_thinking_env.strip().lower() in {"1", "true", "yes", "on"}
)
_fixture_path_enum_env = os.getenv("Q101_CANARY_FIXTURE_PATH_ENUM", "0").strip().lower()
CANARY_FIXTURE_PATH_ENUM = _fixture_path_enum_env in {"1", "true", "yes", "on"}
_explicit_path_prompt_env = os.getenv("Q101_CANARY_EXPLICIT_PATH_PROMPT", "0").strip().lower()
CANARY_EXPLICIT_PATH_PROMPT = _explicit_path_prompt_env in {"1", "true", "yes", "on"}
CANARY_READ_MAX_TOKENS = int(os.getenv("Q101_CANARY_READ_MAX_TOKENS", "512"))
CANARY_WRITE_MAX_TOKENS = int(os.getenv("Q101_CANARY_WRITE_MAX_TOKENS", "1024"))
if CANARY_READ_MAX_TOKENS != 512 or CANARY_WRITE_MAX_TOKENS != 1024:
    raise RuntimeError("Q101 fixed caps must be read_file=512 and write_file=1024")


def read_api_key() -> str:
    env_path = COMPOSE_DIR / ".env"
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("VLLM_API_KEY="):
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                return value
    raise RuntimeError("local API key is missing")


def request_json(path: str, key: str, payload: dict | None = None) -> tuple[dict, float]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
        },
        method="GET" if data is None else "POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            result = json.loads(response.read())
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"HTTP {error.code} from {path}") from None
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(f"request failed for {path}: {type(error).__name__}") from None
    return result, (time.monotonic() - started) * 1000


def require_one_tool(response: dict, name: str) -> tuple[dict, dict]:
    choices = response.get("choices") or []
    if not choices:
        raise RuntimeError("completion returned no choices")
    message = choices[0].get("message") or {}
    calls = message.get("tool_calls") or []
    if len(calls) != 1:
        raise RuntimeError(f"expected exactly one {name} tool call")
    call = calls[0]
    if not call.get("id"):
        raise RuntimeError(f"{name} tool call had no call id")
    function = call.get("function") or {}
    if function.get("name") != name:
        raise RuntimeError(f"expected {name} as the next tool")
    try:
        args = json.loads(function.get("arguments") or "{}")
    except json.JSONDecodeError:
        raise RuntimeError(f"{name} arguments were not valid JSON") from None
    return message, {"call": call, "args": args}


def assistant_tool_message(message: dict) -> dict:
    return {
        "role": "assistant",
        "content": message.get("content"),
        "tool_calls": message.get("tool_calls"),
    }


def usage(response: dict) -> dict:
    value = response.get("usage") or {}
    return {
        "promptTokens": value.get("prompt_tokens"),
        "completionTokens": value.get("completion_tokens"),
        "totalTokens": value.get("total_tokens"),
    }


def tool_choice(name: str | None) -> str | dict:
    if name is None:
        return "none"
    if CANARY_TOOL_CHOICE_MODE == "auto":
        return "auto"
    if CANARY_TOOL_CHOICE_MODE == "named":
        return {"type": "function", "function": {"name": name}}
    raise RuntimeError("unsupported Q101_CANARY_TOOL_CHOICE_MODE")


def response_summary(response: dict) -> dict:
    choices = response.get("choices") or []
    choice = choices[0] if choices else {}
    message = choice.get("message") or {}
    content = message.get("content")
    calls = message.get("tool_calls") or []
    return {
        "finishReason": choice.get("finish_reason"),
        "contentCharCount": len(content) if isinstance(content, str) else 0,
        "toolCallCount": len(calls),
        "toolNames": [((call.get("function") or {}).get("name")) for call in calls],
        "usage": usage(response),
    }


def chat_template_parameters() -> dict:
    if CANARY_ENABLE_THINKING is None:
        return {}
    return {"chat_template_kwargs": {"enable_thinking": CANARY_ENABLE_THINKING}}


def path_parameter_schema(allowed_path: str) -> dict:
    schema = {"type": "string"}
    if CANARY_FIXTURE_PATH_ENUM:
        schema["enum"] = [allowed_path]
    return schema


def main() -> int:
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    receipt_path = ARTIFACTS / "receipts" / f"q101-tool-canary-{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    key = read_api_key()
    record = {
        "task": "Q-20261024-VF-ITERATION-101",
        "startedAtUtc": now.isoformat().replace("+00:00", "Z"),
        "candidateEndpoint": BASE_URL,
        "apiKeyRecorded": False,
        "protocol": {
            "temperature": 0.6,
            "topP": 0.95,
            "topK": 20,
            "minP": 0.0,
            "seed": 42,
            "toolChoiceMode": CANARY_TOOL_CHOICE_MODE,
            "enableThinking": CANARY_ENABLE_THINKING,
            "fixturePathEnum": CANARY_FIXTURE_PATH_ENUM,
            "explicitPathSchemaPrompt": CANARY_EXPLICIT_PATH_PROMPT,
            "toolReadMaxTokens": CANARY_READ_MAX_TOKENS,
            "toolWriteMaxTokens": CANARY_WRITE_MAX_TOKENS,
            "toolChoiceSequence": ["read_file", "write_file", "none"],
            "parallelToolCalls": False,
            "expectedToolSequence": ["read_file", "write_file"],
            "fixtureSha256": hashlib.sha256(SOURCE_TEXT.encode("utf-8")).hexdigest(),
            "filesystemScope": "unique temporary directory under the Q85 candidate HDD temp folder; no persistent files",
        },
        "calls": [],
        "status": "fail",
    }

    try:
        model_list, list_ms = request_json("/v1/models", key)
        model_data = model_list.get("data") or []
        if not model_data:
            raise RuntimeError("/v1/models returned no models")
        model = model_data[0]["id"]
        record["modelId"] = model
        record["modelsEndpointMs"] = round(list_ms, 2)

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the single-line source file in the canary workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": path_parameter_schema("source.txt")},
                        "required": ["path"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write the exact source line to the result file.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": path_parameter_schema("result.txt"),
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                        "additionalProperties": False,
                    },
                },
            },
        ]
        messages = [
            {
                "role": "system",
                "content": (
                    "Use the tools for all file access and edits. Do not invent file contents. "
                    "Call read_file and wait for its result before write_file. Use one tool call "
                    "at a time. Copy the one line from source.txt exactly to result.txt, with no "
                    "extra text or newline in the file. Do not claim success before write_file returns."
                    + (
                        " The exact allowed paths are source.txt for read_file and result.txt for write_file; "
                        "use each exact string with no prefix, directory, or other characters. Follow the tool schema."
                        if CANARY_EXPLICIT_PATH_PROMPT
                        else ""
                    )
                ),
            },
            {
                "role": "user",
                "content": "Read source.txt and create result.txt with exactly the same content.",
            },
        ]
        usage_totals = {"promptTokens": 0, "completionTokens": 0, "totalTokens": 0}

        with tempfile.TemporaryDirectory(prefix="q101-tool-canary-", dir=TEMP_ROOT) as directory:
            workspace = Path(directory)
            (workspace / "source.txt").write_bytes(SOURCE_TEXT.encode("utf-8"))

            response1, ms1 = request_json(
                "/v1/chat/completions",
                key,
                {
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": tool_choice("read_file"),
                    "parallel_tool_calls": False,
                    "temperature": 0.6,
                    "top_p": 0.95,
                    "top_k": 20,
                    "min_p": 0.0,
                    "seed": 42,
                    "max_tokens": CANARY_READ_MAX_TOKENS,
                    **chat_template_parameters(),
                },
            )
            record.setdefault("responseSummaries", []).append(
                {"stage": "read_file", "latencyMs": round(ms1, 2), **response_summary(response1)}
            )
            msg1, tool1 = require_one_tool(response1, "read_file")
            args1 = tool1["args"]
            read_path_matches = args1.get("path") == "source.txt"
            record.setdefault("argumentValidationSummaries", []).append(
                {
                    "stage": "read_file",
                    "pathIsString": isinstance(args1.get("path"), str),
                    "pathMatchesContract": read_path_matches,
                }
            )
            if not read_path_matches:
                raise RuntimeError("read_file requested a path outside the canary contract")
            source = (workspace / "source.txt").read_text(encoding="utf-8")
            messages.append(assistant_tool_message(msg1))
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool1["call"]["id"],
                    "content": json.dumps({"ok": True, "content": source}),
                }
            )
            record["calls"].append({"expected": "read_file", "latencyMs": round(ms1, 2), **usage(response1)})
            for k, v in usage(response1).items():
                if isinstance(v, int):
                    usage_totals[k] += v

            response2, ms2 = request_json(
                "/v1/chat/completions",
                key,
                {
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": tool_choice("write_file"),
                    "parallel_tool_calls": False,
                    "temperature": 0.6,
                    "top_p": 0.95,
                    "top_k": 20,
                    "min_p": 0.0,
                    "seed": 42,
                    "max_tokens": CANARY_WRITE_MAX_TOKENS,
                    **chat_template_parameters(),
                },
            )
            record.setdefault("responseSummaries", []).append(
                {"stage": "write_file", "latencyMs": round(ms2, 2), **response_summary(response2)}
            )
            msg2, tool2 = require_one_tool(response2, "write_file")
            args2 = tool2["args"]
            write_path_matches = args2.get("path") == "result.txt"
            content_is_string = isinstance(args2.get("content"), str)
            content_matches_fixture = (
                content_is_string and args2["content"].encode("utf-8") == SOURCE_TEXT.encode("utf-8")
            )
            record.setdefault("argumentValidationSummaries", []).append(
                {
                    "stage": "write_file",
                    "pathIsString": isinstance(args2.get("path"), str),
                    "pathMatchesContract": write_path_matches,
                    "contentIsString": content_is_string,
                    "contentMatchesFixture": content_matches_fixture,
                }
            )
            if not write_path_matches or not content_is_string:
                raise RuntimeError("write_file arguments violated the canary contract")
            (workspace / "result.txt").write_bytes(args2["content"].encode("utf-8"))
            messages.append(assistant_tool_message(msg2))
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool2["call"]["id"],
                    "content": json.dumps({"ok": True, "bytesWritten": (workspace / "result.txt").stat().st_size}),
                }
            )
            record["calls"].append({"expected": "write_file", "latencyMs": round(ms2, 2), **usage(response2)})
            for k, v in usage(response2).items():
                if isinstance(v, int):
                    usage_totals[k] += v

            response3, ms3 = request_json(
                "/v1/chat/completions",
                key,
                {
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": tool_choice(None),
                    "parallel_tool_calls": False,
                    "temperature": 0.6,
                    "top_p": 0.95,
                    "top_k": 20,
                    "min_p": 0.0,
                    "seed": 42,
                    "max_tokens": 128,
                    **chat_template_parameters(),
                },
            )
            record.setdefault("responseSummaries", []).append(
                {"stage": "final", "latencyMs": round(ms3, 2), **response_summary(response3)}
            )
            msg3 = (response3.get("choices") or [{}])[0].get("message") or {}
            if msg3.get("tool_calls"):
                raise RuntimeError("model issued an unexpected extra tool call")
            final_text = msg3.get("content")
            if not isinstance(final_text, str) or not final_text.strip():
                raise RuntimeError("model returned an empty final response")
            output = (workspace / "result.txt").read_bytes()
            expected = SOURCE_TEXT.encode("utf-8")
            record["calls"].append({"expected": "final response", "latencyMs": round(ms3, 2), **usage(response3)})
            for k, v in usage(response3).items():
                if isinstance(v, int):
                    usage_totals[k] += v
            record["toolSequence"] = ["read_file", "write_file"]
            record["outputSha256"] = hashlib.sha256(output).hexdigest()
            record["outputByteCount"] = len(output)
            record["outputMatchesExpected"] = output == expected
            record["finalResponsePresent"] = True
            record["finalResponseSha256"] = hashlib.sha256(final_text.encode("utf-8")).hexdigest()
            record["usageTotals"] = usage_totals
            if output != expected:
                raise RuntimeError("result.txt did not exactly match source.txt")
            record["status"] = "pass"
            record["completedAtUtc"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    except Exception as error:  # preserve a concise, secret-free failure receipt
        record["failure"] = f"{type(error).__name__}: {error}"
        record["completedAtUtc"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    finally:
        receipt_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.chmod(receipt_path, 0o644)

    print("TOOL_CANARY_STATUS", record["status"])
    print("TOOL_CANARY_MODEL", record.get("modelId", "unavailable"))
    print("TOOL_CANARY_SEQUENCE", ",".join(record.get("toolSequence", [])))
    print("TOOL_CANARY_RECEIPT", receipt_path)
    if record["status"] != "pass":
        print("TOOL_CANARY_FAILURE", record.get("failure", "unknown"))
        return 1
    print("TOOL_CANARY_OUTPUT_MATCH", record["outputMatchesExpected"])
    print("TOOL_CANARY_USAGE", json.dumps(record.get("usageTotals", {}), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
