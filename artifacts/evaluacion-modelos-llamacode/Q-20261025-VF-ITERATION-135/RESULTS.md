# Q135 — evaluación de seis fuentes nuevas (IA local, filas 59–64)

**Cierre: 2026-10-25.** Se revisaron las seis entradas en serie. Sólo JetBrains Qwen3.8-3.6-27B-blend tenía un experimento local justificado y con espacio/runtime compatibles; completó el A/B dual-RTX3090 de tres semillas. Resultado: **no adoptar**. Las otras cinco entradas quedan clasificadas con una condición concreta o sin prueba aplicable. No se cambió ASTRA, SOL, Flash-Next productivo ni ningún modelo de PeritoSoft.

## Decisión del A/B JetBrains blend

Se comparó JetBrains Qwen3.8-3.6-27B-blend Q4_K_M contra Qwen3.8-27B Q4_K_M con el mismo llama.cpp b11554, plantilla, harness, sampler y tres semillas pareadas. Los seis casos se completaron válidamente.

| Métrica | Control Qwen3.8-27B | JetBrains blend | Lectura |
|---|---:|---:|---|
| Tool-Eval Hard Mode, media /100 | 83 (79, 84, 86) | 78 (77, 80, 77) | −5 puntos; gate exigía al menos 81 |
| Mediana E2E en 53 pares caso-semilla aprobados por ambos | 19,16 s | 17,43 s | 9,03% más rápido; gate exigía 15% |
| Completion tokens en esos 53 pares | 37.865 | 37.991 | 0,33% más tokens; no se acerca al −20% requerido |
| E2E de los 28 escenarios, media por corrida | 703,15 s | 638,38 s | Descriptivo; no sustituye el criterio pareado de tareas correctas |
| Prefill, media ponderada de eventos `prompt eval` del harness | 723,26 tok/s (319 eventos) | 703,58 tok/s (332 eventos) | Blend −2,7%; no es un benchmark de prefill largo |
| Decode, media ponderada de eventos `eval` del harness | 72,99 tok/s (638 eventos) | 79,87 tok/s (664 eventos) | Blend +9,4%; eventos de solicitudes/tool calls cortos, no throughput multiusuario |
| Índice exploratorio: score medio / segundos de la suite media | 0,1180 puntos/s | 0,1222 puntos/s | +3,6% para blend, sólo en esta cohorte; no neutraliza el gate de calidad |

El índice score/segundo se incluye como métrica auxiliar solicitada para tomar decisiones. No es un score calibrado ni un criterio de adopción. Los resultados de suites distintas no comparten escala y no deben ordenarse con ese índice.

### Regresiones y mejoras conductuales

- **TC-80:** control pasó 3/3; blend falló 3/3. Regresión crítica que por sí sola falla el gate.
- **TC-82:** control pasó 3/3; blend quedó parcial y generó la advertencia de no confirmar destinatario/conflicto de memoria en 3/3.
- **TC-74 y TC-92:** blend pasó 3/3 en ambos; control falló TC-74 en 3/3 y TC-92 en 1/3.
- Puntajes por semilla: control 79/84/86; blend 77/80/77. Cuentas pass/partial/fail por semilla: control 20/4/4, 22/3/3, 22/4/2; blend 19/5/4, 20/5/3, 19/5/4.

El candidato mejora algunos casos pero pierde cinco puntos de promedio, incorpora TC-80 y TC-82 y no supera los umbrales de velocidad/token. No promoverlo ni reemplazar ASTRA/SOL.

## Configuración reproducible

- **Hardware:** dos RTX 3090, `CUDA_VISIBLE_DEVICES=0,1`, llama.cpp `--split-mode layer --tensor-split 1,1`; host 128 GiB. Un servidor y una semilla a la vez; sin límites artificiales de RAM/swap.
- **Modelos:** control local Qwen3.8-27B Q4_K_M, SHA-256 `c600de0300ae8a0eb3a6c0b8b5561b8b96f16bd2c863c2a66c42de29d391a747`; candidato JetBrains GGUF Q4_K_M, HF revision `d9c54de0a7d89d34fa4f07c482e35b86a12923f6`, SHA-256 `5f54ded85a78f11ad7a1c02d17564a268238ac8afe9b3d94fb0b614e473006a1`. El candidato quedó en `Disco local/Modelos-eval/Q135-jetbrains-blend/`.
- **Motor:** llama.cpp server b11554, commit `966baae76`, ejecutable SHA-256 `fe8a7d6073d3e3a276193fcaec162cbf280d2572ad2016c9100fd924be19c6ed`.
- **Motor args:** `--n-gpu-layers 999 --split-mode layer --tensor-split 1,1 --ctx-size 32768 --batch-size 512 --ubatch-size 512 --threads 8 --cache-type-k q4_0 --cache-type-v q4_0 --flash-attn on --jinja --chat-template-file assets/chat-templates/qwen38-tools-fixed.jinja --reasoning-effort medium --reasoning-budget 4096 --n-predict 4096 --spec-type none`; alias/`--model` cambiaron por brazo. Template SHA-256 `03c3e852d2c349ce306ed9ecd870c83487bf123918843387b179ead1fcce93af`.
- **Harness:** Tool-Eval Bench 2.8.0, commit `0a1ba68c7709f429298bc92417a9e003f61de4e3`, Hard Mode TC-70–TC-97; seeds 42/43/44; variant seed 20261010; temperature .6, top-p .95, top-k 20, min-p 0, repeat penalty 1, reasoning medium; timeout 120 s, máximo 8 turnos, paralelismo 1. El orden de los brazos se contrabalanceó por semilla.
- **Límites de medición:** los TPS se ponderan sobre las líneas `print_timing` de las solicitudes del harness y contienen prompts cortos de herramientas. No equiparar a prefill cold de contexto largo ni a servicio concurrente. La latencia pareada sólo considera las 53 celdas caso-semilla donde ambos modelos aprobaron; score, velocidad y seguridad se conservan como ejes separados.

## Clasificación de las seis fuentes

| Fila | Material | Resultado | Condición / decisión |
|---:|---|---|---|
| 59 | JetBrains Qwen3.8-3.6-27B-blend | **A/B completo; no adoptar** | Misma revisión no merece otra repetición. Reabrir sólo por peso/revisión, runtime, harness o workload materialmente nuevo. |
| 60 | PROMETHEVS 0.2 / DeepSeek V4.1 | **Bloqueada por plataforma y almacenamiento** | Exige Windows y aproximadamente 1,1 TB libres de NVMe; el host actual es Linux y las unidades de modelos tienen 59 GB y 26 GB libres. No descargar/build. |
| 61 | Gyro-Coder-L / Flash-Next | **Bloqueada por almacenamiento/runtime** | Artefacto ~78,2 GiB, objetivo de tarjeta de 32 GB, ~27,54 GiB de pesos GPU; la tarjeta oficial indica soporte Strata pendiente y llama.cpp stock no carga el formato. No descargar. |
| 62 | Basalt / NVFP4 | **Sin prueba aplicable al hardware local** | Basalt requiere Blackwell sm_120/CUDA 13; RTX 3090 es Ampere sm_86. No extrapolar las cifras publicadas ni compilar en estas GPU. |
| 63 | Huihui v2 UD-IQ4_XS | **Bloqueada por espacio; variante distinta** | 87,25 GB de modelo + 26,82 GB de PLE superan 59/26 GB disponibles; el reporte usa RTX 5060 Ti. El QFN local de Q26 es otra revisión, no duplicado. |
| 64 | Strata Qwen3.6-35B-A3B | **Bloqueada por runtime multi-GPU** | La ruta `qwen35` disponible usa una GPU; issue upstream #3294 pide layer split y sigue pendiente. No ejecutar con una GPU como sustituto del A/B dual-3090 solicitado. |

## Sincronización y archivos de evidencia

Se creó la pestaña **Resultados** con 12 filas de perfiles medidos, configuración de harness/motor, rutas Linux, estado de ruta Windows, métricas de calidad/velocidad, memoria/estabilidad y enlaces locales a los recibos. Incluye Q135, Q131, Q32/Q34, Q72, Q09 y el screen RCO de VF-20261019-01. La columna “cohorte comparable” separa las pruebas; los scores entre suites no son un ranking global. El inventario, `IA local`, `Accionables` y el registro Q135 en `Evaluaciones LlamaCode` fueron actualizados y leídos de vuelta.

Recibos principales: `receipts/preregistration.json`, `receipts/attempt-02-benchmark-final.json`, `receipts/attempt-02-campaign-progress.json`, `receipts/source-dispositions.json`, `receipts/google-sheet-sync-results-tab.json`; logs timing `attempts/attempt-02/logs/seed-{42,43,44}-{control,blend}-llama-server.log`.


## Historial verificado incluido en la pestaña Resultados

La pestaña `Resultados` contiene además tres filas provenientes de pruebas históricas ya concluidas; son datos importados con sus recibos, no nuevas inferencias de Q135:

- **Q35 ASTRA 131K:** promedio semántico 7,33/8 en tres intentos (dos completos 8/8 y uno parcial 6/8 por `max_tokens=768`); prefill 3.440,9 tok/s, decode 154,7 tok/s, sesión total media 56,82 s.
- **Q35 ASTRA 1M:** tres respuestas completas 8/8 tras prompts de ~1,001M tokens; prefill 2.310,0 tok/s, decode 89,9 tok/s, sesión total media 454,53 s. Capacidad 1M demostrada; 131K se mantiene como default por latencia, sin ventaja de calidad establecida.
- **Q127 SOL:** smoke aislado de memoria, 24.319 tokens de prompt, 14,953 s de request, RAM disponible mínima 99,973 GiB, RSS máximo 12,421 GiB, VRAM máxima 24.080/23.972 MiB, cero swap/OOM. No midió calidad ni TPS separados; no se usa para ranking. El compose resuelto también contiene `REASONING_EFFORT=medium` en el entorno y `reasoning_effort=low` en los kwargs de la plantilla; el smoke prompt-copy no permitió resolver qué valor prevalece.

La comparación calidad/velocidad de Q35 usa `score medio / sesión total media`, como define el encabezado, con notas en las celdas que limitan su interpretación. Evidencia fuente: Q35 `RESULTS.md`, Q37 `receipts/q35-matrix-final-decision.json`, y Q127 `RESULTS.md`/`receipts/result-analysis.json`.
