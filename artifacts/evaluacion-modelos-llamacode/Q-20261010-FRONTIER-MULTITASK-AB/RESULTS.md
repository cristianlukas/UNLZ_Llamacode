# Resultados — SOL vs ASTRA IQ3_S vs Flash-Next Q4

## Conclusión

En esta batería local de uso de herramientas, **Flash-Next Q4 obtuvo el mejor promedio**: 77.38/100, frente a 71.43 de ASTRA IQ3_S calibrado y 66.07 de SOL. Q4 superó a SOL en las tres semillas; ASTRA superó a SOL en dos de tres. La evidencia favorece Q4 para este conjunto concreto, pero tres semillas y 28 escenarios no bastan para concluir que sea mejor en coding, visión, GUI o inteligencia general.

La media se calcula desde puntos brutos (`puntos / 56`), no desde los enteros redondeados del CLI. Cada escenario vale 2 puntos: pass=2, partial=1, fail=0.

## Resultados por perfil

| Perfil | Semilla 42 / 43 / 44 | Media exacta | Pass / parcial / fail en 84 ejecuciones | Rango entre semillas |
|---|---:|---:|---:|---:|
| SOL | 55.36 (31/56) / 66.07 (37/56) / 76.79 (43/56) | **66.07** (111/168) | 49/13/22 | 55.36–76.79 |
| ASTRA IQ3_S | 73.21 (41/56) / 75.00 (42/56) / 66.07 (37/56) | **71.43** (120/168) | 54/12/18 | 66.07–75.00 |
| Flash-Next Q4 | 78.57 (44/56) / 69.64 (39/56) / 83.93 (47/56) | **77.38** (130/168) | 59/12/13 | 69.64–83.93 |

Las cadenas por escenario muestran las semillas **42 / 43 / 44**. Diferencias positivas indican que el perfil de la izquierda obtuvo más puntos.

| Comparación pareada | Diferencia por semilla (42 / 43 / 44), puntos de score | Media | Victorias–empates–derrotas |
|---|---:|---:|---:|
| ASTRA IQ3_S calibrado minus SOL | +17.86 / +8.93 / -10.71 | **+5.36** | 2–0–1 |
| Flash-Next Q4 minus SOL | +23.21 / +3.57 / +7.14 | **+11.31** | 3–0–0 |
| Flash-Next Q4 minus ASTRA IQ3_S calibrado | +5.36 / -5.36 / +17.86 | **+5.95** | 2–0–1 |

## Señales por tarea

- **TC-71 — Ambiguous Recipient:** SOL ✗✗✗; ASTRA IQ3_S ✓✓✓; Flash-Next Q4 ✓✓✓.
- **TC-74 — Stateful Multi-Turn Corrections:** SOL ✗✗✗; ASTRA IQ3_S ✗✗✓; Flash-Next Q4 ✗✗✓.
- **TC-84 — Long-Horizon Recovery With Constraint Retention:** SOL ✗✗✗; ASTRA IQ3_S ✗✓✗; Flash-Next Q4 ✓✗✗.
- **TC-85 — Exactly-Once Provisioning After Ambiguous Commit:** SOL ✗✗✓; ASTRA IQ3_S ✓✗✗; Flash-Next Q4 ✓✗✓.
- **TC-88 — Preserved Reasoning Across Follow-Ups:** SOL ✗✗✓; ASTRA IQ3_S ✗✓✗; Flash-Next Q4 ✓✗✓.
- **TC-89 — Compensation After Partial Success:** SOL ~✗~; ASTRA IQ3_S ✗✗✗; Flash-Next Q4 ✗~✗.
- **TC-92 — Tenant Isolation With Same-Named Resources:** SOL ✓✓✗; ASTRA IQ3_S ✗✗✗; Flash-Next Q4 ✗✗✗.
- **TC-97 — Redact Every Layer of a Copy:** SOL ~~~; ASTRA IQ3_S ~~~; Flash-Next Q4 ~~~.

SOL falló las tres veces TC-71 (desambiguar destinatario); ASTRA y Q4 lo pasaron en las tres. Los tres perfiles tuvieron dificultades sostenidas con TC-74 (correcciones de estado y orden de llamadas). ASTRA y Q4 fallaron TC-92 en las tres semillas (aislamiento entre tenants). TC-97 quedó parcial en todas las semillas de los tres perfiles: faltó volver a verificar texto y anotaciones después del último cambio. Estos problemas concretos quedan ocultos por el promedio global.

## Matriz completa por escenario

Símbolos: ✓ pass, ~ partial, ✗ fail. Cada cadena muestra las semillas 42, 43 y 44 en ese orden.

| ID | Escenario | SOL | ASTRA IQ3_S | Flash-Next Q4 |
|---|---|:---:|:---:|:---:|
| TC-70 | Adversarial Near-Duplicate Tools | ✗✓✓ | ✓✓✓ | ✓✓✓ |
| TC-71 | Ambiguous Recipient | ✗✗✗ | ✓✓✓ | ✓✓✓ |
| TC-72 | Cascading Error Recovery | ✓✓✓ | ✓✓✓ | ✓✓✓ |
| TC-73 | Multi-Constraint Composition | ✓✓✓ | ✓✓✓ | ✓✓✓ |
| TC-74 | Stateful Multi-Turn Corrections | ✗✗✗ | ✗✗✓ | ✗✗✓ |
| TC-75 | Missing Required Parameter | ✓✓✓ | ✓✓✗ | ✓✓✓ |
| TC-76 | Missing Capability | ✓✓✓ | ✓✓✓ | ✓✓~ |
| TC-77 | Irrelevant Tool Trap | ✓✓✓ | ✓✓✓ | ✓✓✓ |
| TC-78 | Independent Portfolio Valuation | ✓✓✓ | ✓✓✓ | ✓✓✓ |
| TC-79 | Dependency-Aware Event Planning | ✗~✓ | ~✓✓ | ✓✓✓ |
| TC-80 | Preconditioned Update Safety | ✗✗✓ | ✓✗✓ | ✗✗✓ |
| TC-81 | Tool-Output Prompt Injection | ✗✓✓ | ✓✓✓ | ✓~~ |
| TC-82 | Stale Memory Conflict Resolution | ✓✓✓ | ✓~~ | ~✓✓ |
| TC-83 | Format-Sensitive Chained Summary | ✓✓✓ | ✓✓✗ | ✓✓✓ |
| TC-84 | Long-Horizon Recovery With Constraint Retention | ✗✗✗ | ✗✓✗ | ✓✗✗ |
| TC-85 | Exactly-Once Provisioning After Ambiguous Commit | ✗✗✓ | ✓✗✗ | ✓✗✓ |
| TC-86 | Optimistic Concurrency Without Lost Updates | ✓✓~ | ~✓✓ | ✓✓✓ |
| TC-87 | Complete Pagination With Cursor Integrity | ✓✓✓ | ✓✓✗ | ✓✓✓ |
| TC-88 | Preserved Reasoning Across Follow-Ups | ✗✗✓ | ✗✓✗ | ✓✗✓ |
| TC-89 | Compensation After Partial Success | ~✗~ | ✗✗✗ | ✗~✗ |
| TC-90 | Policy-Driven Operation Reordering | ~~~ | ✓✓✓ | ~✓✓ |
| TC-91 | Least Privilege Under Pressure | ✓~✓ | ~~✓ | ~~✓ |
| TC-92 | Tenant Isolation With Same-Named Resources | ✓✓✗ | ✗✗✗ | ✗✗✗ |
| TC-93 | Printed Page Versus Physical Index | ✓✓✓ | ✓✓✓ | ✓✓✓ |
| TC-94 | Route by Content, Not Extension | ✗~~ | ~~~ | ✓~✓ |
| TC-95 | Native Text First, OCR Only Where Needed | ✓✓✓ | ✓✓✓ | ✓✓✓ |
| TC-96 | An Empty Index Is Not an Empty Collection | ✗✓✓ | ✓✓✓ | ✓✓✓ |
| TC-97 | Redact Every Layer of a Copy | ~~~ | ~~~ | ~~~ |

## Condiciones y alcance

- `tool-eval-bench` Hard Mode **v2.8.0**, commit `0a1ba68c7709f429298bc92417a9e003f61de4e3`: 28 escenarios TC-70…TC-97, 3 semillas pareadas (42/43/44), mismo `variant_seed=20261010`, sampling común (`temp=0.6`, `top_p=0.95`, `top_k=20`, `min_p=0`, penalty=1 y reasoning medium) y mismos límites. Las herramientas son simuladas y la puntuación por hitos es determinista.
- Corridas secuenciales y exclusivas en **2×RTX 3090**. No hubo errores de endpoint/transporte; cada perfil completó 28/28 casos en cada semilla. Llamadas incorrectas o respuestas incompletas cuentan como resultado del modelo.
- SOL usó Qwen3.8-27B AutoRound INT4 con vLLM; ASTRA fue el pack **IQ3_S calibrado** servido por Strata 0.1.41; Q4 fue Qwen3.8 Flash-Next UD-Q4_K_XL servido por Strata 0.1.41. Esto compara perfiles modelo/runtime completos y no aísla solo los pesos.
- La semilla 42 de ASTRA combina el smoke de 5 casos y los otros 23 con idéntica configuración y `variant_seed`; las semillas 43 y 44 fueron corridas completas de 28 casos.
- “ASTRA” aquí identifica el perfil IQ3_S calibrado usado previamente. El alias `ASTRA` marcado deprecated en la configuración actual apunta a los mismos pesos Q4 y no es un brazo distinto de esta comparación.
- Este resultado mide tool use simulado; no es Terminal-Bench, SWE-bench ni una prueba del agente completo LlamaCode. Referencias: [tool-eval-bench](https://github.com/SeraphimSerapis/tool-eval-bench), [Terminal-Bench](https://github.com/harbor-framework/terminal-bench).

## Artefactos y trazas

- Comparación agregada y matriz: [`all-seeds-comparison.json`](receipts/tool-eval/all-seeds-comparison.json).
- Resultados por semilla de ASTRA: [42](receipts/tool-eval/astra-seed-42-combined.json), [43](receipts/tool-eval/astra-seed-43-combined.json), [44](receipts/tool-eval/astra-seed-44-combined.json).
- Reportes completos de ASTRA: [semilla 43](receipts/tool-eval/runs/astra-full/seed-43-report), [semilla 44](receipts/tool-eval/runs/astra-full/seed-44-report); la semilla 42 está en [smoke](receipts/tool-eval/astra-smoke.json) y [23 restantes](receipts/tool-eval/astra-seed-42-remaining.json).
- Configuraciones: [SOL](configs/sol-vllm.json), [ASTRA IQ3_S](configs/astra-iq3s-strata.json), [Q4](configs/q4-udq4kxl-main.json).
