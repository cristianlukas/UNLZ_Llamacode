#!/usr/bin/env python3
"""CPU-only audit for Q97 warning cadence over the unchanged Q108 core."""
from __future__ import annotations

import importlib.util
import json
import signal
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-110"
POLICY_PATH = TASK / "runner/q110_warning_policy.py"
RESULT = TASK / "receipts/q110-warning-cadence-audit.json"
spec = importlib.util.spec_from_file_location("q110_warning_policy", POLICY_PATH)
policy = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(policy)
core = policy.core
lock = json.loads((ROOT / "WORK_QUEUE.lock").read_text(encoding="utf-8"))
if lock.get("task_id") != "Q-20261024-VF-ITERATION-110" or lock.get("token") != "549f3a3b-673a-4d3a-9046-1122a67c04a2":
    raise SystemExit("Q110 lock mismatch; refusing test")

checks = []


def check(name, fn):
    try:
        fn()
        checks.append({"name": name, "passed": True})
    except Exception as exc:
        checks.append({"name": name, "passed": False, "error": f"{type(exc).__name__}: {exc}"})


def ok(condition, message):
    if not condition:
        raise AssertionError(message)


def sample(mem=100.0, some=0.0, full=0.0, oom=0, **extra):
    value = {"memAvailableGiB": mem, "memoryPsiAvg10Pct": {"some": some, "full": full}, "oomKill": oom}
    value.update(extra)
    return value


def raw_q108_eager_warning_is_reproduced():
    reason, severe, warning = core.evaluate_sample(sample(mem=69.386, some=46.52, full=46.52), 0, 0)
    ok(reason is None and severe == 0 and warning, "Q108 reference behavior changed; expected one-sample warning")


check("Q108 one-sample moderate warning difference reproduced", raw_q108_eager_warning_is_reproduced)


def warning_starts_on_thirtieth_sample():
    moderate = sample(mem=69.386, some=46.52, full=46.52)
    streak = 0
    for index in range(1, 30):
        reason, severe, streak, warn = policy.evaluate_policy(moderate, 0, 0, streak)
        ok(reason is None and severe == 0 and streak == index and not warn, f"unexpected warning at sample {index}")
    reason, severe, streak, warn = policy.evaluate_policy(moderate, 0, 0, streak)
    ok(reason is None and severe == 0 and streak == 30 and warn, "warning did not start at sample 30")


check("moderate PSI warning begins exactly at 30 consecutive samples", warning_starts_on_thirtieth_sample)


def recovery_resets_streak():
    moderate = sample(mem=69.386, some=46.52, full=46.52)
    clear = sample(mem=100, some=0, full=0)
    _, _, streak, warn = policy.evaluate_policy(moderate, 0, 0, 28)
    ok(streak == 29 and not warn, "sample 29 should not warn")
    _, _, streak, warn = policy.evaluate_policy(clear, 0, 0, streak)
    ok(streak == 0 and not warn, "recovery did not reset warning streak")
    _, _, streak, warn = policy.evaluate_policy(moderate, 0, 0, streak)
    ok(streak == 1 and not warn, "new pressure episode should start at one")


check("PSI recovery resets the consecutive warning counter", recovery_resets_streak)


def severe_stop_remains_at_fifteenth_sample():
    severe = sample(mem=100, some=80, full=60)
    reason, _, moderate_streak, warn = policy.evaluate_policy(severe, 0, 14, 14)
    ok(reason and "15 consecutive" in reason, "severe stop boundary moved")
    ok(moderate_streak == 15 and not warn, "hard stop must win before moderate warning delay")


check("severe PSI hard stop remains 15 samples and takes precedence", severe_stop_remains_at_fifteenth_sample)


def astra_high_rss_control_has_no_warning():
    reason, severe, moderate, warn = policy.evaluate_policy(sample(mem=55.728, rssGiB=51.14), 0, 0, 0)
    ok((reason, severe, moderate, warn) == (None, 0, 0, False), "ASTRA high-RSS control stopped or warned")


check("ASTRA 1M high-RSS / healthy PSI control continues", astra_high_rss_control_has_no_warning)


def malformed_telemetry_remains_rejected():
    try:
        policy.evaluate_policy({"memAvailableGiB": 90, "memoryPsiAvg10Pct": {}, "oomKill": 0}, 0, 0, 0)
    except core.TelemetryError:
        return
    raise AssertionError("malformed telemetry accepted")


check("missing PSI still fails closed in unchanged Q108 core", malformed_telemetry_remains_rejected)

passed = sum(item["passed"] for item in checks)
result = {
    "schemaVersion": 1,
    "taskId": "Q-20261024-VF-ITERATION-110",
    "amendment": 1,
    "recordedAtUtc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    "status": "pass" if passed == len(checks) else "fail",
    "checksPassed": passed,
    "checksTotal": len(checks),
    "gpuUsed": False,
    "modelOrServerStarted": False,
    "memoryAllocationGiB": 0,
    "productionChanged": False,
    "q108CoreChanged": False,
    "checks": checks,
}
if RESULT.exists():
    raise SystemExit(f"refusing to overwrite {RESULT}")
RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
for item in checks:
    print(("PASS" if item["passed"] else "FAIL"), item["name"], item.get("error", ""))
print(f"Q110-A1 warning cadence: {passed}/{len(checks)} PASS")
if result["status"] != "pass":
    raise SystemExit(1)
