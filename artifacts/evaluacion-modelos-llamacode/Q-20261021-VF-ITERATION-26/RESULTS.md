# Q-20261021-VF-ITERATION-26 — Resultado de la evaluación prioritaria

**Estado de esta iteración: bloqueada para una nueva corrida del P1; la suite HE20-05 se abortó por la guarda de memoria y no produjo puntaje.** Se evaluaron las prioridades en serie y se reconcilian aquí las condiciones para no duplicar pruebas que ya se cerraron.

## P1 — Qwen3.8 Flash-Next UD-IQ4_XS

Se ejecutó HE20-05 con fingerprint `a56c723fde568b4db160bbb48ccc9e378aa221bdcaffe544ee957e3ba666dd86`, Strata 0.1.41 y la configuración preregistrada. El runner llegó a 10/20 prompts y la guarda abortó durante el prompt 11/20 a las 2026-10-22 00:46:53 UTC: MemAvailable 70,85 GiB, SwapFree 0,56 GiB, árbol LlamaCode 23,03 GiB RSS y árbol del servidor 73,69 GiB. La guarda de preregistro exige al menos 1 GiB libre de swap.

No se generó EVAL final, grade ni score. El `benchmark-final.json` conserva un `benchmark_running` obsoleto; para el cierre prevalecen el error explícito de guardia, `owned-process-cleanup.json` y el postflight de `safety-abort-result.json`. Strata terminó con exit 0 y la copia aislada de LlamaCode fue detenida con SIGTERM (-15). El postflight no encontró servidores de inferencia, runners ni listeners de prueba.

**Recomendación:** no concluir que Flash-Next falló en calidad ni adoptarlo a partir de telemetría interna. Mantener sin cambios ASTRA/SOL y los modelos de PeritoSoft. No repetir la misma configuración ni bajar el límite de seguridad. Reabrir HE20 sólo con un prerregistro nuevo que trate la trayectoria de memoria/swap y un preflight fresco.

## Prioridades siguientes

| Prioridad | Estado y evidencia | Recomendación / condición para reabrir |
|---|---|---|
| P1.1 — MTP Q4/llama.cpp | Bloqueada por los fallos previos del harness: TaskFlow MTP-on 0/13, MTP-off 0/13 y BCB8 MTP-off cancelado sin score final. | No repetir esas huellas. Reabrir cuando se corrija el contrato de tools/aislamiento y se defina un fingerprint nuevo. |
| P2 — Qwen3.8-27B Q4_K_M | Ya se hicieron los intentos 09–11 del canario Codex con el adaptador de compatibilidad; el 11 fue el intento final y no emitió tool call ni archivo. El diagnóstico directo Responses API terminó HTTP 200 pero devolvió sólo `reasoning`, cero `function_call`. No hay score matched de coding. | No repetir este modelo/runtime/protocolo. Reabrir únicamente con un cambio material de modelo, runtime, template/parser o protocolo y un prerregistro nuevo; sólo después del canario de tools hacer A/B matched con ASTRA/SOL. |
| P2.1 — OpenJet | Screen local previo produjo control, pero ningún resultado del candidato: el kernel fijado requiere 65 bloques y el GGUF Qwen3.8-27B disponible tiene 64; el archivo tampoco tiene capas MTP. | No volver a ejecutar la combinación incompatible. Reabrir con soporte para 64 bloques o un artefacto local compatible de 65 bloques, y un objetivo de comparación decidido. |
| P3 — RCO Coder IQ1_M | Screen local BCB-Hard-8 ya completado en la revisión `bba88856f8c3c0c9e40e45f82d05e228b814ac43`: 0/8 del candidato frente a 1/8 del control ASTRA IQ2_XS; transporte 8/8 en ambos. El umbral de avance preregistrado era ≥3/8; el candidato usó el máximo de 6.144 tokens en 5/8 respuestas. | No descargar ni repetir esta revisión. La ficha del autor declara SWE-bench 79,2 frente a 82,8 BF16 y LiveCodeBench v6 87,43 frente a 87,43; son métricas externas y no cambian el screen local. Reabrir sólo ante nueva revisión/quant, harness o backend materialmente distinto. Los shards de esta revisión ya fueron removidos; quedan hashes y recibos. |
| P4 — Swift 1.5 Qwen3.8-27B | Bloqueada: falta determinar elegibilidad comercial y Strata 0.1.41 no tiene una conversión verificada para el formato del MTP head publicado. | No descargar ni inferir hasta documentar elegibilidad/licencia y una ruta runtime compatible. Un brazo sin MTP sería otro experimento, con control ASTRA emparejado. |
| P5 — Strata y otros claims | Los A/B locales pertinentes ya están registrados. Entre ellos, PLE FP8 dio 3/24 frente a 3/24 para stock y ganó 0/3 pares; no se justifica promoción. Otros cambios de tuning no superaron sus gates o no son comparables con este host. | No repetir resultados negativos con la misma configuración. Añadir una prueba sólo ante claim nuevo verificable, artefacto compatible y métrica que pueda cambiar una decisión. |

## Cierre de iteración

No queda una prueba de modelo nueva que esté habilitada, sea distinta de las ya cerradas y pueda cambiar una decisión bajo las condiciones actuales. Se conservan los bloqueos concretos para reanudación; no se cambió código ni configuración productiva, y no se eliminó ningún modelo en esta iteración. El estado del P1 es **sin score por abort seguro**, no una evaluación negativa de calidad.

Recibos Q26: [prerregistro](attempts/he20-05/receipts/preregistration.json), [guardia](attempts/he20-05/receipts/memory-guard-trip.json), [limpieza](attempts/he20-05/receipts/owned-process-cleanup.json), [cierre autoritativo](attempts/he20-05/receipts/safety-abort-result.json). RCO: [resultado local de la fuente 7](../Q-20261020-VF-20261019-01/receipts/source-07-screen-result.json), [resultado del candidato](../Q-20261020-VF-20261019-01/results/source-07-candidate-bcb.json), [remoción de shards](../Q-20261020-VF-20261019-01/receipts/storage-cleanup/source07-iq1m-weight-removal.json). Qwen3.8-27B: [cierre de los canarios previos](../Q-20261021-VF-RESUME-ITERATION/RESULTS.md).


## Sincronización de Google Sheets

Se reconciliaron las tarjetas P1/P2/P3/P4 de `Accionables`, el resumen/cierre de Q26, Qwen3.8-27B y RCO en `Evaluaciones LlamaCode`, y el inventario vivo en `Inventario de modelos`. El readback confirmó los estados y fundamentos escritos. Se añadieron fichas para Qwen3.8-27B, RCO IQ1_M y Swift 1.5; las rutas Windows, TPS no comparables y usos no verificados se dejaron como N/D en vez de inferirlos. Recibo: [google-sheets-priority-reconciliation-20261022.json](receipts/google-sheets-priority-reconciliation-20261022.json).
