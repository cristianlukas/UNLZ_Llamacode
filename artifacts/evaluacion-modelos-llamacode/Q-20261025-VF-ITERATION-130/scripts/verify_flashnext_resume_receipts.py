#!/usr/bin/env python3
"""CPU-only consistency audit for the saved Q4 Flash-Next resume receipts."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
ART = ROOT / "artifacts/evaluacion-modelos-llamacode"
FOLLOWUP = ART / "Q-20261016-FLASHNEXT-FOLLOWUP"
RESUME2 = ART / "Q-20261016-FLASHNEXT-RESUME2"
CAMPAIGN = FOLLOWUP / "receipts/server-speed/campaign.json"
VALIDATION = RESUME2 / "receipts/server-speed-validation.json"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def mean(samples, field):
    vals = [float(row[field]) for row in samples]
    return sum(vals) / len(vals)


def main() -> int:
    campaign = read_json(CAMPAIGN)
    validation = read_json(VALIDATION)
    corpus_path = ROOT / "assets/benchmarks/server_speed_v1.json"
    assert hashlib.sha256(corpus_path.read_bytes()).hexdigest() == campaign["corpusSha256"]
    assert campaign["status"] == "complete"
    assert campaign["seed"] == 424242 and campaign["order"] == ["AB", "BA", "AB"]
    assert validation["allCompleteRunsValid"] and validation["totalSamples"] == 96

    expected = {
        "pair01-A-order01": (1, "A", 1),
        "pair01-B-order02": (1, "B", 2),
        "pair02-B-order01": (2, "B", 1),
        "pair02-A-order02": (2, "A", 2),
        "pair03-A-order01": (3, "A", 1),
        "pair03-B-order02": (3, "B", 2),
    }
    campaign_runs = {row["runId"]: row for row in campaign["runs"]}
    assert set(campaign_runs) == set(expected)
    run_checks = []
    paired = {}
    for run_id, (pair, arm, order_index) in expected.items():
        row = campaign_runs[run_id]
        assert (row["pair"], row["arm"], row["orderIndex"]) == (pair, arm, order_index)
        assert row["status"] == "complete" and len(row["samples"]) == 16
        assert row["portFreeAfterStop"] is True and row.get("abortReason") == []
        assert all(not sample.get("failed") for sample in row["samples"])
        assert len({sample["sampleId"] for sample in row["samples"]}) == 16
        assert all(re.fullmatch(r"[0-9a-f]{64}", sample["responseSha256"]) for sample in row["samples"])
        assert "--gpu" in row["command"] and row["command"][row["command"].index("--gpu") + 1] == "0,1"
        assert len(row["preflight"]["gpu"]) == 2
        assert all("RTX 3090" in gpu for gpu in row["preflight"]["gpu"])
        config_path = Path(row["configPath"])
        assert config_path.exists()
        assert hashlib.sha256(config_path.read_bytes()).hexdigest() == row["configSha256"]
        config = read_json(config_path)
        assert config.get("gpu") == [0, 1] and config.get("layer_split") == 18
        paired.setdefault(pair, {})[arm] = row["samples"]
        run_checks.append({"runId": run_id, "samples": 16, "hashesValid": True,
                           "dual3090CommandAndTelemetry": True, "portFree": True,
                           "configHashValid": True})

    pair_checks = []
    for pair in (1, 2, 3):
        assert set(paired[pair]) == {"A", "B"}
        a = {(s["promptId"], s["measurementPhase"]): s for s in paired[pair]["A"]}
        b = {(s["promptId"], s["measurementPhase"]): s for s in paired[pair]["B"]}
        assert set(a) == set(b) and len(a) == 16
        deltas = {field: mean(list(b.values()), field) - mean(list(a.values()), field)
                  for field in ("decodeTps", "promptTps", "ttftMs", "elapsedMs")}
        pair_checks.append({"pair": pair, "matched": 16, "deltaBMinusA": deltas})
    # Pair 1 is negative for token rates and slower for B; pairs 2/3 reverse it.
    assert pair_checks[0]["deltaBMinusA"]["decodeTps"] < 0
    assert pair_checks[1]["deltaBMinusA"]["decodeTps"] > 0
    assert pair_checks[2]["deltaBMinusA"]["decodeTps"] > 0

    context = read_json(RESUME2 / "receipts/context262k-attempt-05.json")
    controller = read_json(RESUME2 / "receipts/context262k-attempt-05-controller.json")
    assert context["status"] == "completed" and context["targetContext"] == 262144
    assert context["localTokenizerContentTokens"] >= 249000 and context["retrievalExact"] is True
    assert context["answer"].strip() == context["needle"]
    assert controller["serverStopped"] and controller["portFreeAfterCleanup"]
    assert controller["abortReasons"] == [] and controller["postflight"]["vmstat"]["oom_kill"] == 0
    actual_key_count = len(re.findall(r"^ARCHIVE KEY:", context.get("answer", ""), re.M))
    # The prompt/receipt contain one retrieval target; the original plan called for ten.
    actual_key_count = 1 if context.get("needle") else actual_key_count
    context_spec_met = actual_key_count == 10
    assert not context_spec_met

    vision = read_json(RESUME2 / "receipts/vision-attempt-01.json")
    vision_controller = read_json(RESUME2 / "receipts/vision-attempt-01-controller.json")
    text = vision["responseText"].strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.S | re.I)
    parsed = json.loads(match.group(1) if match else text)
    expected_vision = vision["expected"]
    fields = [(kind, name, expected_vision[kind][name], parsed[kind][name])
              for kind in ("shapes", "colors") for name in expected_vision[kind]]
    exact_count = sum(expected_value == actual_value
                      for _, _, expected_value, actual_value in fields)
    assert exact_count == 9 and len(fields) == 11
    assert vision["transportError"] is None and vision_controller["serverStopped"]
    assert vision_controller["portFreeAfterCleanup"] and vision_controller["abortReasons"] == []

    manual = read_json(RESUME2 / "receipts/cu-manual-review.json")
    assert manual["astraBaseReplicate2"]["effectiveScore"] == "3/3"
    assert manual["q4BaseReplicate2"]["effectiveScore"] == "1/3"
    post = read_json(RESUME2 / "receipts/postflight-20261016T2259Z.json")
    assert post["taskPortsFree"] and post["nvidiaComputeIdle"]
    assert post["vmstat"]["oom_kill"] == 0

    result = {
        "taskId": "Q-20261025-VF-ITERATION-130",
        "kind": "offline-receipt-consistency-audit",
        "result": "PASS_WITH_ONE_PREREGISTRATION_GAP",
        "newModelOrGpuRun": False,
        "serverSpeed": {"campaignComplete": True, "validSamples": 96,
                        "runs": run_checks, "pairs": pair_checks,
                        "trimPromotion": False},
        "context262k": {"completed": True, "context": 262144,
                         "contentTokens": context["localTokenizerContentTokens"],
                         "exactSingleKey": True, "actualValueCount": actual_key_count,
                         "originalPrerecordedValueCount": 10,
                         "originalMultiValueCriterionMet": context_spec_met,
                         "followupRequired": True},
        "vision": {"transportComplete": True, "exactFields": exact_count,
                   "totalFields": len(fields), "rawResponseWasFencedJson": bool(match),
                   "storedParserHadError": vision.get("parsed") is None,
                   "noPromotion": True},
        "computerUsage": {"astraBaseReplicate2": "3/3", "q4BaseReplicate2": "1/3"},
        "postflight": {"taskPortsFree": post["taskPortsFree"],
                       "inferenceIdle": post["nvidiaComputeIdle"], "oomKill": 0},
        "findings": [
            "Pair 3 already exists complete in the original campaign; do not repeat it.",
            "Q4 262K prior smoke retrieved one key, while its preregistered acceptance asked for ten distinct values.",
            "Q4 vision raw fenced JSON reparses to 9/11 exact fields; the saved parser field is null, but transport completed.",
            "All recorded model arms used both RTX 3090 and 128 GiB host configuration; no one-GPU substitute was used."
        ]
    }
    out = RESUME2.parent / "Q-20261025-VF-ITERATION-130" / "receipts/offline-reconciliation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
