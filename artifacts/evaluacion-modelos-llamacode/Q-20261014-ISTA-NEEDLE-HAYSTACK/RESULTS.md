# Resultados — Needle in a Haystack para ISTA IQ2_XS

**Estado: screening completado, 4/4 corridas válidas.** ISTA IQ2_XS recuperó exactamente **10/10 hechos** a 131K, 262K, 512K y 1M, con agujas situadas entre el 5% y el 95% de cada prompt. Es una suite sintética interna inspirada en Needle in a Haystack, no una réplica de un benchmark externo ni una medida de razonamiento general. Una corrida por tamaño; los resultados son provisionales.

## Resultados

| Contexto | Prompt real / ocupación | Recuperación exacta | Prefill / decode | TTFT / petición / sesión Strata | RAM pico RSS / MemAvailable mínima | VRAM GPU0 total (Δ) / GPU1 total (Δ) |
|---|---:|---:|---:|---:|---:|---:|
| 131.072 nativo | 124.535 (95,013%) | **10/10** | 3.279,0 / 148,0 tok/s | 37,98 / 39,43 / 54,98 s | 39,17 / 68,05 GiB | 23.747 (+22.659) / 20.808 (+20.700) MiB |
| 262.144 nativo | 249.146 (95,042%) | **10/10** | 3.168,1 / 134,2 tok/s | 78,64 / 80,28 / 96,14 s | 40,89 / 66,32 GiB | 23.797 (+22.716) / 20.938 (+20.830) MiB |
| 524.288 YaRN ×2 | 498.122 (95,009%) | **10/10** | 2.850,7 / 120,5 tok/s | 174,74 / 176,64 / 194,49 s | 44,31 / 62,72 GiB | 23.371 (+22.251) / 21.944 (+21.836) MiB |
| 1.048.576 YaRN ×4 | 996.163 (95,002%) | **10/10** | 2.230,1 / 98,4 tok/s | 446,69 / 449,17 / 467,63 s | 51,14 / 55,73 GiB | 23.808 (+22.773) / 22.474 (+22.366) MiB |

El prompt real reportado por Strata coincide con el probe previo: 124.535, 249.146, 498.122 y 996.163 tokens (95,013%, 95,042%, 95,009% y 95,002% del límite). Cada request obtuvo 209 tokens de respuesta; `finish_reason=stop`, HTTP 200 y sin error de transporte. Cada hecho recibió comparación exacta por clave/valor; se guardan las posiciones y resultados individuales en `receipts/runs/<contexto>/receipt.json`.

TTFT es tiempo de prefill del engine; petición incluye prefill y respuesta; sesión añade la carga y el cierre del servidor, pero no la preparación de los fixtures. La sesión total de las cuatro corridas fue **13 min 33 s** (12 min 25 s de solicitudes). RSS es la suma de server y engine; MemAvailable es la mínima RAM disponible del host durante la corrida. VRAM muestra pico total por tarjeta y, entre paréntesis, el incremento sobre la línea base. Las GPUs RTX 3090 trabajaron en serie. El swap no se vació; no hubo swap-out global en ninguna corrida, y PSI se mantuvo en cero.

## Interpretación y límites

- La suite muestra recuperación exacta de estos diez valores a las posiciones indicadas, incluyendo el final del contexto, bajo Strata 0.1.41 y esta plantilla de prompt.
- No mide robustez frente a preguntas paraphraseadas, hechos contradictorios, múltiples needles que compiten, razonamiento multi-hop, documentos reales ni variación entre ejecuciones. El 10/10 es **screening**, no garantía universal de calidad a ese tamaño.
- 512K y 1M usan YaRN ×2/×4 desde contexto original 262.144; los resultados describen esa extensión y configuración, no un millón de tokens nativos.
- Las TPS se midieron aquí con 209 tokens de salida, mientras que el barrido previo produjo 64 tokens. No mezclar ambos resultados como un A/B directo de decode; el tiempo y las cifras de prefill se informan para cada corrida.
- ASTRA DEFAULT conserva el límite productivo de **131.072 tokens**. Esta prueba no modifica perfiles.

## Configuración y reproducibilidad

Modelo ISTA-DASLab Qwen3.8-Flash-Next-GSQ-RCO IQ2_XS, revisión `ed59f92082b1e93c0e96d60a8b11aab089b52f09`; shards SHA-256 `92cee27ae5bbadcd732416a0f7a7f0acc092399dbbe8f5a5efa707c2ec0a49d7` y `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`. Strata 0.1.41, commit `fb58e0dbc8399662c0e47c76578c6e878b14f6cf`, binario SHA-256 `770ecf303a4c6271654339c639392ecb455de3a999bf5d2e8dbc73c879103602`; 2×RTX 3090; KV int8, KV-resident 32768, spec4, MTP4, prefill/expert cache auto. Sampling de request: temperature 0, top_p 1, top_k 20, seed 4242, thinking off, `cache_prompt=false`, `max_tokens=768`.

La suite reutilizó byte por byte los cuatro fixtures del probe de rendimiento anterior, que sólo generó 64 tokens y no había calificado las agujas; esta campaña registró las respuestas completas. Hashes, fingerprints normalizados, configs, preflights y contexto de cada needle están en [manifiesto](receipts/effective-profile-manifest.json).

- [Plan preregistrado](PLAN.md)
- [Resumen por contexto](receipts/summary.json)
- [Preflight](receipts/preflight.json) y [postflight](receipts/postflight-cleanup.json)
- Prompts, claves esperadas, request/response crudos, logs y monitor: `fixtures/` y `receipts/runs/`
