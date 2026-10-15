import json
from pathlib import Path

from anyjev import Decider, Question
from anyjev.backends.fake import FakeBackend


ROOT = Path("/task")
fixture = json.loads((ROOT / "fixtures/routing-risk-screen-v1.json").read_text())
gold = {case["state"]: case["label"] for case in fixture["cases"]}


def content(state: str, option: str) -> float:
    return 4.0 if gold.get(state) == option else 0.0


backend = FakeBackend(
    content,
    position_bias=[0.0, 8.0, 16.0, 32.0],
    label_prior={"A": 0.0, "B": 8.0, "C": 16.0, "D": 32.0},
)
raw = Decider(backend, level="raw", prior="none")
l0 = Decider(backend, level="L0", prior="none")

results = {"cases": len(fixture["cases"]), "raw": {}, "L0": {}}
for mode, decider in (("raw", raw), ("L0", l0)):
    correct = 0
    flips = 0
    for case in fixture["cases"]:
        answers = []
        for options in (fixture["options"], list(reversed(fixture["options"]))):
            q = Question.choice(fixture["question"], options, name="route")
            decision = decider.decide(case["state"], [q])[0]
            answers.append(decision.answer)
        correct += answers[0] == case["label"]
        flips += answers[0] != answers[1]
    results[mode] = {"correct_on_canonical": correct, "reverse_order_flips": flips}

out = ROOT / "receipts/fakebackend-smoke-results.json"
out.write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps(results, indent=2))
