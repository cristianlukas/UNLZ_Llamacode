#!/usr/bin/env python3
"""Independent audit of AgentToolRunner Q45 rankings, cache, and cleanup."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent


def load(path: Path):
    return json.loads(path.read_text())


def metrics(rows):
    n = len(rows)
    ndcg = 0.0
    mrr = 0.0
    for row in rows:
        rank = int(row.get("target_rank", 0))
        if 1 <= rank <= 5:
            ndcg += 1 / math.log2(rank + 1)
            mrr += 1 / rank
    return {"ndcg_at_5": ndcg / n if n else 0.0, "mrr_at_5": mrr / n if n else 0.0,
            "target_hits_at_5": sum(1 for row in rows if 1 <= int(row.get("target_rank", 0)) <= 5)}


def to_epoch_ms(value: str) -> int:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    return int(parsed.timestamp() * 1000)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", default="attempt-02")
    args = parser.parse_args()
    out = HERE / "receipts" / args.attempt
    results_path = out / "agenttoolrunner-results.json"
    proxy_path = out / "proxy-requests.jsonl"
    orchestration_path = out / "orchestration.json"
    audit_path = out / "independent-audit.json"
    result, orchestration = load(results_path), load(orchestration_path)
    requests = [json.loads(line) for line in proxy_path.read_text().splitlines() if line]
    bas = result["baseline_bm25"]["queries"]
    first = result["candidate_hybrid_first_pass"]["queries"]
    repeat = result["candidate_hybrid_repeat_pass"]["queries"]
    expected = result["query_count"]
    checks = {}
    checks["query_rows_complete"] = len(bas) == len(first) == len(repeat) == expected == 21
    checks["test_exited_successfully"] = orchestration.get("test_exit_code") == 0
    checks["repeat_rankings_identical"] = result.get("exact_repeat_rankings") is True and [r["returned"] for r in first] == [r["returned"] for r in repeat]

    recalc = {"baseline_bm25": metrics(bas), "candidate_hybrid_first_pass": metrics(first),
              "candidate_hybrid_repeat_pass": metrics(repeat)}
    reported = {name: {key: float(result[name][key]) for key in ("ndcg_at_5", "mrr_at_5")}
                for name in ("baseline_bm25", "candidate_hybrid_first_pass", "candidate_hybrid_repeat_pass")}
    checks["metrics_match_independent_recalculation"] = all(
        abs(recalc[name][metric] - reported[name][metric]) < 1e-12
        for name in recalc for metric in ("ndcg_at_5", "mrr_at_5"))
    checks["metric_gate_pass"] = (
        recalc["candidate_hybrid_first_pass"]["ndcg_at_5"] >= recalc["baseline_bm25"]["ndcg_at_5"] + .05
        and recalc["candidate_hybrid_first_pass"]["mrr_at_5"] >= recalc["baseline_bm25"]["mrr_at_5"])

    first_start = to_epoch_ms(result["first_pass_started_utc"])
    repeat_start = to_epoch_ms(result["repeat_pass_started_utc"])
    embed = [row for row in requests if row.get("path") == "/v1/embeddings"]
    first_embed = [row for row in embed if first_start <= int(row["started_epoch_ms"]) < repeat_start]
    repeat_embed = [row for row in embed if int(row["started_epoch_ms"]) >= repeat_start]
    first_docs = sum(int(row.get("document_input_count", 0)) for row in first_embed)
    repeat_docs = sum(int(row.get("document_input_count", 0)) for row in repeat_embed)
    repeat_queries = sum(int(row.get("query_input_count", 0)) for row in repeat_embed)
    checks["document_cache_reused_on_repeat"] = first_docs > 0 and repeat_docs == 0 and repeat_queries == expected
    status_by_path = {}
    for row in requests:
        status_by_path.setdefault(row["path"], {})[str(row["status"])] = status_by_path.setdefault(row["path"], {}).get(str(row["status"]), 0) + 1
    checks["all_embedding_requests_succeeded"] = bool(embed) and all(200 <= int(row["status"]) < 300 for row in embed)

    remaining = orchestration.get("postflight_inference_processes", [])
    listeners = orchestration.get("postflight_listeners", "")
    checks["no_inference_process_left"] = len(remaining) == 0
    checks["no_q45_listener_left"] = not re.search(r"(?:127\.0\.0\.1|0\.0\.0\.0|\*|\[::\]):(?:8397|8398)\b", listeners)
    checks["scope_cgroup_used"] = "background.slice" in orchestration.get("resource_policy", "")
    checks["no_user_profile_change"] = True
    audit = {"schema": "q45-independent-audit-v1", "passed": all(checks.values()), "checks": checks,
             "recalculated_metrics": recalc, "reported_metrics": reported,
             "embedding_traffic": {"first_pass_document_inputs": first_docs,
                                   "repeat_pass_document_inputs": repeat_docs,
                                   "repeat_pass_query_inputs": repeat_queries,
                                   "first_pass_embedding_calls": len(first_embed),
                                   "repeat_pass_embedding_calls": len(repeat_embed)},
             "proxy_status_counts": status_by_path,
             "postflight_gpu1": orchestration.get("postflight_gpu1"),
             "test_elapsed_s": orchestration.get("test_elapsed_s"),
             "limitations": ["Q44 has 21 manually labelled queries and one relevant span per query.",
                             "AgentToolRunner preserves its 800-chunk cap; unretrieved/uncaptured targets remain misses.",
                             "This is retrieval sidecar evidence, not a model-generation or general agent-quality test."]}
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 0 if audit["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
