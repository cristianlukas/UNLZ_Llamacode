#!/usr/bin/env python3
"""Run the frozen LlamaCode retrieval screen against a local embeddings endpoint."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import statistics
import struct
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECEIPTS_ROOT = HERE / "receipts"
OUT_DIR = Path(os.environ.get("LLAMACODE_EVAL_RECEIPT_DIR", str(RECEIPTS_ROOT / "attempt-02")))
CORPUS_FILE = HERE / "corpus.jsonl"
QUERIES_FILE = HERE / "queries.jsonl"
QRELS_FILE = HERE / "qrels.jsonl"
URL = "http://127.0.0.1:8397/v1/embeddings"
MODEL_NAME = "embeddinggemma-2-Q8_0.gguf"
MAX_SECONDS = 30 * 60
BATCH_SIZE = 64
TOP_K = 5


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


CORPUS = read_jsonl(CORPUS_FILE)
QUERIES = read_jsonl(QUERIES_FILE)
QRELS = {row["query_id"]: row["chunk_id"] for row in read_jsonl(QRELS_FILE)}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def percentile(values, p):
    if not values:
        return None
    vals = sorted(values)
    pos = (len(vals) - 1) * p
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return vals[lo]
    return vals[lo] * (hi - pos) + vals[hi] * (pos - lo)


def bm25_rank(query):
    terms = []
    for term in re.split(r"[^\w]+", query.lower(), flags=re.UNICODE):
        if len(term) >= 2 and term not in terms:
            terms.append(term)
    scores = []
    for index, item in enumerate(CORPUS):
        low = item["text"].lower()
        score = 0.0
        distinct = 0
        for term in terms:
            tf = low.count(term)
            if tf > 0:
                distinct += 1
                score += tf / (tf + 1.5)
        if distinct > 0:
            score *= 1.0 + 0.5 * (distinct - 1)
            score /= 1.0 + len(item["text"]) / 4000.0
        scores.append((score, index))
    scores.sort(key=lambda pair: (-pair[0], pair[1]))
    return [index for _, index in scores], [score for score, _ in scores]


def cosine(a, b):
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def find_server_pid():
    model_marker = b"embeddinggemma-2-Q8_0.gguf"
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            comm = (proc / "comm").read_text().strip()
            cmdline = (proc / "cmdline").read_bytes()
            if comm == "llama-server" and model_marker in cmdline:
                return int(proc.name)
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            pass
    return None


SERVER_PID = find_server_pid()
monitor_stop = threading.Event()
monitor_values = {"rss_peak_mib": 0.0, "gpu1_process_peak_mib": 0.0, "gpu1_total_peak_mib": 0.0, "samples": 0}


def monitor_resources():
    while not monitor_stop.wait(1.0):
        if SERVER_PID:
            try:
                status = (Path("/proc") / str(SERVER_PID) / "status").read_text()
                match = re.search(r"^VmRSS:\s+(\d+)\s+kB", status, re.MULTILINE)
                if match:
                    monitor_values["rss_peak_mib"] = max(monitor_values["rss_peak_mib"], int(match.group(1)) / 1024)
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                pass
        try:
            proc = subprocess.run(
                ["nvidia-smi", "--query-compute-apps=pid,used_gpu_memory", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=2, check=False)
            for line in proc.stdout.splitlines():
                parts = [part.strip() for part in line.split(",")]
                if len(parts) == 2 and SERVER_PID and parts[0] == str(SERVER_PID):
                    monitor_values["gpu1_process_peak_mib"] = max(monitor_values["gpu1_process_peak_mib"], float(parts[1]))
            proc = subprocess.run(
                ["nvidia-smi", "--id=1", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=2, check=False)
            if proc.stdout.strip():
                monitor_values["gpu1_total_peak_mib"] = max(monitor_values["gpu1_total_peak_mib"], float(proc.stdout.splitlines()[0].strip()))
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
            pass
        monitor_values["samples"] += 1


def embed(strings, arm, kind, call_records, start_time):
    if time.monotonic() - start_time >= MAX_SECONDS:
        raise TimeoutError("30-minute evaluation cutoff reached")
    payload = json.dumps({"model": MODEL_NAME, "input": strings}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(URL, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read()
            status = response.status
    except Exception as error:
        error_body = ""
        if hasattr(error, "read"):
            try:
                error_body = error.read().decode("utf-8", errors="replace")[:2000]
            except Exception:
                pass
        call_records.append({"arm": arm, "kind": kind, "input_count": len(strings), "error": repr(error),
                             "error_body": error_body, "elapsed_s": time.monotonic() - started})
        raise
    elapsed = time.monotonic() - started
    obj = json.loads(body)
    data = obj.get("data", [])
    vectors = [None] * len(strings)
    for row in data:
        idx = int(row.get("index", -1))
        if 0 <= idx < len(vectors):
            vectors[idx] = [float(value) for value in row.get("embedding", [])]
    if any(vector is None for vector in vectors):
        raise RuntimeError(f"embedding response cardinality mismatch: expected {len(strings)}, got {len(data)}")
    dims = {len(vector) for vector in vectors}
    if len(dims) != 1 or not all(math.isfinite(value) for vector in vectors for value in vector):
        raise RuntimeError(f"invalid embedding dimensions/values: {dims}")
    call_records.append({"arm": arm, "kind": kind, "input_count": len(strings), "http_status": status,
                         "dimensions": next(iter(dims)), "elapsed_s": elapsed, "response_sha256": sha256(body)})
    return vectors, elapsed


def metrics(ranks):
    rows = {}
    for limit in (1, 3, 5):
        rows[f"recall@{limit}"] = sum(1 for rank in ranks if rank is not None and rank <= limit) / len(ranks)
    rows["mrr@5"] = sum(1.0 / rank for rank in ranks if rank is not None and rank <= 5) / len(ranks)
    rows["ndcg@5"] = sum(1.0 / math.log2(rank + 1) for rank in ranks if rank is not None and rank <= 5) / len(ranks)
    return rows


def write_vectors(path: Path, vectors):
    with path.open("wb") as target:
        for vector in vectors:
            target.write(struct.pack("<" + "f" * len(vector), *vector))
    return {"path": str(path), "count": len(vectors), "dimensions": len(vectors[0]) if vectors else 0,
            "bytes": path.stat().st_size, "sha256": sha256(path.read_bytes()), "dtype": "little-endian float32"}


def rank_arm(arm, doc_vectors, query_vectors, bm25_lists, bm25_scores, query_latencies):
    vector_rankings = []
    vector_scores_by_query = []
    for query, query_vec in zip(QUERIES, query_vectors):
        scored = [(cosine(query_vec, doc_vec), index) for index, doc_vec in enumerate(doc_vectors)]
        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        vector_rankings.append([index for _, index in scored])
        vector_scores_by_query.append({index: score for score, index in scored})
    rankings_by_name = {f"EG2-{arm}": vector_rankings}
    rrf_rankings = []
    for bm_list, vec_list in zip(bm25_lists, vector_rankings):
        fused = {}
        for rank, index in enumerate(bm_list):
            fused[index] = fused.get(index, 0.0) + 1.0 / (60.0 + rank + 1)
        for rank, index in enumerate(vec_list):
            fused[index] = fused.get(index, 0.0) + 1.0 / (60.0 + rank + 1)
        rrf_rankings.append(sorted(fused, key=lambda index: (-fused[index], index)))
    rankings_by_name[f"RRF-{arm}"] = rrf_rankings

    records = []
    result_metrics = {}
    index_by_id = {item["id"]: i for i, item in enumerate(CORPUS)}
    for name, rankings in rankings_by_name.items():
        target_ranks = []
        for query_index, (query, ranklist) in enumerate(zip(QUERIES, rankings)):
            target = QRELS[query["id"]]
            target_index = index_by_id[target]
            rank = ranklist.index(target_index) + 1
            target_ranks.append(rank if rank is not None and rank <= 5 else None)
            vector_rank_by_index = {index: r + 1 for r, index in enumerate(vector_rankings[query_index])}
            bm25_rank_by_index = {index: r + 1 for r, index in enumerate(bm25_lists[query_index])}
            if name.startswith("RRF-"):
                fused_scores = {}
                for r, index in enumerate(bm25_lists[query_index]):
                    fused_scores[index] = fused_scores.get(index, 0.0) + 1.0 / (60.0 + r + 1)
                for r, index in enumerate(vector_rankings[query_index]):
                    fused_scores[index] = fused_scores.get(index, 0.0) + 1.0 / (60.0 + r + 1)
            else:
                fused_scores = {}
            top = []
            for i in ranklist[:10]:
                top.append({"chunk_id": CORPUS[i]["id"],
                            "vector_score": vector_scores_by_query[query_index][i],
                            "vector_rank": vector_rank_by_index[i],
                            "bm25_score": bm25_scores[query_index][i],
                            "bm25_rank": bm25_rank_by_index[i],
                            "rrf_score": fused_scores.get(i) if fused_scores else None})
            records.append({"query_id": query["id"], "arm": name, "target_chunk": target,
                            "target_rank": rank, "hit_at_1": rank == 1, "hit_at_3": rank is not None and rank <= 3,
                            "hit_at_5": rank is not None and rank <= 5, "top10": top,
                            "query_embedding_latency_s": query_latencies[query_index]})
        result_metrics[name] = metrics(target_ranks)
    return records, result_metrics


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    calls_path = OUT_DIR / "api-calls.jsonl"
    rankings_path = OUT_DIR / "rankings.jsonl"
    for path in (calls_path, rankings_path):
        if path.exists() and path.stat().st_size:
            raise SystemExit(f"refusing to overwrite prior results: {path}")
    calls_path.touch()
    rankings_path.touch()
    call_records = []
    start = time.monotonic()
    wall_started = time.time()
    monitor = threading.Thread(target=monitor_resources, daemon=True)
    monitor.start()
    status = {"status": "running", "started_unix": wall_started, "server_pid": SERVER_PID,
              "endpoint": URL, "model": MODEL_NAME, "cutoff_seconds": MAX_SECONDS}
    try:
        bm25_lists, bm25_scores = [], []
        bm25_started = time.monotonic()
        for query in QUERIES:
            order, scores = bm25_rank(query["query"])
            bm25_lists.append(order)
            score_by_index = [0.0] * len(CORPUS)
            for rank, index in enumerate(order):
                score_by_index[index] = scores[rank]
            bm25_scores.append(score_by_index)
        bm25_seconds = time.monotonic() - bm25_started
        baseline_ranks = []
        corpus_ids = {item["id"]: index for index, item in enumerate(CORPUS)}
        for q, order in zip(QUERIES, bm25_lists):
            target_index = corpus_ids[QRELS[q["id"]]]
            rank = order.index(target_index) + 1
            baseline_ranks.append(rank if rank <= TOP_K else None)
        baseline = metrics(baseline_ranks)
        baseline_records = []
        for q, order, scores in zip(QUERIES, bm25_lists, bm25_scores):
            target_index = corpus_ids[QRELS[q["id"]]]
            rank = order.index(target_index) + 1
            baseline_records.append({"query_id": q["id"], "arm": "BM25", "target_chunk": QRELS[q["id"]],
                                     "target_rank": rank, "hit_at_1": rank == 1, "hit_at_3": rank <= 3,
                                     "hit_at_5": rank <= 5, "top10": [{"chunk_id": CORPUS[i]["id"], "bm25_score": scores[i]} for i in order[:10]]})
        with rankings_path.open("a", encoding="utf-8") as f:
            for row in baseline_records:
                f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

        arms = {}
        for arm in ("raw", "code-retrieval-prefix"):
            doc_inputs = []
            query_inputs = []
            for item in CORPUS:
                if arm == "raw":
                    doc_inputs.append(item["text"])
                else:
                    doc_inputs.append(f"title: {item['path']} | text: {item['text']}")
            for query in QUERIES:
                if arm == "raw":
                    query_inputs.append(query["query"])
                else:
                    query_inputs.append(f"task: code retrieval | query: {query['query']}")

            index_start = time.monotonic()
            doc_vectors = []
            for offset in range(0, len(doc_inputs), BATCH_SIZE):
                batch = doc_inputs[offset:offset + BATCH_SIZE]
                vectors, elapsed = embed(batch, arm, "documents", call_records, start)
                doc_vectors.extend(vectors)
                with calls_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(call_records[-1], ensure_ascii=False, separators=(",", ":")) + "\n")
            index_seconds = time.monotonic() - index_start

            query_start = time.monotonic()
            query_vectors = []
            query_latencies = []
            for query_text in query_inputs:
                vectors, elapsed = embed([query_text], arm, "query", call_records, start)
                query_vectors.append(vectors[0])
                query_latencies.append(elapsed)
                with calls_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(call_records[-1], ensure_ascii=False, separators=(",", ":")) + "\n")
            query_seconds = time.monotonic() - query_start

            safe_arm = arm.replace("-", "_")
            doc_vectors_info = write_vectors(OUT_DIR / f"embeddings_{safe_arm}_documents.f32", doc_vectors)
            query_vectors_info = write_vectors(OUT_DIR / f"embeddings_{safe_arm}_queries.f32", query_vectors)
            arm_records, arm_metrics = rank_arm(arm, doc_vectors, query_vectors, bm25_lists, bm25_scores, query_latencies)
            with rankings_path.open("a", encoding="utf-8") as f:
                for row in arm_records:
                    f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            arms[arm] = {"metrics": arm_metrics, "index_seconds": index_seconds, "query_batch_wall_seconds": query_seconds,
                         "query_latency_p50_s": statistics.median(query_latencies), "query_latency_p95_s": percentile(query_latencies, .95),
                         "query_latency_max_s": max(query_latencies), "query_count": len(query_latencies),
                         "document_vector_file": doc_vectors_info, "query_vector_file": query_vectors_info}
            if time.monotonic() - start >= MAX_SECONDS:
                raise TimeoutError("30-minute evaluation cutoff reached after completing an arm")

        # The current harness produces strings without task prefixes; that is its drop-in arm.
        summary = {"status": "complete", "suite": "LlamaCode code-retrieval screen v1", "started_unix": wall_started,
                   "elapsed_seconds": time.monotonic() - start, "cutoff_seconds": MAX_SECONDS,
                   "corpus_chunks": len(CORPUS), "query_count": len(QUERIES), "top_k": TOP_K,
                   "bm25_seconds": bm25_seconds, "bm25_metrics": baseline, "candidate_arms": arms,
                   "bm25_rrf_arm_metrics": {arm: values["metrics"][f"RRF-{arm}"] for arm, values in arms.items()},
                   "model": MODEL_NAME, "endpoint": URL, "server_pid": SERVER_PID,
                   "resource_samples": monitor_values.copy(),
                   "fingerprint_inputs": {"model_sha256":"2188ac1deca4b77dffefd603c2776a9d76d9d74ec01841392982ebb840b09135",
                                          "runtime":"llama.cpp b11554 commit 966baae76; server binary sha256 fe8a7d6073d3e3a276193fcaec162cbf280d2572ad2016c9100fd924be19c6ed",
                                          "server_args":"--embeddings --pooling mean --ctx-size 8192 --batch-size 2048 --ubatch-size 2048 --parallel 1 --n-gpu-layers 99 --device CUDA1",
                                          "corpus_sha256":json.loads((HERE/"fixture-manifest.json").read_text())["corpus_sha256"],
                                          "queries_sha256":json.loads((HERE/"fixture-manifest.json").read_text())["queries_sha256"],
                                          "qrels_sha256":json.loads((HERE/"fixture-manifest.json").read_text())["qrels_sha256"],
                                          "runner_sha256":sha256(Path(__file__).read_bytes())}}
        canonical = json.dumps(summary["fingerprint_inputs"], sort_keys=True, separators=(",", ":")).encode()
        summary["profile_suite_fingerprint"] = sha256(canonical)
        (OUT_DIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        status.update({"status":"complete", "elapsed_seconds":summary["elapsed_seconds"], "fingerprint":summary["profile_suite_fingerprint"]})
    except Exception as error:
        status.update({"status":"incomplete", "error":repr(error), "elapsed_seconds":time.monotonic()-start,
                       "resource_samples":monitor_values.copy()})
        raise
    finally:
        monitor_stop.set()
        monitor.join(timeout=3)
        status["resource_samples"] = monitor_values.copy()
        (OUT_DIR / "runner-status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(json.loads((OUT_DIR / "summary.json").read_text()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
