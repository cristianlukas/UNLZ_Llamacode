"""RFC 7396 JSON Merge Patch."""

import copy


def apply_merge_patch(target, patch):
    """Apply a RFC 7396 merge patch, returning a new object.

    - If patch is not an object (dict), the result is a deep copy of patch.
    - If patch is an object, a non-object target is treated as {}.
    - Keys with value None are removed; others are applied recursively.
    - Arrays are replaced wholesale.
    - Neither target nor patch is mutated; the result is independent of both.
    """
    if not isinstance(patch, dict):
        return copy.deepcopy(patch)

    result = {} if not isinstance(target, dict) else copy.deepcopy(target)

    for key, value in patch.items():
        if value is None:
            result.pop(key, None)
        else:
            result[key] = apply_merge_patch(result.get(key), value)

    return result
