# Q142 — resultados de conciliación histórica

**Estado:** completado el 2026-10-26. Se añadieron 11 registros históricos respaldados por informes y recibos locales a la pestaña `Resultados`.

## Alcance y método

Se revisaron 196 informes `RESULTS.md` preexistentes del repositorio, los metadatos de las 18 pestañas del workbook y las pestañas de IA/evaluación/inventario/accionables/panel. También se buscaron menciones de modelos y métricas como Qwen, prefill y throughput, y se contrastaron los IDs candidatos con los 224 registros anteriores de `Resultados`.

La migración fue append-only: `Resultados!A226:AF236`. Cada fila incluye cohorte, modelo/perfil, huellas disponibles, decisión, uso verificado, ruta Linux, motor, harness, configuración, métricas, límites y vínculo al informe/recibo. Las rutas Windows no verificadas quedan como N/D. No se calculó un ranking global ni un índice calidad/velocidad entre suites incompatibles. Donde una métrica no se midió, se dejó N/D.

## Registros añadidos

| ID | Evidencia que queda visible | Lectura correcta |
|---|---|---|
| `Q10-P100-UDQ4KXL-LCH1` | Flash-Next UD-Q4_K_XL, Strata 0.1.41, dual RTX 3090, LC-H1 + ADV: 32/39 primer intento, 39/39 final tras reparación; 75 min. | Screening de una corrida, no comparación apareada ni promoción. Prefill/decode son observaciones de suites, no Server Speed. |
| `Q10-EG2-BM25` | Baseline de recuperación léxica: nDCG@5 .4588, MRR@5 .4079; 21 consultas. | Control del fixture Q10, no modelo generativo. |
| `Q10-EG2-RAW` | EmbeddingGemma 2 Q8_0, strings planos: nDCG@5 .6594 (+20.06 pp), MRR@5 .6071; query p50 5.30 ms. | Screen prometedor; no E2E de AgentToolRunner ni integración. |
| `Q10-EG2-RRF-RAW` | BM25 + EG2 RRF, strings planos: nDCG@5 .6400 (+18.12 pp), MRR@5 .5849. | Retrieval, no calidad generativa; fusión no tuvo tiempo aislado. |
| `Q10-EG2-CODE-PREFIX` | EG2 con prefijo de code retrieval y título: nDCG@5 .6612 (+20.24 pp), MRR@5 .6111; p50 5.41 ms. | Mayor nDCG de este screen; requiere adaptar entradas de query/documento. |
| `Q10-EG2-RRF-CODE-PREFIX` | RRF con prefijos: nDCG@5 .6291 (+17.02 pp), MRR@5 .5532, Recall@5 18/21. | Mejor Recall@5, menor MRR/nDCG que EG2 solo. |
| `Q15-ANYJEV-RAW` | Qwen3.8-27B AutoRound INT4 + AnyJev raw, fixture sintético: accuracy 78.1/90.6%, 9/32 cambios ante inversión de opciones. | Clasificador de routing de una corrida; no evalúa un agente ni autoriza acciones. |
| `Q15-ANYJEV-L0` | L0: accuracy 96.9/93.8%, 1/32 cambios; Brier .135/.179; batch 14.07/14.36 s. | Reduce el sesgo de posición en este fixture, con ~3.6× tiempo de lote; ECE sigue alto y no es certificación de seguridad. |
| `Q14-IQ3XXS-MODALITIES` | Flash-Next IQ3_XXS: recuperación exacta 10/10 a 115K; visión formas 4/4 y colores 5/7; CU tuvo fallos/incompletitud; 262K quedó sin prompt. | Modalidades distintas dentro de una fila de screen; no hay score agregado ni promoción. |
| `Q15-ASTRA-IQ3S-VISION` | ASTRA IQ3_S: 9/11 campos exactos en una imagen sintética, shapes 4/4, colores 5/7; 5.144 s. | Control visual de una corrida, confunde amarillo/naranja; no es Server Speed. |
| `Q19-UDIQ4XS-HE20` | Flash-Next UD-IQ4_XS HE20: 20/20 primera pasada, 4,705.197 s, 22.86 tok/s, TTFT medio 49.95 s. | HE20 válido de una semilla. BCB8, ADV y TaskFlow quedaron incompletos/sin score; no promover. |

## Exclusiones y deduplicación

- Q19 JSON Schema (~680K) no se duplicó: Q141 identificó la misma huella/fixture ya representada por Q56.
- No se repitieron resultados ya representados: EmbeddingGemma Q44 (holdout diferente), ASTRA 1M/Q35, screens previos de Q14, Q09 IQ3_XXS, Q10 Frontier, Q130 trim y resultados MTP existentes.
- Fallos de infraestructura sin inferencia, suites incompletas/abortadas sin score, auditorías documentales de claims externos y pruebas del harness sin resultado de modelo no se transformaron en resultados de calidad.
- EmbeddingGemma Q10 y Q44 se conservan como cohortes diferentes; sus métricas no deben compararse directamente.
- Ningún perfil productivo ni archivo de modelo se modificó. No se ejecutaron inferencias, benchmarks, builds ni uso de GPU.

## Verificación

Se escribió el rango `A226:AF236` y se leyó de vuelta. Las 352 celdas coinciden exactamente con el payload local `receipts/sheet-rows.json`; los 11 IDs son nuevos y la pestaña tiene 235 IDs únicos tras la migración. El grid quedó en 236 filas incluyendo encabezado; se preservaron 1 fila congelada, 4 columnas congeladas y el estilo de las filas nuevas (Arial 10, WRAP, TOP).

El detalle exacto de cada celda, la lista de IDs, los descartes y la lectura de vuelta están en `receipts/google-sheet-sync.json`.
