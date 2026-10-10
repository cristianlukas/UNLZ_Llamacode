"""resolve_config: resuelve referencias $NAME en un dict JSON-like.

- Un string exactamente con forma "$NAME" se reemplaza por env[NAME] (valor tal cual).
- Un string con interpolaciones "$NAME" dentro del texto reemplaza todas las variables.
- Resuelve recursivamente dicts y listas; preserva tipos de valores no string.
- Lanzá KeyError con la primera variable ausente.
- No expande '$' que no tenga nombre valido.
- No muta config ni env: devuelve una copia profunda.
"""

import re

# Nombre de variable: letra o guion bajo, seguido de letras, digitos o guion bajo.
_NAME_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")


def _lookup(name, env):
    if name not in env:
        raise KeyError(name)
    return env[name]


def _resolve_string(value, env):
    # Forma exacta: "$NAME" -> env[NAME] (preserva el tipo del valor).
    if _NAME_RE.fullmatch(value):
        return _lookup(_NAME_RE.fullmatch(value).group(1), env)

    # Interpolacion: reemplaza todas las ocurrencias de "$NAME" dentro del texto.
    def replace(match):
        return str(_lookup(match.group(1), env))

    return _NAME_RE.sub(replace, value)


def _resolve(value, env):
    if isinstance(value, str):
        return _resolve_string(value, env)
    if isinstance(value, dict):
        # Claves sin interpolar (se copian tal cual); valores resueltos.
        return {key: _resolve(item, env) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve(item, env) for item in value]
    if isinstance(value, tuple):
        return tuple(_resolve(item, env) for item in value)
    # Tipos no string (int, float, bool, None, etc.) se preservan sin tocar.
    return value


def resolve_config(config, env):
    if not isinstance(env, dict):
        raise ValueError("env debe ser un dict de variables")

    return _resolve(config, env)
