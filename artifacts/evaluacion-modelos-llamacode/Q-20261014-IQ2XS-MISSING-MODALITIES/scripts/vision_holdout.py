#!/usr/bin/env python3
"""Submit a synthetic objective image holdout to a local OpenAI-compatible model."""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import re
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261014-IQ2XS-MISSING-MODALITIES"


def make_image() -> bytes:
    from PIL import Image, ImageDraw

    im = Image.new("RGB", (960, 640), "#f5f6f8")
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((28, 28, 932, 612), radius=22, fill="white", outline="#25364b", width=4)
    d.text((58, 48), "Inspection board - synthetic holdout", fill="#172b4d")
    # Three unambiguous blue triangles and two red circles, mixed in position.
    d.polygon([(190, 205), (115, 335), (265, 335)], fill="#2463eb", outline="#163b91")
    d.ellipse((375, 185, 515, 325), fill="#dc2626", outline="#7f1d1d", width=4)
    d.polygon([(685, 185), (610, 315), (760, 315)], fill="#2463eb", outline="#163b91")
    d.ellipse((170, 405, 310, 545), fill="#dc2626", outline="#7f1d1d", width=4)
    d.polygon([(520, 390), (445, 520), (595, 520)], fill="#2463eb", outline="#163b91")
    return_image = io.BytesIO()
    im.save(return_image, format="PNG", optimize=True)
    return return_image.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8350/v1")
    ap.add_argument("--model", required=True)
    ap.add_argument("--profile", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--image-out", type=Path, default=TASK / "fixtures/vision_holdout.png")
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()

    image = make_image()
    args.image_out.parent.mkdir(parents=True, exist_ok=True)
    args.image_out.write_bytes(image)
    image_hash = hashlib.sha256(image).hexdigest()
    data_url = "data:image/png;base64," + base64.b64encode(image).decode("ascii")
    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": (
                'Count the blue triangles and red circles in the attached synthetic inspection board. '
                'Return only JSON exactly shaped as {"blue_triangles": <integer>, "red_circles": <integer>}.'
            )},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]}],
        "temperature": 0.0,
        "top_p": 1.0,
        "top_k": 20,
        "max_tokens": 512,
        "stream": False,
    }
    req = Request(args.base_url.rstrip("/") + "/chat/completions",
                  data=json.dumps(payload).encode("utf-8"),
                  headers={"Content-Type": "application/json"})
    start = time.monotonic()
    try:
        with urlopen(req, timeout=args.timeout) as response:
            status = response.status
            body = json.loads(response.read())
    except HTTPError as error:
        status = error.code
        body = error.read().decode("utf-8", "replace")
    elapsed = time.monotonic() - start
    content = ""
    if status == 200 and isinstance(body, dict):
        choices = body.get("choices") or []
        if choices:
            content = str((choices[0].get("message") or {}).get("content") or "")
    match = re.search(r"\{.*?\}", content, re.S)
    parsed = None
    if match:
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    passed = status == 200 and parsed == {"blue_triangles": 3, "red_circles": 2}
    row = {
        "schema": "q14-vision-holdout-v1",
        "profile": args.profile,
        "model": args.model,
        "endpoint": args.base_url,
        "imageSha256": image_hash,
        "imageBytes": len(image),
        "httpStatus": status,
        "elapsedSeconds": round(elapsed, 3),
        "expected": {"blue_triangles": 3, "red_circles": 2},
        "rawContent": content,
        "parsed": parsed,
        "passed": passed,
        "response": body,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"profile": args.profile, "httpStatus": status,
                      "parsed": parsed, "passed": passed,
                      "elapsedSeconds": row["elapsedSeconds"]}, ensure_ascii=False), flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
