#!/usr/bin/env python3
"""Generate an image-only Spanish scan PDF and exercise Poppler + Tesseract."""
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import time

from PIL import Image, ImageDraw, ImageFont

OUT = pathlib.Path(sys.argv[1]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
source = OUT / "synthetic-scan.jpg"
pdf = OUT / "synthetic-scan.pdf"
rendered = OUT / "rendered-page.png"
ocr_txt = OUT / "ocr.txt"
receipt = OUT / "result.json"

width, height = 1654, 2339  # A4 at ~200 DPI
image = Image.new("RGB", (width, height), "white")
draw = ImageDraw.Draw(image)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 58)
small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 42)
lines = [
    ("FORMULARIO DE ENSAYO DOCUMENTAL", font),
    ("Referencia: OCR-PDF-5231", font),
    ("Laboratorio: UNLZ-LAB-07", font),
    ("Valido hasta: 25/10/2026", font),
    ("Muestra sintetica para validar OCR local.", small),
]
y = 350
for text, line_font in lines:
    draw.text((145, y), text, fill="black", font=line_font)
    y += 145
# Slight skew and JPEG artifacts make this a simple scan-like image, not a born-digital PDF.
image = image.rotate(0.25, resample=Image.Resampling.BICUBIC, fillcolor="white")
image.save(source, "JPEG", quality=88, optimize=False)
Image.open(source).convert("RGB").save(pdf, "PDF", resolution=200.0)

def run(argv):
    return subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

pdfinfo = run(["pdfinfo", str(pdf)]).stdout
page_match = re.search(r"^Pages:\s+(\d+)\s*$", pdfinfo, re.MULTILINE)
if not page_match:
    raise RuntimeError("pdfinfo did not report page count")
page_count = int(page_match.group(1))
pdf_text = run(["pdftotext", str(pdf), "-"]).stdout
run(["pdftoppm", "-f", "1", "-l", "1", "-singlefile", "-r", "220", "-png", str(pdf), str(rendered.with_suffix(""))])
start = time.perf_counter()
ocr = run(["tesseract", str(rendered), "stdout", "-l", "spa+eng", "--psm", "6"])
ocr_seconds = time.perf_counter() - start
ocr_txt.write_text(ocr.stdout, encoding="utf-8")
compact = re.sub(r"[^A-Z0-9]+", "", ocr.stdout.upper())
expected = {
    "reference": "OCRPDF5231",
    "lab_id": "UNLZLAB07",
    "date": "25102026",
}
matched = {key: value in compact for key, value in expected.items()}
result = {
    "status": "PASS" if page_count == 1 and not pdf_text.strip() and all(matched.values()) else "FAIL",
    "pageCount": page_count,
    "pdfHasSelectableText": bool(pdf_text.strip()),
    "pdfTextChars": len(pdf_text.strip()),
    "expectedSentinels": expected,
    "matchedSentinels": matched,
    "ocrSeconds": round(ocr_seconds, 3),
    "tesseractVersion": run(["tesseract", "--version"]).stdout.splitlines()[0],
    "languages": ["spa", "eng"],
    "psm": 6,
    "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (source, pdf, rendered, ocr_txt)},
    "ocrText": ocr.stdout,
    "stderr": {"pdftoppm": "", "tesseract": ocr.stderr},
}
receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
if result["status"] != "PASS":
    raise SystemExit(1)
