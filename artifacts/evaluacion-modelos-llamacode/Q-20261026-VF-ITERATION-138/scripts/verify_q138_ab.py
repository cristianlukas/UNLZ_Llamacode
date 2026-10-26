#!/usr/bin/env python3
"""CPU-only preregistration and runner checks; never starts an inference server."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261026-VF-ITERATION-138"
sys.path.insert(0, str(TASK / "scripts"))
import run_q138_ab as runner


def main() -> int:
    prereg = json.loads((TASK / "receipts/amendment-01-runtime-and-prompt-correction.json").read_text())
    assert prereg["workload"]["requestsPerProfile"] == 36
    assert prereg["workload"]["seeds"] == [4242, 5051, 6061]
    assert prereg["worker"]["memoryLimits"] == {"MemoryHigh": None, "MemoryMax": None, "MemorySwapMax": None}
    assert prereg["guard"]["onlyStopOwnedServerProcessGroup"] is True
    assert prereg["preflight"]["noGUIProcessTermination"] is True
    assert len(prereg["profiles"]) == 2
    assert prereg["profiles"][0]["port"] != prereg["profiles"][1]["port"]
    source, questions = runner.verify_fixture()
    schedule = [(seed, q["id"]) for seed in prereg["workload"]["seeds"] for q in questions]
    assert len(schedule) == 36 and len(set(schedule)) == 36
    assert all(source in runner.assembled_prompt(q, source)[0][1]["content"] for q in questions)
    assert runner.strict_score("A", "A")
    assert runner.strict_score(" A\n", "A")
    assert not runner.strict_score("Answer: A", "A")
    assert not runner.strict_score("A.", "A")
    qwen = prereg["profiles"][1]
    assert qwen["serverArgs"][qwen["serverArgs"].index("--tensor-split") + 1] == "1,1"
    astra = prereg["profiles"][0]
    assert "--max-context" in astra["engineArgs"]
    assert astra["engineArgs"][astra["engineArgs"].index("--max-context") + 1] == "1048576"
    assert astra["mtp"]["mode"] == "4-token speculative decoding"

    runner_path = TASK / "scripts/run_q138_ab.py"
    verifier_path = TASK / "scripts/verify_q138_ab.py"
    attempt06_path = TASK / "receipts/amendment-06-startup-timeout-preregistration.json"
    attempt05_path = TASK / "receipts/amendment-05-astra-config-log-parent.json"
    attempt04_path = TASK / "receipts/amendment-04-runner-prereg-name-fix.json"
    attempt02_path = TASK / "receipts/amendment-02-attempt02-log-directory-fix.json"
    active_path = attempt06_path if attempt06_path.exists() else (attempt05_path if attempt05_path.exists() else (attempt04_path if attempt04_path.exists() else attempt02_path))
    active_pins = json.loads(active_path.read_text()) if active_path.exists() else prereg
    assert hashlib.sha256(runner_path.read_bytes()).hexdigest() == active_pins["runner"]["sha256"]
    assert hashlib.sha256(verifier_path.read_bytes()).hexdigest() == active_pins["staticVerifier"]["sha256"]
    text = runner_path.read_text(encoding="utf-8")
    parsed = ast.parse(text)
    assert runner.wait_ready.__defaults__ == (1800,)
    assert 'within {timeout}s; log tail:' in text and '[-5000:]' in text
    verify_fn = next(node for node in parsed.body if isinstance(node, ast.FunctionDef) and node.name == "verify_artifacts")
    assert not any(isinstance(node, ast.Name) and node.id == "prereg" and isinstance(node.ctx, ast.Load) for node in ast.walk(verify_fn))
    assert 'profile_prereg["guard"]' in text
    assert 'runs" / attempt_name' in text and 'attempt05' in text
    assert 'campaign-{attempt_name}-progress.json' in text and 'preflight-attempt05.json' in text
    astra_profile = prereg["profiles"][0]
    configured_engine_log = runner.ensure_astra_engine_log_parent(astra_profile)
    assert configured_engine_log.parent.is_dir()
    assert TASK.resolve() in configured_engine_log.parents
    server_fn = next(node for node in parsed.body if isinstance(node, ast.FunctionDef) and node.name == "server_process")
    server_source = ast.get_source_segment(text, server_fn)
    assert server_source.index("ensure_astra_engine_log_parent(profile)") < server_source.index("subprocess.Popen")
    assert text.index("gates = preflight") < text.index("server_process(profile, log_path)")
    assert "monitor.start()" in text and text.index("monitor.start()") < text.index("server_process(profile, log_path)")
    assert "MemoryMax" not in text and "MemoryHigh" not in text and "MemorySwapMax" not in text
    report = {
        "status": "PASS",
        "kind": "cpu_only_runner_and_preregistration_validation",
        "modelInferenceStarted": False,
        "gpuInferenceStarted": False,
        "questionCount": len(questions),
        "decompilationCharacters": len(source),
        "requestsPerProfile": len(schedule),
        "profilesSerialized": True,
        "strictExactScorer": True,
        "monitorStartsBeforeInferenceServer": True,
        "noWorkerMemoryCaps": True,
        "runnerSha256": hashlib.sha256(runner_path.read_bytes()).hexdigest(),
        "attribution": "A pilot of these two complete inference profiles on the fixed synthetic Ghidra corpus; not general model quality."
    }
    assert 'choices=("attempt05",)' in text
    output = TASK / "receipts/runner-static-validation-attempt05.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
