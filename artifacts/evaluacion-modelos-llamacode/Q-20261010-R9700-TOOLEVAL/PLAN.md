# Evaluación del post R9700: Flash-Next AtomicChat Q4 vs Qwen3.8-27B Q5

- **ID:** `Q-20261010-R9700-TOOLEVAL`
- **Estado:** activa desde 2026-10-12T20:24:20+00:00 bajo token `44b871d3-d3ee-486d-86f3-29df5730a786`. Revisión documental primaria realizada; todavía no se ejecutó benchmark local en este turno.
- **Registro de cola:** se añadió después de las cuatro tareas que ya estaban pendientes. La toma de lock `82a84f10-1447-4cfa-af1a-91712c0fd50d` cubrió únicamente esta actualización documental/de cola y se libera al cerrar este turno.
- **Objetivo:** determinar si la señal de tool-use Hard Mode del post puede mejorar coding/agentes con los perfiles disponibles de LlamaCode, manteniendo separadas calidad, velocidad, Computer Usage, contexto, visión y voz.
- **No promover:** no cambiar modelo, perfil, template, HarnessSpec ni defaults con el resultado de Reddit ni con un screening local aislado.

## Fuente y datos reportados

El autor publica scripts/configuración y recibos en [r9700-flash-next-notes](https://github.com/Shali12/r9700-flash-next-notes). Compara Flash-Next AtomicChat Q4_K_M y Qwen3.8-27B Q5_K_XL en una Radeon AI PRO R9700 de 32 GB, Ryzen 5 7600X y 64 GB DDR5; Ubuntu 24.04.4 y ROCm 10.0. Usa builds distintas de un fork llama.cpp: r20 para 27B y r30 para Flash-Next. El uso incluye dos slots de 131.072 tokens para Flash-Next, `-ncmoe 41`, caché de expertos de 4096 MiB, KV Q8_0 y Flash Attention. Los configs del tool-eval usan dos slots para ambos, un escenario a la vez, `max_tokens=16384`, temperatura 1.0, top-p 0.95, top-k 20, min-p 0 y esfuerzo medio. El 27B corre con draft head MTP; Flash-Next corre sin draft head.

Los resultados reportados son:

| Suite | Flash-Next AtomicChat Q4_K_M | Qwen3.8-27B Q5_K_XL | Límite |
|---|---:|---:|---|
| tool-eval-bench 2.7.0 estándar | 94,8 | 95,3 | Tres seeds; media comparable en 64 escenarios comunes. TC-65/66/67/69 fallan al inicializar gramática en ambos servidores; TC-45 `tool_choice=required` se excluye del Flash (su r30 no lo impone), pero se califica en 27B; por eso no usar los puntajes completos 64 vs 65 como A/B directo. |
| Hard Mode | 93,9 | 79,8 | Tres seeds; 19 escenarios en la versión del reporte. |
| Velocidad citada | ~36 tok/s, un stream; ~50 tok/s combinado, dos slots | ~1,7× más rápido por turno; prefill ~1,6–2× | Hardware, builds, concurrencia y perfiles distintos; comparación reportada por el autor. |
| Contexto/carga | Dos slots × 131K configurados; ~15,5 GB libres en una prueba de contexto completo | No se presenta una medición de recuperación equiparable | La longitud configurada y la memoria libre no prueban recuperación ni calidad en contexto. |

El benchmark cubre 69 escenarios con herramientas mockeadas y una conversación por escenario. El promedio estándar publicado toma sólo los 64 escenarios puntuados para ambos modelos; cuatro errores de gramática tool+JSON excluyen casos en ambos y `tool_choice=required` introduce la exclusión asimétrica de TC-45 (no se impone en Flash r30; se puntúa y falla en 27B r20). Hard Mode usa 19 escenarios, todos puntuados por cada modelo en cada seed; los resultados de Flash-Next por seed son 92/97/92 y de 27B 84/76/79, con medias del reporte 93,9/79,8. La pequeña muestra no establece una diferencia general.

La suite mide conversaciones con herramientas simuladas y una conversación por escenario. Evalúa algunos patrones de secuenciación de tool calls, incluidos casos donde el 27B emite dos llamadas dependientes antes de tener el resultado previo; no demuestra coordinación multiagente, handoff/delegación, ejecución real de Computer Usage ni el estado final de una aplicación. En el reporte, IFEval fue 84/100 en ambos; no cambia la conclusión sobre los usos específicos de LlamaCode. El autor observó una cadena `////` desde el segundo request en su build r30, mitigada allí con `GGML_SCHED_DEVGATHER=0`; verificó tres requests y no probó r31. El fork RDNA documenta cambios posteriores en gather. Para una prueba de throughput local, primero se comprobará salida íntegra en múltiples requests/turnos.

## Lectura preliminar para LlamaCode

- **Coding/agentes:** la ventaja reportada en Hard Mode justifica un screening de tool-use secuencial, en especial llamadas dependientes que requieren esperar el resultado previo. No prueba mejor desempeño en HE/BCB, repositorios, tests independientes, reparación ni TaskFlow. La suite externa sería complementaria al harness de LlamaCode.
- **Computer Usage:** no se usaron UIA/AT-SPI, screenshots/OCR, acciones ni estado final verificable; no hay transferencia demostrada. Conservar la evidencia existente: los 216 prompts de Computer Use fueron textuales/sintéticos, no GUI E2E.
- **Ingi-Charla:** sin audios, ASR, TTS, WER/CER o escucha; ningún cambio.
- **Visión:** no se probó Flash-Next vision ni imágenes. Una ficha de arquitectura multimodal no es medición de calidad de la cuantización.
- **Contexto:** 2×131K y memoria libre reportados son datos de carga, no prueba de contexto efectivo, no truncamiento ni retrieval. No se cambia la receta 256K actual.
- **Rendimiento:** las cifras son una observación para una máquina con builds distintas y condiciones específicas. No son comparables con Server Speed de LlamaCode; los resultados locales deben medirse en una misma máquina y reportarse como A/B de perfiles completos.
- **Harness:** el método útil es evaluar llamadas dependientes y revisar trazas, pero LlamaCode ya dispone de herramientas de agente, pruebas de aceptación y reparación. La suite externa no reemplaza gates existentes ni justifica cambiar `HarnessSpec`.

## Protocolo preregistrado

1. **Preflight e integridad:** fijar release/tag y commit del runner v2.7.0, suite y Hard Mode exactos; calcular hashes de binarios/scripts/suites locales y modelo GGUF + archivos asociados. Identificar versiones de servidor/runtime, template, parámetros efectivos, GPU/RAM, KV, contexto, MTP, slots y estado de carga. No descargar weights hasta verificar origen, espacio e integridad; preferir checkpoints ya locales.
2. **Perfiles:** comparar como perfiles completos los controles locales elegidos en preflight (SOL Qwen3.8-27B AutoRound INT4 y ASTRA Qwen3.8-Flash-Next disponible). No afirmar equivalencia con Q5_K_XL o AtomicChat Q4_K_M. Confirmar si el runner puede consumir ambos endpoints OpenAI-compatible y representar sus tool calls sin alterar la suite.
3. **Protocolo de calidad:** mismo runner, escenarios, límites, esfuerzo medio y configuración de sampling preregistrada. Hacer tres parejas de seeds comunes para suite estándar e Hard Mode, correr serialmente y mantener igual presupuesto por perfil. Conservar puntuación inicial/final por escenario, herramienta solicitada, argumentos, orden, salida, número de turnos, reparaciones, duración y errores. No descartar fallas de gramática/infraestructura silenciosamente: clasificarlas por brazo y reportar denominadores comunes y completos.
4. **Integridad del runtime:** smoke de varios turnos y requests antes y después de las suites, incluyendo comprobación de la salida textual exacta/no corrupta. Detener calidad si hay corrupción; corregir/reconstruir el entorno y repetir sólo bajo un fingerprint nuevo documentado.
5. **Velocidad separada:** Server Speed local con el mismo corpus y cargas definidas; reportar TTFT, prefill, decode, latencia total, mediana/dispersión y recursos. No extrapolar los tok/s del post a otra GPU/runtime.
6. **Criterio de decisión:** cualquier conclusión local será provisional si no se completan tres parejas válidas. No declarar mejora estable ni promover por tool-eval aislado: pedir mejora repetida sin regresión en HE0→HE20→BCB8, ADV/TaskFlow y estabilidad. CU E2E, imágenes reales, corpus de audio y retrieval se dejan como campañas independientes si se quiere decidir esos usos.

## Estado de ejecución y conclusión

El preflight se cerró y las tres suites por perfil se completaron en serie. SOL ya estaba descargado y sus shards locales se reutilizaron; no se descargaron pesos ni se alteró ningún perfil productivo. Hard Mode v2.7.0 (19 casos, seeds 42/43/44) dio medias SOL 58,00, ASTRA 75,33 y Q4 86,67. La suite estándar v2.7.0 (69 casos) dio SOL 25,67, ASTRA 87,67 y Q4 90,67. Q4 lideró esta medición de tool-use simulado, sin promoción general.

La comparación histórica citada usa v2.8.0 y 28 escenarios con temperatura 0,6; esta corrida usa v2.7.0 y 19 escenarios con temperatura 1,0. Por eso las diferencias aritméticas entre tablas no demuestran mejora o regresión. TC-80 falló con todos los perfiles en las tres semillas. ASTRA/Q4 Strata obtuvieron HTTP 400 en cuatro casos estándar por `structured response_format` combinado con tools; el runner los registra como parciales. TC-92 y TC-97 del conjunto v2.8 no se incluyeron y siguen sin revalidar.

No se midió TPS/Server Speed, GUI E2E, voz, visión ni recuperación de contexto. El endpoint Q4 propio se detuvo al cierre; puerto 8350 cerrado y GPUs sin carga de benchmark. Los recibos, fingerprints, reintentos incompletos y comparación están en `artifacts/evaluacion-modelos-llamacode/Q-20261010-R9700-TOOLEVAL/`.

## Fuentes primarias

- [Notas, configuración y resultados del autor](https://github.com/Shali12/r9700-flash-next-notes)
- [Resultados de suite estándar](https://github.com/Shali12/r9700-flash-next-notes/blob/main/results/tool-eval-main.md)
- [Resultados Hard Mode](https://github.com/Shali12/r9700-flash-next-notes/blob/main/results/tool-eval-hard-mode.md)
- [Repositorio y metodología de tool-eval-bench](https://github.com/SeraphimSerapis/tool-eval-bench)
- [Ficha oficial Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)
- [Fork de parches RDNA](https://github.com/stew675/llama-cpp-rdna-boosts/)
- [Issue #85 del fork RDNA, sobre salida incoherente en multi-GPU/gather](https://github.com/stew675/llama-cpp-rdna-boosts/issues/85)

## Evidencia local pertinente

- [Decisiones y registro acumulativo](../../../docs/evaluacion-modelos-llamacode.md)
- [Qwen3.8-27B UD-IQ4_XS / TaskFlow y probe de contexto](../../../docs/qwen38-unsloth-iq4xs-196k-eval-20261009.md)
- [Flash-Next IQ3_XXS vs ASTRA IQ3_S / Strata](../../../docs/qwen38-flashnext-iq3xxs-strata-20261009.md)
- [Computer Use Flash-Next, sólo prompts textuales](../../../docs/flashnext-computer-use-20261006.md)
- [Auditoría de voz local](../../../docs/ingicharla-local-voice-audit-20260918.md)
- [Auditoría de visión/MTP](../../../docs/target-profiles-mtp-vision-audit-20260915.md)


## Activación del turno

- Orden FIFO: activada inmediatamente después de cerrar Q-20261009-EKBASIS-27B; lock exclusivo vigente en WORK_QUEUE.lock.
- Alcance actual: revisar el preflight del plan, localizar runner/fixture v2.7.0 y comprobar perfiles, endpoints y hardware disponibles. No iniciar servidor, inferencia o benchmark antes de terminar estas comprobaciones.
- Comparación sólo como perfil completo si el runner permite la misma suite y solicitudes multi-turno sin modificar semántica; si no, conservar resultado documental y cerrar con la limitación concreta.


## Enmienda preregistrada y activación (2026-10-12)

- Runner oficial fijado a tool-eval-bench 2.7.0, tag object `544afb576b395259196e341432944f3afaf3793e`, commit `c483eef867d75d9dd04c7d370fe553f96a49d672`. El checkout y Python aislado están en `vendor/tool-eval-bench-v2.7.0/` y `runtime/venv/`; `--version` confirma 2.7.0. Los dry-runs confirmaron 69 escenarios estándar y 19 Hard Mode (TC-70–TC-88). La versión 2.8.0 cambió los escenarios/puntuación; sus 28 tareas anteriores quedan como otra suite y no se mezclan.
- Perfiles locales completos: SOL Qwen3.8-27B AutoRound INT4 / vLLM TP2 P2P MTP4; ASTRA Qwen3.8-Flash-Next IQ3_S calibrado / Strata 0.1.41; Flash-Next Q4 local UD-Q4_K_XL / Strata 0.1.41. Incluyo Q4 por la petición previa de comparar ese perfil. Los dos pesos exactos del post (AtomicChat Q4_K_M y Qwen3.8-27B Q5_K_XL) no son los perfiles locales: el resultado local medirá transferencia a perfiles completos, no reproducirá aquellos modelos ni la Radeon R9700.
- A/B local: cada perfil por separado, tres seeds emparejadas 42/43/44; suite estándar y Hard Mode en llamadas distintas. Mismo runner/tag, 8 turns, timeout 600 s, una conversación a la vez, sin variantes y sin error injection. Sampling fijado para replicar el reporte externo: temperature 1.0, top_p 0.95, top_k 20, min_p 0, repetition penalty 1.0, presence penalty 0, reasoning effort medio y max_tokens 16384. La temperatura 1.0 corresponde al protocolo publicado; no es un cambio del sampling productivo. v2.7.0 pasa cada seed al servidor.
- Primero haré un smoke pequeño (TC-01, TC-47, TC-70) para verificar texto, tool calls y continuidad; se registrará aparte, sin añadirlo a la puntuación oficial. Después correré 69 + 19 en seeds 42/43/44 por perfil. Conservaré scores y denominadores por perfil y la intersección comparable; los errores de transporte/servidor se clasifican como infraestructura y no como fallos de calidad.
- Sol ya estaba descargado, con sus pesos locales verificados; no se vuelve a descargar. ASTRA/Q4 también existen localmente con hashes verificados en sus campañas previas. No se descargarán pesos. SOL Compose publicaba originalmente 8113 en todas las interfaces, así que esta tarea usa el override aislado `configs/sol-localhost.override.yml`, `pull_policy: never` y nombre de contenedor propio; no altera los perfiles productivos ni el Compose original. ASTRA/Q4 escuchan en loopback.
- Corridas en serie sobre las dos RTX 3090. Repetir chequeo de VRAM/RAM/swap, procesos y puertos antes de cada perfil; parar la secuencia si aparece un workload ajeno o la guarda de memoria no se cumple. Los resultados de velocidad publicados quedan fuera de esta tarea: el objetivo es transferencia de tool-use/calidad.


## Preflight cerrado y preparación de corridas (2026-10-12T20:33:23+00:00)

- Se verificó de nuevo que SOL ya existe en `/media/cristian/Disco local/Models/llamacpp/club-3090/qwen3.8-27b-autoround-int4`; la corrida reutiliza esos pesos y la imagen local `vllm/vllm-openai:v0.27.1` con `pull_policy: never` y modo offline. No se descargará SOL. También están presentes los directorios locales de ASTRA IQ3_S y Q4 UD-Q4_K_XL; se conservarán sus hashes registrados.
- Configuración Compose efectiva revisada con los tres archivos (base, `vram-quarantine.override.yml`, y override de la tarea): servicio SOL `llamacode-q9700-sol-vllm`, puerto host `127.0.0.1:8113`, GPU 0+1. Sin contenedor existente, sin listeners en 8113/8350; VRAM libre salvo escritorio: GPU0 1221 MiB usados, GPU1 108 MiB. RAM disponible 108 GiB; swap usada 1.9/8 GiB. El Docker root tiene 8.3 GiB libres; datos de pesos y cachés viven en el volumen externo, con 106 GiB libres.
- El CLI v2.7.0 no tiene flags separados para `presence_penalty` ni `max_tokens`; se enviarán por `--backend-kwargs` junto con `chat_template_kwargs.enable_thinking=true`. Temperatura 1.0, top-p 0.95, top-k 20, min-p 0, repetition penalty 1.0, presence penalty 0, seed común, máximo 16384 tokens, 8 turnos, timeout 600 s, serie y sin error injection.
- El runner ofrece `--no-think`, pero no un nivel interoperable `reasoning_effort=medium`; por compatibilidad no forzaré un campo específico de un runtime en otro. Se enviará `chat_template_kwargs.enable_thinking=true` y `reasoning_effort=medium` por `--backend-kwargs`, que v2.7.0 mezcla en el payload. El smoke debe confirmar que ambos runtimes aceptan la solicitud sin alterar el transporte; cualquier endpoint que ignore o rechace esos campos se documentará. Por tanto, esto es transferencia A/B de perfiles completos, no réplica exacta de pesos o hardware del post R9700.
- Próximo gate: smoke separado TC-01/TC-47/TC-70 por perfil; sólo si conserva texto, tool calls y transporte se inician las 69 tareas estándar y 19 Hard Mode por semillas 42/43/44.


## Corrida smoke SOL concluida (2026-10-12T20:38:55+00:00)

TC-01/TC-47/TC-70 terminaron normalmente; el score agregado de smoke fue 5/6 (83/100), con TC-01 parcial por no resumir los datos después de elegir el tool correcto, TC-47 y TC-70 aprobados. El JSON confirma T=1, top-p=.95, top-k=20, min-p=0, repetition penalty=1, presence penalty=0, max_tokens=16384 y `chat_template_kwargs={enable_thinking:true, reasoning_effort:medium}`; vLLM aceptó las solicitudes con HTTP 200. Es un fallo de calidad real, no infraestructura. Se conserva en `receipts/smoke/` y no se agrega a los scores oficiales. Para evitar recargar cada perfil varias veces, continúo por perfil: completar SOL, luego cargar y hacer smoke + suites de ASTRA, y luego Q4; cada smoke precede a las suites de su propio perfil.


## Incidente en SOL estándar seed 42 (2026-10-12T20:45:17+00:00)

La primera ejecución completa del comando terminó el runner, pero sólo 47 de 69 escenarios respondieron. TC-48–TC-69 son fallos de infraestructura (HTTP 500); el score global del runner (85/100) no es válido. Entre los 47 casos con inferencia hubo 38 pass, 4 partial y 5 fail, 80/94. El servidor registró un CUDA device-side assert del Worker_TP0 en `synchronize_input_prep`/`num_accepted_tokens_event.synchronize`, seguido de salida del EngineCore; el contenedor no fue OOM-killed. Se guardó el incidente y el log completo. El contenedor aislado ya se detuvo para liberar VRAM; reiniciaré sin cambiar el perfil, haré TC-48 como diagnóstico y repetiré la suite 69 si responde normalmente.


## Resultados iniciales válidos de SOL (actualización 2026-10-12T21:05:52+00:00)

- Estándar seed 42, intento repetido tras reinicio: completo 69/69, 34/138 puntos, score final tool-eval 25/100; 10 pass, 14 partial, 45 fail funcionales. Sin HTTP 5xx, timeout ni CUDA error; TC-64 tomó 289.73 s y terminó como fallo de calidad. Recibo `receipts/raw/sol-standard-seed42-retry1.json`, log `receipts/logs/sol-standard-seed42-retry1.log`.
- Hard Mode seed 42: completo 19/19, 22/38 puntos, score final 58/100; 10 pass, 2 partial, 7 fail; sin errores de infraestructura. Recibo `receipts/raw/sol-hardmode-seed42.json`, log `receipts/logs/sol-hardmode-seed42.log`.
- La primera ejecución estándar del mismo seed tuvo 47 resultados de calidad (80/94 puntos; 38 pass, 4 partial, 5 fail) antes de un CUDA assert y 22 errores HTTP 500. No es score y se conserva en `receipts/raw/sol-standard-seed42.json`. TC-48 aislado después del reinicio respondió normal, con fallo de calidad.
- La repetición con igual perfil y seed produjo muchos menos aciertos en los primeros 47 casos que el intento previo. No asumo causa; queda señal de variación entre reinicios con MTP4/temperature 1.0. Mantendré ambos recibos separados, usaré sólo la corrida completa sin infraestructura como corrida válida, y reportaré variación/limitación explícitamente. Continúo semillas 43 y 44 para completar el screening predefinido.


## Cierre (2026-10-13T03:51:55Z)

- Tres perfiles × dos suites × tres semillas completados; corridas válidas 69/69 para estándar y 19/19 para Hard Mode. Se conservaron reintentos inválidos/incompletos y se excluyeron de los promedios.
- Mejor perfil en las métricas de esta suite: Flash-Next Q4 UD-Q4_K_XL. No se promueve: el resultado es tool-use simulado y la suite no cubre repositorios, GUI, visión, audio ni contexto recuperable.
- Cierre del servicio: Strata Q4 PID 1246027 terminó tras SIGINT; puerto 8350 cerrado. GPU0 1050 MiB y GPU1 108 MiB usados al comprobar.
- SOL ya estaba descargado; reutilizado sin descarga. No se cambiaron pesos, perfiles productivos ni HarnessSpec.
- Reporte: [RESULTS.md](RESULTS.md). Matrices y fingerprints: `receipts/tool-eval/all-seeds-comparison.json`, `receipts/profile-fingerprints.json`.
