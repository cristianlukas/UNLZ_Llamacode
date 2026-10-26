# Q144 — resultados históricos incorporados a `Resultados`

**Estado:** completado · 2026-10-26
**Tipo de trabajo:** reconciliación documental y actualización del Google Sheet.
**Sin:** inferencia, benchmark, build, descarga, servicio de modelo ni uso de GPU.

## Resultado

Se revisaron las 18 pestañas del libro junto con los artefactos locales de evaluación y se agregaron 32 filas históricas que estaban ausentes de `Resultados`, en `Resultados!A237:AF268`. La pestaña queda con 267 IDs de datos únicos (235 anteriores y 32 incorporados).

Las filas cubren:

- Retests ASTRA/SOL de TaskFlow fixed-gold y Ledger fixed-gold.
- Smoke de Qwen3.8-27B Q4 en modo autoregresivo, n-gram y MTP4.
- Dos probes antiguos de inicio/health para Flash-Next y Qwen3.8; no son mediciones de calidad de contexto.
- Sweep MTP2–MTP8 de Qwen3.6 y Qwen3.8.
- Smoke de template safe-v2, dos brazos de ablación Flash-Next, resultados AURA multisite/transición y tres modos lazy.

## Interpretación y deduplicación

Las fallas de ASTRA previas a un artefacto/herramienta válido se registraron como fallas operativas no puntuables, no como cero de calidad. Las corridas SOL fixed-gold se identifican como una sola pasada tras reparación, con grader visible. El smoke de Qwen usa cuantización Q4 estándar y no demuestra calidad general ni reemplaza una comparación con QAT Q2. Los MTP sweep tienen el marcador final inválido para el grader de calidad; sus puntuaciones de calidad quedan N/D y solo se conserva la telemetría de velocidad con su muestra de 12 solicitudes. Los context probes reportan startup/health, no recuperación semántica a contexto largo. AURA y safe-v2 quedan etiquetados como pruebas sintéticas/smoke de alcance limitado. Lazy-on produjo salida corrupta en su prompt pequeño; lazy-direct fue válido pero más lento en esa corrida.

No se duplicaron A/B de fixture complejo, perfiles base/calibrado ya cargados, resultados Q09 ni otros fingerprints ya representados. Los campos ausentes quedaron como N/D; no se extrapoló ni derivó TPS. Cada fila conserva suite, configuración disponible, muestra, limitación y referencia local.

## Verificación del Sheet

- Readback de `Resultados!A237:AF268`: 32 filas × 32 columnas = 1.024 celdas, coincidencia exacta con el payload enviado y cero diferencias.
- IDs: 32 nuevos, sin duplicados internos y sin colisión con los 235 IDs anteriores.
- Formato: Arial 10, ajuste WRAP y alineación TOP; panes congelados preservados (1 fila y 4 columnas).
- Solo se escribió en `Resultados`; no se modificaron otras pestañas.

## Recibos

- `receipts/google-sheet-sync.json`: rango, conteos, readback, formato, fuente y hashes.
- `receipts/sheet-rows.json`: payload de las 32 filas anexadas.
- `PLAN.md`: plan de auditoría.
