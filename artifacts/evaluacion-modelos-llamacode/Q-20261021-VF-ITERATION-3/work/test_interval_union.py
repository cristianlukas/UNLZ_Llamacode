from __future__ import annotations

import importlib.util
from pathlib import Path


spec = importlib.util.spec_from_file_location("candidate", Path("solution.py"))
assert spec and spec.loader
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)
assert callable(getattr(candidate, "covered_duration", None)), "missing covered_duration"

cases = [
    ([], 0),
    ([(4, 4)], 0),
    ([(1, 5)], 4),
    ([(1, 5), (4, 8)], 7),
    ([(1, 10), (3, 4), (5, 7)], 9),
    ([(-5, -1), (1, 3)], 6),
    ([(1, 4), (1, 4)], 3),
    ([(0, 2), (2, 5)], 5),
    ([(9, 12), (0, 3), (2, 10)], 12),
]
for index, (intervals, expected) in enumerate(cases, 1):
    original = [tuple(pair) for pair in intervals]
    got = candidate.covered_duration(intervals)
    assert got == expected, f"case {index}: expected {expected}, got {got}"
    assert intervals == original, f"case {index}: mutated its input"

try:
    candidate.covered_duration([(3, 2)])
except ValueError:
    pass
else:
    raise AssertionError("reversed interval must raise ValueError")

print("PASS: 10 interval-union holdout cases")
