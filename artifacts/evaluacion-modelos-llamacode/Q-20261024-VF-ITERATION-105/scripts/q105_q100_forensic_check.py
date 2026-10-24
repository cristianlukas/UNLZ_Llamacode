#!/usr/bin/env python3
"""Reconciliación CPU-only de los artefactos persistidos de Q100."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
Q100 = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-100"
raw_path = Q100 / "runs/attempt-05-complete-label-mapping-issue/live-probe-result.json"
scored_path = Q100 / "runs/attempt-05-complete-label-mapping-issue/rescored-result.json"
cpp_path = ROOT / "tests/test_q100_subagent_probe.cpp"
raw = json.loads(raw_path.read_text())
scored = json.loads(scored_path.read_text())
source = cpp_path.read_text()
checks = []

def check(name, condition, detail):
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    checks.append({"name": name, "passed": True, "detail": detail})

runs = raw["runs"]
scored_by_key = {(x["seed"], x["policy"]): x for x in scored["runs"]}
check("six-runs-present", len(runs) == 6, f"count={len(runs)}")
expected_wrong = {("parallel2", 5051), ("parallel2", 5053)}
observed_wrong = set()
serial_correct = 0
parallel_correct = 0
card_orders = {}
for run in runs:
    cards = run["taskCards"]
    check(f"two-task-cards-{run['policy']}-{run['seed']}", len(cards) == 2,
          f"count={len(cards)}")
    labels = []
    for card in cards:
        output = card["output"]
        has_a = bool(re.search(r"Q100_ALPHA_PRIVATE_\d+_7c1d9", output))
        has_b = bool(re.search(r"Q100_BETA_PRIVATE_\d+_3f8a2", output))
        check(f"one-marker-{run['policy']}-{run['seed']}-{len(labels)}", has_a ^ has_b,
              f"alpha={has_a}, beta={has_b}")
        labels.append("ALPHA" if has_a else "BETA")
    card_orders[f"{run['policy']}-{run['seed']}"] = labels
    check(f"both-distinct-markers-{run['policy']}-{run['seed']}", set(labels) == {"ALPHA", "BETA"},
          f"order={labels}")
    score = scored_by_key[(run["seed"], run["policy"])]
    mapping_ok = score["finalLabelMappingCorrect"]
    key = (run["policy"], run["seed"])
    if not mapping_ok:
        observed_wrong.add(key)
    if run["policy"] == "serial":
        serial_correct += int(mapping_ok)
    else:
        parallel_correct += int(mapping_ok)
check("serial-final-3-of-3", serial_correct == 3, f"correct={serial_correct}/3")
check("parallel-final-1-of-3", parallel_correct == 1, f"correct={parallel_correct}/3")
check("parallel-wrong-seeds", observed_wrong == expected_wrong,
      f"observed={sorted(observed_wrong)}")
for key in ["parallel2-5051", "parallel2-5053"]:
    check(f"wrong-final-has-correct-task-markers-{key}", card_orders[key] == ["ALPHA", "BETA"],
          f"task-card marker order={card_orders[key]}; final mapping is reversed")
# The receipt's card projection and the C++ extraction retain only ok/output/toolTrace.
identity_fields = {"taskId", "taskCallId", "toolCallId", "requestId", "messageId", "call_id"}
projected = set(scored["runs"][0]["taskCards"][0])
check("task-card-identities-not-persisted", not (identity_fields & projected),
      f"persisted fields={sorted(projected)}")
collector = source[source.index("QJsonArray taskCards;"):source.index("taskCards.append(QJsonObject", source.index("QJsonArray taskCards;"))]
check("cpp-collector-discards-correlation-identifiers",
      not any(name in collector for name in ["tool_call_id", "toolCallId", "call_id", "requestId", "messageId"]),
      "task card projection stores only ok, output and toolTrace")
check("scorer-reads-final-assistant-answer",
      "q100HasExactMarkerLabels(\n                finalText" in source,
      "correctness is evaluated on the final assistant text, not by reordering task-card outputs")
check("one-million-profile-keeps-serial-default",
      "adaptiveSubagentLimit(2, 1048576, 49152, 4096), 1" in source,
      "ASTRA production 1M context remains serial by default")

result = {
    "taskId": "Q-20261024-VF-ITERATION-105",
    "sourceTask": "Q-20261024-VF-ITERATION-100",
    "status": "pass-diagnostic-inconclusive-on-component-attribution",
    "checksPassed": len(checks),
    "checksFailed": 0,
    "serialFinalCorrect": f"{serial_correct}/3",
    "parallelFinalCorrect": f"{parallel_correct}/3",
    "parallelWrongFinalSeeds": sorted(seed for policy, seed in observed_wrong),
    "taskCardMarkerOrderByRun": card_orders,
    "taskCardsHaveStableCorrelationIds": False,
    "interpretation": "En dos semillas parallel2 los dos resultados de task contienen los marcadores correctos, mientras el texto final invierte las etiquetas. Esto apunta al ensamblado/respuesta final del padre, pero el recibo no persiste IDs de llamada/tarea para atribuirlo definitivamente al scheduler o al modelo. No hay defecto de dispatch reproducido ni base para adoptar parallel2.",
    "memory": {"gpuUsed": False, "serverUsed": False, "networkUsed": False},
    "evidence": [str(raw_path.relative_to(ROOT)), str(scored_path.relative_to(ROOT)), str(cpp_path.relative_to(ROOT))],
    "checks": checks,
}
out = Path(__file__).resolve().parents[1] / "receipts/q105-forensic-check.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({k: result[k] for k in ["status", "checksPassed", "checksFailed", "serialFinalCorrect", "parallelFinalCorrect", "parallelWrongFinalSeeds", "taskCardsHaveStableCorrelationIds"]}, ensure_ascii=False))
