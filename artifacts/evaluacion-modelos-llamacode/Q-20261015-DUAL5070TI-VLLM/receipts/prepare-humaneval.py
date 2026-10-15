import gzip, hashlib, json, urllib.request
from pathlib import Path

base = Path("artifacts/evaluacion-modelos-llamacode/Q-20261015-DUAL5070TI-VLLM/receipts")
metadata = json.loads((base / "humaneval-upstream-metadata.json").read_text())
req = urllib.request.Request(metadata["download_url"], headers={"User-Agent": "LlamaCode-evaluation"})
with urllib.request.urlopen(req, timeout=60) as response:
    compressed = response.read()
if len(compressed) != metadata["size_bytes"]:
    raise SystemExit(f"size mismatch: {len(compressed)} != {metadata['size_bytes']}")
git_blob_sha1 = hashlib.sha1(f"blob {len(compressed)}\0".encode() + compressed).hexdigest()
if git_blob_sha1 != metadata["git_blob_sha1"]:
    raise SystemExit(f"Git blob SHA1 mismatch: {git_blob_sha1} != {metadata['git_blob_sha1']}")
compressed_sha256 = hashlib.sha256(compressed).hexdigest()
rows_raw = gzip.decompress(compressed)
rows = [json.loads(line) for line in rows_raw.splitlines() if line.strip()]
required = {"task_id", "prompt", "test", "entry_point"}
if len(rows) != 164 or any(not required.issubset(row) for row in rows):
    raise SystemExit(f"dataset shape invalid: rows={len(rows)}")
if [row["task_id"] for row in rows[:20]] != [f"HumanEval/{i}" for i in range(20)]:
    raise SystemExit("unexpected first 20 HumanEval task IDs")
(base / "data").mkdir(exist_ok=True)
(base / "data" / "HumanEval.jsonl.gz").write_bytes(compressed)
(base / "data" / "HumanEval.jsonl").write_bytes(rows_raw)
sha256 = hashlib.sha256(rows_raw).hexdigest()
summary = {
    "source_commit": metadata["commit"],
    "compressed_size_bytes": len(compressed),
    "git_blob_sha1_verified": git_blob_sha1,
    "compressed_sha256": compressed_sha256,
    "jsonl_size_bytes": len(rows_raw),
    "jsonl_sha256": sha256,
    "record_count": len(rows),
    "first_20_task_ids": [row["task_id"] for row in rows[:20]],
    "HE0_pack_sha256": hashlib.sha256((rows_raw.splitlines()[0] + b"\n")).hexdigest(),
    "HE20_pack_sha256": hashlib.sha256(b"\n".join(rows_raw.splitlines()[:20]) + b"\n").hexdigest(),
}
(base / "humaneval-dataset-integrity.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
