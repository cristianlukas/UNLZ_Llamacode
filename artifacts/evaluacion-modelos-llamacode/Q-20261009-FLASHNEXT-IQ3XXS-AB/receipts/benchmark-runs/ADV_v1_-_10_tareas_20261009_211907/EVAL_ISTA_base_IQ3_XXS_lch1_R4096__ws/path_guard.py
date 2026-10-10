"""safe_join: resuelve user_path dentro de root sin permitir escape (traversal/symlinks)."""

import os


def safe_join(root, user_path):
    """Devuelve la ruta real absoluta de user_path dentro de root.

    Acepta subdirectorios normales y el propio root. Rechaza con ValueError:
    rutas absolutas, traversal con '..', NUL y cualquier ruta cuyo realpath
    escape root. Resuelve symlinks existentes segmento a segmento antes de
    comprobar el limite, sin seguir enlaces que salgan del root.
    """
    if not isinstance(user_path, (str, bytes)):
        raise ValueError("user_path debe ser una ruta")
    if user_path == "":
        raise ValueError("user_path vacio")
    if "\x00" in user_path or b"\x00" in os.fsencode(user_path):
        raise ValueError("user_path contiene NUL")
    if os.path.isabs(user_path):
        raise ValueError("user_path debe ser relativa a root")

    root_real = os.path.realpath(os.path.abspath(root))

    # Segmentos del path pedido (split completo, sin depender del orden de un set/dict).
    separators = [os.sep] + ([os.altsep] if os.altsep else [])
    parts = [user_path]
    for sep in separators:
        parts = [chunk for part in parts for chunk in part.split(sep)]
    segments = [part for part in parts if part and part != os.curdir]

    current = root_real
    for seg in segments:
        if seg in (os.curdir, os.pardir):
            raise ValueError("segmento invalido: {!r}".format(seg))

        candidate = os.path.join(current, seg)
        # Resuelve symlinks existentes antes de comprobar el limite.
        resolved = os.path.realpath(candidate)

        if resolved != root_real and os.path.commonpath([resolved, root_real]) != root_real:
            raise ValueError("ruta escapa del root: {!r}".format(user_path))

        current = resolved

    return current
