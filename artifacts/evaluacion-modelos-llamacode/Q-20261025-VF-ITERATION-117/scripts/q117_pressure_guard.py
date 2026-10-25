#!/usr/bin/env python3
"""Q117-only live pressure guard: Q108 fail-closed telemetry + Q116 composite PSI."""
from __future__ import annotations

from pathlib import Path
import sys

GUARD_SOURCES = Path(__file__).resolve().parents[1] / "guard_sources"
sys.path.insert(0, str(GUARD_SOURCES))
import q108_guard_core as telemetry
import q116_composite_psi as psi_gate


def initial_counts():
    return {
        "warning_full20": 0,
        "warning_some70": 0,
        "severe_full60": 0,
        "severe_some80": 0,
        "severe_any": 0,
    }


def read_sample(proc_root: Path = Path("/proc")) -> dict:
    """Read the required host values; missing/malformed values raise TelemetryError."""
    return telemetry.read_host_sample(proc_root)


def evaluate(sample: dict, previous_oom: int, counters: dict):
    """Return stop reason, next counters and moderate-warning flag."""
    # Q108 validates numeric ranges and required PSI/OOM/MemAvailable fields. With a
    # zero single-metric streak this call applies immediate low-memory/OOM stops.
    immediate, _, _ = telemetry.evaluate_sample(sample, previous_oom, 0)
    next_counters, psi_warning, severe_stop = psi_gate.pressure_gate_transition(
        sample["memoryPsiAvg10Pct"], counters
    )
    return immediate or severe_stop, next_counters, psi_warning


def cgroup_psi_diagnostic(psi: dict) -> dict:
    """Validate and report worker PSI; it is diagnostic and never a stop input."""
    if not isinstance(psi, dict) or not {"some", "full"}.issubset(psi):
        raise telemetry.TelemetryError("worker cgroup PSI some/full telemetry missing")
    some = telemetry._number(psi["some"], "worker cgroup PSI some avg10")
    full = telemetry._number(psi["full"], "worker cgroup PSI full avg10")
    return {"some": some, "full": full,
            "severeDiagnostic": some >= 80.0 or full >= 60.0,
            "hardStop": False}


def evaluate_worker_cgroup(run: dict, baseline_oom: dict, baseline_swap_bytes: int,
                           swap_limit_bytes: int = 4 * 1024 * 1024):
    """Validate worker cgroup OOM/swap and PSI; PSI is diagnostic, never a stop."""
    if not isinstance(run, dict):
        raise telemetry.TelemetryError("worker cgroup telemetry missing")
    events = run.get("memory_events")
    if not isinstance(events, dict) or not isinstance(baseline_oom, dict):
        raise telemetry.TelemetryError("worker cgroup OOM telemetry missing")
    current_events = {}
    for key in ("oom", "oom_kill"):
        current = events.get(key)
        baseline = baseline_oom.get(key)
        if (not isinstance(current, int) or isinstance(current, bool) or current < 0
                or not isinstance(baseline, int) or isinstance(baseline, bool) or baseline < 0):
            raise telemetry.TelemetryError(f"invalid worker cgroup {key} counter")
        current_events[key] = current

    current_swap = run.get("memory_swap_current_bytes")
    if (not isinstance(current_swap, int) or isinstance(current_swap, bool) or current_swap < 0
            or not isinstance(baseline_swap_bytes, int) or isinstance(baseline_swap_bytes, bool)
            or baseline_swap_bytes < 0):
        raise telemetry.TelemetryError("invalid worker cgroup swap telemetry")

    psi = run.get("psi")
    if not isinstance(psi, dict):
        raise telemetry.TelemetryError("worker cgroup PSI telemetry missing")
    avg10 = {}
    for key in ("some", "full"):
        values = psi.get(key)
        if not isinstance(values, dict) or "avg10" not in values:
            raise telemetry.TelemetryError(f"worker cgroup PSI {key} avg10 missing")
        avg10[key] = values["avg10"]
    diagnostic = cgroup_psi_diagnostic(avg10)

    reason = None
    if any(current_events[key] > baseline_oom[key] for key in ("oom", "oom_kill")):
        reason = "worker cgroup OOM event counter increased"
    swap_delta = current_swap - baseline_swap_bytes
    if swap_delta > swap_limit_bytes:
        reason = reason or f"worker cgroup swap current increased by more than {swap_limit_bytes} bytes"
    return reason, diagnostic, swap_delta
