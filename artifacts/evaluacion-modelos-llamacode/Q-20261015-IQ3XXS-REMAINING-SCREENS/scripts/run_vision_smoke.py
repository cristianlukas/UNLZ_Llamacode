#!/usr/bin/env python3
"""Send one preregistered image-counting request and retain a compact receipt."""
import argparse
import base64
import datetime
import hashlib
import json
import pathlib
import subprocess
import time
import urllib.request


def snapshot():
    out = {"atUtc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    mem = {}
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        key, value = line.split(":", 1)
        if key in ("MemAvailable", "SwapTotal", "SwapFree"):
            mem[key] = int(value.split()[0]) * 1024
    mem["SwapUsed"] = mem.get("SwapTotal", 0) - mem.get("SwapFree", 0)
    out["memoryBytes"] = mem
    proc = subprocess.run(
        ["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total,utilization.gpu", "--format=csv,noheader"],
        capture_output=True, text=True,
    )
    out["gpuCsv"] = proc.stdout.strip().splitlines() if proc.returncode == 0 else proc.stderr
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--image", required=True, type=pathlib.Path)
    parser.add_argument("--prompt", required=True, type=pathlib.Path)
    parser.add_argument("--expected", required=True, type=pathlib.Path)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args()

    image_bytes = args.image.read_bytes()
    prompt = args.prompt.read_text(encoding="utf-8")
    expected = json.loads(args.expected.read_text(encoding="utf-8"))
    base_url = args.endpoint.rsplit("/v1/", 1)[0]
    health = None
    response = None
    transport_error = None
    elapsed = None
    request_sha = None
    before = snapshot()
    try:
        with urllib.request.urlopen(base_url + "/health", timeout=30) as result:
            health = json.load(result)
        if health.get("status") != "ok" or not health.get("images"):
            raise RuntimeError(f"vision endpoint not ready: {health}")
        payload = {
            "model": health.get("model", "strata"),
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii")}},
            ]}],
            "temperature": 0.0,
            "top_p": 1.0,
            "top_k": 1,
            "seed": 4242,
            "max_tokens": 512,
            "reasoning_effort": "none",
            "stream": False,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request_sha = hashlib.sha256(body).hexdigest()
        request = urllib.request.Request(
            args.endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        started = time.monotonic()
        with urllib.request.urlopen(request, timeout=1800) as result:
            response = json.load(result)
        elapsed = round(time.monotonic() - started, 3)
    except Exception as exc:
        transport_error = f"{type(exc).__name__}: {exc}"

    content = ""
    if response:
        choices = response.get("choices") or []
        if choices:
            content = str((choices[0].get("message") or {}).get("content") or "")
    parsed = None
    parse_error = None
    try:
        parsed = json.loads(content)
    except Exception as exc:
        parse_error = f"{type(exc).__name__}: {exc}"
    exact_match = isinstance(parsed, dict) and parsed == expected
    receipt = {
        "profile": args.profile,
        "completedAtUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "endpointHealth": health,
        "fixture": {
            "imagePath": str(args.image),
            "imageSha256": hashlib.sha256(image_bytes).hexdigest(),
            "imageBytes": len(image_bytes),
            "promptSha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "expectedSha256": hashlib.sha256(args.expected.read_bytes()).hexdigest(),
        },
        "request": {
            "sha256": request_sha, "temperature": 0.0, "topP": 1.0, "topK": 1,
            "seed": 4242, "maxTokens": 512, "reasoningEffort": "none",
        },
        "before": before,
        "elapsedSeconds": elapsed,
        "transportError": transport_error,
        "response": response,
        "responseText": content,
        "parsed": parsed,
        "jsonParseError": parse_error,
        "expected": expected,
        "exactMatch": exact_match,
        "usage": response.get("usage") if response else None,
        "finishReason": (response.get("choices") or [{}])[0].get("finish_reason") if response else None,
        "after": snapshot(),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in ("profile", "elapsedSeconds", "transportError", "exactMatch", "usage", "finishReason")}, ensure_ascii=False))
    return 0 if response and not transport_error else 1


if __name__ == "__main__":
    raise SystemExit(main())
