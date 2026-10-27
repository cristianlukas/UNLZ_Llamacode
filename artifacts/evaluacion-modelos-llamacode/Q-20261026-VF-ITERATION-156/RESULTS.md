# Q156 — Gyro-M TQ2_0 vs ASTRA RCO IQ2_XS, dual RTX 3090

**Estado final (2026-10-27T01:43:17Z):** attempt02 completado con no-go de etapa; ambas ejecuciones válidas y limpias.

- El GGUF Gyro-M fijado se descargó completo: 91,965,774,272 B; SHA-256 verificado `7aa36d15131d255179ab6c87fa9c9f81a0b541fc9e81e959d4c3e29eb20feb5f`.
- Strata generó el pack. El archivo de pesos `dense.bin` tiene 1,485,688,320 B, SHA-256 `e9588a855a18984a01c4202eaa295fb7211b341d49c440b0f203b5c310048954`; índice, expertos nativos y tokenizer también están fijados en `receipts/preregistration.json`.
- ASTRA y Gyro-M pasaron los planes offline finales, sin notas, en Strata Control 0.1.51 / CUDA engine 0.1.50, GPUs 0 y 1, MTP4 común, perfil neutral, contexto/prefill 8,192 y KV int8.
- La ayuda del engine aclaró que `--max-new` limita tokens generados. Antes de cualquier inferencia se corrigieron ambos configs de 256 a 6,144, igual al runner; hashes actualizados y planes repetidos.
- Preflight 2026-10-27T01:11:53Z: no hubo proceso/listener/container de PeritoSoft o servidor de inferencia que terminar; no se envió señal. GPUs libres para compute; ArtCraft sólo tiene uso gráfico en GPU0 y sigue intacto. MemAvailable 115,923,240 kB; PSI some/full avg10 0.00/0.00; OOM 0; D libre 402,681,024,512 B.
- **No hay score, calidad, prefill/decode ni tiempo E2E todavía.** Próximo paso: ejecutar el screen BCB-Hard-8 seed 4242 serial ASTRA→Gyro-M, con verificación de hashes y de compute propio en las dos GPU.
- Gate de ampliación: Gyro-M ≥4/8 y al menos +2 respecto al control, transporte 8/8, cero sandbox errors y cero respuestas vacías; sólo después preregistrar 3 semillas y throughput separado.

El pack y runtime viven en `Models-eval/Q156-gyro-m` sobre D. ASTRA, SOL, perfiles productivos y PeritoSoft permanecen intactos.

## Intento 1 — inválido por sandbox del grader (2026-10-27T01:24:42Z)

- ASTRA control: transporte 8/8; las ocho respuestas generaron contenido, pero el grader devolvió `sandbox_error` 8/8 porque `bwrap` no puede acceder al intérprete aislado `.../runtime/control-0.1.51/python/bin/python3.12`: el sandbox monta `/media` como tmpfs.
- Gyro-M candidato: **no iniciado**.
- No hay score de calidad válido y no se agrega fila a `Resultados`. La falla está antes de ejecutar las soluciones, no se atribuye al modelo.
- Cleanup: servidor control propio detenido; puertos 8363/18789 libres; procesos de inferencia/compute propios en cero; GPU vuelve a su uso gráfico previo.
- Recibo: `receipts/attempt-01-grader-gate-failure.json`. Próximo paso preregistrado: smoke del grader con Python del sistema dentro de bwrap y repetición serial ASTRA→Gyro-M.

## Corrección validada del grader (2026-10-27T01:25:49Z)

- Se cambió el intérprete del grader a `/usr/bin/python3`, visible dentro del namespace; el archivo resuelve a `/usr/bin/python3.12`, SHA-256 `e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f`.
- El smoke reprodujo el mismo `bwrap`+seccomp, incluido `--tmpfs /media`, y ejecutó `sandbox-smoke-ok /usr/bin/python3` con código 0. No hizo inferencia ni usó GPU.
- Runner actualizado y fingerprint fijado: `6cccb15ec423d0917eb6aaa4c05d00b56809e190175b4c3c415ed9cd086d3637`.
- Siguiente: repetir el par completo desde ASTRA y después Gyro-M; el intento anterior queda invalidado para calidad.

## Attempt 2 — brazo ASTRA completado (2026-10-27T01:40:02Z)

- ASTRA RCO IQ2_XS: **2/8**, transporte 8/8, sandbox errors 0, respuestas vacías 0; configuración/revisión/hashes fijados y mismas 2×RTX3090, Strata 0.1.51/engine 0.1.50, MTP4, contexto/prefill8192, `max-new 6144`.
- El supervisor confirmó limpieza del brazo control y liberación del puerto. Gyro-M inició como segundo brazo; su resultado todavía no está.
- No es comparación final ni se escribió fila en `Resultados`. Gate para ampliar campaña: Gyro-M ≥4/8 y ≥2 casos más que este control.
- Recibo: `receipts/attempt-02-control-result.json`.


## Attempt 2 — comparación final, gate fallido (2026-10-27T01:43:17Z)

| Medida | ASTRA RCO IQ2_XS (control) | Gyro-M TQ2_0 (candidato) | Lectura del screen |
| --- | ---: | ---: | --- |
| BCB-Hard-8 seed 4242 | 2/8 | 2/8 | Empate; aprobaron los mismos IDs: 870 y 310 |
| Transporte | 8/8 | 8/8 | Completo en ambos |
| Errores del grader/sandbox | 0 | 0 | No hubo fallos de infraestructura |
| Prefill mediano por request | 411.25 tok/s | 418.80 tok/s | Candidato +1.8%; muestra corta |
| Decode mediano por request | 159.20 tok/s | 125.95 tok/s | Candidato -20.9% |
| Latencia mediana por request | 15.765 s | 19.612 s | Candidato +24.4% más lento |
| Tokens generados (suma de 8) | 19397 | 19356 | No equivale a calidad |

Ambos brazos usaron Strata Control 0.1.51 / CUDA engine 0.1.50, las dos RTX 3090, MTP4 común, perfil neutral, KV int8, contexto/prefill 8.192, `max-new 6144`, temperature 0.6, top-p 0.95, top-k 20, min-p 0, repeat penalty 1.0, reasoning on con presupuesto 2.048; ejecución serial con el mismo BCB-Hard-8. Los hashes de entrada/config y los resultados por tarea están fijados en los recibos.

Gyro-M no llegó al umbral preregistrado de ≥4/8 y ≥2 aciertos de ventaja. En este screen su decode mediano fue menor y su latencia mediana mayor, aunque el prefill mediano fue parecido. **No se ejecutan las tres semillas ni throughput** porque el gate de etapa falló. Es evidencia de no-go para esta comparación y carga; por el tamaño del holdout no se generaliza una afirmación de calidad a todos los usos. ASTRA y SOL permanecen intactos.

El supervisor cerró los dos servidores y liberó los puertos 8363/18789; `runs/state.json` registra limpieza completada en ambos brazos. Attempt01 se conserva como inválido por el grader; no se mezcló con el score.

Recibos finales: `receipts/attempt-02-final.json`, `receipts/candidate-retirement-preregistration.json` y, tras ejecutar la limpieza autorizada, `receipts/candidate-cleanup-completion.json`.


- **Retiro de almacenamiento (2026-10-27T01:52:36Z):** se quitaron el GGUF (91,965,774,272 B), el marker (71 B) y el pack dedicado de 11 archivos (1,495,844,329 B lógicos). `df` mostró +93461643264 B disponibles (delta observado; puede incluir granularidad/metadatos del filesystem). ASTRA, SOL, runtime compartido, MTP, configs y evidencia permanecen. Recibo: `receipts/candidate-cleanup-completion.json`.
