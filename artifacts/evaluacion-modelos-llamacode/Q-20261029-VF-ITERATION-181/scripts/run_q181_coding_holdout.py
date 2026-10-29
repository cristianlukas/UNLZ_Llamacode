#!/usr/bin/env python3
"""Run the frozen coding suite against two isolated Q171 system agent profiles."""
from __future__ import annotations

import copy
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import run_harness2_control_v5 as h

FIXTURE = Path("/opt/q181/agent_efficiency_e2e_v1.json")
EXPECTED_SHA = "37c5907fa9220f56446c2ea8b3ed402d475b88aaa1d15fbceffe1960fd0b3f01"
MODEL_ID = "qwen3.8-flash-next-iq2_xs"
PASSES = 3
RESUME_PASSES = (2, 3)
AGENT_IDS = [
    "ce949c6a-d38c-49df-8a13-18a8cb49907b",  # Básico (copia)
    "8c898045-d1e1-4754-9ce4-b71a639cc160",  # Intermedio (copia)
]
LAUNCH_ID = "ea7f0e2c-8cd4-413e-a2fc-5315fc5f8adb"
MODEL_PROFILE_ID = "83230930-2646-4e5e-9078-aa108a883d3b"
BACKEND_ID = "6c6e81ef-f554-4b70-a957-899fd1a90351"
FIRST_PASS_STARTED_MS = 1793262010000


def reuse_q181_profiles() -> tuple[str, str, list[str]]:
    """Reuse the isolated profiles from the two completed pass-1 runs."""
    agent_specs = [h.invoke("profileManager", "agentProfileSpec", [agent_id])
                   for agent_id in AGENT_IDS]
    if any(not isinstance(spec, dict) or spec.get("tools", {}).get("mcpTools") is not False
           or spec.get("permissions", {}).get("fsScope") != "project"
           for spec in agent_specs):
        raise RuntimeError("persisted Q181 agent profile/isolation validation failed")
    backend = h.invoke("profileManager", "getBackend", [BACKEND_ID])
    model_profile = h.invoke("profileManager", "getModelProfile", [MODEL_PROFILE_ID])
    launch = h.invoke("profileManager", "getLaunchProfile", [LAUNCH_ID])
    if (backend.get("cloudBaseUrl") != h.MODEL_URL or backend.get("cloudKeyRef")
            or backend.get("cloudModel") != MODEL_ID
            or model_profile.get("modelId") != MODEL_ID
            or launch.get("backendProfileId") != BACKEND_ID
            or launch.get("modelProfileId") != MODEL_PROFILE_ID):
        raise RuntimeError("persisted Q181 launch/model/backend identity validation failed")
    return LAUNCH_ID, MODEL_PROFILE_ID, AGENT_IDS


def benchmark_definition(suite: dict[str, Any], pass_number: int) -> dict[str, Any]:
    prompts = copy.deepcopy(suite["prompts"])
    for prompt in prompts:
        # LlamaCode suppresses already-completed identical workloads. Unique
        # metadata IDs permit preregistered repeats; prompt/oracle remain fixed.
        prompt["id"] = f"{prompt['id']}_q181_repeat_{pass_number:02d}"
    return {
        "id": f"q181_agent_efficiency_v1_pass_{pass_number:02d}",
        "name": f"Q181 coding holdout · pass {pass_number}",
        "description": (
            "Frozen agent_efficiency_e2e_v1 coding prompts and acceptance tests; "
            "only agent profile differs."
        ),
        "prompts": prompts,
        "source": "Q181 preregistration; agent_efficiency_e2e_v1",
    }


def main() -> int:
    fixture_bytes = FIXTURE.read_bytes()
    fixture_sha = hashlib.sha256(fixture_bytes).hexdigest()
    if fixture_sha != EXPECTED_SHA:
        raise RuntimeError(f"coding fixture SHA mismatch: {fixture_sha}")
    suite = json.loads(fixture_bytes)
    prompt_ids = [p.get("id") for p in suite.get("prompts", [])]
    if prompt_ids != ["python_parser_regression", "typescript_localization", "cpp_safe_refactor"]:
        raise RuntimeError(f"unexpected coding holdout tasks: {prompt_ids}")

    models = h.wait_ready()
    if not any(item.get("id") == MODEL_ID for item in models):
        raise RuntimeError(f"unexpected local model list: {models}")
    if h.prop("", "privacyModeEnabled") is not True:
        enabled = h.request("/setprop", method="POST",
                            data={"name": "privacyModeEnabled", "value": True})
        if enabled.get("ok") is not True or h.prop("", "privacyModeEnabled") is not True:
            raise RuntimeError(f"could not enable isolated privacy mode: {enabled}")

    launch_id, model_profile_id, agent_ids = reuse_q181_profiles()
    prior_events = [json.loads(line) for line in h.EVENTS.read_text(encoding="utf-8").splitlines()
                    if line.strip()]
    prior_runs = [event for event in prior_events
                  if event.get("event") == "run_complete" and event.get("variant") == "pass_01"]
    prior_order = next((event for event in prior_events
                        if event.get("event") == "q181_pair_start" and event.get("pass") == 1), None)
    if (len(prior_runs) != 2 or prior_order is None
            or {run.get("agent") for run in prior_runs} != set(agent_ids)):
        raise RuntimeError("expected two complete and balanced Q181 pass-1 records before resuming")
    orders: list[dict[str, Any]] = [{
        "pass": 1, "benchmark_id": "q181_agent_efficiency_v1_pass_01",
        "agent_order": prior_order["agent_order"], "prompt_ids": prompt_ids,
    }]
    runs: list[dict[str, Any]] = list(prior_runs)
    started_ms = FIRST_PASS_STARTED_MS
    resume_started_ms = int(time.time() * 1000)
    for pass_number in RESUME_PASSES:
        definition = benchmark_definition(suite, pass_number)
        benchmark_id = h.make_benchmark(definition)
        order = agent_ids if pass_number in (1, 3) else list(reversed(agent_ids))
        orders.append({"pass": pass_number, "benchmark_id": benchmark_id,
                       "agent_order": order, "prompt_ids": prompt_ids})
        h.append_event({"event": "q181_pair_start", "pass": pass_number,
                        "benchmark_id": benchmark_id, "agent_order": order,
                        "resume_after_duplicate_guard": True})
        for order_index, agent_id in enumerate(order, 1):
            runs.append(h.run_once(launch_id, benchmark_id, agent_id,
                                   f"pass_{pass_number:02d}", order_index))

    report = h.invoke("", "compareHarnessBenchmarks",
                       [agent_ids, "", float(started_ms)])
    result = report.get("result", report)
    row_count = int(result.get("rows", 0))
    profiles = result.get("profiles", [])
    counts = {str(item.get("profileId")): int(item.get("runs", 0))
              for item in profiles}
    summary = {
        "task": "Q181-Harness2-coding-holdout",
        "fixture_id": suite["id"], "fixture_sha256": fixture_sha,
        "prompt_ids": prompt_ids, "passes_per_profile": PASSES,
        "task_executions_per_profile": PASSES * len(prompt_ids),
        "task_executions_total": PASSES * len(prompt_ids) * len(agent_ids),
        "started_epoch_ms": started_ms,
        "resume_started_epoch_ms": resume_started_ms,
        "resume_attempt": 2,
        "resumed_after_duplicate_guard": True,
        "model_id": MODEL_ID, "model_endpoint": h.MODEL_URL,
        "model_ready": models,
        "launch_profile_id": launch_id, "model_profile_id": model_profile_id,
        "agent_profile_ids": agent_ids,
        "agent_system_profiles": ["agent-basico", "agent-intermedio"],
        "mcp_enabled": False, "privacy_mode": True,
        "external_network": "systemd PrivateNetwork; loopback only",
        "gpu_selection": "CUDA_VISIBLE_DEVICES=0,1; Strata ASTRA dual RTX 3090",
        "context_tokens": 1048576, "pair_order": orders,
        "run_rows": runs, "comparison_rows": row_count,
        "profile_runs": counts, "comparison": result,
        "validity": {
            "balanced": row_count == PASSES * len(agent_ids)
                        and all(counts.get(agent_id) == PASSES for agent_id in agent_ids),
            "expected_comparison_rows": PASSES * len(agent_ids),
        },
        "decision_rule": (
            "Recommend Intermedio only if accepted tasks are not lower, no critical "
            "regressions occur, and median E2E improves >=10% or repairs decrease."
        ),
    }
    h.SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    h.append_event({"event": "q181_complete", "summary": str(h.SUMMARY),
                    "comparison_rows": row_count, "profile_runs": counts,
                    "valid": summary["validity"]["balanced"]})
    return 0 if summary["validity"]["balanced"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
