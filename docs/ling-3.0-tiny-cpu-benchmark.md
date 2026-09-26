# Ling 3.0 Tiny: benchmark CPU-only

Este run compara los GGUF Q4_K_M y Q6_K en CPU, con contextos de 4k y 8k y
thinking desactivado/activado. Fuerza `--n-gpu-layers 0`, fija los mismos
threads, batch, ubatch, KV q8 y sampling en todas las variantes. El runner usa
el tokenizer del servidor para preparar cada documento cerca del límite útil
del contexto, dejando margen para plantilla, respuesta y razonamiento.

Cada variante resume dos informes sintéticos en español. El score cuenta la
retención de hechos requeridos; sirve como comprobación repetible de salida,
no como grader semántico ni como evaluación general de calidad. El JSON registra
la respuesta, hechos encontrados, prompt/decode tok/s, tiempo por petición,
pico de working set, versión de `llama-server`, hardware y SHA-256 de ambos
GGUF. Los logs del servidor quedan junto al JSON.

## Reproducción en esta notebook

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\tools\benchmark_ling_cpu.ps1 `
  -ServerPath 'D:\Models\llamacpp\bench-runtime\b10964\unpacked\llama-server.exe' `
  -Q4ModelPath 'D:\Models\llamacpp\Ling30-cpu-benchmark\Ling-3.0-tiny-Q4_K_M.gguf' `
  -Q6ModelPath 'D:\Models\llamacpp\Ling30-cpu-benchmark\Ling-3.0-tiny-Q6_K.gguf' `
  -Threads 16
```

El reporte se guarda por defecto en `artifacts/ling-tiny-cpu-<fecha>.json` y los
logs en el subdirectorio homónimo. Cambiar threads, runtime, quant, plantilla,
sampling o corpus crea una configuración distinta y no debe mezclarse con esta.

Si el proceso termina después de guardar las peticiones, se reconstruyen los
agregados sin volver a ejecutar inferencia:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\tools\benchmark_ling_cpu.ps1 `
  -FinalizeExistingReport .\artifacts\ling-tiny-cpu-20260926.json
```

El chequeo de helpers y entradas se puede repetir sin los GGUF ni el servidor:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\tests\test_benchmark_ling_cpu.ps1
```

## Resultado local — 2026-09-26

Equipo: AMD Ryzen 9 9950X3D (16 núcleos/32 hilos), Windows 11 Pro, 64 GiB RAM.
Runtime `llama-server` build 10964, Windows x64; todas las corridas usaron
`--n-gpu-layers 0`, 16 threads, batch/ubatch 512/128 y KV q8. El proceso mostró
~32,8 GiB libres antes y ~30,2 GiB después de la matriz. Son resultados de este
CPU de escritorio; no predicen la velocidad de un i5 móvil de 2017.

La tabla resume las dos tareas por variante. `Recall` cuenta hechos requeridos
en la respuesta final (12 por variante); el score de thinking-on cae a cero
cuando se agotan los tokens antes de producir el resumen.

| Quant | Contexto | Thinking | Decode tok/s medio | Recall | Pico working set |
|---|---:|---|---:|---:|---:|
| Q4_K_M | 4k | off | 49,46 | 0,92 | 4,67 GiB |
| Q4_K_M | 4k | on | 48,35 | 0,50 | 4,84 GiB |
| Q4_K_M | 8k | off | 42,68 | 1,00 | 4,71 GiB |
| Q4_K_M | 8k | on | 34,63 | 0,00 | 4,88 GiB |
| Q6_K | 4k | off | 37,86 | 0,67 | 5,97 GiB |
| Q6_K | 4k | on | 34,16 | 0,00 | 6,25 GiB |
| Q6_K | 8k | off | 33,55 | 0,92 | 6,03 GiB |
| Q6_K | 8k | on | 30,25 | 0,00 | 6,26 GiB |

Con thinking apagado el recall conjunto fue 42/48 (87,5%); Q4_K_M quedó en
23/24 y Q6_K en 19/24. En thinking-on, sólo una de las ocho respuestas llegó a
una respuesta final: las otras siete usaron el tope de 2048 tokens y acabaron
con `finish_reason=length`. Por eso su recall mide el comportamiento con ese
presupuesto, no la calidad potencial con razonamiento sin límite. El modo
apagado resumió ambos documentos a 8k en Q4 y perdió un hecho en uno de los dos
documentos a 8k en Q6.

El reporte bruto con prompts medidos por el tokenizer, respuestas, tiempos,
hashes y logs está en
[`artifacts/ling-tiny-cpu-20260926.json`](../artifacts/ling-tiny-cpu-20260926.json).
Los GGUF usados fueron Q4_K_M SHA-256
`a21f717779203d86b53996239c4903941858b938c50e85b03e6a981132b5621a` y Q6_K
SHA-256 `f9698dcc5801274ac7b33fd287081811525e9fac326700d08c2b40c761b92e63`.

Esta prueba confirma velocidad útil en CPU de escritorio con thinking apagado,
y que Q4 reduce memoria y mejora decode frente a Q6 en esta máquina. El tope
actual de thinking no completó la mayoría de resúmenes dentro del presupuesto;
el resultado no justifica etiquetar la configuración como CPU-ready en equipos
de poca RAM sin repetir la medición allí.
