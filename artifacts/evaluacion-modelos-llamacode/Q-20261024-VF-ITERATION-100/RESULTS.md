# Q100 — resultado final

## Decisión

**No adoptar dos subagentes paralelos** para ASTRA/Strata en este flujo. El modo paralelo tuvo errores de mapeo ALPHA/BETA en dos de tres semillas y además fue más lento en throughput bruto. Los tres seeds seriales terminaron con el mapeo correcto; los paralelos sólo 1/3. Mantener serial cuando la respuesta dependa de asociar exactamente los resultados de cada subagente.

## Evidencia E2E

Screen de `LlamaAgentBackend` real con ASTRA Flash-Next IQ2_XS / Strata 0.1.41 MTP4, ambas RTX 3090 y 128 GB sin límites, servidor de dos slots, contexto 65.536, tres semillas (5051–5053) y dos tareas sintéticas de lectura por seed. Cada subagente leyó el marcador asignado; en parallel2 las respuestas finales de las semillas 5051 y 5053 intercambiaron las etiquetas ALPHA y BETA.

| Métrica | Serial, 1 worker | Parallel2 |
|---|---:|---:|
| Corridas con respuesta final correcta | 3/3 | 1/3 |
| Tareas E2E correctamente resueltas | 6/6 | 2/6 |
| Tiempo total | 35,863 ms | 37,795 ms |
| Marcadores leídos por segundo (bruto) | 0.1673 | 0.1588 |
| Tareas E2E correctas por segundo | 0.1673 | 0.0529 |

El ratio de throughput bruto parallel/serial fue 0,9489 (paralelo 5,11% menor). El ratio de throughput E2E correcto fue 0,3163. No hay claim general sobre todos los modelos: es un resultado de screening con un workload sintético y tres seeds.

El scorer anterior sólo comprobaba que ambos marcadores aparecieran en alguna parte, sin validar su asignación; por eso dos respuestas invertidas habían sido marcadas como correctas. Enmienda 006 valida la respuesta final exacta después del último `</think>`, y separa “screen completado” de “gate de adopción aprobado”. Cuatro regresiones CPU cubren mapping correcto, invertido, valor ausente y razonamiento correcto seguido por una respuesta final incorrecta.

## Presión de memoria y detector

En las 220 muestras del intervalo de carga Q100, MemAvailable mínima fue 69,386 GiB; PSI full global avg10 alcanzó 46,52% y generó 34 muestras de aviso. Los contadores OOM global y cgroup permanecieron en cero; la guarda no abortó, las seis corridas terminaron y el cleanup pasó. El comportamiento coincide con la política calibrada: PSI moderada avisa; el hard stop exige PSI global severa sostenida, MemAvailable bajo 32 GiB u OOM. Repetimos 10 regresiones CPU de los gates y trazas Q91/Q93: 10/10 PASS.

Esto **no contradice** los usos productivos exitosos que mencionaste: ASTRA DEFAULT 1M Q14/Q35 y SOL dual-GPU Q34 se conservan como evidencia histórica válida. Q100 corrió con contexto 65.536 por el límite heredado de tokens; no fue una repetición de 1M. Los resultados de esta prueba no cambian modelos, perfiles ni valores productivos.

## Validación

`CUDA_VISIBLE_DEVICES= LC_JOBS=2 ./scripts/tests-linux.sh Release`: build del harness y **95/95 CTest PASS** (112,43 s). El target Q100 reportó 7 passed, 0 failed y 1 live slot opt-in omitido por falta de endpoint; el screen de seis corridas ya está guardado. Las regresiones de presión PSI/replay dieron 10/10 PASS. No se ejecutó inferencia durante esta validación CPU y no se reconstruyó la app de producción.

## Artefactos

`runs/attempt-05-complete-label-mapping-issue/rescored-result.json`, `receipts/q100-amendment-006-validation.json`, `receipts/q100-memory-guard-revalidation.json`, `receipts/q100-final-result.json` y `receipts/q100-cleanup-postflight.json`.
Final postflight 2026-10-24T21:56:15Z: Q100 systemd unit and inference/proxy ports clear; MemAvailable 110.124 GiB; PSI memory/io avg10 recorded in `receipts/q100-final-cleanup-postflight.json`. ArtCraft is an unrelated GPU compute app and was preserved. Q100 lock released after receipts, Sheets readback, app queue and WORK_QUEUE were reconciled.
