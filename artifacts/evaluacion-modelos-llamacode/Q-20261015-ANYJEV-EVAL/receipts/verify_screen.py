import json
import math
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
fixture = json.loads((ROOT / "fixtures/routing-risk-screen-v1.json").read_text())
result = json.loads((ROOT / "receipts/model-screen-results.json").read_text())
logprobs = [
    json.loads(line)
    for line in (ROOT / "receipts/model-screen-logprobs.jsonl").read_text().splitlines()
    if line.strip()
]
assert result["fixture_cases"] == 32 == len(fixture["cases"])
assert result["latency"]["request_count"] == len(logprobs) == 320
assert all(len(row["token_ids"]) == len(row["logprobs"]) == 4 for row in logprobs)
assert all(math.isfinite(row["duration_ms"]) and row["duration_ms"] >= 0 for row in logprobs)

labels = fixture["options"]
expected_ids = {case["id"] for case in fixture["cases"]}
flips = {"raw": 0, "L0": 0}
checks = []
for arm, metrics in result["metrics"].items():
    rows = metrics["rows"]
    assert len(rows) == 32 and {row["id"] for row in rows} == expected_ids
    assert all(row["answer"] in labels for row in rows)
    assert all(set(row["distribution"]) == set(labels) for row in rows)
    assert all(abs(sum(row["distribution"].values()) - 1.0) < 1e-5 for row in rows)
    assert all(all(math.isfinite(v) for v in row["distribution"].values()) for row in rows)
    accuracy = sum(row["correct"] for row in rows) / len(rows)
    brier = statistics.mean(
        sum((row["distribution"][label] - float(label == row["gold"])) ** 2 for label in labels)
        for row in rows
    )
    assert abs(accuracy - metrics["accuracy"]) < 1e-12
    assert abs(brier - metrics["brier_multiclass"]) < 1e-12
    if "canonical" in arm:
        sibling = arm.replace("canonical", "reversed")
        reverse_rows = {row["id"]: row for row in result["metrics"][sibling]["rows"]}
        flips["raw" if arm.startswith("raw") else "L0"] += sum(
            row["answer"] != reverse_rows[row["id"]]["answer"] for row in rows
        )
    if arm.startswith("L0"):
        assert all(row["diagnostics"]["permutations"] == 4 for row in rows)
        assert all(row["diagnostics"]["prior_method"] == "batch" for row in rows)
    checks.append({"arm": arm, "rows": len(rows), "accuracy": accuracy, "brier": brier})

assert flips == result["order_flip_count"]
receipt = {
    "task_id": "Q-20261015-ANYJEV-EVAL",
    "decision": "pass",
    "fixture_cases_per_arm": 32,
    "full_run_logprob_requests": len(logprobs),
    "probability_distributions_valid": True,
    "metrics_recomputed": True,
    "flip_counts_recomputed": flips,
    "l0_full_rotations_and_batch_prior_verified": True,
    "arms": checks,
}
(ROOT / "receipts/verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
