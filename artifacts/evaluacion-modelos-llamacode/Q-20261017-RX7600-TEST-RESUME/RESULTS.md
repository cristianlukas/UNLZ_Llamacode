# Resultados — Q-20261017-RX7600-TEST-RESUME

**Estado: bloqueada; screening complementario parcial, sin comparación A/B ni promoción.**

## Dictamen

La prueba exacta del post no pudo ejecutarse: este host no confirma una RX 7600/gfx1102, no tiene el GGUF Qwen3.6-35B-A3B Q6_K_XL con MTP y el checkout local de llama.cpp sólo contiene un ejecutable Windows. No se descargó ni compiló nada.

Por pedido del usuario se hizo un screening complementario con el checkpoint Qwen3.6-35B-A3B AutoRound INT4 local y vLLM. Es otro perfil y hardware: sirve para comprobar carga y registrar una muestra local, pero no replica los 23,6→32,0 tok/s del post ni el A/B RX7600/llama.cpp.

## Screening complementario ejecutado

| Paso | Resultado | Clasificación |
|---|---|---|
| Control MTP-off, API smoke | HTTP 200; 0,214 s | Smoke de servicio; sin score de calidad |
| Control MTP-off, warmup 4.100→32 tokens | HTTP 200; 0,794 s | Warmup; no es muestra de velocidad de 320 tokens |
| Control MTP-off, prompt A | 4.100 prompt + 320 tokens; TTFT 0,574 s; tiempo total 2,745 s; decode 147,41 tok/s | Una muestra individual válida de velocidad; no hay mediana ni dispersión |
| Candidato MTP-on, warmup 4.100→32 tokens | HTTP 200; 1,126 s; el modelo y el drafter cargaron en TP2 | Warmup de compatibilidad/carga; no es muestra A/B de velocidad ni de calidad |
| Candidato MTP-on, prompt A | No enviado: la guarda detectó el proceso CUDA externo `wordcraft` (PID 3408627, 207 MiB) y detuvo el servidor de esta tarea | No es resultado del modelo |

Ambos brazos usaron el mismo checkpoint local (manifiesto agregado SHA-256 `c5f5d44459aa29b0851eeb7f320529e67f1a960a404e8373419503fc5c2e757f`), vLLM `v0.27.1`, TP2 sobre 2×RTX 3090 y contexto 32K. La solicitud de velocidad fue greedy, seed 4242, thinking desactivado, prompt A de 4.100 tokens y salida fija de 320. Prompt A SHA-256 `aef3f9c346db7edddf50abf97ebd9a35f9e95b70153d5060fdeb1c3f14e092e7`. La configuración completa y los comandos están en `PLAN.md` y los recibos.

La muestra off-A se conserva y no debe repetirse idéntica. Cuando ambas GPU pasen un preflight sin cómputo CUDA ajeno, se puede emparejar con on-A y continuar con B/C para completar tres pares. El par 1 no cuenta hasta tener ambos brazos.

## Por qué no se completaron las demás pruebas

- No hubo hardware/artefactos para probar el claim exacto de RX 7600 + Q6_K_XL + llama.cpp MTP2.
- La guarda del screening alternativo exige GPUs sin procesos CUDA ajenos. `wordcraft` apareció durante el warmup MTP-on y seguía activo al cerrar; no se lo detuvo. Se apagó únicamente el contenedor propio. El postflight confirma sin contenedor propio, proceso propio o listener en 18051; MemAvailable ≈109,0 GiB y PSI avg10 0.00. La receipt conserva bytes exactos. OOM cgroup no está expuesto en este host.
- No se inició HE0/HE20/BCB8 ni TaskFlow ULTRA: no se completó el A/B ni el gate de runtime previsto para la rama coding. No son ceros ni fallos de calidad.
- Computer Usage, audio/ASR/TTS, visión y contexto largo no se evaluaron. La ruta complementaria es textual; el artefacto/runtime exacto del post no está disponible.

## Decisión y reanudación

No cambiar perfiles, sampling, HarnessSpec ni defaults. La evidencia es inconclusa para la comparación MTP-on/off local y bloqueada por infraestructura para la afirmación RX7600. Reanudar el screening complementario sólo con preflight fresco y ambas GPU sin procesos de inferencia ajenos; retomar desde el control off-A ya guardado. Reanudar la reproducción del post cuando estén disponibles simultáneamente la RX 7600/gfx1102, el Q6_K_XL+MTP íntegro y el build Linux de llama.cpp fijado.

## Evidencia

- Plan preregistrado y receta: `PLAN.md`.
- Inventario inicial, pesos y hardware: `receipts/current-preflight.json` y `receipts/preflight-before-load-off.json`.
- Smoke/warmups: `receipts/smoke-mtp-off.json`, `receipts/warmup-mtp-off.json`, `receipts/warmup-mtp-on.json`.
- Única muestra de velocidad: `receipts/speed-off-A.json`; prompts: `receipts/speed-prompts.json`.
- Detección y apagado propio: `receipts/external-compute-observation.json`, `receipts/vllm-control-command.json`, `receipts/vllm-candidate-command.json` y sus recibos de inicio.
- Estado final: `receipts/postflight-close.json`.
