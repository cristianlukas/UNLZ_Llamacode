# QwFN-hybrid: rendimiento local

Campaña del 2026-10-01 con QwFN-hybrid `6b26989f8a2bdefd6c541ba0d0586c80b9e3b011`, quant GSQ-RCO IQ3_XXS (dos shards, 70,62 GiB), head MTP Q8 y `llama.cpp` limpio `ca1426903fabe9af26cd10c42034cb4bbd2e0e11`. GPU visible: una RTX 3090 de 24 GiB; RAM del host: 123 GiB. Contexto 73.728, KV Q8, batch 32.768. QwFN se limitó a 12 GiB VRAM + 19 GiB RAM, `--ram-frac .95`, 5 threads. El control usó `llama-bench`, `-ngl 99 -ot exps=CPU -fa 1 -ctk/ctv q8_0 -t 8`; llama.cpp pudo usar la page cache del sistema sin un límite de RAM equivalente.

## Resultados

| Trabajo | QwFN, MTP apagado | QwFN, MTP Q8 | llama.cpp limpio | Lectura local |
|---|---:|---:|---:|---|
| Prefill 512 | 32,2 / 39,5 tok/s | 38,8 / 39,3 tok/s | 186,37 ± 1,92 tok/s | Upstream bastante más rápido en prompt corto |
| Decode, contexto 512 | 11,55 / 11,97 tok/s | 12,86 / 12,99 tok/s | 19,11 ± 0,21 tok/s | Upstream más rápido; MTP sube poco en QwFN |
| Prefill 16K | 606,9 / 718,3 tok/s | 304,8 / 726,8 tok/s | 182,74 ± 1,88 tok/s | QwFN gana en el ensayo caliente; primera repetición MTP tuvo una anomalía de I/O |
| Decode 128 tokens a profundidad 16K | 7,73 / 7,21 tok/s | 1,77 / 9,38 tok/s | 18,59 tok/s | Upstream gana; la variación de MTP hace que no sea promoción segura |

Las dos repeticiones están separadas por `/`. El primer resultado QwFN 16K+MTP leyó 43,9 GiB de expertos a sólo 0,27 GB/s; la repetición siguiente midió 726,8 tok/s de prefill y 9,38 tok/s de decode. Se conservan ambas como una señal de variabilidad del camino de almacenamiento, no se descarta silenciosamente la corrida lenta. La comparación larga es de prefill fijo y decode greedy generado; no equivale a una solicitud agentiva end-to-end.

`llama.md`, `llama.err` y los ocho logs del engine QwFN están guardados en `raw/`. La matriz exacta es `bench/llamabench.sh` del checkout QwFN indicado arriba. No repetir pp512/pp16K/tg128 con esta misma quant, contexto, split y hardware salvo que cambie explícitamente la pregunta (p. ej. límite de RAM o estado frío/caliente).
