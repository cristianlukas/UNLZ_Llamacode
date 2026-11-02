# Q197 — resultados

**Preregistrado:** 2026-11-02T22:40:02Z. **Estado actual:** PAUSADO por el usuario tras el smoke PASS en la reanudación Q198; ladder Q173, cold/hot y Q172 siguen pendientes.

La prueba es un único smoke Chat Completions dual 8K con `reasoning_effort="none"`, cap 32 y respuesta visible `PONG`, definido en `PLAN.md`. Sólo pasa con salida exacta, finish normal, cero tokens de reasoning, asignación/uso de ambas 3090 y sin faults. No es medición Q173 ni de calidad.


## Preflight 1 — no request sent (2026-11-02T22:42:16Z)

Los gates de servicios/hardware/RAM/discos pasan: no hay servidor de inferencia, compute app ni listener 18503; PeritoSoft web sigue en 32100, sin compute visible, intacto; ASUS retiene 1636/1636 frames; P2P read/write bidireccional OK; `gpu_unlock` y boot verifier PASS en ambos PCI; MemAvailable y discos por encima de pisos. No hay nuevos faults de kernel desde el inicio Q195; se conserva como baseline el historial GPU1 previo del 1 de noviembre. El archivo actual coincide byte por byte con el SHA Q190/Q193 correcto `3e33297645dc33557751be1a3c407a74ed7c00f34909b5d4e8cfdce91b3dbe84`.

La compuerta se detuvo por un error de transcripción en el SHA incluido en el preregistro Q197 (62 caracteres, no 64), no por cambio del peso. Corregí el preregistro en Amendment 01 y lo dejaré sincronizado en Sheets; aún no hubo arranque/request/carga de modelo. Se repetirá el preflight completo con el SHA corregido antes de lanzar. Evidencia: `receipts/preflight-initial-q197-20261102.json`, `receipts/prereg-amendment-01-model-sha.json`.

## Arranque detenido por solicitud del usuario — 2026-11-02T22:45:00Z

El segundo preflight (con SHA correcto) pasó a las 22:43:10Z. A continuación se inició el `ninfer-serve` preregistrado en `127.0.0.1:18503` con `--devices 0,1`, 8K, KV `rk4v4` y el resto de los argumentos del plan. Los logs muestran pesos listos en 12,3 s, contexto host de 8 GiB fijado, CUDA graphs listos y engine listo en 23,5 s; el log reportó `stages | 2 devices`. El servidor quedó escuchando 45,2 s desde el arranque y luego recibió SIGINT por la solicitud de pausa del usuario.

No se consultaron `/health` ni `/v1/models` y no se envió el prompt PONG: **el smoke no se ejecutó y no tiene PASS/FAIL**. No se obtuvo un model ID ni tokens, score, TTFT, prefill/decode TPS o resultado de calidad. La duración de carga no debe rellenar métricas Q173, init cold/hot ni Q172. El proceso terminó limpiamente según `server.log`; postflight confirmó sin listener en 18503, sin `ninfer-serve` y sin CUDA compute processes. No se revisó el journal del kernel después de esta carga, así que el estado de faults posteriores queda sin determinar. PeritoSoft/GUI y procesos ajenos quedaron intactos.

Métricas Q190 se conservan sin cambios. Q173 y Q172 no iniciaron. Reanudación: seguir el procedimiento de `PLAN.md` desde un lock nuevo y un preflight fresco; mantener un solo smoke sin retry. Recibo de pausa: `receipts/pause-point-q197-20261102.json`.

## Reanudación Q198 — smoke único PASS — 2026-11-02T22:52:57Z

Con lock Q198, el preflight completo fue repetido inmediatamente. Sin inference server/CUDA compute previo y 18503 libre; cuarentena ASUS 1636/1636; P2P read/write OK ambas direcciones; `gpu_unlock` y verificador de arranque PASS en las dos RTX 3090; RAM/discos por encima de mínimos; hashes y tamaños del modelo/runtime exactos; sin faults nuevos desde el inicio Q195. El proceso PID 1997147 llegó a `engine ready` en 20,5 s y la telemetría `nvidia-smi` lo mostró usando GPU0/GPU1 con 11.756/10.258 MiB. Logs reportaron dos dispositivos/etapas.

Se hizo **una** petición, sin retry: Chat Completions 8K, `reasoning_effort="none"`, `temperature=0`, `max_tokens=32`, prompt “Respond exactly PONG and nothing else.” Health/model GET dieron HTTP 200 y el único model ID `qwen3.6-35b-a3b`. La petición respondió HTTP 200, contenido exacto `PONG`, `finish_reason=stop`, cero reasoning tokens, `20` prompt tokens, `3` completion tokens y `23` totales. El cliente tardó 98,29 ms; el servidor informó TTFT 79,0 ms, total 88,3 ms, prefill 422,5 tok/s y decode 216,6 tok/s; MTP aceptó 3/3. Las tasas corresponden a un fixture de 20/3 tokens y son diagnósticas, **no** ladder ni promedios. El init de 20,5 s tampoco se mezcla con cold/hot anteriores.

**Gate smoke PASS.** El servidor propio se detuvo con SIGINT; `server stopped`, proceso/listener 18503 y CUDA compute apps ausentes; ninguna Xid nueva desde el preflight. PeritoSoft/GUI quedaron intactos. El Sheet se sincronizó y leyó de vuelta antes de seguir; Q190 D:F/Z siguen idénticos. El PASS habilita la siguiente etapa ya preregistrada Q173 hasta 261888; Q172 viene después, sólo tras completar y sincronizar la ladder. No usar 523K. Receipt completo: `receipts/smoke-result-q197-q198.json`; log íntegro: `receipts/q197-server-q198.log`.

## Pausa solicitada — 2026-11-02T22:55:16Z

El usuario solicitó pausar las pruebas, liberar el lock y dejar un punto de reanudación. No se inició ningún test después del smoke ya documentado. El servidor propio está detenido; no hay proceso NInfer, listener en 18503 ni CUDA compute app de esta campaña. Q173 (incluida medición cold/hot) y Q172 permanecen pendientes según el orden preregistrado; no correr 523K. El estado fue sincronizado y leído de vuelta en Google Sheets antes de liberar sólo el lock Q198.

Para continuar: lock nuevo y preflight completo; luego Q173 serial a 8K×3, 32K, 64K, 128K y 261888, salida de 128 tokens, registrar TTFT/P/D/init y actualizar/readback de Sheets tras cada hito. Después Q172 seeds 42/43/44, 28 escenarios cada una, timeout 120 s y `fail_on_safety`, una por vez. Mantener Q190 como perfil/runtime independiente. Checkpoint estructurado: `receipts/pause-point-q198-20261102.json`.
