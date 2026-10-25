#!/usr/bin/env python3
"""Q110 candidate cadence wrapper; keeps Q108 hard stops unchanged."""
from __future__ import annotations

from pathlib import Path
import importlib.util

CORE_PATH = Path(__file__).resolve().parents[2] / "Q-20261024-VF-ITERATION-108/runner/q108_guard_core.py"
spec = importlib.util.spec_from_file_location("q108_guard_core", CORE_PATH)
core = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(core)

WARNING_SUSTAINED_SAMPLES = 30


def evaluate_policy(sample: dict, previous_oom: int, severe_streak: int, moderate_streak: int):
    """Return (stop_reason, next_severe_streak, next_moderate_streak, warn).

    The Q108 core owns telemetry validation and hard-stop thresholds. This Q110
    wrapper adds Q97's calibrated 30-consecutive-sample warning cadence. It is
    candidate-only and deliberately has no process-control or production hooks.
    """
    if not isinstance(moderate_streak, int) or isinstance(moderate_streak, bool) or moderate_streak < 0:
        raise core.TelemetryError("invalid moderate PSI streak")
    reason, next_severe, _raw_warning = core.evaluate_sample(sample, previous_oom, severe_streak)
    psi = sample["memoryPsiAvg10Pct"]
    moderate = float(psi["full"]) >= 20.0 or float(psi["some"]) >= 70.0
    next_moderate = moderate_streak + 1 if moderate else 0
    warn = reason is None and next_moderate >= WARNING_SUSTAINED_SAMPLES
    return reason, next_severe, next_moderate, warn
