"""Strict tool-call request parser."""

import os
import re

ALLOWED_METHODS = ("read_file", "write_file")
ALLOWED_TOP_LEVEL = ("method", "args")
ALLOWED_ARGS = {"read_file": ("path",), "write_file": ("path", "content")}


def _check_path(path):
    if not isinstance(path, str):
        raise ValueError("args.path must be a string")
    if "\x00" in path:
        raise ValueError("args.path must not contain NUL bytes")
    if os.path.isabs(path) or re.match(r"^[A-Za-z]:", path):
        raise ValueError("args.path must be a relative path")
    if any(part == ".." for part in path.replace("\\", "/").split("/")):
        raise ValueError("args.path must not contain '..' traversal")
    if not path:
        raise ValueError("args.path must not be empty")


def parse_tool_call(payload):
    """Validate a tool-call payload and return a new normalized dict.

    Accepts only a dict with 'method' in {read_file, write_file} and 'args'.
    - read_file requires args.path.
    - write_file requires args.path and args.content (string).
    Rejects unknown methods, wrong arg types, missing required fields,
    absolute paths, '..' traversal, NUL bytes and any extra field in the
    request or args. Never mutates payload.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object (dict)")

    extra = [key for key in payload if key not in ALLOWED_TOP_LEVEL]
    if extra:
        raise ValueError(f"unexpected field(s) in request: {sorted(extra)}")

    method = payload.get("method")
    if method not in ALLOWED_METHODS:
        raise ValueError(f"unknown method: {method!r} (allowed: {list(ALLOWED_METHODS)})")

    args = payload.get("args")
    if not isinstance(args, dict):
        raise ValueError("args must be a JSON object (dict)")

    allowed = ALLOWED_ARGS[method]
    extra_args = [key for key in args if key not in allowed]
    if extra_args:
        raise ValueError(f"unexpected field(s) in args: {sorted(extra_args)}")

    for field in allowed:
        if field not in args:
            raise ValueError(f"missing required field: args.{field}")

    normalized_args = {}
    _check_path(args["path"])
    normalized_args["path"] = args["path"]

    if method == "write_file":
        content = args["content"]
        if not isinstance(content, str):
            raise ValueError("args.content must be a string")
        if "\x00" in content:
            raise ValueError("args.content must not contain NUL bytes")
        normalized_args["content"] = content

    return {"method": method, "args": normalized_args}
