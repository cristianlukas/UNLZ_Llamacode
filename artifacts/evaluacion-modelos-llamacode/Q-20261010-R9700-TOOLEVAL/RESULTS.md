# Resultados — transferencia local del post R9700 / tool-eval-bench

**Tarea:** `Q-20261010-R9700-TOOLEVAL`  
**Estado:** completada; screening de perfiles locales, sin promoción.  
**Fecha de cierre:** 2026-10-13.

## Resumen

Se completaron tres corridas emparejadas por semilla (42/43/44) en `tool-eval-bench` v2.7.0: 69 escenarios estándar y 19 Hard Mode por perfil, con herramientas simuladas. En Hard Mode, el orden fue **Flash-Next Q4 UD-Q4_K_XL 86,67**, **ASTRA IQ3_S calibrado 75,33** y **SOL 58,00**. Q4 superó a ASTRA y SOL en cada una de las tres semillas. Es evidencia repetida para esta suite concreta de tool-use; no demuestra superioridad general ni mejora de coding/agentes en repositorios.

La tabla de la campaña anterior era de v2.8.0 y 28 escenarios. Los promedios publicados eran Q4 77,38, ASTRA 71,43 y SOL 66,07. Si se restan los promedios, las diferencias aritméticas son +9,29, +3,90 y −8,07 puntos, respectivamente, pero **no son deltas comparables**: cambiaron release, cantidad/selección/puntuación de tareas y temperatura (la campaña anterior usó 0,6; esta usó 1,0 para seguir el protocolo R9700). La clasificación ordinal Q4 > ASTRA > SOL se repitió; no se puede concluir que cada modelo haya mejorado o empeorado.

| Perfil local completo | Hard Mode v2.8 · 28 tareas (histórico) | Hard Mode v2.7 · 19 tareas (actual) | Diferencia aritmética, no comparable | Estándar v2.7 · 69 tareas (actual) |
|---|---:|---:|---:|---:|
| Flash-Next Q4 UD-Q4_K_XL | 77,38 | **86,67** (87 / 84 / 89) | +9,29 | **90,67** (88 / 89 / 95) |
| ASTRA IQ3_S calibrado | 71,43 | 75,33 (68 / 76 / 82) | +3,90 | 87,67 (88 / 87 / 88) |
| SOL Qwen3.8-27B AutoRound INT4 | 66,07 | 58,00 (58 / 61 / 55) | −8,07 | 25,67 (25 / 25 / 27) |

## Lectura de la comparación anterior

La evidencia local actual refuerza la selección de Q4 **para este Hard Mode v2.7.0**: aventajó a ASTRA por 11,34 puntos de media y a SOL por 28,67; ASTRA superó a SOL por 17,33. La misma jerarquía de promedios aparecía en la prueba histórica de 28 tareas, pero las diferencias de protocolo impiden interpretar el cambio de puntos como tendencia. Q4 de ambas campañas es el perfil UD-Q4_K_XL; ASTRA es el IQ3_S calibrado; SOL reutiliza el Qwen3.8-27B AutoRound INT4. Aun así, estos son perfiles completos de runtime/hardware/configuración y la suite v2.7 ejecuta herramientas mockeadas.

Hard Mode sigue teniendo un fallo funcional claro: **TC-80 falló en las tres semillas para los tres perfiles**. Q4 también falló TC-74 en 2/3 semillas y TC-88 en 1/3; tuvo parciales en TC-85 en 2/3 y TC-71 en 1/3. Los perfiles ASTRA y Q4 comparten una limitación de endpoint en la suite estándar descrita abajo. El TC-92 de aislamiento entre tenants y TC-97 de redacción, que fallaron/parcializaron en v2.8, no forman parte de los 19 casos v2.7: esta prueba no los revalidó.

## Resultados completos

### Hard Mode · 19 tareas, 3 semillas por perfil

| Perfil | Seed 42 | Seed 43 | Seed 44 | Media | Pasadas / parciales / fallidas, 57 casos |
|---|---:|---:|---:|---:|---:|
| Flash-Next Q4 UD-Q4_K_XL | 87/100 (33/38) | 84/100 (32/38) | 89/100 (34/38) | **86,67** | 48 / 3 / 6 |
| ASTRA IQ3_S calibrado | 68/100 (26/38) | 76/100 (29/38) | 82/100 (31/38) | 75,33 | 41 / 4 / 12 |
| SOL AutoRound INT4 | 58/100 (22/38) | 61/100 (23/38) | 55/100 (21/38) | 58,00 | 31 / 4 / 22 |

Las 9 corridas terminaron los 19 casos, con respuestas normales; son resultados válidos de calidad para tool-eval-bench v2.7.0. Los totales de estados se suman sobre las tres semillas.

### Estándar · 69 tareas, 3 semillas por perfil

| Perfil | Seed 42 | Seed 43 | Seed 44 | Media | Pasadas / parciales / fallidas, 207 casos |
|---|---:|---:|---:|---:|---:|
| Flash-Next Q4 UD-Q4_K_XL | 88/100 (122/138) | 89/100 (123/138) | 95/100 (131/138) | **90,67** | 176 / 24 / 7 |
| ASTRA IQ3_S calibrado | 88/100 (122/138) | 87/100 (120/138) | 88/100 (122/138) | 87,67 | 165 / 34 / 8 |
| SOL AutoRound INT4 | 25/100 (34/138) | 25/100 (34/138) | 27/100 (37/138) | 25,67 | 31 / 43 / 133 |

Q4 y ASTRA recibieron HTTP 400 en TC-65, TC-66, TC-67 y TC-69: `structured response_format with tools/MCP is not supported`. La suite guardó esos cuatro como `partial` en cada seed (12 parciales por perfil); no hubo 5xx ni interrupción en las corridas completas. Esto mide una limitación de compatibilidad del perfil Strata junto con el modelo y no debe atribuirse sólo a la calidad de pesos. Los demás escenarios, incluido TC-68, fueron puntuados con transporte normal. SOL completó 69/69 en las tres semillas sin esa incompatibilidad.

Todos los perfiles completaron el smoke separado TC-01/TC-47/TC-70; SOL obtuvo 5/6 y ASTRA/Q4 6/6. El smoke no se suma a las medias.

## Reintentos y validez

- **SOL, estándar seed 42:** primer intento incompleto con 47/69 y luego 22 HTTP 500 después de un CUDA device-side assert en vLLM/Worker TP0; inválido por infraestructura y excluido. Tras reiniciar el contenedor aislado, TC-48 respondió normalmente y la repetición terminó 69/69, 25/100, válida. Pesos locales ya existentes; no se descargó SOL.
- **ASTRA, estándar seed 42:** primer intento incompleto (62 escenarios); el endpoint se cerró durante el intento, así que no cuenta como score. La repetición terminó 69/69 y 88/100. Se conservan ambos recibos.
- **Q4, estándar seed 42:** primer intento interactivo perdió el proceso del runner tras 14 escenarios y no produjo JSON final. Se clasificó incompleto, no score. La ejecución capturada de nuevo terminó 69/69 y 88/100. No hubo OOM ni error CUDA registrado en el endpoint; se conserva la nota de incidente y el reintento.
- Las otras 15 corridas estándar/Hard Mode llegaron a su cantidad completa de casos. No se excluyeron resultados por puntaje.

## Configuración, huellas y recursos

- **Suite:** `tool-eval-bench` v2.7.0, commit `c483eef867d75d9dd04c7d370fe553f96a49d672`; 69 estándar/19 Hard Mode (TC-70…TC-88). Fingerprint de suite `23458e28ce6ee21524f14dd61ab091a12d50e6a58bd0466ef74a78c556191fad`; hashes de código estándar y Hard Mode en `receipts/runner-source.json`.
- **Sampling común enviado por el runner:** temperature 1.0, top-p .95, top-k 20, min-p 0, repetition penalty 1, presence penalty 0, max_tokens 16384, thinking enabled, reasoning effort medium; seeds 42/43/44, máximo 8 turnos, timeout 600 s, una conversación a la vez, sin error injection.
- **SOL:** Qwen3.8-27B AutoRound INT4; vLLM 0.27.1 TP2/P2P/MTP4, KV FP8, contexto 262144, loopback 8113. Imagen local `pull_policy: never`, modo offline. Los shards existentes fueron verificados y reutilizados; no se descargaron pesos.
- **ASTRA:** Qwen3.8-Flash-Next IQ3_S calibrado; Strata 0.1.41, dos RTX 3090, contexto 131072, KV int8, MTP/spec 4 y endpoint loopback 8350.
- **Q4:** Qwen3.8-Flash-Next UD-Q4_K_XL; Strata 0.1.41, dos RTX 3090, split de capas 18/30, contexto 131072, KV int8, caché residente 32768 y MTP/spec 4; endpoint loopback 8350. Q4 estándar tomó aprox. 53:51 en las tres corridas; Hard Mode 19:02. Tiempos desde launch hasta los reportes y sin carga del modelo. No se midió TPS ni Server Speed independiente.
- Los SHA-256 de shards, runner y archivos de configuración están en `receipts/model-source-checksums.txt`, `receipts/runner-source.json` y los JSON de configuración. Los perfiles comparados difieren en runtime, contexto, KV y hardware efectivo; el resultado es de perfiles completos, no una atribución sólo al modelo.
- El servidor Q4 propio se detuvo tras la evaluación; puerto 8350 cerrado. GPUs al cierre: 1050 MiB usados en GPU0 (escritorio/Xorg) y 108 MiB en GPU1; sin carga de benchmark.

## Decisión y límites

No cambiar perfiles productivos ni HarnessSpec. Para la suite simulada v2.7.0, Q4 es el candidato local mejor clasificado y superó a los controles en las tres semillas Hard Mode; ASTRA quedó segundo. Mantenerlo como evidencia provisional por uso. La siguiente validación de una decisión de coding/agente debe sumar tareas de repositorio con verificador independiente, HE20/BCB8, ADV y TaskFlow ULTRA, y una prueba E2E real si la decisión cubre Computer Usage. No inferir visión, audio, recuperación larga, inteligencia general ni operación GUI desde esta suite.

No es una réplica del post: los pesos del autor (AtomicChat Q4_K_M y 27B Q5_K_XL), su Radeon R9700 y builds de llama.cpp no son los perfiles locales de esta evaluación.

## Recibos principales

- [`PLAN.md`](PLAN.md) y [preflight](receipts/preflight.json).
- [Matriz agregada por perfil y semilla](receipts/tool-eval/all-seeds-comparison.json).
- [Resultados crudos JSON](receipts/raw/).
- [Logs del runner y del servidor](receipts/logs/).
- [SHA-256 y huellas](receipts/model-source-checksums.txt), [origen/versiones de runner](receipts/runner-source.json).
- [Comparación histórica v2.8.0 de 28 casos](../Q-20261010-FRONTIER-MULTITASK-AB/RESULTS.md).
