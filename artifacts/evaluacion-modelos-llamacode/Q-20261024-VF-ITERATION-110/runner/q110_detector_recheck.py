#!/usr/bin/env python3
"""CPU-only Q110 regression for the candidate memory-pressure guard."""
from __future__ import annotations

import importlib.util
import json
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-110"
CORE_PATH = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-108/runner/q108_guard_core.py"
RESULT_PATH = TASK / "receipts/q110-regression-result.json"
spec = importlib.util.spec_from_file_location("q108_guard_core", CORE_PATH)
core = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(core)

checks: list[dict] = []


def assert_lock_owned():
    lock = json.loads((ROOT / "WORK_QUEUE.lock").read_text(encoding="utf-8"))
    if lock.get("task_id") != "Q-20261024-VF-ITERATION-110" or lock.get("token") != "549f3a3b-673a-4d3a-9046-1122a67c04a2":
        raise SystemExit("Q110 lock mismatch; refusing to test or write result")


assert_lock_owned()


def check(name, fn):
    try:
        fn()
        checks.append({"name": name, "passed": True})
    except Exception as exc:  # include the precise failure in the durable receipt
        checks.append({"name": name, "passed": False, "error": f"{type(exc).__name__}: {exc}"})


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def record(rel):
    return json.loads((ROOT / "artifacts/evaluacion-modelos-llamacode" / rel).read_text(encoding="utf-8"))


def valid(mem=100.0, some=0.0, full=0.0, oom=0, **extra):
    sample = {"memAvailableGiB": mem, "memoryPsiAvg10Pct": {"some": some, "full": full}, "oomKill": oom}
    sample.update(extra)
    return sample


def test_lock_owned():
    lock = json.loads((ROOT / "WORK_QUEUE.lock").read_text(encoding="utf-8"))
    assert_true(lock.get("task_id") == "Q-20261024-VF-ITERATION-110", "Q110 lock task mismatch")
    assert_true(lock.get("token") == "549f3a3b-673a-4d3a-9046-1122a67c04a2", "Q110 lock token mismatch")


check("Q110 exclusive lock is still owned", test_lock_owned)


def test_astra_high_rss_continues():
    # RSS is intentionally an extra/non-input field. The decision uses available
    # memory, PSI and OOM; successful ASTRA 1M left 55.728 GiB available.
    reason, streak, warning = core.evaluate_sample(
        valid(mem=55.728, rssGiB=51.14), previous_oom=0, severe_streak=0
    )
    assert_true((reason, streak, warning) == (None, 0, False), "ASTRA 1M historical control stopped/warned")


check("ASTRA 1M high RSS (51.14 GiB) with 55.728 GiB available continues", test_astra_high_rss_continues)


def test_sol_recorded_without_invented_psi():
    review = record("Q-20261024-VF-ITERATION-97/receipts/q97-memory-guard-review.json")
    sol = {item["id"]: item for item in review["historicalEvidence"]}["Q34 SOL vLLM TP2"]
    assert_true(sol["oomKill"] == 0 and "completed" in sol["outcome"], "SOL completion/no-OOM missing")
    assert_true(sol["gpus"] == "both RTX 3090", "SOL dual-3090 control missing")
    assert_true("no per-second PSI" in sol["outcome"], "SOL PSI limitation must remain explicit")


check("SOL Q34 TP=2 completed on dual 3090 without OOM; PSI caveat preserved", test_sol_recorded_without_invented_psi)


def test_q97_astra_moderate_psi_warned_not_stopped():
    reason, streak, warning = core.evaluate_sample(
        valid(mem=71.864, some=34.72, full=34.72), previous_oom=0, severe_streak=0
    )
    assert_true((reason, streak, warning) == (None, 0, True), "Q97 moderate PSI should warn and continue")


check("Q97 ASTRA moderate PSI (34.72%) warns but continues", test_q97_astra_moderate_psi_warned_not_stopped)


def test_q100_moderate_psi_warn_only():
    result = record("Q-20261024-VF-ITERATION-100/receipts/q100-final-result.json")
    guard = result["memoryGuard"]
    assert_true(guard["guardAborted"] is False and guard["allSixRunsCompleted"] is True, "Q100 completed run evidence missing")
    reason, streak, warning = core.evaluate_sample(
        valid(mem=69.386, some=46.52, full=46.52), previous_oom=0, severe_streak=0
    )
    assert_true((reason, streak, warning) == (None, 0, True), "Q100 moderate PSI should warn and continue")


check("Q100 six runs completed under moderate PSI; guard warns without stop", test_q100_moderate_psi_warn_only)


def test_stop_boundaries_and_recovery():
    assert_true(core.evaluate_sample(valid(mem=32.0), 0, 0)[0] is None, "exact 32 GiB should continue")
    assert_true(core.evaluate_sample(valid(mem=31.99), 0, 0)[0] == "MemAvailable <32 GiB", "below-32 GiB stop missing")
    assert_true(core.evaluate_sample(valid(oom=1), 0, 0)[0] == "global oom_kill counter increased", "OOM delta stop missing")
    _, streak14, _ = core.evaluate_sample(valid(some=80, full=60), 0, 13)
    reason15, streak15, _ = core.evaluate_sample(valid(some=80, full=60), 0, 14)
    assert_true(streak14 == 14 and reason15 and streak15 == 15, "severe PSI 14→15 boundary wrong")
    _, recovered, _ = core.evaluate_sample(valid(), 0, 14)
    assert_true(recovered == 0, "PSI recovery did not reset the streak")


check("hard-stop floor/OOM/severe-PSI boundaries and recovery remain intact", test_stop_boundaries_and_recovery)


def test_missing_telemetry_rejected():
    for text in ("", "some avg10=0.1 avg60=0 avg300=0 total=1", "some avg10=nan\nfull avg10=0"):
        try:
            core.parse_psi_text(text)
        except core.TelemetryError:
            continue
        raise AssertionError(f"accepted missing/malformed PSI: {text!r}")
    for text in ("", "oom_kill x", "oom_kill -1", "oom_kill 0\noom_kill 1"):
        try:
            core.parse_oom_text(text)
        except core.TelemetryError:
            continue
        raise AssertionError(f"accepted missing/malformed OOM: {text!r}")


check("missing/malformed PSI and OOM telemetry fails closed", test_missing_telemetry_rejected)


def test_only_candidate_pid_signaled_on_missing_proc():
    sent = []
    with TemporaryDirectory() as tmp:
        reason_path = Path(tmp) / "stop.txt"
        reason, streak, warning = core.monitor_once(
            424242,
            lambda: core.read_host_sample(Path(tmp) / "missing-proc-root"),
            0,
            0,
            reason_path,
            lambda pid, sig: sent.append((pid, sig)),
        )
        assert_true(reason and reason.startswith("memory telemetry unavailable:"), "missing proc did not fail closed")
        assert_true(reason_path.read_text(encoding="utf-8").strip() == reason, "stop reason was not persisted")
        assert_true((streak, warning) == (0, False), "missing proc returned misleading pressure signal")
    assert_true(sent == [(424242, signal.SIGTERM)], f"unexpected signal scope: {sent}")


check("missing live telemetry signals only explicit candidate PID", test_only_candidate_pid_signaled_on_missing_proc)


def test_live_proc_sample():
    sample = core.read_host_sample(Path("/proc"))
    reason, streak, warning = core.evaluate_sample(sample, sample["oomKill"], 0)
    assert_true(reason is None, f"current host hit hard stop unexpectedly: {reason}")
    assert_true(set(sample["memoryPsiAvg10Pct"]) == {"some", "full"}, "live PSI incomplete")
    assert_true(sample["memAvailableGiB"] > 32.0, "live MemAvailable below hard floor")
    assert_true(streak == 0 or warning, "live PSI state internally inconsistent")


check("live /proc metrics are complete and do not cross a hard stop", test_live_proc_sample)


passed = sum(item["passed"] for item in checks)
result = {
    "schemaVersion": 1,
    "taskId": "Q-20261024-VF-ITERATION-110",
    "recordedAtUtc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    "status": "pass" if passed == len(checks) else "fail",
    "checksPassed": passed,
    "checksTotal": len(checks),
    "gpuUsed": False,
    "modelOrServerStarted": False,
    "memoryAllocationGiB": 0,
    "foreignProcessSignals": 0,
    "checks": checks,
}
if RESULT_PATH.exists():
    raise SystemExit(f"refusing to overwrite {RESULT_PATH}")
RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
for item in checks:
    print(("PASS" if item["passed"] else "FAIL"), item["name"], item.get("error", ""))
print(f"Q110 detector regression: {passed}/{len(checks)} PASS")
if result["status"] != "pass":
    raise SystemExit(1)
