# Q123 · OCR de PDF escaneado con fixture sintético · 2026-10-25

## Resultado

**PASS en el alcance sintético.** Se creó un PDF A4 de una página cuya única capa es una imagen escaneada sintética (giro 0,25°, JPEG quality 88). `pdftotext` no encontró texto seleccionable. Poppler lo rasterizó a 220 dpi y Tesseract 5.3.4 (`spa+eng`, PSM 6) recuperó **3/3** campos (`OCR-PDF-5231`, `UNLZ-LAB-07`, `25/10/2026`) en 0,343 s.

No se usaron documentos reales, modelo generativo, servidor de inferencia, GPU, red externa ni cambios productivos.

## Qué valida y qué falta

Esto demuestra que las dependencias instaladas pueden reconocer una fixture simple. No demuestra calidad en documentos reales ni integración con LlamaCode. La revisión de `src/core/DocumentExtractor.cpp` confirma que `extractRich` devuelve “sin texto extraíble (¿PDF escaneado? requeriría OCR)” cuando no hay texto; no llama a Tesseract ni rasteriza páginas. `OcrEngine` está limitado a imágenes de UI. Por tanto el OCR automático de PDF sigue sin existir en el camino de la app.

**Decisión:** mantener el producto sin cambios. Para cerrar el actionable hace falta diseñar/integrar un fallback PDF claramente opt-in y validarlo con un holdout real autorizado contra el extractor actual. Hasta entonces, no afirmar OCR de PDF integrado ni calidad documental real.

## Evidencia

- `PLAN.md`, `receipts/preregistration.json` y `receipts/sheet-preregistration-readback.json`.
- Runner congelado por SHA-256 antes del test: `scripts.py`.
- `runs/synthetic-scan-01/result.json`, `ocr.txt`, PDF fixture y página renderizada.
- `receipts/synthetic-pdf-ocr-result.json`, `receipts/postflight.json`, `receipts/actionables-sync-local.json` y `receipts/google-sheet-sync-final.json`.
