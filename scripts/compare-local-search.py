#!/usr/bin/env python3
"""Compare two already-running loopback SearXNG-compatible JSON search APIs."""

from __future__ import annotations

import argparse
import http.client
import ipaddress
import json
import math
import socket
import statistics
import sys
import time
from pathlib import Path
from urllib.parse import urlencode, urlsplit


def loopback_target(raw_url: str) -> tuple[str, int, bool, str]:
    parsed = urlsplit(raw_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("endpoint must be an absolute HTTP(S) URL")
    host = parsed.hostname
    is_localhost = host.lower() == "localhost" or host.lower().endswith(".localhost")
    try:
        is_loopback = ipaddress.ip_address(host).is_loopback
    except ValueError:
        is_loopback = False
    if not (is_loopback or is_localhost):
        raise ValueError("endpoint must resolve by literal loopback IP or localhost name")
    if parsed.username or parsed.password:
        raise ValueError("endpoint must not contain credentials")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    base_path = parsed.path.rstrip("/")
    return host, port, parsed.scheme == "https", base_path


def tcp_preflight(target: tuple[str, int, bool, str], timeout: float) -> None:
    host, port, _, _ = target
    with socket.create_connection((host, port), timeout=timeout):
        pass


def fetch_results(target: tuple[str, int, bool, str], query: str, timeout: float) -> dict:
    host, port, tls, base_path = target
    connection_type = http.client.HTTPSConnection if tls else http.client.HTTPConnection
    connection = connection_type(host, port, timeout=timeout)
    path = (base_path + "/search") if base_path else "/search"
    path += "?" + urlencode({"q": query, "format": "json"})
    started = time.perf_counter()
    try:
        connection.request("GET", path, headers={"User-Agent": "LlamaCode-local-search-eval/1"})
        response = connection.getresponse()
        body = response.read(2 * 1024 * 1024 + 1)
        latency_ms = (time.perf_counter() - started) * 1000.0
        if len(body) > 2 * 1024 * 1024:
            raise ValueError("response exceeded 2 MiB")
        if response.status < 200 or response.status >= 300:
            return {"status": response.status, "latency_ms": latency_ms,
                    "error": f"HTTP {response.status}", "results": []}
        payload = json.loads(body.decode("utf-8"))
        results = payload.get("results", []) if isinstance(payload, dict) else []
        if not isinstance(results, list):
            raise ValueError("JSON results field is not an array")
        return {"status": response.status, "latency_ms": latency_ms,
                "error": None, "results": results[:10]}
    except Exception as exc:  # keep the other provider/cases observable
        return {"status": None, "latency_ms": (time.perf_counter() - started) * 1000.0,
                "error": f"{type(exc).__name__}: {exc}", "results": []}
    finally:
        connection.close()


def canonical_url(raw_url: str) -> str:
    parsed = urlsplit(raw_url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return ""
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.hostname.lower()}{path}"


def score_case(case: dict, response: dict) -> dict:
    expected = {canonical_url(url) for url in case["relevant_urls"]}
    expected.discard("")
    results = response["results"][:5]
    relevant_ranks = []
    matched_urls = set()
    normalized_results = []
    for rank, result in enumerate(results, start=1):
        url = result.get("url", "") if isinstance(result, dict) else ""
        normalized = canonical_url(str(url))
        normalized_results.append({
            "title": result.get("title", "") if isinstance(result, dict) else "",
            "url": str(url),
        })
        if normalized in expected and normalized not in matched_urls:
            relevant_ranks.append(rank)
            matched_urls.add(normalized)
    first_rank = min(relevant_ranks) if relevant_ranks else None
    dcg = sum(1.0 / math.log2(rank + 1) for rank in relevant_ranks)
    ideal_dcg = sum(1.0 / math.log2(rank + 1)
                    for rank in range(1, min(len(expected), 5) + 1))
    return {
        "id": case["id"],
        "status": response["status"],
        "error": response["error"],
        "latency_ms": round(response["latency_ms"], 3),
        "first_relevant_rank": first_rank,
        "hit_at_3": bool(first_rank is not None and first_rank <= 3),
        "recall_at_5": len(relevant_ranks) / len(expected) if expected else 0.0,
        "relevant_found_at_5": len(relevant_ranks),
        "mrr_at_5": 1.0 / first_rank if first_rank else 0.0,
        "ndcg_at_5": dcg / ideal_dcg if ideal_dcg else 0.0,
        "unique_hosts_at_5": len({urlsplit(item["url"]).hostname.lower()
                                  for item in normalized_results if urlsplit(item["url"]).hostname}),
        "results_at_5": normalized_results,
    }


def percentile(values: list[float], percent: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(percent * len(ordered)) - 1)]


def summarize(rows: list[dict], total_relevant: int) -> dict:
    valid = [row for row in rows if row["status"] is not None and row["error"] is None]
    latencies = [row["latency_ms"] for row in rows]
    return {
        "queries": len(rows),
        "successful_responses": len(valid),
        "errors": len(rows) - len(valid),
        "hit_rate_at_3": statistics.mean(row["hit_at_3"] for row in rows) if rows else 0.0,
        "mrr_at_5": statistics.mean(row["mrr_at_5"] for row in rows) if rows else 0.0,
        "ndcg_at_5": statistics.mean(row["ndcg_at_5"] for row in rows) if rows else 0.0,
        "recall_at_5_micro": (sum(row["relevant_found_at_5"] for row in rows)
                              / total_relevant) if total_relevant else 0.0,
        "unique_hosts_at_5_mean": statistics.mean(row["unique_hosts_at_5"] for row in rows)
                                  if rows else 0.0,
        "latency_p50_ms": percentile(latencies, 0.50),
        "latency_p95_ms": percentile(latencies, 0.95),
        "total_relevant_urls": total_relevant,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plumb-url", required=True)
    parser.add_argument("--searxng-url", required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    payload = {
        "status": "blocked",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "method": "same 30 queries, serial requests, local endpoints only; no redirects or retries",
        "queries_sent": 0,
    }
    try:
        plumb_target = loopback_target(args.plumb_url)
        searx_target = loopback_target(args.searxng_url)
        cases = json.loads(args.cases.read_text(encoding="utf-8"))
        if not isinstance(cases, list) or not cases:
            raise ValueError("cases must be a non-empty JSON array")
        for case in cases:
            if not all(key in case for key in ("id", "query", "relevant_urls")):
                raise ValueError("every case needs id, query and relevant_urls")
        # Check both providers before sending any query, so a missing baseline
        # cannot produce an unpaired or accidentally public comparison.
        preflight_errors = []
        for label, target in (("PlumbSearch", plumb_target), ("SearXNG", searx_target)):
            try:
                tcp_preflight(target, min(args.timeout, 2.0))
            except Exception as exc:
                preflight_errors.append(f"{label}: {type(exc).__name__}: {exc}")
        if preflight_errors:
            raise ConnectionError("; ".join(preflight_errors))
    except Exception as exc:
        payload["reason"] = f"{type(exc).__name__}: {exc}"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(payload["reason"], file=sys.stderr)
        return 2

    plumb_rows: list[dict] = []
    searx_rows: list[dict] = []
    for index, case in enumerate(cases):
        # Alternate order to reduce a systematic warm-cache/position advantage.
        order = [("plumbsearch", plumb_target, plumb_rows),
                 ("searxng", searx_target, searx_rows)]
        if index % 2:
            order.reverse()
        for _, target, destination in order:
            response = fetch_results(target, case["query"], args.timeout)
            destination.append(score_case(case, response))
            payload["queries_sent"] += 1

    total_relevant = sum(len(case["relevant_urls"]) for case in cases)
    payload.update({
        "status": "complete",
        "case_count": len(cases),
        "providers": {
            "plumbsearch": {
                "summary": summarize(plumb_rows, total_relevant), "cases": plumb_rows},
            "searxng": {
                "summary": summarize(searx_rows, total_relevant), "cases": searx_rows},
        },
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(json.dumps({"status": payload["status"], "case_count": len(cases),
                      "queries_sent": payload["queries_sent"],
                      "summaries": {name: provider["summary"]
                                    for name, provider in payload["providers"].items()}},
                     indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
