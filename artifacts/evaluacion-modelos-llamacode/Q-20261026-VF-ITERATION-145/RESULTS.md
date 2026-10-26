# Q145 · Resultados históricos migrados a Google Sheets

**Estado:** completado.  
**Fecha:** 2026-10-26.  
**Destino:** pestaña `Resultados` del workbook “Listado”, filas 269–290.  
**Cambios:** 22 filas nuevas, append-only; ninguna fila existente ni otra pestaña fue modificada.

## Qué se añadió

- **Swift Genesis NVFP4:** LC-H1 (HE20 20/20, BCB 2/8, ADV cancelado sin score), además de su screen de Computer Use textual (720/720 en corpus sintético, pero gate de latencia fallido) y decode corto de cinco repeticiones (mediana 56,35 tok/s). Se distinguen de la cuantización Q4_K_M y de Swift 1.5.
- **Qwen3.8 RCO Coder IQ1_M, revisión 5348543…:** LC-H1 histórico apareado: HumanEval 1/1 y 20/20; BCB 5/8 y 4/8 en repetición. Esta revisión anterior se separa de la revisión bba88856… ya registrada (screen de 0/8).
- **QwFN-hybrid IQ3_XXS:** BCB 2/8, tool contract 5/5, Computer Use textual 72/72 pero lento, y 3/3 visual no ejecutado. Se incluyen prefill/decode en prompts cortos y de 16K, con la variación observada.
- **Strata:** Q2_0 en una 3090 (BCB 1/8, code smoke 3/3, tool roundtrip correcto y needle 3/3 hasta 110K); IQ3_S con recuperación de un marcador a ~262K (2 requests, sin score general); y Strata-DualGPU 0.1.38 IQ3_S (LC-H1 funcional, throughput microbench y Computer Use textual), con los límites de comparabilidad y el gate de promoción fallido.
- **Browser planner sintético:** Qwen3.5-9B y Qwen3.8-27B AP-Q3 completaron 39/39 decisiones simuladas, con el mismo corpus; el 27B tardó más. Qwen3-8B Q6_K con reasoning off completó 39 decisiones pero tuvo 6 acciones incorrectas y 3 selecciones inseguras; con reasoning auto no emitió llamadas de herramienta.
- **Visión:** LFM2.5-VL-3B F16 (6/6 campos en una captura de settings; mala grounding en una captura de navegador) y WebBrain-VL-2 450M (5/6 settings; mala grounding). Ambas quedan como smoke cualitativo WASM/visual, no como evaluación comparativa robusta.
- **DeepSeek short-smoke:** nueve configuraciones locales de UD-IQ3_S/antirez con una petición caliente (57 tokens de entrada, 256 de salida). Se registran los TPS únicamente como diagnóstico de runtime/colocación; sin puntaje de calidad, repetición ni resultado E2E.

## Controles de duplicados y límites

- El workbook completo tiene 18 pestañas y se revisó antes de escribir; se cotejaron especialmente `IA local`, `Evaluaciones LlamaCode`, `Inventario de modelos`, `Accionables`, `Enlaces revisados` y `Resultados`.
- No se duplicaron Genesis/Strata/QwFN por similitud de nombre: se verificaron quant, revisión, engine, suite, contexto y recibos. Qwen3.5 AURA y los perfiles AP-Q3 de perplexity ya existentes usan cohortes distintas de los nuevos browser probes.
- Se dejaron fuera dos invocaciones DeepSeek que fallaron antes de generar por requisitos de memoria/arranque de herramienta, y un contexto DeepSeek externo a este checkout cuyo JSON no estaba disponible para verificación. También se excluyeron mediciones de velocidad de la aplicación que no evalúan un modelo y un benchmark Strata de terceros en RTX 5090.
- Las pruebas de una petición, las capturas únicas y los simuladores sintéticos están marcados explícitamente. No sostienen afirmaciones generales de calidad ni sustitución de perfiles productivos.
- No hubo benchmark, inferencia, build, descarga, servidor ni uso de GPU. No se cambiaron ASTRA, SOL, Flash-Next productivo, perfiles ni inventario.

## Verificación

- `Resultados` pasó de 267 a 289 IDs de datos, todos únicos.
- Readback de `Resultados!A269:AF290`: 22 filas, 704 celdas, 0 diferencias frente al payload guardado.
- Se mantuvieron `TOP / WRAP / Arial 10`, una fila congelada y cuatro columnas congeladas; sin fórmulas, chips ni validaciones nuevas.
- Payload exacto: `receipts/sheet-rows.json`.
- Recibo de sincronización: `receipts/google-sheet-sync.json`.

