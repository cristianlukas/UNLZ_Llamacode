"""parse_tool_call: valida y normaliza un request de tool call (read_file / write_file)."""

import os

ALLOWED_METHODS = ("read_file", "write_file")

REQUIRED_ARGS = {
    "read_file": ("path",),
    "write_file": ("path", "content"),
}

ALLOWED_ARGS = {
    "read_file": frozenset(("path",)),
    "write_file": frozenset(("path", "content")),
}


def _reject(reason, payload_repr):
    raise ValueError("tool call invalido: {} ({})".format(reason, payload_repr))


def _validate_path(path, payload_repr):
    if not isinstance(path, str):
        _reject("args.path debe ser string", payload_repr)
    if path == "":
        _reject("args.path vacio", payload_repr)
    if "\x00" in path:
        _reject("args.path contiene NUL", payload_repr)
    if os.path.isabs(path):
        _reject("args.path no puede ser absoluta: {!r}".format(path), payload_repr)
    separators = [os.sep] + ([os.altsep] if os.altsep else [])
    parts = [path]
    for sep in separators:
        parts = [chunk for part in parts for chunk in part.split(sep)]
    for part in parts:
        if part == os.pardir:
            _reject("args.path no puede contener '..': {!r}".format(path), payload_repr)
    return path


def _parse_path(args, payload_repr):
    if "path" not in args:
        _reject("falta el campo requerido args.path", payload_repr)
    return _validate_path(args["path"], payload_repr)


def parse_tool_call(payload):
    """Valida payload y devuelve un dict nuevo normalizado con method y args.

    No muta payload. Lanzá ValueError con mensaje util para entradas invalidas.
    """
    if not isinstance(payload, dict):
        _reject("payload debe ser un dict JSON", repr(payload))

    if "method" not in payload:
        _reject("falta el campo requerido method", repr(payload))
    method = payload["method"]
    if method not in ALLOWED_METHODS:
        _reject("method desconocido: {!r}".format(method), repr(payload))

    extra_request = sorted(set(payload) - {"method", "args"})
    if extra_request:
        _reject("campos extra en el request: {}".format(extra_request), repr(payload))

    if "args" not in payload:
        _reject("falta el campo requerido args", repr(payload))
    args = payload["args"]
    if not isinstance(args, dict):
        _reject("args debe ser un dict", repr(payload))

    extra_args = sorted(set(args) - ALLOWED_ARGS[method])
    if extra_args:
        _reject("campos extra en args: {}".format(extra_args), repr(payload))

    missing = [name for name in REQUIRED_ARGS[method] if name not in args]
    if missing:
        _reject("faltan campos requeridos en args: {}".format(missing), repr(payload))

    path = _parse_path(args, repr(payload))

    normalized_args = {"path": path}
    if method == "write_file":
        content = args["content"]
        if not isinstance(content, str):
            _reject("args.content debe ser string", repr(payload))
        normalized_args["content"] = content

    return {"method": method, "args": normalized_args}
