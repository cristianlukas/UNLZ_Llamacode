# Q197 — resultados

**Preregistrado:** 2026-11-02T22:40:02Z. **Estado:** pausado por el usuario antes del primer request; no hay resultado de inferencia.

La prueba es un único smoke Chat Completions dual 8K con `reasoning_effort="none"`, cap 32 y respuesta visible `PONG`, definido en `PLAN.md`. Sólo pasa con salida exacta, finish normal, cero tokens de reasoning, asignación/uso de ambas 3090 y sin faults. No es medición Q173 ni de calidad.


## Preflight 1 — no request sent (2026-11-02T22:42:16Z)

Los gates de servicios/hardware/RAM/discos pasan: no hay servidor de inferencia, compute app ni listener 18503; PeritoSoft web sigue en 32100, sin compute visible, intacto; ASUS retiene 1636/1636 frames; P2P read/write bidireccional OK; `gpu_unlock` y boot verifier PASS en ambos PCI; MemAvailable y discos por encima de pisos. No hay nuevos faults de kernel desde el inicio Q195; se conserva como baseline el historial GPU1 previo del 1 de noviembre. El archivo actual coincide byte por byte con el SHA Q190/Q193 correcto `3e33297645dc33557751be1a3c407a74ed7c00f34909b5d4e8cfdce91b3dbe84`.

La compuerta se detuvo por un error de transcripción en el SHA incluido en el preregistro Q197 (62 caracteres, no 64), no por cambio del peso. Corregí el preregistro en Amendment 01 y lo dejaré sincronizado en Sheets; aún no hubo arranque/request/carga de modelo. Se repetirá el preflight completo con el SHA corregido antes de lanzar. Evidencia: `receipts/preflight-initial-q197-20261102.json`, `receipts/prereg-amendment-01-model-sha.json`.

## Arranque detenido por solicitud del usuario — 2026-11-02T22:45:00Z

El segundo preflight (con SHA correcto) pasó a las 22:43:10Z. A continuación se inició el `ninfer-serve` preregistrado en `127.0.0.1:18503` con `--devices 0,1`, 8K, KV `rk4v4` y el resto de los argumentos del plan. Los logs muestran pesos listos en 12,3 s, contexto host de 8 GiB fijado, CUDA graphs listos y engine listo en 23,5 s; el log reportó `stages | 2 devices`. El servidor quedó escuchando 45,2 s desde el arranque y luego recibió SIGINT por la solicitud de pausa del usuario.

No se consultaron `/health` ni `/v1/models` y no se envió el prompt PONG: **el smoke no se ejecutó y no tiene PASS/FAIL**. No se obtuvo un model ID ni tokens, score, TTFT, prefill/decode TPS o resultado de calidad. La duración de carga no debe rellenar métricas Q173, init cold/hot ni Q172. El proceso terminó limpiamente según `server.log`; postflight confirmó sin listener en 18503, sin `ninfer-serve` y sin CUDA compute processes. No se revisó el journal del kernel después de esta carga, así que el estado de faults posteriores queda sin determinar. PeritoSoft/GUI y procesos ajenos quedaron intactos.

Métricas Q190 se conservan sin cambios. Q173 y Q172 no iniciaron. Reanudación: seguir el procedimiento de `PLAN.md` desde un lock nuevo y un preflight fresco; mantener un solo smoke sin retry. Recibo de pausa: `receipts/pause-point-q197-20261102.json`.
