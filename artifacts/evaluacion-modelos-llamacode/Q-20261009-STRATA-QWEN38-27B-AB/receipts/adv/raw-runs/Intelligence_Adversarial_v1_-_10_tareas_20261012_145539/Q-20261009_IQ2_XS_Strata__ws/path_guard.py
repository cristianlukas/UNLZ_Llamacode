"""Safe path joining inside a root directory."""

import os
import re


def safe_join(root, user_path):
    """Return the real absolute path of user_path inside root.

    Accepts normal subdirectories and root itself. Raises ValueError for:
    - absolute user_path
    - traversal with '..'
    - NUL bytes
    - any path whose realpath escapes root (existing symlinks are resolved
      before the boundary check, so links leaving root are rejected).

    The boundary check uses os.path.commonpath, not textual prefix matching.
    """
    if not isinstance(user_path, str):
        raise ValueError("user_path must be a string")

    if "\x00" in user_path:
        raise ValueError("NUL byte in path")

    if os.path.isabs(user_path) or re.match(r"^[A-Za-z]:", user_path):
        raise ValueError("absolute path not allowed")

    parts = user_path.replace("\\", "/").split("/")
    if any(part == ".." for part in parts):
        raise ValueError("path traversal not allowed")

    root_real = os.path.realpath(root)
    candidate = os.path.realpath(os.path.join(root_real, user_path))

    if os.path.commonpath([root_real, candidate]) != root_real:
        raise ValueError("path escapes root")

    return candidate
