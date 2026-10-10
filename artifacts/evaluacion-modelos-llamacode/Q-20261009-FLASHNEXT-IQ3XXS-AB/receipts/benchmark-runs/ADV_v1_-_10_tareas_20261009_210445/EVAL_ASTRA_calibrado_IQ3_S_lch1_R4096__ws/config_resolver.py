import copy
import re

_VAR_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")


def _lookup(name, env):
    if name not in env:
        raise KeyError(name)
    return env[name]


def _resolve_value(value, env):
    if isinstance(value, str):
        exact = _VAR_RE.fullmatch(value)
        if exact:
            return copy.deepcopy(_lookup(exact.group(1), env))
        parts = []
        position = 0
        for match in _VAR_RE.finditer(value):
            parts.append(value[position:match.start()])
            replacement = _lookup(match.group(1), env)
            parts.append(replacement if isinstance(replacement, str) else str(replacement))
            position = match.end()
        parts.append(value[position:])
        return "".join(parts)
    if isinstance(value, dict):
        return {key: _resolve_value(item, env) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_value(item, env) for item in value]
    return copy.deepcopy(value)


def resolve_config(config, env):
    return _resolve_value(config, env)
