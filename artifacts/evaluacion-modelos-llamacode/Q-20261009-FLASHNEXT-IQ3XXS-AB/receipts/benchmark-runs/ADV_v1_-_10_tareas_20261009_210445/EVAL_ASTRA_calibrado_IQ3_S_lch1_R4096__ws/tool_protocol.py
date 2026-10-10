import os
import re

_ALLOWED_METHODS = ("read_file", "write_file")
_REQUIRED_ARGS = {"read_file": ("path",), "write_file": ("path", "content")}
_DRIVE_RE = re.compile(r"^(?:[A-Za-z]:|//|\\\\)")


def _validate_path(path):
    if not isinstance(path, str):
        raise ValueError("args.path must be a string")
    if "\x00" in path:
        raise ValueError("args.path must not contain a NUL byte")
    if os.path.isabs(path) or os.path.splitdrive(path)[0]:
        raise ValueError("args.path must be a relative path")
    if os.path.isabs(path.replace("\\", "/")) or _DRIVE_RE.match(path):
        raise ValueError("args.path must be a relative path")
    if any(part == ".." for part in path.replace("\\", "/").split("/")):
        raise ValueError("args.path must not contain '..' traversal")
    return path


def parse_tool_call(payload):
    if not isinstance(payload, dict):
        raise ValueError("tool call must be a JSON object")

    extra_top = set(payload) - {"method", "args"}
    if extra_top:
        raise ValueError(
            "unexpected field(s) in request: " + ", ".join(sorted(extra_top))
        )

    if "method" not in payload:
        raise ValueError("missing required field: method")
    method = payload["method"]
    if not isinstance(method, str) or method not in _ALLOWED_METHODS:
        raise ValueError("unsupported method: " + repr(method))

    if "args" not in payload:
        raise ValueError("missing required field: args")
    raw_args = payload["args"]
    if not isinstance(raw_args, dict):
        raise ValueError("args must be a JSON object")

    required = _REQUIRED_ARGS[method]
    extra_args = set(raw_args) - set(required)
    if extra_args:
        raise ValueError(
            "unexpected field(s) in args: " + ", ".join(sorted(extra_args))
        )
    for name in required:
        if name not in raw_args:
            raise ValueError("missing required field: args." + name)

    args = {"path": _validate_path(raw_args["path"])}
    if method == "write_file":
        content = raw_args["content"]
        if not isinstance(content, str):
            raise ValueError("args.content must be a string")
        args["content"] = content

    return {"method": method, "args": args}
