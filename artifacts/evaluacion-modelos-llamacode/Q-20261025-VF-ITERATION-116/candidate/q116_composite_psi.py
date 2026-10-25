"""Versioned candidate PSI transition; intentionally not wired into Q97/Q100."""
from __future__ import annotations


def pressure_gate_transition(psi, previous):
    thresholds = {
        "warning_full20": ("full", 20.0),
        "warning_some70": ("some", 70.0),
        "severe_full60": ("full", 60.0),
        "severe_some80": ("some", 80.0),
    }
    counts = {}
    for key, (stall, limit) in thresholds.items():
        counts[key] = previous.get(key, 0) + 1 if psi[stall] >= limit else 0

    composite_severe = psi["full"] >= 60.0 or psi["some"] >= 80.0
    counts["severe_any"] = previous.get("severe_any", 0) + 1 if composite_severe else 0
    warning = counts["warning_full20"] >= 30 or counts["warning_some70"] >= 30
    stop = None
    if counts["severe_any"] >= 15:
        stop = "global memory PSI full avg10 >=60% OR some avg10 >=80% for 15 consecutive samples"
    return counts, warning, stop
