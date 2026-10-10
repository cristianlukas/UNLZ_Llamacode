"""RFC 7396 (JSON Merge Patch) implementation."""

import copy


def _is_object(value):
    return isinstance(value, dict)


def apply_merge_patch(target, patch):
    """Apply an RFC 7396 JSON Merge Patch to ``target`` and return a new value.

    Neither ``target`` nor ``patch`` are mutated; the result is independent of
    both (deep copies).
    """
    if not _is_object(patch):
        # A non-object patch replaces the whole target.
        return copy.deepcopy(patch)

    # A non-object target is treated as an empty object.
    result = copy.deepcopy(target) if _is_object(target) else {}

    for key, value in patch.items():
        if value is None:
            result.pop(key, None)
        else:
            result[key] = apply_merge_patch(result.get(key), value)

    return result
