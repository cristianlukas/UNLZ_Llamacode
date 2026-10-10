import os
import re

_DRIVE_RE = re.compile(r"^(?:[A-Za-z]:|//|\\\\)")


def _reject_traversal(user_path):
    parts = user_path.replace("\\", "/").split("/")
    if any(part == ".." for part in parts):
        raise ValueError("path traversal ('..') is not allowed")


def safe_join(root, user_path):
    if not isinstance(user_path, str):
        raise ValueError("user_path must be a string")
    if "\x00" in user_path:
        raise ValueError("NUL byte in path is not allowed")
    if os.path.isabs(user_path) or os.path.splitdrive(user_path)[0]:
        raise ValueError("user_path must be relative to root")
    normalized = user_path.replace("\\", "/")
    if os.path.isabs(normalized) or _DRIVE_RE.match(user_path):
        raise ValueError("user_path must be relative to root")
    _reject_traversal(user_path)
    root_real = os.path.realpath(root)
    if not os.path.isdir(root_real):
        raise ValueError("root must be an existing directory")
    candidate = os.path.join(root_real, user_path)
    resolved = os.path.realpath(candidate)
    try:
        common = os.path.commonpath([root_real, resolved])
    except ValueError:
        raise ValueError("path escapes root")
    if common != root_real:
        raise ValueError("path escapes root")
    return resolved
