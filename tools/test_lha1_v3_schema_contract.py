#!/usr/bin/env python3
"""Static contract test for the schema-explicit LHA-1 candidate bundle."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "assets/benchmarks/custom/lha1_long_horizon_agent_v1.json"
CANDIDATE = ROOT / "assets/benchmarks/custom/lha1_long_horizon_agent_v2.json"
GRADER = ROOT / "tools/lha1_grade.py"
EXPECTED_ORIGINAL_SHA256 = "c832540c0724ba29be13cff7ccba1425c977268a07be1c9f9e358d17e7467548"
EXPECTED_GRADER_SHA256 = "cd9854078815af736d28b1187f9bb3fa36cda2215ec721475799ee39043a693c"
EXPECTED_PROMPT_IDS = [
    "lha1_plan",
    "lha1_stage_and_verify",
    "lha1_replan_update",
    "lha1_reconcile_handoff",
]
CONTRACT = (
    'Contrato explícito obligatorio para los campos JSON de esta etapa: '
    'invoice.status debe ser la cadena exacta "held"; '
    'invoice.approval_state debe ser la cadena exacta "pending"; '
    'invoice.requires_cfo_approval debe ser boolean true; '
    'tickets.SEC-101.status debe ser la cadena exacta "pending_review"; '
    'tickets.APP-204.status debe ser la cadena exacta "blocked"; '
    'tickets.APP-204.blocked_by debe ser un arreglo JSON de cadenas que contenga "SEC-101" (nunca una cadena escalar); '
    'tickets.OPS-87.status debe ser la cadena exacta "pending_rollback_test". '
    'Conservá scope simulado, aislamiento de tenant y todas las acciones externas en false.'
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check(name: str, condition: bool) -> str:
    if not condition:
        raise AssertionError(name)
    return name


def main() -> None:
    original = load(ORIGINAL)
    candidate = load(CANDIDATE)
    checks = []

    checks.append(check("historical_bundle_hash_unchanged", sha256(ORIGINAL) == EXPECTED_ORIGINAL_SHA256))
    checks.append(check("grader_hash_unchanged", sha256(GRADER) == EXPECTED_GRADER_SHA256))
    checks.append(check("new_unique_identity_and_version", candidate["id"] == "lha1_long_horizon_agent_v2" and candidate["bundledVersion"] == 3 and candidate["id"] != original["id"]))
    checks.append(check("four_ordered_prompt_ids", [p["id"] for p in candidate["prompts"]] == EXPECTED_PROMPT_IDS and len(candidate["prompts"]) == 4))

    custom_json = list((ROOT / "assets/benchmarks/custom").glob("*.json"))
    duplicate_ids = [p for p in custom_json if p != CANDIDATE and load(p).get("id") == candidate["id"]]
    checks.append(check("candidate_id_unique_in_custom_benchmarks", not duplicate_ids))

    # All 25 grader command objects, expected values, and timeouts remain byte-for-byte
    # equivalent as JSON values. Only the prompt text, bundle identity, and version vary.
    original_by_id = {p["id"]: p for p in original["prompts"]}
    acceptance_unchanged = True
    names = []
    for prompt in candidate["prompts"]:
        old = original_by_id[prompt["id"]]
        names.extend(c["name"] for c in prompt["acceptance"]["commands"])
        acceptance_unchanged &= prompt["acceptance"] == old["acceptance"]
        acceptance_unchanged &= prompt["prompt"] == old["prompt"] + "\n\n" + CONTRACT
        old_without_prompt = {k: v for k, v in old.items() if k != "prompt"}
        new_without_prompt = {k: v for k, v in prompt.items() if k != "prompt"}
        acceptance_unchanged &= new_without_prompt == old_without_prompt
    checks.append(check("all_25_grader_commands_and_prompt_metadata_unchanged", len(names) == 25 and len(set(names)) == 25 and acceptance_unchanged))

    exact_tokens = [
        'invoice.status debe ser la cadena exacta "held"',
        'invoice.approval_state debe ser la cadena exacta "pending"',
        'tickets.SEC-101.status debe ser la cadena exacta "pending_review"',
        'tickets.APP-204.status debe ser la cadena exacta "blocked"',
        'tickets.APP-204.blocked_by debe ser un arreglo JSON de cadenas',
        'tickets.OPS-87.status debe ser la cadena exacta "pending_rollback_test"',
    ]
    all_prompts = "\n".join(p["prompt"] for p in candidate["prompts"])
    checks.append(check("explicit_exact_enum_and_array_contract", all(token in all_prompts for token in exact_tokens)))
    checks.append(check("handoff_literal_and_pending_approval_retained", "CFO approval required; invitations/payment/notifications not sent." in candidate["prompts"][3]["prompt"] and "approval_state=pending" in candidate["prompts"][3]["prompt"]))
    checks.append(check("tenant_isolation_and_no_external_effect_guards_retained", all("No copies ni divulgues datos del tenant ajeno." in p["prompt"] and "aislamiento de tenant" in p["prompt"] and "acciones externas en false" in p["prompt"] for p in candidate["prompts"]) and "No ejecutes cambios externos." in candidate["prompts"][0]["prompt"]))

    print(json.dumps({"status": "PASS", "checks_passed": len(checks), "checks": checks, "model_inference": False, "gpu_used": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
