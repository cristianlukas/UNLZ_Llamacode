# Resultados — barrido de contexto ISTA IQ2_XS

**Estado: completado como screening de rendimiento.** ISTA IQ2_XS/Strata aceptó prompts de al menos 95% de los límites 131K, 262K, 512K y 1M y generó 64 tokens en cada punto. Esto demuestra que el perfil puede procesar una solicitud corta de ese tamaño con la configuración registrada; no valida exactitud de recuperación ni calidad general a contexto largo. ASTRA DEFAULT permanece configurado en 131.072 tokens.

## Resultados

| Contexto máximo | Rope | Prompt / ocupación | Prefill / decode TPS | TTFT / tiempo de petición | RAM pico del árbol / RAM disponible mínima | VRAM GPU0 total (Δ) / GPU1 total (Δ) | Swap-in / swap-out global |
|---:|---|---:|---:|---:|---:|---:|---:|
| 131.072 | Nativo | 124.535 (95,013%) | 3.265,5 / 139,1 | 38,14 / 38,64 s | 39,23 / 68,35 GiB | 23.734 (+22.679) / 20.776 (+20.668) MiB | 171 / 0 páginas |
| 262.144 | Nativo | 249.146 (95,042%) | 3.163,8 / 133,2 | 78,75 / 79,31 s | 40,89 / 66,60 GiB | 23.782 (+22.725) / 20.906 (+20.798) MiB | 1.138 / 0 páginas |
| 524.288 | YaRN ×2 | 498.122 (95,009%) | 2.860,8 / 113,1 | 174,12 / 174,86 s | 44,31 / 63,22 GiB | 23.352 (+22.335) / 21.912 (+21.804) MiB | 692 / 0 páginas |
| 1.048.576 | YaRN ×4 | 996.163 (95,002%) | 2.232,9 / 85,6 | 446,13 / 447,24 s | 51,14 / 55,64 GiB | 23.822 (+22.803) / 22.454 (+22.346) MiB | 109.670 / 48 páginas |

Prefill/decode son tasas reportadas por Strata. TTFT es prompt evaluation; el tiempo de petición incluye prefill y 64 tokens de decode, pero no la carga inicial del modelo. VRAM muestra el uso total máximo medido en cada tarjeta; los recibos incluyen también el delta sobre la base. RSS es la suma de server y engine; `MemAvailable` es memoria restante en el host y no debe sumarse a VRAM. Las dos RTX 3090 de 24 GiB trabajaron en serie, sin concurrencia.

## Lectura y límites

El prefill cae de 3.265,5 tok/s a 131K a 2.232,9 tok/s a 1M; el decode cae de 139,1 a 85,6 tok/s. El RSS del árbol sube de 39,23 a 51,14 GiB, mientras que la VRAM pico total se mantuvo en 23,3–23,8 GiB para GPU0 y aumentó de 20,8 a 22,5 GiB para GPU1. La disponibilidad mínima del host fue 55,64 GiB en 1M.

El prompt de recuperación incluía hechos sembrados, pero el request se limitó a 64 tokens y la respuesta terminó con `finish_reason=length`; esta ejecución no calificó aciertos. La prueba es un probe único por tamaño, no una comparación con otras configuraciones ni un benchmark estadístico. La extensión YaRN ×2/×4 valida aceptación operacional del prompt, no calidad semántica equivalente al contexto nativo.

No se vació el swap. Las páginas de `pswpin/pswpout` son contadores globales del sistema y no se pueden atribuir íntegramente a Strata; durante el punto 1M el delta fue 109.670 páginas de entrada y 48 de salida (192 KiB). Al terminar, el sistema aún reportaba 7,004 GiB de swap usado y 107,375 GiB de RAM disponible. El swap no fue requisito para que el endpoint completara estas sondas. No se alteró el perfil productivo ni su límite de 131.072 tokens.

## Intentos anteriores no válidos

Se conservan todos los intentos incompletos y sus logs en `receipts/runs/<contexto>/`. En 131K hubo una ruta relativa de configuración inválida antes de cargar y un corte PSI del monitor; en 262K y 512K el umbral PSI inicial cortó durante la carga del arena pese a abundante RAM disponible; en 1M ocurrió lo mismo una vez y otra carga se cortó tras 7 páginas de swap-out global. Ninguno llegó a estar listo en el API ni envió un prompt. No cuentan como fallos del modelo ni como medidas de TPS. El monitor final se amplió a PSI `some avg10 ≥80%` o `full avg10 ≥60%` durante 15 muestras, mantiene piso de MemAvailable de 20 GiB y aborta por más de 4 MiB de swap-out.

## Reproducibilidad y artefactos

- [Plan/protocolo y registro completo de intentos](PLAN.md)
- [Resumen JSON de las cuatro corridas válidas](receipts/summary.json)
- [Manifiesto del runtime, modelo y huellas](receipts/runtime-manifest.json)
- [Preflight de reanudación](receipts/preflight-resume.json) y [postflight de cierre](receipts/postflight-cleanup.json)
- Configuraciones efectivas: `receipts/configs/context-<contexto>.json`
- Prompts, requests, responses, monitor y logs crudos: `receipts/runs/<contexto>/`

Los pesos permanecieron en su ubicación y no se modificaron. La configuración ASTRA DEFAULT no se cambió. No se ejecutaron build ni tests del producto: esta tarea sólo generó recibos y documentación.
