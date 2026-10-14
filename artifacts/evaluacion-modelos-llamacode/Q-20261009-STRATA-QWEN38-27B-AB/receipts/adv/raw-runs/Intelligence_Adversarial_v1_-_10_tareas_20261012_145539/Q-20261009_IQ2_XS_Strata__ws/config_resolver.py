"""Resolve $NAME variable interpolation in a config dict."""

import copy
import re

_NAME_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")


def _resolve_value(value, env):
    if isinstance(value, dict):
        return {key: _resolve_value(value[key], env) for key in value}
    if isinstance(value, list):
        return [_resolve_value(item, env) for item in value]
    if isinstance(value, str):
        # Exact "$NAME": the whole string is replaced by env[NAME], preserving
        # the variable's type.
        if _NAME_RE.fullmatch(value):
            name = value[1:]
            if name not in env:
                raise KeyError(name)
            return copy.deepcopy(env[name])

        # Interpolation inside text: replace every valid $NAME occurrence.
        # A '$' without a valid name is left untouched.
        out = ""
        pos = 0
        for match in _NAME_RE.finditer(value):
            name = match.group(1)
            if name not in env:
                raise KeyError(name)
            out += value[pos:match.start()]
            out += str(env[name])
            pos = match.end()
        out += value[pos:]
        return out
    return copy.deepcopy(value)


def resolve_config(config, env):
    """Return a deep copy of config with $NAME variables resolved from env.

    - Strings exactly of the form $NAME become env[NAME] (type preserved).
    - Strings containing $NAME inside text have every occurrence replaced.
    - Dicts and lists are resolved recursively; non-string values keep types.
    - Raises KeyError on the first missing variable.
    - A lone '$' without a valid name is not expanded.
    - config and env are not mutated.
    """
    if not isinstance(config, dict):
        raise TypeError("config must be a dict")
    if not isinstance(env, dict):
        raise TypeError("env must be a dict")
    return {key: _resolve_value(config[key], env) for key in config}
