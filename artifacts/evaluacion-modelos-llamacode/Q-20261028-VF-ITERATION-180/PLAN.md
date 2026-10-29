# Q180 — Qwen3.6-35B-A3B en doble RTX 3090

**Estado final (2026-10-29 06:55Z): Q180 A03 completado en 2×RTX 3090, layer split 1:1. Q172 seeds42/43/44: 0/100 cada una (28/28 fallos por agotamiento del techo de 16.384 tokens de razonamiento sin tool call/respuesta); safety gate PASS, warnings vacíos en las tres. Ladder de contexto completada hasta 261.888 tokens; init proceso→health 5,194 s y relanzamiento inmediato→health 5,138 s. El perfil no es apto para coding/agentes con esta configuración y no se promueve frente a SOL/ASTRA; TPS son mediciones de fixture y no reparan el fallo funcional.** Attempts01–03 quedan preservados como inválidos; A03 es el resultado válido de esta iteración.

## Pregunta de decisión

¿Qwen3.6-35B-A3B UD-Q4_K_XL, servido por `llama.cpp` con distribución de capas entre GPU0 y GPU1, ofrece una alternativa útil a TERRA (Qwen3.8-27B AutoRound) en calidad de herramientas, seguridad y velocidad en el host 2×RTX 3090/128 GiB RAM? Es comparación de **perfiles completos** con runtimes distintos; no aislará la arquitectura del motor.

## Evidencia externa y límites

- Strata issue #3294 sigue describiendo Qwen3.6 de una sola GPU y reporta 58 tok/s frente a 91–95 tok/s de `llama.cpp -sm layer` en 2×P100. Son mediciones ajenas, no estimaciones del host RTX 3090: https://github.com/Niko1221/Strata/issues/3294
- El archivo disponible es el GGUF oficial de Unsloth, Apache-2.0: https://huggingface.co/unsloth/Qwen3.6-35B-A3B-MTP-GGUF/blob/5bc3e238d916f48a861bac2f8a1990a0e9b7e98d/Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf
- Pin exacto: revisión HF `5bc3e238d916f48a861bac2f8a1990a0e9b7e98d`, archivo `Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf`, tamaño 22,853,663,008 bytes, SHA-256 `55983c5a75a1ab969824077b3bb3de4146e82a9234072b48ad4e8f92ad3fe9f1`.
- Motor fijado: `ggml-org/llama.cpp` master commit `2e0d86bebc210947680e8f0d67daa79f3260c106` (verificado por `git ls-remote` el 2026-10-29T02:33:29Z). CUDA Toolkit fijado: `/usr/local/cuda-12.8` / `nvcc` 12.8.93; build para SM86.
- Qwen3.8-27B TERRA histórico obtuvo Q172 62/100, TC-74/84 fallidos; Flash-Next NInfer preview obtuvo 77/100 con TC-75/82/84/92 fallidos. Estos scores pertenecen a perfiles previos y no se transfieren a Q180.

## Perfil fijado

- Modelo: Qwen3.6-35B-A3B UD-Q4_K_XL, sin MTP/draft/speculative decoding.
- GPU: RTX 3090 GPU0 + GPU1; `--split-mode layer --tensor-split 1,1`, ambas deben recibir el mismo proceso y asignación sustancial de memoria. No se acepta fallback a una sola GPU.
- Runtime: build CUDA del commit fijado; context/KV pool 262144; una solicitud/concurrencia; mmap; Flash Attention habilitado si el runtime lo confirma; chat template GGUF/Jinja del modelo.
- Tokenizador para llama-benchy: `Qwen/Qwen3.6-35B-A3B` en revisión `995ad96eacd98c81ed38be0c5b274b04031597b0`; `tokenizer.json` (12.807.982 B) y `tokenizer_config.json` (16.718 B), con SHA registrados antes de medir. La plantilla de conversación y tools viene del GGUF exacto con Jinja habilitado.
- Muestreo Tool-Eval: temp 0.6, top-p 0.95, top-k 20, min-p 0, repeat penalty 1, presence 0, seed42; no desactivar thinking. Tool-Eval 2.8.0, TC-70..TC-97, variant-seed 20261010, reasoning medium cuando el endpoint lo acepte; registrar cualquier incompatibilidad de parámetro/template.

## Secuencia preregistrada

1. **Completado:** descargar directamente a D el archivo exacto y verificar bytes/SHA antes de cargar. Tokenizador upstream también descargado y verificado; recibos en `receipts/model-download.json` y `receipts/tokenizer-download.json`.
2. **Fuente y build completados:** `llama.cpp` aislado en D, commit exacto; A01 se construyó en `llama-build-cu128` con `CUDAToolkit_ROOT=/usr/local/cuda-12.8`. El intento 01 mixto se conserva en log y receipt; nunca se usará para inferencia.
3. Arranque inicial de proceso con 262144 contexto, medir `Popen→/health`; comprobar endpoint loopback, archivo/runtime, listener y el mismo PID CUDA en ambas GPU. Enviar smoke no puntuado de 16 tokens exactos.
4. Ejecutar Q172 Hard Mode 2.8.0, los 28 casos TC-70..TC-97, seed42, una prueba y concurrencia. El resultado completo se acepta aunque `--fail-on-safety` devuelva 2. Si aparece fallo crítico de seguridad, no lanzar seeds adicionales; la ladder de velocidad puede continuar porque responde una decisión de rendimiento separada.
5. Si seed42 completa sin fallo crítico, ejecutar seeds43 y 44 en serie. Comparar mediana/rango con los perfiles Q172 existentes. Candidato a TERRA sólo si 3/3 semillas completas, cero fallos críticos y mediana ≥62/100; candidato a reemplazar SOL requiere además mediana ≥73/100 y ningún gate crítico. Esto no promueve automáticamente.
6. Ladder serial con llama-benchy 0.4.0, no cache/prefix reuse: prompts 8192×3, 32768×1, 65536×1, 131072×1 y 261888×1; salida exacta 128; TTFT/prefill y decode cliente, manteniendo tokenizador validado contra el GGUF. No 512K ni 1M.
7. Tras cerrar la ladder, parada limpia y un relanzamiento inmediato sin generación para registrar `process-cold` y `immediate-relaunch`; el hash previo calienta page cache, así que no se llamará “disco frío”.

## Criterios de parada/validez

- Antes de build/download/GPU: lock Q146 vigente, espacio D ≥55 GiB, ambas 3090 visibles, `MemAvailable` ≥32 GiB, puerto 18481 libre y ningún otro inference server. No cerrar PeritoSoft GUI ni otros procesos.
- Preflight, smoke y cada muestra verifican ambos GPUs. Durante la corrida: monitoreo cada 15 s; detener sólo procesos propios si desaparece un GPU, hay OOM/Xid/runtime error, tokenización/contexto no coincide, listener no queda en loopback, cuatro muestras seguidas caen bajo 32 GiB disponibles o aparece otro inference server.
- Si el formato, la capa Qwen3.6, la plantilla de tools o el split dual falla, documentar el fallo y detener; no cambiar de motor/cuanti/config sin enmienda antes de una nueva corrida.
- Conservar modelo y build después del benchmark para evaluación; no borrar ASTRA, SOL ni archivos de PeritoSoft.

## Inventario

La fila existente de `Inventario de modelos!A19:R19` se actualizó después de verificar el GGUF local. Rutas, tamaño, SHA, perfil planeado y estados N/D se leyeron de vuelta; no se sobrescribieron métricas inexistentes. Receipt: `receipts/google-sheet-q180-inventory-sync.json`.

## Artefactos

Runner fijado y validado sintácticamente: `scripts/run_q180.py`, SHA-256 A02 `f2958906063306e18bbb5ce553d49afe4e24d9d3eff8bd2cba15e467605111b1`. Servidor SHA-256 `0f25065d4c5e304000b38c6e1d288b483aac0a1c8936f3bfdc130b5d44d15ae5`. Prerregistro base: `receipts/preregistration.json`; A01 CUDA: `receipts/prereg-amendment-a01-cuda-toolkit.json`; A02 reasoning-effort: `receipts/prereg-amendment-a02-reasoning-effort.json`; build: `receipts/build-success-a01.json`. Resultados/raw: `runs/`, logs: `logs/`. Sheet: Inventario de modelos y `Resultados`, sólo tras verificar el artefacto y las mediciones.


## A03 — intento limpio de Q172 tras interferencia PeritoSoft

Registrado 2026-10-29T03:40:02+00:00, antes del intento 02. El informe del intento 01 completó formalmente 28 escenarios, pero completion_rate=None%, score=0; TC-84..TC-97 quedaron excluidos por errores de conexión. El proceso 8033 se trazó a peritosoft-app, y Q180 se detuvo antes del ladder. Se preservaron logs y resultados en runs/attempt01-peritosoft-interference/. La app y su llama-server se cerraron con SIGTERM bajo autorización explícita; puerto 8033 verificado libre.

A03 repite seed42 con la configuración ya fijada, sin cambios de modelo ni parámetros. Seeds 43/44 solo se ejecutan si seed42 completa los 28 escenarios y supera el safety gate. Después sigue el ladder si el servidor permanece estable y aislado. Recibos: receipts/prereg-amendment-a03-clean-q172-rerun.json, receipts/q180-attempt01-preserved.json, receipts/peritosoft-server-stop-q180.json.


## A04 — detección exacta de procesos de inferencia

Prerregistrado 2026-10-29T03:45:45+00:00, antes de editar el detector. El intento 02 produjo un falso positivo: una shell de Claude que ejecutaba grep llama-server fue clasificada como servidor por una búsqueda de subcadenas. A04 cambia la detección a comm/ejecutable argv y módulos Python conocidos; añade regresión CPU-only para shell, llama-server, vLLM y proceso ajeno. No reduce el guard para servidores reales. En este momento los servidores Qwen3.5-9B de PeritoSoft 1870175/8033 y 1870341/8081 están activos en una scope de Claude; Q180 GPU permanece bloqueado hasta que desaparezcan. Receipt: receipts/prereg-amendment-a04-guard-specificity.json.

A04 implementada y validada 2026-10-29T03:46:49+00:00: búsqueda exacta por comm/executable argv; llama-server real y vLLM Python se detectan, bash con grep y Python texto casual no. Regresión unittest CPU-only: 6/6 PASS. Runner SHA-256 actualizado a c053e71e5c7d50dad45e390bf537b01cf51d5fcd1aa78c443bab73caf0229504; no se ha iniciado inferencia. El muestreo live de inference_processes devolvió [] aunque una tarea de Claude ejecuta una shell de diagnóstico; GPU Q180 sigue bloqueada si reaparece un llama-server. Receipt a04-inference-detector-cpu-test.json.


## Attempt03 — interferencia persistente de PeritoSoft

Registrado 2026-10-29T04:01:29Z. Preflight dual y smoke correctos; Q172 seed42 quedó inválido: TC-70..TC-73 expiraron por respuesta sin tool-call; `llama-server` Q180 salió con rc=0 durante el escenario siguiente y TC-74..TC-97 resultaron errores de conexión. No usar el score 0/100. Sin ladder ni init cold/hot. La scope externa `app-com.anthropic.Claude-3228104.scope` relanzó Qwen3.5-9B en 8033 y 8081 durante la prueba. Se detuvieron solo los procesos PeritoSoft identificados; no se cerró Claude. Reanudar solo tras detener el supervisor o recibir autorización expresa para cerrar la scope. Ver receipt `receipts/q180-attempt03-peritosoft-takeover.json`.


### Causa probable del relanzamiento y salida del servidor (2026-10-29T04:03:34Z)

La inspección de proceso encontró Claude Bash PID 1895866 (PPID 1554132) dentro de `app-com.anthropic.Claude-3228104.scope`, con un bucle que ejecuta `ps ... | grep llama-server ... | xargs -r kill` antes de relanzar PeritoSoft `server.js`. Ese `kill` alcanza cualquier `llama-server`, no sólo el suyo, y coincide con la salida `rc=0` del servidor Q180 y el retorno de Qwen3.5-9B en 8033/8081. Es una causa muy probable, pero no se capturó la señal exacta; se conserva como inferencia, no como hecho probado. La scope está activa. No iniciar otra inferencia mientras siga ese bucle. Receipt: `receipts/q180-autorestart-process-identification.json`.

## Reintento limpio después de detener PeritoSoft (2026-10-29)

El usuario confirmó que había detenido el Qwen3.5-9B previo y ya había autorizado cerrar PeritoSoft y sus servidores. La instancia volvió a aparecer; se cerraron con SIGTERM la app, `server.js`, los servidores de los puertos 8033/8081 y ocho workers `job_runner` residuales, sin cerrar Claude. El preflight nuevo pasó a 04:10:18Z con el mismo prerregistro A03, hash de GGUF/runtime/harness, dual RTX 3090 y sin inferencia/CUDA ajena. Reintento Q172 seed42 en curso; primeros tres casos fallaron por timeout del modelo (~113–115 s), el cuarto sigue activo. Sin score parcial, seeds adicionales, ladder o init que reportar hasta que termine la semilla. Recibos: `receipts/q180-clean-rerun-progress-20261029.json` y `receipts/peritosoft-stop-clean-rerun-20261029.json`.

## Cierre Q180 A03 — 2026-10-29T06:54:46Z

Las tres semillas Q172 y todos los puntos de la ladder terminaron con el servidor en el perfil preregistrado. No hay más corridas Q180 habilitadas por este plan. El resultado funcional impide promover el perfil para agentes; conservar sus datos de throughput como referencia exploratoria. El runner dejó 127.0.0.1:18481 libre y sin servidores Q180; ver `runs/q180-summary.json` y `receipts/q180-postflight.json`.
