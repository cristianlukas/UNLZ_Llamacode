"""apply_merge_patch: JSON Merge Patch segun RFC 7396 (sin mutar target ni patch)."""

import copy


def apply_merge_patch(target, patch):
    # Un patch que no es un objeto JSON reemplaza por completo a target.
    if not isinstance(patch, dict):
        return copy.deepcopy(patch)

    # Un target que no es un objeto se trata como el objeto vacio.
    base = copy.deepcopy(target) if isinstance(target, dict) else {}

    for key, value in patch.items():
        if value is None:
            base.pop(key, None)
        else:
            base[key] = apply_merge_patch(base.get(key), value)

    return base
