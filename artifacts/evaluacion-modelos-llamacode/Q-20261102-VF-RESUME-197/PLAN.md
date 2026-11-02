# Q197 — smoke dual con reasoning desactivado (NInfer-3090 v0.17.1)

**Estado actual:** PAUSADO por pedido del usuario después de un smoke único PASS bajo continuación Q198. Q173, cold/hot y Q172 pendientes; no hay prueba activa ni servidor propio. El bloque de pausa histórico y su detalle se conservan abajo.

## Pregunta

¿El smoke Qwen3.6 dual anterior falló porque Chat Completions dedicó todo el límite de `max_tokens` al canal de reasoning? Q194/Q195 cargaron el modelo en ambas GPUs y devolvieron HTTP 200, pero la respuesta visible fue vacía; Q195 usó 128 tokens, todos reasoning, con `finish_reason=length`. La hipótesis es plausible, no está probada.

## Evidencia que motiva el cambio

- La ayuda del binario local NInfer-3090 `0.17.1-rtx3090` lista opciones para reasoning (`--no-thinking`, `--default-thinking-budget`, `--reasoning-loop`, `--reasoning-effort`). El request-level `reasoning_effort="none"` está documentado upstream en la versión fijada para deshabilitar thinking en Chat Completions.
- Fuente primaria fijada: https://github.com/ashalliants/ninfer-3090/blob/v0.17.1-rtx3090/docs/serving.md (sección Chat Completions, `reasoning_effort`).
- Q196 fue sólo investigación read-only; ningún request ni GPU. Q197 es el primer experimento que prueba la hipótesis.

## Artefactos fijos

- Modelo existente, sin copia ni modificación: `/media/cristian/Disco local/Modelos-eval/Qwen3.6-35B-A3B-NInfer-all-20261101/qwen3_6_35b_a3b.ninfer`, 22,790,484,480 bytes, SHA-256 `3e33297645dc33557751be1a3c407a74ed7c00f34909b5d4e8cfdce91b3dbe84`.
- Binario existente: `/media/cristian/Disco local/Modelos-eval/Qwen3.6-35B-A3B-NInfer-all-20261101/runtime-ninfer-3090-v0.17.1/ninfer-serve`, 787,854,768 bytes, SHA-256 `ae49d7912564cd1f942fbe6d28b70bdb60dc109a7cbf3d9e61267085f4a4ff9b`.
- Hardware objetivo: 2×RTX 3090, pipeline NInfer `--devices 0,1`. No TP. Mismos pesos y flags base de Q193; 8K contexto y KV.

## Procedimiento exacto

1. Antes del primer proceso, hacer preflight live: lock Q197 propio, procesos/puertos de inferencia ausentes (PeritoSoft web en 32100 no es un motor de inferencia; dejarlo intacto), GPUs 0/1 y sus PCI IDs visibles, quarantine ASUS en 1636/1636 frames, P2P bidireccional, `gpu_unlock` en ambos targets, helper verifier OK, cero faults nuevos, `MemAvailable >= 32 GiB`, raíz `>=2,000,000,000 B`, D `>=10 GB`, HDD extra `>=20 GB`, puerto 18503 libre, y tamaños/SHA exactos de ambos artefactos. Cualquier gate FAIL bloquea antes de arrancar el runtime.
2. Arrancar el mismo comando directo Q193, sólo `<context>=8192`: `ninfer-serve MODEL --host 127.0.0.1 --port 18503 --devices 0,1 --max-concurrency 1 --max-context 8192 --kv-capacity 8192 --kv-dtype rk4v4 --spec mtp --draft-tokens 3 --lm-head-draft --mtp-experts-q4 --gdn-state-fp16 --prefill-cublas --prefill-chunk 4096 --vision --vision-residency overlay --host-context-mib 8192 --min-p 0.03 --presence-penalty 0.5`.
3. Esperar `engine ready`, verificar logs que asignan etapas a GPU0/GPU1 y registrar PID/VRAM de ambas. GET `/health`; GET `/v1/models` y usar exactamente el único model ID anunciado en el request. No hacer otras generaciones.
4. Un solo POST `http://127.0.0.1:18503/v1/chat/completions`: mensaje de usuario `Respond exactly PONG and nothing else.`, `temperature=0`, `max_tokens=32`, `reasoning_effort="none"`, `stream=false`.
5. **PASS** sólo si HTTP 200, contenido visible tras trim exactamente `PONG`, `finish_reason=stop`, reasoning tokens 0, logs confirman dos devices/etapas y el PID propio aparece usando ambas GPUs; sin Xid/OOM/CUDA fault. **FAIL** ante rechazo del campo, contenido vacío/distinto, finish reason distinto, GPU unilateral o cualquier fault. Una sola solicitud; sin retries. Registrar el cuerpo completo saneado, tiempos, uso/razonamiento, inicio e IDs.
6. Detener sólo el servidor Q197 iniciado por esta prueba y hacer postflight: sin proceso/compute/listener 18503 y cero faults nuevos. Luego actualizar y releer el Sheet, `RESULTS.md`, recibos y `WORK_QUEUE.md` antes de decidir la siguiente etapa.

## Punto de pausa — 2026-11-02

El preflight completo corregido pasó a las 22:43:10Z. Se arrancó el binario fijado a las 19:43:52.336 -03 (22:43:52.336Z); cargó los pesos y el contexto, anunció `engine ready` a las 19:44:15.824 -03 (22:44:15.824Z), con `stages | 2 devices`, y escuchó en loopback `127.0.0.1:18503` desde las 19:44:15.910 -03. A pedido del usuario, se interrumpió con SIGINT a las 19:45:00.232 -03 (22:45:00.232Z), antes de `/health`, `/v1/models` o cualquier generación. Por tanto, no hay resultado del smoke ni métricas Q173/Q172 nuevas; el inicio/carga de 23,5 s sólo es telemetría de arranque, no un test comparable ni una métrica de inventario.

Postflight inmediato: el log dice `server stopped`; `ss` no muestra listener 18503; `nvidia-smi --query-compute-apps` no devolvió procesos de cómputo; `ps` no devolvió `ninfer-serve`. No se hizo una nueva lectura de faults del kernel después de esta carga; no afirmar cero faults nuevos para este intento. GUI y procesos ajenos no fueron tocados. El log original permanece en `.../runtime-ninfer-3090-v0.17.1/q197/server.log`.

Al reanudar: reclamar un lock nuevo, volver a leer AGENTS/README/WORK_QUEUE, repetir el preflight completo y sincronizar/readback del Sheet. Si todo pasa, volver a arrancar exactamente el artefacto y flags de este plan, comprobar readiness y el único model ID, y entonces enviar una sola vez el smoke `reasoning_effort="none"`. No ejecutar retries. Si pasa, registrar/sincronizar antes de considerar la ladder Q173 (hasta 261888) y luego Q172; si falla, parar esa rama y mantener Q190 intacto. Este punto de pausa no autoriza iniciar nada automáticamente.

## Estado posterior de la reanudación Q198

El smoke se ejecutó una vez y pasó; el detalle exacto y los límites están en `RESULTS.md` y `receipts/smoke-result-q197-q198.json`. Próxima etapa: continuar el preregistro Q173 existente en Q193 (8K×3, 32K, 64K, 128K y máximo 261888; sin 523K), serialmente y sincronizando/leyendo el Sheet después de cada tramo. Q172 normal de tres semillas espera a que Q173 cierre. Mantener Q190 y el perfil productivo sin cambios.

## Pausa solicitada — continuación Q198 — 2026-11-02T22:55:16Z

El usuario pidió pausar las pruebas, liberar el lock y registrar el estado para retomarlo después. Q197 smoke permanece **PASS**; no se inició Q173, la medición cold/hot pendiente ni Q172. El servidor del smoke ya está detenido, el puerto 18503 está libre y no queda proceso `ninfer-serve` propio. Se actualizó y leyó de vuelta el Sheet antes de cerrar esta pausa. Se libera únicamente el lock `Q-20261102-VF-RESUME-198`; no tocar locks de otras tareas.

Al reanudar: adquirir un lock exclusivo nuevo; releer AGENTS.md, README.md y WORK_QUEUE.md; repetir todos los gates live (servicios, GPU0/1, cuarentena ASUS, P2P, gpu_unlock/helper, faults, RAM, espacio, hashes y puerto); luego continuar desde Q173 preregistrado, sin copiar ni modificar pesos, usando pipeline `--devices 0,1`, serial, contexto máximo 261888 y sin 523K. Medir cold/hot y Q173 con 8192×3, 32768, 65536, 131072 y 261888; actualizar y leer de vuelta Resultados/Modelos locales por peso tras cada hito. Sólo al cerrar Q173 ejecutar Q172 seeds 42/43/44 en serie, actualizando Accionables/inventario después de cada semilla. Mantener métricas Q190 independientes e intactas. Checkpoint estructurado: `receipts/pause-point-q198-20261102.json`.

## Límites y secuencia después del smoke

`reasoning_effort="none"` es **sólo para el gate visible del smoke**. No cambiar la configuración normal de Q172, ni alterar el procedimiento Q173. Q173 ya está preregistrado en Q193 y usa su ruta completion/ladder hasta 261888, sin 523K; sólo queda habilitado si este smoke pasa y el resultado se sincroniza. Después, Q172 Tool-Eval 2.8.0 seeds 42/43/44 se ejecuta serialmente con configuración normal; cada hito actualiza el Sheet antes de avanzar. Q190 NInfer-all v3 (D:F/Z en la pestaña de inventario) es un perfil/runtime distinto y no se sobrescribe con Q197.
