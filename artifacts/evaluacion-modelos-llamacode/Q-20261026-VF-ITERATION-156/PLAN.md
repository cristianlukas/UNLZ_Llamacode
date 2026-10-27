# Q156 · Gyro-M TQ2_0 vs ASTRA RCO IQ2_XS · dual-RTX-3090 Flash-Next screen

**Preregistrado:** 2026-10-27 00:03:53 UTC  
**Lock umbrella:** Q146, token `2242863e-c78e-4fa9-9649-c1d1541f3919`  
**Estado inicial:** candidato aún no descargado; no hay score local.

## Pregunta

¿Gyro-M, una variante Gyro cuantizada de Qwen3.8 Flash-Next, consigue una mejora reproducible de calidad en coding y después una ventaja de tiempo de respuesta frente al perfil ASTRA RCO IQ2_XS, usando **las dos RTX 3090 y 128 GiB de RAM**?

El model card de AgentionAI estima Gyro-M en calidad cercana a IQ3_XXS y ~35 GB de memoria de pesos; Strata advierte que Gyro-M no es una opción por defecto y que el prefill de Gyro no se reparte al segundo GPU. Son claims/documentación del proyecto, no mediciones de esta máquina. La prueba usa el split dual para alojar/ejecutar el modelo en las dos tarjetas; no asume que eso acelere el prefill.

## Artefactos fijados

- Repositorio: `agentionai/Qwen3.8-Flash-Next-Gyro-GGUF`, revisión inmutable `1ada08422e404aca51ab9df665f089f34c419c6b`.
- GGUF: `Qwen3.8-Flash-Next-Gyro-M-TQ2_0.gguf`, 91,965,774,272 bytes, SHA-256/LFS `7aa36d15131d255179ab6c87fa9c9f81a0b541fc9e81e959d4c3e29eb20feb5f`. HEAD a la revisión fijada devolvió el mismo tamaño y ETag.
- Destino de evaluación aislado: `/media/cristian/Disco local/Models-eval/Q156-gyro-m/`; no tocar roots productivos ni PeritoSoft. El preflight mostró 498,122,457,088 B libres en D; descargar sólo si quedan ≥180 GB antes de empezar.
- Motor: Strata Control 0.1.51, CUDA engine 0.1.50, ya presente y verificado en Q153/Q154. El setup local exige Gyro engine ≥0.1.45.1; el engine fijado satisface el mínimo. No instalar ni sustituir el runtime global.
- Control ASTRA: Qwen3.8 Flash-Next RCO IQ2_XS, mismos archivos y configuración de Q154/Q97; reejecutar con Control 0.1.51/engine 0.1.50 para evitar comparar sólo con el runtime histórico Q97.
- Hardware obligatorio: GPUs 0 y 1, ambas RTX 3090; 128 GiB RAM. Si el proceso dueño no asigna compute/memoria a las dos tarjetas, parar antes de puntuar. **No hay fallback de una GPU.**
- Perfil pareado de caché neutral Q154, SHA-256 `b3e62120218cd96d175a0547530158869177dd2164b22b40f32bea7d7e85fb8c`, para ambos brazos.
- El protocolo usa MTP4 y el mismo head/draft Qwen3.8 compartido, contexto 8,192, prefill fijo de 8,192, KV int8/resident 32,768, split automático, una petición, orden serial. La corrección del prefill quedó enmendada antes de inferencia para igualar el control Q154. Antes de descargar se validará que Gyro-M y ASTRA resuelven el mismo artefacto MTP y que el setup aislado permite desactivar cualquier salida externa. Si no se puede mantener el runtime y el perfil pareados, registrar bloqueo en vez de improvisar otro perfil.
- Sampling coding: temp 0.6, top-p 0.95, top-k 20, min-p 0, repeat penalty 1.0, presence penalty 0, thinking on y presupuesto 2,048; máximo 6,144 tokens.
- Fixture `artifacts/bigcodebench-hard-ubuntu-8.json`, SHA-256 `11279cde14113fc8527f141c53e14cb5ccf0dba65749081a4f914408e391c268`; runner base Q89 SHA-256 `0760f48da5f1804d8605960b7ff913308182f911a35a906313b864a9cff9bf7f`. El runner Q156 etiquetará correctamente ambos brazos y conservará los artefactos crudos.

## Secuencia y gates

1. Verificar de nuevo lock propio, procesos/puertos de inferencia, driver, GPUs, RAM, PSI, OOM y espacio. Terminar sólo PeritoSoft/llama-server atribuibles a esas aplicaciones si aparecen; en el chequeo de 2026-10-27 00:03 UTC no aparecieron procesos, listeners ni contenedores que terminar.
2. Ejecutar el preflight/plan de Strata sin iniciar servidor y verificar `--gpu 0,1`, capas divididas, MTP4, perfiles y rutas exactas. Ambos planes offline pasaron antes de reanudar la descarga. Tras preparar el pack se repetirá el plan; no iniciar si hay fallback, runtime distinto o no se confirma split dual. Guardar fingerprints de fixture, runner, configs, modelo, packs, MTP y runtime.
3. Descargar el GGUF fijado en la carpeta aislada, calcular SHA-256 completo y validar tamaño exacto antes de empaquetar o arrancar servidor. No se escribe en roots de modelos de LlamaCode ni PeritoSoft.
4. Cargar ASTRA primero y Gyro después, un servidor y una inferencia a la vez. Exigir proceso de inferencia propio en ambas GPUs. Ejecutar BCB-Hard-8 seed 4242 con misma fixture, mismo runner, sampling y máximo. Registrar transport, score, tests aprobados, salida vacía, errores de sandbox, tokens, prefill/decode, E2E, tiempo de carga, RAM/PSI/swap/OOM y VRAM.
5. El screen sólo abre una campaña más amplia si Gyro-M obtiene **≥4/8 y al menos 2 casos más que el ASTRA reejecutado**, con 8/8 transportes, cero errores de sandbox y cero respuestas vacías. Cualquier fallo de runtime no se etiqueta como mala calidad.
6. Si pasa, antes de otra carga se añadirá una enmienda preregistrada para 3 semillas emparejadas de calidad y una serie separada de throughput (4K/16K/32K, 3 repeticiones por tamaño y brazo). No combinar suites; no calcular un score artificial de “inteligencia/velocidad”. Para considerar un perfil rápido se exigirá calidad no inferior, cero regresiones críticas y ≥15% menor mediana E2E en tareas correctas. La adopción para agentes requiere además un gate Tool-Eval de acciones y seguridad; Q154 dejó TC-92 pendiente en ambos perfiles.
7. Si el screen falla, detener la campaña y no afirmar que Gyro-M es peor de forma general. Retirar el GGUF descargado sólo si la verificación final confirma hash exacto, link count 1 y ausencia de consumidores; conservar packs compartidos, ASTRA, SOL, resultados y recibos. PeritoSoft no es consumidor autorizado para este experimento.

## Política de memoria y limpieza

No aplicar MemoryMax/MemoryHigh/MemorySwapMax ni límites artificiales de RAM/VRAM. RSS, swap usado, uso gráfico de GPU y PSI moderada son observaciones, no motivos de aborto. Hard stop sólo por servicio fallido, OOM nuevo confirmado, MemAvailable <32 GiB, PSI global full ≥60% o some ≥80% durante 15 muestras de 10 s, puerto/proceso que no se limpia o interrupción del usuario. Registrar el alto uso exitoso histórico de ASTRA 1M/SOL como contexto; no presentar esta prueba como diagnóstico de crashes de Codex.

## Lecturas primarias consultadas

- [AgentionAI Gyro GGUF model card, revision pinned](https://huggingface.co/agentionai/Qwen3.8-Flash-Next-Gyro-GGUF/tree/1ada08422e404aca51ab9df665f089f34c419c6b)
- [Strata Gyro guide](https://github.com/Niko1221/Strata/blob/main/docs/GYRO.md)
- [Strata multi-GPU layer split guide](https://github.com/Niko1221/Strata/blob/main/docs/MULTI_GPU.md)
- Q97 baseline and matched-fixture precedent: `artifacts/evaluacion-modelos-llamacode/Q-20261024-VF-ITERATION-97/RESULTS.md`.
- Local Gyro support: Q153 Strata Control 0.1.51 `setup.py`, `data/gguf_fingerprints.json`, and `strata_control/models.py`.

## Enmienda previa a inferencia (2026-10-27T01:12:27Z)

La inspección de la ayuda del engine fijado mostró que `--max-new` es el límite de tokens de generación. Ambos configs aún indicaban 256 mientras el runner solicita `max_tokens=6144`; habría reducido silenciosamente la salida máxima frente al protocolo preregistrado. Antes de cualquier request, se actualizaron ambos perfiles de 256 a 6,144 de forma simétrica y se repitieron los dos planes offline. Ambos devolvieron `ok=true`, `notes=[]` y `--max-new 6144`. Se actualizó el fingerprint de configs y se fijaron los hashes del pack y tokenizer generado en el preregistro.

**Descarga y artefactos:** tamaño/SHA del GGUF coinciden con el pin; pack generado y hash independiente de `dense.bin` coincide con el recibo local. Los planes finales pasaron. Ningún server ni request de inferencia se inició durante esta preparación.

## Remediación del grader antes de repetir (2026-10-27T01:24:42Z)

El primer intento se detuvo después del brazo ASTRA: 8/8 respuestas llegaron por HTTP, pero 8/8 fallaron al arrancar el grader. La traza exacta dice que `bwrap` no encuentra el intérprete Q156 bajo `/media`; el namespace crea `--tmpfs /media`, por lo que la ruta no existe dentro del sandbox. Esto invalida la puntuación, no evalúa calidad del modelo. Gyro-M no se inició y el supervisor liberó GPUs/puerto.

**Plan preregistrado:** ejecutar un smoke sólo de CPU con `bwrap`+seccomp usando `/usr/bin/python3`, visible bajo `/usr` dentro del sandbox; fijar ruta resuelta y SHA del binario, cambiar el runner y actualizar su fingerprint; repetir la comparación completa con ASTRA primero y Gyro-M después. El resultado previo queda preservado sólo como diagnóstico y no se incorpora a `Resultados`.

## Corrección validada del grader (2026-10-27T01:25:49Z)

- Se cambió el intérprete del grader a `/usr/bin/python3`, visible dentro del namespace; el archivo resuelve a `/usr/bin/python3.12`, SHA-256 `e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f`.
- El smoke reprodujo el mismo `bwrap`+seccomp, incluido `--tmpfs /media`, y ejecutó `sandbox-smoke-ok /usr/bin/python3` con código 0. No hizo inferencia ni usó GPU.
- Runner actualizado y fingerprint fijado: `6cccb15ec423d0917eb6aaa4c05d00b56809e190175b4c3c415ed9cd086d3637`.
- Siguiente: repetir el par completo desde ASTRA y después Gyro-M; el intento anterior queda invalidado para calidad.
