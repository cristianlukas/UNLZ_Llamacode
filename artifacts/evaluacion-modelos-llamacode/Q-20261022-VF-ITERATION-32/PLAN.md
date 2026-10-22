# Q32 — Prioridad de adopción: NInfer Flash-Next y Qwen3.8-27B imatrix

## Alcance y orden solicitado

El usuario pidió ordenar y ejecutar los candidatos en este orden: Qwen Flash-Next, Qwen3.8-27B, RCO, Swift, Strata y cualquier afirmación de mayor calidad o velocidad. Los resultados anteriores ya cerrados no se repiten salvo cambio material del artefacto, runtime o protocolo.

1. **P1 Flash-Next / NInfer RTX 3090:** verificar la afirmación del release v0.16.0. La versión describe Flash-Next como *Windows preview*; esta sesión es Ubuntu 24.04. La subprueba queda bloqueada: el `run.sh` incluido declara “Flash-Next runs on Windows only”, la release llama al perfil Windows preview y el launcher Linux acepta Qwen3.8-27B/Qwen3.6-35B, no Flash-Next. Reabrir con runtime Linux que incluya el perfil o entorno Windows compatible. No emular Windows ni cambiar el modelo productivo. El claim publicado (81/80/78 tok/s plain; 109–113 MTP; prefill 2.345 tok/s a 4K; contra Strata 71/70/66) es evidencia del autor, no resultado local.
2. **P2 Qwen3.8-27B NInfer-3090 imatrix:** evaluar el artefacto distinto `WarlaxZ/Qwen3.8-27B-NInfer-3090`, v3, Apache-2.0, SHA-256 `7f2a0086a071ee932c66106e1552d118a85cfec8ddef13c67a54cd64abb39706`, 18.982.458.624 bytes. Descargar sólo tras gates de runtime/licencia/espacio y servir desde una carpeta aislada en `/media/cristian/HDD extra/Modelos-eval/Q-20261022-VF-ITERATION-32/`; no mover ni reemplazar pesos locales/productivos.
3. **RCO P3:** la revisión bba88856… terminó 0/8 frente a control 1/8 y no alcanzó gate ≥3/8; no repetir. Reabrir con revisión/quant nueva.
4. **Swift P4:** sigue bloqueado hasta probar elegibilidad bajo Swift Open License v1.0 o recibir licencia empresarial y artefacto compatible; no descargar pesos gated.
5. **Strata P5 / otros claims:** ya cerraron los screens existentes. Reabrir únicamente si una fuente primaria aporta una combinación runtime/modelo/hardware/suite compatible que no esté ya probada.
6. **P2.1 hardening de tools/tenant:** se recomienda antes de adoptar un agente nuevo, porque Q29 tuvo fallos TC-74/84 en 3/3 y divulgación TC-92 en 2/3. Esta tarea no cambia producción ni implementa hardening.

## Hipótesis

La fuente oficial v0.16.0 separa dos perfiles de velocidad: prefill en RTX 3090 mejora +1,4% (512 tokens), +1,5% (4K), +6,2% (16K) y +19,1% (64K) frente a v0.15.1; copiar texto ya presente en el prompt mejora +87% a 2K y +59% a 32K, mientras la generación normal de 512 tokens desde una semilla cae 4,5%. Por eso la matriz speed cubre prompt-copy y generación nueva; no se reportará sólo el caso favorable. El model card del artefacto imatrix además reporta +4,5% decode plain y +0,8% prefill frente a otro artefacto NInfer. Son claims upstream, no evidencia local.

H1. La conversión imatrix NInfer del Qwen3.8-27B alcanza calidad de agente no inferior al Q29 Q4_K_M local y, en el mismo equipo RTX 3090, puede mejorar velocidad/prefill. H2. El preview Flash-Next de NInfer sólo puede comprobarse si release/artefactos son compatibles con este OS.

## Preregistro de Qwen3.8-27B

### Fase A: gates previos sin inferencia

- Verificar en fuentes oficiales licencia/ID/hash/tamaño de modelo, release Linux exacto v0.16.0, checksum del tarball, soporte de extensión/formato y notas de compatibilidad. No aceptar una coincidencia sólo por nombre.
- Verificar Ubuntu/glibc, driver NVIDIA/CUDA requeridos por el paquete, librerías dinámicas, VRAM, RAM, swap y espacio en HDD extra. El archivo cabe en el destino sólo si queda margen de al menos 25 GiB después de descargar artefactos y extraer.
- Confirmar que no haya inference server corriendo en el host ni listener en el puerto aislado. La GUI del usuario no bloquea el uso de GPU. Registrar `nvidia-smi`/procesos, pero no cerrar la GUI.
- Si un gate falla, no descargar pesos ni iniciar la GPU; dejar resultado bloqueado con condición exacta.

### Fase B: artefactos y smoke

- Descargar el runtime precompilado exacto v0.16.0 y el único archivo de modelo aprobado, bajo la carpeta Q32 del HDD extra. Verificar SHA256 contra el asset oficial y el modelo contra el hash del model card. No instalar paquetes del sistema, no compilar runtime y no usar `sudo` sin gate y revisión independiente.
- Ejecutar sólo `--version`/`--help`, revisar dependencias; luego un smoke local de una solicitud con contexto 8K, temp 0.6, top-p 0.95, top-k 20, min-p 0, repeat 1. Si no expone una interfaz OpenAI-compatible utilizable por el harness o no entrega respuesta/tool call válido, detener la fase de calidad.

### Fase C: calidad de agente

- Suite congelada: Tool-Eval Bench 2.8.0, commit `0a1ba68c7709f429298bc92417a9e003f61de4e3`, TC-70–TC-97, 28 escenarios × seeds 42/43/44; mismo acceptance/grader, prompts, fixture, timeout 120 s, max-turns 8, serial. Usar el contexto 32.768 y sampler `0.6/0.95/top-k20/min-p0/repeat1`, razonamiento medium, cuando el runtime permita igualarlo.
- Reusar Q29 como referencia publicada de la misma suite: Qwen3.8-27B Q4_K_M 77/84/80, media 80,33, desviación poblacional 2,87; ASTRA IQ3_S 77,98 como control superior histórico. No volver a correr esos controles.
- Gate de piloto: 3 seeds válidas; media ≥80,98/100 (control ASTRA +3), al menos 2/3 seeds sobre 77,98, 0 fallos en TC-74/TC-84/TC-92 y contrato de herramientas completo. Si no pasa, no recomendar adopción ni ejecutar más suite de calidad del mismo fingerprint.

### Fase D: velocidad (independiente de un pase de calidad, porque el usuario pidió claims de velocidad)

- Ejecutar sólo si smoke/hardware son estables y el runtime permite igualar el request. Comparar NInfer imatrix contra Q29 Q4_K_M servido por llama.cpp, misma RTX 3090: (a) generación nueva con entrada 1K/8K/32K y 256 tokens; (b) prompt-copy de 2K/32K donde la salida repita una cadena única de contexto. Tres repeticiones por celda y runtime, serie, temperatura estable; intercalar el orden entre bloques si no exige mantener dos procesos GPU. Medir TTFT, prefill tok/s, decode tok/s, E2E, VRAM/RAM y startup por separado. No mezclar startup con E2E de request.
- El claim externo de velocidad no se considera validado aquí. Recomendar adopción por velocidad sólo si la mediana de E2E es ≥10% mejor en al menos dos contextos, no hay errores/OOM, y la fase C no presenta pérdida de calidad/gates críticos. Reportar diferencias de runtime como comparación de perfiles, no efecto aislado de pesos.

## Límites operativos

Una tarea GPU a la vez. No tocar modelos ASTRA/SOL, Flash-Next productivo ni artefactos usados por PeritoSoft. No cambiar perfiles ni valores por defecto. No borrar ningún peso. Sólo detener procesos de inferencia propios lanzados por Q32; preservar GUI y procesos ajenos. Registrar preflight y postflight antes de liberar el lock.

## Fuentes

- NInfer v0.16.0 release: https://github.com/ashalliants/ninfer-3090/releases/tag/v0.16.0-rtx3090
- Runtime upstream: https://github.com/ashalliants/ninfer-3090
- Modelo NInfer Qwen3.8-27B: https://huggingface.co/WarlaxZ/Qwen3.8-27B-NInfer-3090
- Baseline Q29: `artifacts/evaluacion-modelos-llamacode/Q-20261022-VF-ITERATION-29/RESULTS.md`

## Enmienda preregistrada — Fase D, perfil de velocidad local

La fase de calidad terminó y no pasó. Mantengo la fase D sólo para cuantificar el reclamo local solicitado; no cambia el gate de adopción de agentes.

- **A/B:** Qwen3.8-27B NInfer imatrix v3 con NInfer 0.16.0 contra el Qwen3.8-27B Q4_K_M exacto de Q29 con llama.cpp build 11554. Es comparación de perfiles completos y del mismo caso de uso; no es un efecto aislado de los pesos ni comparación con ASTRA/SOL.
- **Hardware/aislamiento:** misma RTX 3090 física GPU1, contexto máximo 32.768, un servidor y una solicitud a la vez; scope de systemd con MemoryHigh 86 GiB, MemoryMax 96 GiB y swap 1 GiB. Preflight independiente antes de cada servidor; cierre del scope propio y postflight antes de cambiar runtime.
- **Perfil NInfer de velocidad:** `--kv-dtype int8 --prefill-cublas --prefill-chunk 2048 --spec dflash2 --draft-tokens 7 --lm-head-draft --ngram-draft-tokens 15 --no-prefix-reuse`. El decodificador especulativo y cuBLAS forman parte del perfil medido. Si el artefacto no acepta estos flags, se registra bloqueo y no se sustituye silenciosamente el perfil.
- **Control llama.cpp:** mismo archivo Qwen3.8-27B Q4_K_M y plantilla Qwen38 local; GPU layers 999, contexto 32.768, KV q4_0, Flash Attention, batch/ubatch 512, `--spec-type none`. No se cambia la configuración productiva.
- **Matriz:** generación nueva con objetivos de prompt 1K, 8K y largo (~24K tokens); copia de texto del prompt con objetivos 2K y largo (~24K). Tres repeticiones por celda y perfil; mismos textos, IDs de repetición y orden de celdas para A/B. Cada petición permite 256 tokens de salida. La longitud real se toma del `usage.prompt_tokens`; el máximo de entrada es 30.000 tokens para reservar salida dentro del contexto. Una salida menor se conserva y se anota, no se corrige post hoc.
- **Métricas:** prefill y decode TPS internos del servidor, TTFT interno cuando exista, E2E de reloj monotónico, prompt/output tokens, VRAM, RAM/swap, temperatura, eventos OOM, latencia de arranque hasta `/v1/models` y errores. NInfer usa sus eventos JSONL `request_done/throughput`; llama.cpp usa los `slot print_timing` del log. No se mezcla tiempo de arranque con tiempo de petición.
- **Regla:** reportar medianas y todas las repeticiones. Un perfil sólo cuenta como ≥10% más rápido si su E2E mediano gana en al menos dos cargas comparables, sin errores/OOM. Aun así, la adopción para agentes queda rechazada por los fallos TC-74/84/92 de la fase C y no se recomendará reemplazar ASTRA/SOL sin A/B emparejado directo contra esos perfiles.
- **Recibos:** `receipts/speed-preregistration.json`, `receipts/speed-preflight-*.json`, `receipts/speed-invocation-*.json`, `receipts/speed-results.json`, `receipts/speed-postflight-*.json`; datos sin texto de prompt en `runs/speed-measurements.jsonl` y logs completos del servidor bajo `logs/`.


## Cierre de ejecución — 2026-10-22T09:19:44Z

P1 quedó bloqueado por falta de soporte Linux de Flash-Next. P2 completó calidad y velocidad: calidad no pasa los gates de adopción y la matriz A/B de perfiles sí confirma un claim local de velocidad bajo workload sintético (5/5 celdas). La recomendación final es no adoptar NInfer v3 para agentes con tools; priorizar P2.1 (orden seguro de tools, aislamiento/authz por tenant y gating de mutaciones). No se modificaron ASTRA, SOL, Flash-Next productivo, PeritoSoft ni perfiles por defecto. Consulte `RESULTS.md` y `receipts/final-summary.json`.
