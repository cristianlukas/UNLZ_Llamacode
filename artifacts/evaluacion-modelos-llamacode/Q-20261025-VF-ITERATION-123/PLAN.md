# Q123 · OCR de PDF escaneado con fixture sintético · 2026-10-25

## Objetivo

Extender Q119 de ingestión de un sidecar Markdown a una comprobación técnica del OCR local de una página PDF escaneada. Determinar si el stack Poppler + Tesseract en Ubuntu reconoce identificadores en español sin depender de un modelo generativo. No se usarán documentos reales ni se cambiará la extracción productiva.

## Evidencia previa e hipótesis

- Q119 sólo probó el sidecar Markdown sintético a través de DataLabStore.
- `DocumentExtractor::extractRich` actualmente devuelve “sin texto extraíble (¿PDF escaneado? requeriría OCR)” si el extractor no obtiene texto. `OcrEngine` procesa imágenes de UI, no documentos fotográficos/PDF; no se presupone que la aplicación integre un fallback PDF.
- Preflight: `tesseract`, idioma `spa`, `pdftoppm`, `pdftotext`, ImageMagick, Pillow y fuente DejaVu Sans disponibles.
- Hipótesis limitada: generar un PDF de una página cuya única capa sea una imagen, rasterizarlo y reconocer los tres campos centinela con Tesseract `spa+eng`. Esto demuestra viabilidad de dependencias y calidad en un fixture sintético, no una integración LlamaCode ni exactitud en documentación real.

## Preregistro

- Fixture reproducible generado localmente en `runs/synthetic-scan-01/`: página A4 1654×2339, texto sintético grande, giro 0,25° y JPEG quality 88 embebido en PDF.
- Sentinelas: `OCR-PDF-5231`, `UNLZ-LAB-07`, `25/10/2026`.
- Gate: `pdfinfo` informa 1 página; `pdftotext` no obtiene texto seleccionable; `pdftoppm` rasteriza página 1 a 220 dpi; `tesseract -l spa+eng --psm 6` reconoce los tres sentinelas (comparación normalizada alfanumérica). CPU-only.
- Si falla la generación/render/OCR, clasificar por etapa y no ajustar umbrales luego de observar el resultado. Una sola fixture sintética no autoriza adopción. Un pase sólo habilita solicitar/seleccionar un holdout real autorizado para validar el flujo de la aplicación.
- No build, inferencia LLM, GPU, descarga, red, documentos del usuario, edición de código productivo ni cambios a perfiles/modelos/RAM/swap.

## Comando preregistrado

```bash
python3 artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-123/scripts.py artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-123/runs/synthetic-scan-01
```
