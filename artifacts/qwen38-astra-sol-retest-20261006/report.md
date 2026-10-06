# ASTRA IQ3_S calibrado vs SOL AutoRound INT4 — retest 2026-10-06

## Diseño

Se añadieron dos tareas coding con contratos y graders fijos, compartidos entre perfiles:

- **TaskFlow**: 13 checks funcionales + `py_compile` (14 total): validación/normalización, serialización, CRUD, dependencias/ciclos, gate de finalización, recurrencia con fin de mes, dos casos de undo (incluida finalización recurrente), persistencia JSON tolerante a corrupción, concurrencia de 40 altas, filtros combinados y exportaciones.
- **Ledger**: 8 checks funcionales + `py_compile` (9 total): parseo monetario/redondeo, validación, balance/resumen, filtros combinados, undo, CSV con comillas/commas y roundtrip, continuidad de IDs y orden estable.

Se ejecutó serialmente con `Máximo` y hasta dos ciclos de reparación iguales para ambos modelos. Los tiempos incluyen reparación y trabajo del agente; no son latencia pura de tokens. **El grader fijo se expuso en el comando de aceptación**, por lo que la prueba no es ciega ni resistente a inspección del oráculo. Los recibos permiten reproducirla, pero el score debe leerse con esa limitación.

## Corridas válidas

| Tarea | Perfil | Puntaje final | Primer intento | Reparaciones | Tiempo total | Lectura |
|---|---|---:|---:|---:|---:|---|
| TaskFlow | SOL AutoRound INT4 | **14/14** | 0/14 | 1 | **442,526 s** | Pasó todos los checks después de reparar el primer artefacto. |
| TaskFlow | ASTRA IQ3_S calibrado | **No puntuable** | — | — | — | Tres intentos terminaron en error de agente antes de primera llamada de herramienta; el artefacto contenía razonamiento `<think>`/no era código. No contar como 0/14 de calidad. |
| Ledger | SOL AutoRound INT4 | **9/9** | 0/9 | 1 | **113,912 s** | Pasó todos los checks después de reparar el primer artefacto. |
| Ledger | ASTRA IQ3_S calibrado | **No puntuable** | — | — | — | Dos intentos concluyeron con fallo pre-herramientas y el artefacto ausente o con `<think>` como texto fuente. No contar como 0/9 de calidad. |

Hubo además un intento ASTRA que no cargó el encoder de visión mientras el contenedor vLLM de SOL seguía ocupando VRAM. Lo excluí como interferencia de entorno; detuve vLLM, verifiqué la memoria libre y repetí. El ASTRA posterior llegó a la fase del agente, pero repitió el problema de razonamiento insertado en el artefacto. Una copia temporal de `Máximo` con `thinking=false` y `thinkingLeakGuard=true` tampoco lo corrigió; la copia se eliminó al cierre.

## Relación con los resultados anteriores

| Evidencia | ASTRA IQ3_S | SOL AutoRound INT4 | Conclusión acotada |
|---|---:|---:|---|
| Tarea compleja anterior (la tabla que pasaste) | **12/13, 177,4 s** | 11/13, 589,4 s | ASTRA ganó esa única pareja; ambos fallaron el mismo self-test de undo. |
| TaskFlow fixed gold | Sin score funcional válido | **14/14 final, 442,5 s** | SOL completó. ASTRA no produjo una entrega evaluable en este flujo. |
| Ledger fixed gold | Sin score funcional válido | **9/9 final, 113,9 s** | SOL completó. ASTRA volvió a fallar el protocolo de artefacto. |
| ASTRA histórico | **8/8 BigCodeBench** y **10/10 adversarial** | — | ASTRA sí completó otras tareas; los fallos actuales no demuestran inferioridad general del modelo. |

## Veredicto

Los resultados nuevos **no confirman que ASTRA sea más inteligente que SOL**: en las dos tareas nuevas sólo SOL dejó artefactos puntuables, ambos después de una reparación. A la vez, tampoco permiten afirmar que ASTRA sea peor en calidad, porque sus corridas nuevas no llegaron a una evaluación válida y los ensayos históricos de ASTRA fueron fuertes. La señal accionable es una incompatibilidad reproducible de esta configuración ASTRA con la salida de artefactos del agente `Máximo` (razonamiento `<think>` incorporado en el archivo requerido); hay que resolverla antes de usar estas corridas para rankear capacidad coding.

**Recomendación práctica:** mantener SOL como opción coding confiable en la configuración actual y conservar ASTRA como candidato/alternativa, sin borrar el modelo por estos ensayos. La pareja anterior sigue favoreciendo ASTRA en una sola tarea, pero la muestra es insuficiente. Para cerrar la comparación, hace falta una repetición ASTRA que termine al menos una de estas suites sin fuga del razonamiento, bajo la misma configuración de `Máximo`, seguida de una segunda corrida por perfil para estimar variación. No cambié perfiles productivos ni harness.

## Trazabilidad

- Suites y graders: `benchmark-suite.json`, `fixed_grader.py`, `ledger-benchmark-suite.json`, `ledger_grader.py` en este directorio.
- Recibos íntegros y checks por comando: [`results.json`](results.json). Las rutas absolutas originales están en cada fila de `runs`.
- Perfil SOL: `86b52354-8c78-4138-8636-4aa1bf66a85f`; ASTRA: `astra-strata-iq3s-calibrated-lch1-20261003`; agente común: `agent-maximo`.
- Después de cada corrida detuve el servidor asociado. Al cierre: `benchmarkRunning=false`, `serverState=stopped`, contenedor vLLM parado y memoria GPU observada en ~0,76/0,11 GiB.
