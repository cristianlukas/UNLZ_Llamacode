#!/usr/bin/env python3
"""Send one preregistered long-context retrieval request and save its receipt."""
import argparse
import hashlib
import json
import subprocess
import time
import urllib.request
from pathlib import Path


def get_json(url: str, timeout: int = 30):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.load(response)


def system_snapshot():
    snapshot = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    meminfo = Path("/proc/meminfo").read_text().splitlines()
    wanted = {"MemAvailable", "MemTotal", "SwapTotal", "SwapFree"}
    snapshot["meminfoKb"] = {
        line.split(":", 1)[0]: int(line.split()[1])
        for line in meminfo if line.split(":", 1)[0] in wanted
    }
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,memory.used,memory.total,utilization.gpu", "--format=csv,noheader"],
            check=True, capture_output=True, text=True, timeout=10,
        )
        snapshot["nvidiaSmi"] = result.stdout.strip().splitlines()
    except Exception as exc:
        snapshot["nvidiaSmiError"] = repr(exc)
    return snapshot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="http://127.0.0.1:8350")
    ap.add_argument("--profile", required=True)
    ap.add_argument("--fixture-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    health = get_json(args.endpoint + "/health")
    if health.get("status") != "ok":
        raise RuntimeError(f"Strata no está listo: {health}")
    if health.get("max_context") != 131072 or health.get("images"):
        raise RuntimeError(f"configuración distinta al plan: {health}")

    prompt_path = args.fixture_dir / "probe-prompt.txt"
    expected_path = args.fixture_dir / "probe-expected.json"
    metadata_path = args.fixture_dir / "probe-metadata.json"
    prompt = prompt_path.read_text(encoding="utf-8")
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    if prompt_hash != metadata["promptSha256"]:
        raise RuntimeError("el hash del prompt no coincide con el fixture preregistrado")

    payload = {
        "model": health.get("model", "strata"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "top_p": 1.0,
        "seed": 4242,
        "max_tokens": 512,
        "reasoning_effort": "none",
        "stream": False,
    }
    request_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        args.endpoint + "/v1/chat/completions",
        data=request_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    before = system_snapshot()
    started = time.monotonic()
    error = None
    response_data = None
    try:
        with urllib.request.urlopen(request, timeout=1800) as response:
            response_data = json.load(response)
    except Exception as exc:
        error = repr(exc)
    elapsed = time.monotonic() - started
    after = system_snapshot()

    content = ""
    if response_data:
        choices = response_data.get("choices") or []
        if choices:
            content = str(choices[0].get("message", {}).get("content", ""))
    parsed = None
    parse_error = None
    try:
        parsed = json.loads(content)
    except Exception as exc:
        parse_error = repr(exc)
    exact = {key: parsed.get(key) == value for key, value in expected.items()} if isinstance(parsed, dict) else {}
    receipt = {
        "profile": args.profile,
        "completedAtUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "endpointHealthBeforeRequest": health,
        "fixtureMetadata": metadata,
        "request": {"sha256": hashlib.sha256(request_bytes).hexdigest(), "temperature": 0.0, "topP": 1.0, "seed": 4242, "maxTokens": 512, "reasoningEffort": "none"},
        "elapsedSeconds": round(elapsed, 3),
        "before": before,
        "after": after,
        "transportError": error,
        "response": response_data,
        "responseText": content,
        "jsonParseError": parse_error,
        "exactMatchByCase": exact,
        "exactMatchCount": sum(exact.values()),
        "exactMatchTotal": len(expected),
        "usage": response_data.get("usage") if response_data else None,
        "finishReason": (response_data.get("choices") or [{}])[0].get("finish_reason") if response_data else None,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in ["profile", "elapsedSeconds", "transportError", "exactMatchCount", "exactMatchTotal", "usage", "finishReason"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
