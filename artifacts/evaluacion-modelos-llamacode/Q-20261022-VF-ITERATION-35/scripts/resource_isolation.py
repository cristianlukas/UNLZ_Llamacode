"""Hard cgroup containment for model-evaluation workers; never changes model settings."""
from pathlib import Path

GIB = 1024 ** 3
RESERVE_BYTES = 16 * GIB
MAX_WORKER_BYTES = 104 * GIB
MIN_WORKER_BYTES = 64 * GIB
WORKER_HIGH_HEADROOM_BYTES = 8 * GIB
MAX_WORKER_SWAP_BYTES = 4 * GIB
SYSTEM_SWAP_RESERVE_BYTES = 1 * GIB


def parse_meminfo(text):
    values = {}
    for line in text.splitlines():
        key, value = line.split(":", 1)
        if key in {"MemTotal", "MemAvailable", "SwapFree"}:
            values[key] = int(value.split()[0]) * 1024
    missing = {"MemTotal", "MemAvailable", "SwapFree"} - values.keys()
    if missing:
        raise ValueError(f"/proc/meminfo missing fields: {sorted(missing)}")
    return values


def calculate_worker_limits(meminfo_text):
    """Give a worker as much as current free RAM permits, retaining host headroom."""
    values = parse_meminfo(meminfo_text)
    mem_total = values["MemTotal"]
    mem_available = values["MemAvailable"]
    memory_max = min(MAX_WORKER_BYTES, mem_total - RESERVE_BYTES,
                     mem_available - RESERVE_BYTES)
    if memory_max < MIN_WORKER_BYTES:
        raise RuntimeError(
            "safe isolated-worker budget is below 64 GiB; stop before model startup "
            f"(MemAvailable={mem_available / GIB:.2f} GiB)"
        )
    memory_high = memory_max - WORKER_HIGH_HEADROOM_BYTES
    swap_max = min(MAX_WORKER_SWAP_BYTES,
                   max(0, values["SwapFree"] - SYSTEM_SWAP_RESERVE_BYTES))
    return {
        "mem_total_bytes": mem_total,
        "mem_available_bytes": mem_available,
        "memory_high_bytes": memory_high,
        "memory_max_bytes": memory_max,
        "memory_swap_max_bytes": swap_max,
        "oom_score_adjust": 900,
        "oom_policy": "kill",
        "kill_mode": "control-group",
        "managed_oom_memory_pressure": "kill",
        "managed_oom_memory_pressure_limit": "35%",
    }


def systemd_properties(limits):
    """Return required systemd-run properties in stable, testable order."""
    return [
        "--property=Type=exec",
        "--property=KillMode=control-group",
        "--property=OOMPolicy=kill",
        f"--property=OOMScoreAdjust={limits['oom_score_adjust']}",
        f"--property=MemoryHigh={limits['memory_high_bytes']}",
        f"--property=MemoryMax={limits['memory_max_bytes']}",
        f"--property=MemorySwapMax={limits['memory_swap_max_bytes']}",
        "--property=ManagedOOMMemoryPressure=kill",
        "--property=ManagedOOMMemoryPressureLimit=35%",
    ]


def verify_effective_cgroup(cgroup_path, expected_limits, oom_score_adjust):
    """Fail closed unless the process is really bounded and group-killable."""
    root = Path(cgroup_path)
    actual = {
        "memory_high_bytes": int((root / "memory.high").read_text().strip()),
        "memory_max_bytes": int((root / "memory.max").read_text().strip()),
        "memory_swap_max_bytes": int((root / "memory.swap.max").read_text().strip()),
        "oom_group": int((root / "memory.oom.group").read_text().strip()),
        "oom_score_adjust": int(Path("/proc/self/oom_score_adj").read_text().strip()),
    }
    expected = {
        "memory_high_bytes": expected_limits["memory_high_bytes"],
        "memory_max_bytes": expected_limits["memory_max_bytes"],
        "memory_swap_max_bytes": expected_limits["memory_swap_max_bytes"],
        "oom_group": 1,
        "oom_score_adjust": oom_score_adjust,
    }
    if actual != expected:
        raise RuntimeError(f"effective worker cgroup differs from preregistered limits: {actual} != {expected}")
    return actual
