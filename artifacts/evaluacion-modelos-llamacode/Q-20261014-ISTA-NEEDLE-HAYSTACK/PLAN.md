# Plan — Needle in a Haystack para ISTA IQ2_XS

**ID:** `Q-20261014-ISTA-NEEDLE-HAYSTACK`  
**Estado:** completada; screening de recuperación con cuatro corridas válidas en serie  
**Lock:** `f6c151ae-dcad-4954-ade7-e50f71031839`  

## Pregunta y criterio preregistrado

Medir si ISTA IQ2_XS recupera hechos exactos sembrados a lo largo del contexto a 131.072, 262.144, 524.288 y 1.048.576 tokens. En cada tamaño se usa el mismo fixture de diez hechos, con agujas distribuidas aproximadamente entre 5% y 95% del prompt. Las respuestas se califican por coincidencia exacta de cada valor, 0–10; un valor omitido o normalizado incorrectamente cuenta como fallo de ese hecho. Se reporta también la posición real de cada aguja.

Una corrida es **válida de calidad** si el servidor acepta el prompt al tamaño previsto (≥95% del límite), responde HTTP 200, termina normalmente (`finish_reason=stop`) y completa el transporte. Una respuesta normal con errores de contenido sí se puntúa como calidad. Timeout, OOM, caída del servidor, prompt truncado, respuesta limitada o error de transporte se clasifica como **inválida por infraestructura** o **incompleta**, nunca como score cero. Un JSON mal formado con respuesta completa se conserva y puntúa 0 en las claves que no puedan verificarse. Una sola corrida por tamaño es screening, no una afirmación de estabilidad.

## Perfil y protocolo

- Perfil: ASTRA DEFAULT / ISTA-DASLab Qwen3.8-Flash-Next-GSQ-RCO IQ2_XS, Strata 0.1.41, mismo runtime, GGUF, tokenizer, MTP y perfil del sweep `Q-20261014-ISTA-CONTEXT-SWEEP`.
- Runtime binario SHA-256 `770ecf303a4c6271654339c639392ecb455de3a999bf5d2e8dbc73c879103602`; commit `fb58e0dbc8399662c0e47c76578c6e878b14f6cf`; perfil productivo base SHA-256 `b4b83171c136d8cb4b1944de532c096276844da5a2cd987d1d1517dd0a73b484`.
- Pesos: revisión `ed59f92082b1e93c0e96d60a8b11aab089b52f09`; shards con SHA-256 `92cee27ae5bbadcd732416a0f7a7f0acc092399dbbe8f5a5efa707c2ec0a49d7` y `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`.
- Dos RTX 3090, Strata en serie, una solicitud por servidor; KV int8, KV-resident 32768, spec4, MTP del mismo bundle, caché/prefill auto, `cache_prompt=false`.
- Contextos: 131K nativo, 262K nativo, 512K YaRN ×2 (origen 262144), 1M YaRN ×4 (origen 262144). En cada punto sólo cambia el límite/escala y la ruta de logs.
- Requests: exactamente el prompt y las agujas ya fijados en el probe de rendimiento previo (allí la respuesta se cortó a 64 tokens y nunca se puntuó); el presente test solicita JSON completo, `max_tokens=768`, temperature 0, top_p 1, top_k 20, seed 4242, thinking desactivado. La respuesta termina sólo cuando el modelo completa el JSON.
- Por corrida se registran tokens de prompt/salida, score exacto, posiciones, prefill/decode, TTFT, duración de request y sesión, RSS pico del árbol del proceso, MemAvailable mínimo, VRAM pico/base/delta por GPU, PSI y deltas globales de swap. El monitor conserva muestras de 1 s.

## Ejecución y seguridad

Orden ascendente 131K → 262K → 512K → 1M; reiniciar el servidor entre configuraciones. Antes de cada carga, exigir al menos 32 GiB MemAvailable, puertos 8350/8898 libres y ausencia de otro proceso de inferencia. No detener procesos ajenos ni vaciar swap. Monitor: abortar este proceso de prueba si MemAvailable <20 GiB, swap-out global >4 MiB o PSI sostenida `some avg10 ≥80%` / `full avg10 ≥60%` durante 15 muestras. Timeout duro de 15 minutos por punto. Cada aborto y reintento se conserva.

El preflight de `receipts/preflight.json` observó 112.963.000 kB MemAvailable, PSI 0, sin proceso compute ni listener Strata; GPU 0/1 tenían 1088/108 MiB ocupados. `nvidia-smi pmon` atribuyó actividad visible a Xorg/compositor de escritorio; no se identificó servidor de inferencia ajeno. Se mantiene el swap tal como está.

## Artefactos

- `fixtures/<contexto>/`: copia byte por byte de prompt, expected y metadata del sweep previo; no se modifica ese historial.
- `receipts/configs/`: configuraciones efectivas por contexto y hash de la configuración fuente; sólo se redirige el log al directorio de esta tarea.
- `receipts/runs/<contexto>/`: request/response, runner y engine logs, muestras del monitor y recibo de score/memoria/tiempo.
- `receipts/summary.json` y `RESULTS.md`: resumen de las cuatro corridas, límites y conclusión.

No se modifica ASTRA DEFAULT ni se cambian pesos. No se ejecutan builds/tests del producto.
