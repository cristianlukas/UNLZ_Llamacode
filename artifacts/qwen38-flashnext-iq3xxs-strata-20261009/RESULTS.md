# Resultados — Qwen3.8-Flash-Next IQ3_XXS / Strata

Fecha: 2026-10-09  
Tarea: Q-20261009-FLASHNEXT-IQ3XXS-AB  
Conclusión: no promover IQ3_XXS. En LC-H1 completo (HE20, BCB8 y ADV/10) más
TaskFlow ULTRA obtuvo 45/51 criterios finales, frente a 51/51 de ASTRA IQ3_S
calibrado; HE0 pasó 1/1 en ambos como prerrequisito separado. La primera
pasada formal fue 42/51 contra 41/51. Su media de Server Speed fue 126,59
tok/s (rango 119,78–133,40) frente a 122,09
(120,32–123,86); los rangos se solapan. TTFT fue menor en las dos pasadas
(media 370,63 ms vs 451,00 ms), señal que merece repetición, insuficiente
para compensar el resultado final de calidad.

El informe completo, con la tabla por suite, parámetros, muestreo, flags,
memoria y limitaciones está en
[docs/qwen38-flashnext-iq3xxs-strata-ab-20261009.md](../../docs/qwen38-flashnext-iq3xxs-strata-ab-20261009.md).

## Recibos principales

| Evidencia | Ruta |
|---|---|
| Snapshot de hardware, suite hashes, origen del modelo, instalación y estado final | [preflight.json](preflight.json) |
| Build de Strata local (commit, CUDA y arquitectura) | [engine-BUILD.json](engine-BUILD.json) |
| Configuraciones base, controles y ablations de flags | [configs/](configs/) |
| IQ3_XXS: LC-H1 HE20 / BCB8 / ADV10, más HE0 prerrequisito | [quality/iq3xxs/LC-H1/](quality/iq3xxs/LC-H1/) |
| ASTRA: LC-H1 HE20 / BCB8 / ADV10, más HE0 prerrequisito | [quality/iq3s/LC-H1/](quality/iq3s/LC-H1/) |
| IQ3_XXS y ASTRA: TaskFlow ULTRA | [quality/](quality/) |
| Cuatro variantes de sampling aisladas por modelo en HumanEval/0 | [sampling/](sampling/) |
| Server Speed v1 de ambos modelos, dos recibos base por modelo y tres ablations | [server-speed/](server-speed/) |
| Datos normalizados por suite y corrida | [results.json](results.json) |
| Muestreo suplementario de RSS/HWM y VRAM | [memory-samples.json](memory-samples.json) |
| Suites exactas usadas | [suites/](suites/) |
| Logs de setup, servidores y benchmark | [logs/](logs/) |
| SHA-256 y tamaño de los artefactos | [manifest.json](manifest.json) |

Todos los resultados de calidad usaron agent-maximo, thinking habilitado,
semilla 4242, temperatura efectiva 0,1, máximo de tres reparaciones, misma
suite y mismo harness. LC-H1 usó reasoning budget 4096 y TaskFlow ULTRA 8192.
La suite LC-H1 sigue el ledger histórico: HE20 + BCB8 + Intelligence
Adversarial v1 (38 criterios); HE0 es sólo prerrequisito. La primera pasada
formal fue 42/51 frente a 41/51; resultado final 45/51 frente a 51/51.
El contexto de servidor Strata fue 131072, KV int8, MTP/spec 4,
expert-cache auto y configuración calibrada spec-min-p 0,70 / PCIe fraction
0,00 / prefill auto. No se editaron perfiles productivos ni código de la app.

SOL Qwen3.8-27B AutoRound INT4 se incluye sólo como referencia histórica válida
para TaskFlow ULTRA: 0/13 primera pasada, 7/13 final, tres reparaciones,
138,365 s, 42,90 tok/s y TTFT 4.766,5 ms. El recibo usa el mismo hash de suite
y HarnessSpec, agente, seed, temperatura y presupuesto de razonamiento, pero
es una corrida única con vLLM TP2; no se midió Server Speed con SOL. Ver
[recibo SOL histórico](../astra-comparable-retest-20261008/sol/sol_r8192_three_repairs_ultra.json).

Los fallos PEP 668, asset publicado ausente y URL temporal con /v1 se
diagnosticaron y resolvieron antes de cerrar corridas válidas. El intento de
Server Speed cancelado por readiness conserva su recibo separado; no se mezcla
con las 32/32 muestras válidas de cada pasada terminada.
