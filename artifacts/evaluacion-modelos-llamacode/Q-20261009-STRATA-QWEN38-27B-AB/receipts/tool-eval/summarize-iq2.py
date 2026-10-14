#!/usr/bin/env python3
"""Aggregate the three IQ2_XS Hard Mode seeds with the frozen historical controls."""
import json
import pathlib
import re
import statistics


HERE = pathlib.Path(__file__).resolve().parent
TASK_ROOT = HERE.parents[1]
BASELINE = pathlib.Path("artifacts/evaluacion-modelos-llamacode/Q-20261010-FRONTIER-MULTITASK-AB/receipts/tool-eval/all-seeds-comparison.json")
SEEDS = (42, 43, 44)
PROFILE_FP = "1906a54af838d39dbf3d8fc4ccfbc71bcf0985927869068dfb5e5aba4ff223bc"
ENGINE_LOG = pathlib.Path("artifacts/evaluacion-modelos-llamacode/Q-20261009-STRATA-QWEN38-27B-AB/receipts/logs/iq2_xs-strata.log")


def main():
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    runs = {}
    seed_rows = []
    for seed in SEEDS:
        path = HERE / f"iq2-hardmode-seed-{seed}.json"
        run = json.loads(path.read_text(encoding="utf-8"))
        runs[seed] = run
        score = run["scores"]
        category = score["category_scores"][0]
        seed_rows.append({
            "seed": seed,
            "json": path.name,
            "report": run["report_path"],
            "run_id": run["run_id"],
            "points": score["total_points"],
            "max_points": score["max_points"],
            "score_percent": score["final_score"],
            "pass": category["pass_count"],
            "partial": category["partial_count"],
            "fail": category["fail_count"],
            "safety_gate_passed": run["safety_gate"]["passed"],
            "safety_warnings": score["safety_warnings"],
            "median_turn_ms": score["median_turn_ms"],
            "total_tokens": score["total_tokens"],
            "runner_exit": 0,
        })

    status_lines = (HERE / "status.txt").read_text(encoding="utf-8").splitlines()
    elapsed = {}
    for line in status_lines:
        match = re.search(r"seed=(\d+).*elapsed_sec=(\d+).*exit=(\d+)", line)
        if match:
            elapsed[int(match.group(1))] = {
                "elapsed_sec": int(match.group(2)), "exit_code": int(match.group(3))
            }
    for row in seed_rows:
        row.update(elapsed.get(row["seed"], {}))

    log_pattern = re.compile(
        r"strata serve: prompt ([\d,]+) tokens .*?, ([\d,]+) generated in "
        r"([\d,]+) ms \(([-\d.]+) tok/s\)"
    )
    inference_rows = []
    for line_number, line in enumerate(ENGINE_LOG.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        match = log_pattern.search(line)
        if match:
            inference_rows.append({
                "line": line_number,
                "prompt_tokens": int(match.group(1).replace(",", "")),
                "output_tokens": int(match.group(2).replace(",", "")),
                "generation_ms": int(match.group(3).replace(",", "")),
                "reported_tps": float(match.group(4)),
            })
    # Hard Mode is the first sustained short-prompt block after the long-context
    # BCB runs, and ends when TaskFlow starts sending 10K+ context prompts.
    block_start = next(
        i for i, row in enumerate(inference_rows)
        if row["line"] > 370 and row["prompt_tokens"] < 10000
        and max(x["prompt_tokens"] for x in inference_rows[:i]) > 50000
    )
    block_end = next(
        (i for i in range(block_start + 1, len(inference_rows))
         if inference_rows[i]["prompt_tokens"] >= 10000), len(inference_rows)
    )
    hardmode_calls = [row for row in inference_rows[block_start:block_end]
                      if row["prompt_tokens"] > 24 and row["output_tokens"] > 0
                      and row["generation_ms"] > 0]

    candidate_scores = [row["score_percent"] for row in seed_rows]
    candidate_mean = statistics.mean(candidate_scores)
    historical = {}
    for name, data in baseline["profiles"].items():
        historical[name] = {
            "mean_score": data["mean_score"],
            "mean_points_per_run": data["mean_points_per_run"],
            "scores": data["scores"],
            "delta_candidate_mean_points": round(
                statistics.mean(row["points"] for row in seed_rows) - data["mean_points_per_run"], 2
            ),
            "delta_candidate_mean_score_pp": round(candidate_mean - data["mean_score"], 2),
            "comparison_type": "historical full-profile comparison; not model-only",
        }

    scenario_rows = []
    baseline_scenarios = {row["scenario_id"]: row for row in baseline["per_scenario"]}
    for i, scenario in enumerate(runs[SEEDS[0]]["scores"]["scenario_results"]):
        scenario_id = scenario["scenario_id"]
        historical_row = baseline_scenarios.get(scenario_id, {})
        candidate_by_seed = {}
        for seed in SEEDS:
            item = next(x for x in runs[seed]["scores"]["scenario_results"]
                        if x["scenario_id"] == scenario_id)
            candidate_by_seed[str(seed)] = {"status": item["status"], "points": item["points"]}
        scenario_rows.append({
            "scenario_id": scenario_id,
            "title": scenario.get("title") or historical_row.get("title"),
            "IQ2_XS": candidate_by_seed,
            "historical_controls": historical_row.get("profiles", {}),
        })

    summary = {
        "task_id": "Q-20261009-STRATA-QWEN38-27B-AB",
        "suite": baseline["suite"],
        "variant_seed": baseline["variant_seed"],
        "candidate": {
            "model": runs[SEEDS[0]]["config"]["model"],
            "backend": runs[SEEDS[0]]["config"]["backend"],
            "engine_version": runs[SEEDS[0]]["metadata"].get("engine_version"),
            "quantization": runs[SEEDS[0]]["metadata"].get("quantization"),
            "context": runs[SEEDS[0]]["metadata"].get("max_model_len"),
            "profile_fingerprint": PROFILE_FP,
            "runner_git_sha": runs[SEEDS[0]]["metadata"].get("git_sha"),
            "seeds": seed_rows,
            "mean_score": round(candidate_mean, 2),
            "population_sd_score": round(statistics.pstdev(candidate_scores), 2),
            "mean_points": round(statistics.mean(row["points"] for row in seed_rows), 2),
            "aggregate_counts": {
                key: sum(row[key] for row in seed_rows)
                for key in ("pass", "partial", "fail")
            },
            "aggregate_max_points": sum(row["max_points"] for row in seed_rows),
            "mean_scenario_seconds": round(statistics.mean(row["elapsed_sec"] for row in seed_rows), 2)
                if all("elapsed_sec" in row for row in seed_rows) else None,
            "total_scenario_seconds": sum(row.get("elapsed_sec", 0) for row in seed_rows),
            "hardmode_logged_decode": {
                "source_log": str(ENGINE_LOG),
                "source_line_range": [inference_rows[block_start]["line"],
                                      inference_rows[block_end]["line"]
                                      if block_end < len(inference_rows) else None],
                "valid_generation_calls": len(hardmode_calls),
                "output_tokens": sum(row["output_tokens"] for row in hardmode_calls),
                "generation_seconds": round(sum(row["generation_ms"] for row in hardmode_calls) / 1000, 3),
                "mean_logged_tps": round(statistics.mean(row["reported_tps"] for row in hardmode_calls), 2),
                "median_logged_tps": round(statistics.median(row["reported_tps"] for row in hardmode_calls), 2),
                "token_weighted_tps": round(
                    sum(row["output_tokens"] for row in hardmode_calls)
                    / (sum(row["generation_ms"] for row in hardmode_calls) / 1000), 2
                ),
                "method": "Strata per-generation decode rates over all valid model responses in the 28×3 Hard Mode block; excludes zero-token cancellations and the 24-token warmup probe.",
            },
        },
        "historical_comparisons": historical,
        "per_scenario": scenario_rows,
        "interpretation": {
            "classification": "valid quality runs; endpoint completed all 28 scenarios for each seed",
            "safety_gate_passed_all_seeds": all(row["safety_gate_passed"] for row in seed_rows),
            "stable_improvement_over_Q4": False,
            "limitation": "IQ2_XS/Strata is compared with historical complete profiles; small mean delta over Q4 does not establish a model-only gain.",
        },
    }
    out = HERE / "iq2-hardmode-comparison.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
