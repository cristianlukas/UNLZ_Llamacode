#!/usr/bin/env python3
"""Strict, candidate-only memory pressure decision core for Q108."""
from __future__ import annotations
import math
import signal
from pathlib import Path
from typing import Callable

class TelemetryError(ValueError):
    pass

def _number(raw: str, label: str) -> float:
    if isinstance(raw, bool):
        raise TelemetryError(f"invalid {label}")
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise TelemetryError(f"invalid {label}") from exc
    if not math.isfinite(value) or value < 0.0 or value > 100.0:
        raise TelemetryError(f"out-of-range {label}")
    return value

def parse_psi_text(text: str) -> dict[str, float]:
    result: dict[str, float] = {}
    for line in text.splitlines():
        parts = line.split()
        if not parts or parts[0] not in {"some", "full"}:
            continue
        fields = dict(item.split("=", 1) for item in parts[1:] if "=" in item)
        if parts[0] in result:
            raise TelemetryError(f"duplicate PSI {parts[0]} record")
        if "avg10" not in fields:
            raise TelemetryError(f"missing avg10 in PSI {parts[0]} record")
        result[parts[0]] = _number(fields["avg10"], f"PSI {parts[0]} avg10")
    if set(result) != {"some", "full"}:
        raise TelemetryError("memory PSI requires both some and full avg10 records")
    return result

def parse_oom_text(text: str) -> int:
    values=[]
    for line in text.splitlines():
        parts=line.split()
        if parts and parts[0] == "oom_kill":
            if len(parts) != 2:
                raise TelemetryError("malformed oom_kill counter")
            try: value=int(parts[1])
            except ValueError as exc: raise TelemetryError("invalid oom_kill counter") from exc
            if value < 0: raise TelemetryError("negative oom_kill counter")
            values.append(value)
    if len(values) != 1:
        raise TelemetryError("oom_kill counter missing or duplicated")
    return values[0]

def read_memavailable_gib(path: Path) -> float:
    try:
        lines=path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise TelemetryError(f"cannot read MemAvailable: {exc}") from exc
    for line in lines:
        parts=line.split()
        if parts and parts[0]=="MemAvailable:":
            if len(parts)!=3 or parts[2]!="kB":
                raise TelemetryError("malformed MemAvailable record")
            try: value=int(parts[1])
            except ValueError as exc: raise TelemetryError("invalid MemAvailable value") from exc
            if value<0: raise TelemetryError("negative MemAvailable value")
            return value*1024/(1024**3)
    raise TelemetryError("MemAvailable missing")

def read_psi_path(path: Path) -> dict[str,float]:
    try: text=path.read_text(encoding="utf-8")
    except OSError as exc: raise TelemetryError(f"cannot read memory PSI: {exc}") from exc
    return parse_psi_text(text)

def read_oom_path(path: Path) -> int:
    try: text=path.read_text(encoding="utf-8")
    except OSError as exc: raise TelemetryError(f"cannot read oom_kill counter: {exc}") from exc
    return parse_oom_text(text)

def read_host_sample(proc_root: Path=Path("/proc")) -> dict:
    """Read one host pressure sample; fail closed if a required procfs metric is absent."""
    return {
        "memAvailableGiB":read_memavailable_gib(proc_root/"meminfo"),
        "memoryPsiAvg10Pct":read_psi_path(proc_root/"pressure/memory"),
        "oomKill":read_oom_path(proc_root/"vmstat"),
    }

def evaluate_sample(sample: dict, previous_oom: int, severe_streak: int) -> tuple[str | None, int, bool]:
    try:
        mem=float(sample["memAvailableGiB"])
        oom=sample["oomKill"]
        psi=sample["memoryPsiAvg10Pct"]
    except (KeyError, TypeError, ValueError) as exc:
        raise TelemetryError("required memory telemetry missing") from exc
    if isinstance(sample.get("memAvailableGiB"), bool) or not math.isfinite(mem) or mem < 0:
        raise TelemetryError("invalid MemAvailable")
    if not isinstance(oom,int) or isinstance(oom,bool) or oom < 0 or not isinstance(previous_oom,int) or previous_oom < 0:
        raise TelemetryError("invalid oom_kill baseline/current value")
    if not isinstance(psi,dict) or not {"some","full"}.issubset(psi):
        raise TelemetryError("memory PSI some/full telemetry missing")
    some=_number(psi["some"],"PSI some avg10")
    full=_number(psi["full"],"PSI full avg10")
    severe=full>=60.0 or some>=80.0
    streak=severe_streak+1 if severe else 0
    warning=full>=20.0 or some>=70.0
    reason=None
    if mem<32.0: reason="MemAvailable <32 GiB"
    elif oom>previous_oom: reason="global oom_kill counter increased"
    elif streak>=15: reason="global PSI severe threshold persisted for 15 consecutive 1-second samples"
    return reason,streak,warning

def stop_candidate(pid:int, reason:str, stop_reason_path:Path, signal_sender:Callable[[int,int],None]=__import__("os").kill) -> None:
    """Persist a fail-closed reason and signal only the supplied candidate PID."""
    stop_reason_path.write_text(reason+"\n",encoding="utf-8")
    signal_sender(pid,signal.SIGTERM)


def monitor_once(
    candidate_pid: int,
    sample_reader: Callable[[], dict],
    previous_oom: int,
    severe_streak: int,
    stop_reason_path: Path,
    signal_sender: Callable[[int, int], None] = __import__("os").kill,
) -> tuple[str | None, int, bool]:
    """Read one sample; fail closed on telemetry errors and signal only candidate."""
    try:
        sample = sample_reader()
        reason, streak, warning = evaluate_sample(sample, previous_oom, severe_streak)
    except (TelemetryError, OSError) as exc:
        reason = f"memory telemetry unavailable: {exc}"
        stop_candidate(candidate_pid, reason, stop_reason_path, signal_sender)
        return reason, severe_streak, False
    if reason:
        stop_candidate(candidate_pid, reason, stop_reason_path, signal_sender)
    return reason, streak, warning
