# Q181 — Resultados finales

**Estado:** completado. **Decisión:** no promover `agent-intermedio`; el holdout favorece a `agent-basico`.

## Diseño

Tres pasadas intercaladas Básico/Intermedio, 3 tareas de programación por pasada y oracles deterministas. En total se procesaron 18 ejecuciones de tarea (9 por perfil) y seis filas de comparación. Modelo fijo: Qwen3.8 Flash-Next RCO IQ2_XS / ASTRA Strata, dos RTX 3090, contexto configurado de 1.048.576 tokens con YaRN×4 y KV int8. La comparación es de perfiles de agente, no un benchmark general de inteligencia del modelo.

## Resultados por pasada

| Pasada | Perfil | Aceptación | E2E (s) | Primer intento (s) | Reparaciones | Tool calls | Éxito tools | Redundantes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | Básico (copia) | 11/11 | 76.726 | 76.423 | 0 | 32 | 78.12% | 11 |
| 1 | Intermedio (copia) | 11/11 | 68.071 | 67.770 | 0 | 33 | 75.76% | 14 |
| 2 | Básico (copia) | 11/11 | 60.638 | 60.337 | 0 | 18 | 94.44% | 0 |
| 2 | Intermedio (copia) | 11/11 | 105.155 | 85.776 | 2 | 22 | 100.00% | 2 |
| 3 | Básico (copia) | 11/11 | 94.903 | 69.761 | 2 | 30 | 100.00% | 2 |
| 3 | Intermedio (copia) | 10/11 | 110.194 | 64.773 | 3 | 44 | 88.64% | 13 |

En la pasada 3, Intermedio no pasó `test_negative_and_signed_tokens`: esperaba `min = -3`, recibió `-43` (10/11 criterios). La limitación no fue un timeout del test; el caso terminó con error de aceptación del producto generado.

## Medianas agregadas (n=3 pasadas por perfil)

| Perfil | Pasadas aceptadas | E2E mediano (s) | Primer intento mediano (s) | Reparaciones medianas | Éxito de tools mediano | Tools redundantes medianas |
|---|---:|---:|---:|---:|---:|---:|
| Intermedio (copia) | 2/3 | 86.613 | 76.773 | 1 | 87.88% | 8 |
| Básico (copia) | 3/3 | 76.726 | 69.761 | 0 | 94.44% | 2 |

Básico redujo la mediana E2E **11.42%** y la mediana de primer intento **9.13%** frente a Intermedio. Ambos tuvieron mediana de calidad 100%, pero la corrida fallida y la variabilidad de Intermedio impiden declararlos equivalentes con este holdout.

## Decisión y límites

- La regla preregistrada no habilita recomendar Intermedio: su tasa de pasadas aceptadas fue menor, su mediana E2E fue más lenta y su mediana de reparaciones fue mayor.
- Resultado acotado a esta combinación modelo/runtime, tres tareas y tres pasadas. No generalizar a otros lenguajes, repositorios ni perfiles.
- No se modificó ningún perfil productivo. No se hizo build de la aplicación.
- Carga inicial de Strata en el intento final: **194 s hasta READY**. Init hot no se midió por separado.
- Pico de memoria del cgroup: ~82,5 GB; mínimo observado de MemAvailable: ~62,8 GB; OOM/OOM-kill = 0. No se aplicó límite artificial de RAM/swap.
- Cleanup comprobado: `q181-harness.service` inactivo, puertos 18473/18877 libres y cero compute apps tras parar el scope de prueba.

## Evidencia

- Receipt completo: `receipts/results.json`.
- Datos durables: `home/harness2-run/summary.json` y `home/harness2-run/control-events.jsonl` en HDD extra; hashes SHA-256 incluidos en el receipt.
- Corridas originales: `home/.qttest/share/LlamaCode/LlamaCode/benchmark-runs/Q181_coding_holdout_pass_*` en HDD extra.
- Perfil/runtime congelado: `configs/astra-iq2xs-dual-1m-q181.json`; fixture y modificaciones de prerregistro en `receipts/`.
