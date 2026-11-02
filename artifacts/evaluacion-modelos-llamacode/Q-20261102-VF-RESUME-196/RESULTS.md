# Q196 — pausa y punto de reanudación

**Estado:** pausado por pedido explícito del usuario, 2026-11-02 22:36 UTC. No se ejecutó ninguna prueba en Q196.

## Alcance y actividad de esta reanudación

Q196 retomó la investigación del gate de humo de Qwen3.6-35B-A3B con NInfer-3090 v0.17.1, 2×RTX 3090, que quedó bloqueado después del smoke Q195. Se volvieron a leer `AGENTS.md`, `README.md`, `WORK_QUEUE.md` y `WORK_QUEUE.lock`; el lock exclusivo Q196 ya existía y pertenecía a esta tarea. La inspección de procesos/listeners al pausar encontró **ningún `ninfer-serve`, `llama-server` ni listener en 18503**.

Se hizo únicamente revisión local/documental:

- `ninfer-serve --help` local enumera `--no-thinking`, `--default-thinking-budget`, `--reasoning-loop` y `--reasoning-effort`.
- La documentación upstream fijada a NInfer-3090 `v0.17.1-rtx3090` documenta `reasoning_effort: "none"` para deshabilitar thinking en Chat Completions, además de la extensión `thinking_budget`: [serving.md](https://github.com/ashalliants/ninfer-3090/blob/v0.17.1-rtx3090/docs/serving.md).
- Esto es una explicación plausible del smoke Q195: HTTP 200, pero el límite de 128 tokens se consumió completamente en reasoning y `message.content` quedó vacío. **No prueba causalidad** ni demuestra que una opción vaya a resolverlo; Q196 no envió requests.

## Estado heredado que no cambia

- Q195: el pipeline dual cargó el fingerprint verificado de Q190, pero el smoke visible falló: `content` vacío, 128/128 tokens de reasoning, `finish_reason=length`. La muestra de velocidad de ese smoke no es Q173. Q173/Q172 no empezaron.
- Q190 sigue siendo la única fuente de métricas válidas de ese modelo/runtime distinto: NInfer-all v3, P/D/Q172 e init originales quedan intactos en `Modelos locales por peso`; no sobrescribirlos con smoke.
- Ningún peso, runtime, perfil, archivo de configuración o servicio se modificó en Q196. No hubo request, benchmark, build ni uso de GPU.
- El proceso gráfico RustDesk observado durante un chequeo previo es ajeno a inferencia y no se detuvo.

## Punto de reanudación

Mantener la pausa. Al reanudar con lock exclusivo nuevo, preregistrar un gate nuevo antes de inferencia, corregir explícitamente la frase demasiado amplia del plan Q193 sobre mantener idénticas las opciones del smoke en Q173/Q172 y separar protocolos:

1. Repetir los gates live de ASUS quarantine, P2P bidireccional, `gpu_unlock` en ambas PCI, espacio/memoria, faults, hashes de pesos/runtime, procesos y puerto.
2. Habilitar solamente un smoke Chat Completions 8K con el prompt `Respond exactly PONG and nothing else.`, `temperature=0`, `reasoning_effort="none"` y `max_tokens=32`. Requerir HTTP 200, `content` visible `PONG`, fin normal, uso de ambas GPU y ausencia de faults. Si la API rechaza el campo o el contenido no pasa, parar; no encadenar retries sin preregistro.
3. Ese cambio es **sólo del smoke**. No cambiar el protocolo de Q173 (completion ladder ya preregistrada hasta 261888, nunca 523K) ni la configuración normal de Q172 Tool-Eval; mantenerlos separados y registrar el ajuste en un amendment antes de cualquier request.
4. Sólo con smoke PASS, ejecutar Q173 en serie y actualizar/readback del Sheet después del hito; después evaluar si Q172 está habilitado y actualizar/readback tras cada semilla. No usar métricas del smoke como TPS.

La continuación detallada de Q193/Q194/Q195 está enlazada en `../Q-20261102-VF-RESUME-194/PAUSE-POINT-VF-20261019-01-20261102.md` y sus recibos.


## Sincronización documental (2026-11-02T22:37:28Z)

Se actualizó Google Sheets `Listado`: `Accionables!D60,H60:K60,M60:N60` y `Modelos locales por peso!C33,X33`. Readback PASS; Arial 10, WRAP y TOP preservados. Se mantuvieron intactos `Modelos locales por peso!D33:F33/Z33`, que siguen representando únicamente Q190. Receipt `receipts/sheet-sync-pause-q196-20261102.json`.
