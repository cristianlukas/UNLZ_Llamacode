# Resultados — Qwen3.8-Flash-Next IQ3_XXS / Strata

Fecha: 2026-10-09/10  
Tarea: Q-20261009-FLASHNEXT-IQ3XXS-AB  
Conclusión: no promover IQ3_XXS. El subtotal oficial HE20+BCB8 fue 24/28
frente a 28/28 de ASTRA IQ3_S calibrado; HE0 pasó 1/1 para ambos y se informa
aparte. ADV v1 es complementaria: ambos terminaron 10/10 tras dos reparaciones
(primera pasada 7/10 vs 8/10). TaskFlow ULTRA dio 11/13 vs 13/13. La suma
descriptiva HE20+BCB8+ADV+TaskFlow fue 45/51 vs 51/51. Server Speed promedió
126,59 tok/s (rango 119,78–133,40) frente a 122,09
(120,32–123,86); los rangos se solapan. TTFT fue menor en las dos pasadas
(media 370,63 ms vs 451,00 ms), señal que merece repetición, insuficiente
para compensar el resultado final de calidad.

En ADV, IQ3_XXS usó 977,519 s/105 tool calls y ASTRA 773,404 s/63; es un
screening de una pareja, con la corrida ASTRA marcada como desviación de
preregistro. La sonda retrieval 115K se cortó por transporte cuando procesaba
65.536/115.015 tokens, sin respuesta ni `usage` válido. El smoke separado 262K
para el post Q4/4×P100 quedó bloqueado antes de cargar por swap usado
3,253 GiB >2 GiB; no se generó ni envió prompt y no es un fallo del modelo.
No hay resultado válido de contexto largo.

El informe completo, con la tabla por suite, parámetros, muestreo, flags,
memoria y limitaciones está en
[informe de esta evaluación](../../../../docs/qwen38-flashnext-iq3xxs-strata-20261009.md)
y [registro canónico](../../../../docs/evaluacion-modelos-llamacode.md).

## Recibos principales

| Evidencia | Ruta |
|---|---|
| Snapshot de hardware, suite hashes, origen del modelo, instalación y estado final | [preflight.json](preflight.json) |
| Build de Strata local (commit, CUDA y arquitectura) | [engine-BUILD.json](engine-BUILD.json) |
| Configuraciones base, controles y ablations de flags | [configs/](configs/) |
| IQ3_XXS: LC-H1 HE0 / HE20 / BCB8 | [quality/iq3xxs/LC-H1/](quality/iq3xxs/LC-H1/) |
| ASTRA: LC-H1 HE0 / HE20 / BCB8 | [quality/iq3s/LC-H1/](quality/iq3s/LC-H1/) |
| IQ3_XXS y ASTRA: TaskFlow ULTRA | [quality/](quality/) |
| IQ3_XXS y ASTRA: ADV v1 complementaria, screening apareado | [quality/iq3xxs/LC-H1/ADV10.json](quality/iq3xxs/LC-H1/ADV10.json), [control](quality/iq3s/LC-H1/ADV10.json) |
| Cuatro variantes de sampling aisladas por modelo en HumanEval/0 | [sampling/](sampling/) |
| Server Speed v1 de ambos modelos, dos recibos base por modelo y tres ablations | [server-speed/](server-speed/) |
| Suites exactas usadas | [suites/](suites/) |
| Logs de setup, servidores y benchmark | [logs/](logs/) |
| Workspaces crudos de las corridas LlamaCode y Server Speed de esta campaña | [benchmark-runs/](benchmark-runs/) |
| Fixture y recibo de la sonda de contexto fallida | [context/](../context/) |

La fuente efectivamente evaluada en este cierre es el post de r/Qwen_AI sobre
la RTX 4060 Laptop; se conserva en [`source-request.txt`](../source-request.txt).
Este directorio contiene también artefactos anteriores de otra solicitud con
el mismo ID de cola; el plan y el manifiesto identifican las rutas usadas para
esta evaluación. Las rutas alternas preservadas se enumeran en
[`SHA256SUMS-NOTES.md`](../SHA256SUMS-NOTES.md) y no son evidencia de este post.

Todos los resultados de calidad usaron agent-maximo, thinking habilitado,
semilla 4242, temperatura efectiva 0,1, máximo de tres reparaciones, misma
suite y mismo harness. LC-H1 usó reasoning budget 4096 y TaskFlow ULTRA 8192.
HE20+BCB8 finalizó 24/28 para IQ3_XXS y 28/28 para ASTRA; ADV complementaria cerró 10/10 en ambos (7/10 vs 8/10 primera pasada). La suma descriptiva HE20+BCB8+ADV+TaskFlow fue 45/51 vs 51/51.

El contexto de servidor Strata fue 131072, KV int8, MTP/spec 4,
expert-cache auto y configuración calibrada spec-min-p 0,70 / PCIe fraction
0,00 / prefill auto. No se editaron perfiles productivos ni código de la app.

SOL Qwen3.8-27B AutoRound INT4 se incluye sólo como referencia histórica válida
para TaskFlow ULTRA: 0/13 primera pasada, 7/13 final, tres reparaciones,
138,365 s, 42,90 tok/s y TTFT 4.766,5 ms. El recibo usa el mismo hash de suite
y HarnessSpec, agente, seed, temperatura y presupuesto de razonamiento, pero
es una corrida única con vLLM TP2; no se midió Server Speed con SOL. Ver
[recibo SOL histórico](../../../astra-comparable-retest-20261008/sol/sol_r8192_three_repairs_ultra.json).

Los fallos PEP 668, asset publicado ausente y URL temporal con /v1 se
diagnosticaron y resolvieron antes de cerrar corridas válidas. El intento de
Server Speed cancelado por readiness conserva su recibo separado; no se mezcla
con las 32/32 muestras válidas de cada pasada terminada.

Los logs seleccionados de Strata y LlamaCode están copiados en `logs/`.
[`SHA256SUMS.txt`](../SHA256SUMS.txt) contiene los hashes de los recibos y
workspaces de esta evaluación; [`SHA256SUMS-NOTES.md`](../SHA256SUMS-NOTES.md)
documenta artefactos previos de otra fuente que se preservaron intactos y se
excluyeron.
