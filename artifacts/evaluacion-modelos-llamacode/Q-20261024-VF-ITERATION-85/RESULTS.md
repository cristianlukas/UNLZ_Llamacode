# Q85 · resultados

Estado: **Q85 evaluado en TP=2 con ambas RTX 3090 y 128 GB RAM. Intento 9: `read_file` cumplió el path; `write_file` agotó 512 tokens y emitió path/contenido inválidos. Canario fallido; Tool-Eval y A/B de calidad/velocidad no iniciados. Según el preregistro, detener este loop hasta un cambio material del parser/runtime. No adoptar; ASTRA/SOL/Flash-Next y PeritoSoft intactos.**

## Evidencia inicial

- Lock Q85: token `vf85-hyperqwen-tp2-20261024-1421`.
- Equipo: 2×RTX 3090 y 128 GB RAM declarados por el usuario.
- Perfil local LlamaCode `sys-astra-iq2xs-default`: Flash-Next IQ2_XS, GPU `[0,1]`, `layer_split=auto`; max context 1.048.576, YaRN original 262.144, KV int8, resident 32.768. Config SHA-256 `b4a55b263ad8bf1df809afb76603c23d55c1471c2e7cac6997e979bd3ad5e38f`. La identidad productiva final y hashes de los dos shards quedan como gate antes de la suite.
- Preflight previo al intento 1, 2026-10-24 15:15 UTC: `/` 10.203.824.128 B libres; `/var/lib/containerd` 19.767.672.832 B; HDD extra 35.933.433.856 B; 115.327.574.016 B RAM available. Cero servidores/listeners antes de arrancar; topología GPU0↔GPU1 `PHB`.
- Imagen pinned por digest, base Qwen3.8-27B y drafter DFlash2 descargados/verificados; `prepare` CPU-only y `verify --no-server` con CUDA_COUNT=2 terminaron correctamente. API key sólo en `.env` modo 0600; no registrada.
- El intento 1 creó un único servicio HyperQwen y luego lo detuvo; quedó cero contenedores y el puerto 18142 libre. ASTRA/SOL/Flash-Next y la GUI se mantuvieron intactos.
- Candidate context del perfil rápido: 65.536; por tanto el test de coding no emite afirmación de paridad con el ASTRA configurado a 1M. El contexto largo queda para un ensayo matched separado.

## Estado de la evaluación

- El canario de tools no pasó en nueve intentos; el último ejecutó TP=2 en ambas 3090 y usó 115,95 GB RAM disponible antes del arranque. `read_file` respetó el enum tras alineación explícita del prompt; `write_file` terminó en `length` a 512 tokens con path inválido y contenido no-string. No se escribió el fixture.
- Tool-Eval, evaluación comparativa de calidad y benchmark de velocidad quedan bloqueados por la falla del flujo de herramientas. Según la política preregistrada, reanudar esta línea sólo cuando cambie materialmente el parser/runtime. No inferir superioridad ni inferioridad general.
- Servicio candidato detenido, puerto libre, contenedores activos ausentes, VRAM regresó al nivel de escritorio y GUI intacta. Recibo `receipts/q85-tool-canary-attempt-09-result.json`.

## Gate de tools preregistrado · 2026-10-24T15:13:38Z

- Se congeló un canario único de lectura→escritura para el servicio HyperQwen TP=2 antes de Tool-Eval. Fixture `Q85-CANARY-READ-THEN-WRITE-314159` (33 bytes, SHA-256 `72e104733ce4d825eae8998b516025aa2c278284e1d875bddb05e9b7b8f48063`), workspace temporal aislado en HDD y allowlist exacta de rutas.
- Los scripts pasaron parseo AST de Python y `bash -n`; hashes y criterios están en `receipts/q85-tool-canary-preregistration.json`. No hubo inferencia al registrar el protocolo.
- Gate: el servidor debe responder health/models; emitir exactamente `read_file` y luego `write_file` con call IDs; persistir bytes idénticos; dar respuesta final no vacía; limpiar workspace y bajar el contenedor. Una sola corrida, cero reintentos. Si falla, Tool-Eval queda bloqueado.
- Es una comprobación del protocolo del servidor, no una validación E2E de LlamaCode ni evidencia de superioridad. El intento 1 falló al iniciar; el intento 2 usa un KV pin preregistrado.

## Canario · intento 1 · 2026-10-24T15:16–15:20Z

- El servidor TP=2 no llegó a health. EngineCore informó `RuntimeError: CUDA error: out of memory`; un worker murió durante startup/warmup. No se enviaron requests de canario ni se inició Tool-Eval. El contenedor permaneció `running` aunque el worker ya había fallado; se detuvo sólo la unidad propia `q85-hyperqwen-canary` y se confirmó puerto libre después.
- Antes del cierre se observó GPU 0: 1.281 MiB / 55 °C y GPU 1: 22.980 MiB / 46 °C; RAM disponible ~104 GiB. No hubo OOM de RAM ni se acercó al límite térmico de 85 °C. El muestreo no identifica qué rank causó el error.
- El log mostraba TP=2 sin `KV_MEM`, usando GPU_UTIL=0.93; también advertía padding híbrido que podía desperdiciar hasta 60% de KV. La guía multi-GPU del commit fijado indica que TP>1 omite el pin single-GPU y recomienda fijar KV antes de medir. Son hipótesis plausibles, no causa probada.
- El primer wrapper eliminó el contenedor antes de conservar su log completo; queda un extracto del error en el historial interactivo, no un archivo íntegro. Se corrigió el wrapper para retener logs redacted modo 0600 y detectar errores CUDA/worker temprano. Se corrigió además el Compose override: `KV_MEM` no llegaba al contenedor y ahora se valida en config.
- Recibos: `receipts/q85-tool-canary-attempt-01.json`, `receipts/q85-canary-start-preflight-20261024T151539Z.json`; intento 2 preregistrado en `receipts/q85-tool-canary-attempt-02-preregistration.json` y config readback `receipts/q85-compose-kv-pin-config-validated.json`. No hay métricas de calidad, TPS o adopción.

## Canario · intento 2 · 2026-10-24T15:34–15:35Z

- Se validó que `KV_MEM=3000000000` llegaba a vLLM junto con TP=2, GPU_COUNT=2 y GPU_UTIL=0.93. El proceso arrancó en ambas GPU, pero un worker rechazó la inicialización en `cuda:0`: 21.91 GiB libres frente a 21.95 GiB solicitados (déficit 0.04 GiB, ~41 MiB). El contenedor salió 1; `OOMKilled=false`; no es el mismo CUDA OOM del intento 1 ni evidencia de que el KV pin haya fallado. No hubo health, llamadas del canario, tokens generados ni Tool-Eval.
- El muestreo previo mostraba la app oculta `artcraft-launcher` con 209 MiB en GPU0; el usuario había autorizado terminar procesos no-inferencia. Se envió SIGTERM sólo a ese PID, liberando ~232 MiB según el muestreo de VRAM; Xorg, Codex y el resto de la GUI quedaron abiertos. Preflight posterior: GPU0 1.002 MiB, GPU1 110 MiB; servicio y puerto 18142 detenidos/libres.
- El wrapper no detectó el contenedor caído porque `docker compose ps -q` omite servicios detenidos; esperó hasta que se paró manualmente nuestra unidad. Corregido a `compose ps --all -q` en health-check y captura de logs. El log redacted completo (mode 0600) está en `receipts/q85-server-boot-attempt02-20261024T153555Z.log`, SHA-256 `9c180220dd66302a565daa740010507c2a1c468e3fa454dfa55be8eff5e77f83`.
- Cierre: se detuvo sólo la unidad Q85; contenedor eliminado por Compose, sin listener en 18142, sin proceso de inferencia candidato. No se reinició automáticamente.

## Preflight read-only · 2026-10-24T15:33:19Z

- Confirmada por una unidad transient user-systemd la propagación de `KV_MEM=3000000000` hacia Compose, junto con `GPU_COUNT=2` y `--tensor-parallel-size 2`; no inició servidor ni inferencia. La invocación inicial falló antes de Compose porque un shell de login cambió el working directory; se corrigió con `WorkingDirectory` explícito.
- Lock Q85 sigue coincidiendo. No hay contenedores, procesos/listeners de inferencia ni listener en el puerto 18142. Ambas RTX 3090 están visibles; topología PHB. RAM disponible: 116.731.478.016 B. Espacio: `/` 10.197.385.216 B, containerd 19.767.672.832 B, HDD extra 35.352.989.696 B; pasan los pisos preregistrados, aunque containerd queda con margen estrecho sobre 18 GiB.
- NVIDIA muestra una aplicación de escritorio `artcraft-launcher` con 209 MiB; el muestreo de procesos/listeners no encontró servidor de inferencia. No se la terminó y la GUI permanece abierta. ASTRA/SOL no se modificaron. El proceso de canario aún no había iniciado al escribir esta actualización.

## Canario · intento 3 · 2026-10-24T15:39–15:40Z

- Tras cerrar `artcraft-launcher`, el servidor candidato arrancó con TP=2, KV=3.000.000.000 B/worker y GPU_UTIL=0,93. `/health` y `/v1/models` respondieron; durante el canario las GPU llegaron a ~14.036/13.152 MiB y ~57/44 °C. El wrapper apagó el servicio después del canario y liberó ambas tarjetas.
- El primer completion, con `tool_choice=auto`, procesó 474 tokens de prompt, generó 256 tokens en 7,34 s y terminó con `finish_reason=length`; no incluyó `read_file`. No se guardó texto de respuesta. El canario falló, no escribió `result.txt`, no hubo interacción de tools ni Tool-Eval. Es un fallo observado de selección de tools en modo auto, no de arranque ni evidencia de inferioridad general.
- Recibo `receipts/q85-tool-canary-20261024T154050Z.json`; log redacted mode 0600 `receipts/q85-server-boot-20261024T154057Z.log` (SHA-256 `b4f9d159fd1816d487bb7466c6b94af6d163f649a4be10b80381eebc08e8707e`).
- Próximo diagnóstico separado: ejecutar el fixture con llamadas nombradas (`read_file`, luego `write_file`) y cierre `tool_choice=none`. La documentación oficial de vLLM describe llamadas nombradas como salida estructurada según el schema; así separamos soporte del servidor/parser de la decisión espontánea del modelo. Si pasa, no borra el fallo `auto`; antes de cualquier suite se requiere una prueba real que conserve selección automática.

## Canario · intento 4 · 2026-10-24T15:46:35–15:46:44Z

- El servidor TP=2 pasó health; la llamada nombrada `read_file` no llegó a producir tool call. Misma observación que el intento 3: 474 prompt tokens, 256 completion tokens, 7,36 s, `finish_reason=length`, cero tool calls. El endpoint devolvió 200, el servidor limpió bien y ambas GPU quedaron libres. No hubo archivo escrito ni Tool-Eval.
- Esto no distingue parser de truncamiento. El `chat_template.jinja` local muestra `enable_thinking` habilitado por defecto, añade instrucciones `xhigh` cuando falta `reasoning_effort` y abre un `<think>` antes de generar. Ambos tests tenían `max_tokens=256`; la salida quedó truncada en ese límite.
- Recibo `receipts/q85-tool-canary-20261024T154635Z.json` (SHA-256 `d4f5769064d57da2dea9f97e20f9683ab2c744e62d14f378a89b6a722072f152`) y log redacted mode 0600 `receipts/q85-server-boot-20261024T154643Z.log` (SHA-256 `9043fd64eb1231c43a670f0c4bafb3f7573381650370fe3816ed98eb3803d8d7`).
- Siguiente cambio único: conservar llamadas nombradas, fixture y límite de salida, pero pasar `chat_template_kwargs={"enable_thinking": false}`. vLLM 0.31 acepta estos kwargs por request; si esto tampoco produce la llamada, se bloqueará Tool-Eval para esta configuración hasta revisar template/parser/prompt con un test nuevo.


## Avance Q85 · 2026-10-24T14:37:34Z

- Código oficial fijado en `/media/cristian/HDD extra/Modelos-eval/Q85-HyperQwen/HyperQwen`, commit `ce9615c4f2309be727407918a6c979bd67968069`.
- Compose CPU-only válido. Readback de config confirma imagen por digest, `GPU_COUNT=2`, reserva de dos dispositivos y `--tensor-parallel-size 2`; puerto loopback `127.0.0.1:18142`; modelos y caché en HDD; logs limitados a 2×100 MB; candidato sin restart automático. GUI preservada.
- Docker almacena contenido en `/var/lib/containerd` (35,0 GB libres); su root `/var/lib/docker` está en `/` (10,2 GB libres). Hay 0 contenedores activos, 2 vLLM detenidos y no hay listener en 18142 ni servidor de inferencia.
- Se ajustó el piso post-pull de containerd de 20 GiB a 18 GiB porque el tamaño registrado incluye 4,668 GB comprimidos más ~9,5 GB desempaquetados. Se mantiene el piso de raíz ≥8 GiB y HDD ≥20 GiB. El pull sólo sigue si la comprobación inmediata confirma margen; si el post-pull queda bajo 18 GiB, parar antes de modelo/prepare/GPU.
- El candidato aún no se descargó; no se ejecutó build, prepare, inferencia ni uso de GPU. Recibo: `receipts/q85-compose-config-validated.json`.


## Avance Q85 · 2026-10-24T15:07:30Z

- Imagen HyperQwen verificada por digest; código pinned. Base Qwen3.8-27B descargada en HDD: los 9 archivos LFS publicados coinciden en tamaño y SHA-256. Drafter DFlash2 coincide con el hash publicado. Recibos: `receipts/base-model-hash-verification.json`, `receipts/drafter-hash-and-tmp-bind.json`, `receipts/hf-pinned-model-manifests.json`.
- `docker compose run prepare` terminó con `model ready`; CPU-only. `verify.sh --no-server` desde el servicio dual-GPU terminó `verify: OK (0 failures)`, incluyendo 8 shards preparados, tokenizer y DFlash2. Verificación explícita: CUDA_COUNT=2; GPU 0 y 1 son RTX 3090. Dos intentos previos fallaron solo por gates esperados (sin GPU en servicio prepare y sin servidor para `verify` normal); tras añadir API key local a `.env` modo 0600, el último verifier pasó. La clave no se guardó en recibos/logs.
- Control ASTRA confirmado por `LlamaCode.conf` (`lastLaunchId=sys-astra-iq2xs-default`) y recibo de instalación; hashes actuales de ambos shards coinciden con el fingerprint histórico.
- Postflight: `/` 10205052928 B; containerd 19767672832 B; HDD 35933433856 B; cero contenedores activos y puerto 18142 libre. No se ejecutó inferencia del modelo, canario ni suite Tool-Eval; no hay resultados de calidad/TPS.
- Próximo gate: iniciar solo el servidor candidato TP=2 tras releer instrucciones, lock, espacio y ausencia de otro servidor; registrar arranque frío y KV pool, luego ejecutar canario de tools. La suite emparejada corre solo si el canario pasa.
- Recibo: `receipts/q85-dual-gpu-runtime-preflight.json`.


## Canario · intento 5 · 2026-10-24T15:50:28–15:50:35Z

- El servidor vLLM 0.31 pasó health y `/v1/models` con TP=2 en ambas RTX 3090; el servicio se detuvo y el puerto 18142 quedó libre.
- Con `tool_choice` nombrado y `enable_thinking=false`, el modelo emitió un `read_file` (438 tokens de prompt, 256 de completion, 7,30 s, `finish_reason=length`), pero su argumento de ruta no coincidió con `source.txt`. La ruta generada no se guardó. No se leyó ni escribió el fixture y no se ejecutó Tool-Eval.
- El resultado muestra que thinking-off permitió emitir la llamada, pero ésta no cumplió el contrato. No es resultado de calidad/velocidad ni evidencia de inferioridad general.
- Canario `receipts/q85-tool-canary-20261024T155028Z.json` SHA-256 `61d1b83b27faf1f7862e0eea06c716c4748f8d7ab1751e16f2adba690988018c`; log redacted modo 0600 SHA-256 `2e431bdeafc679b5c6265f785bda14239559e2f3cb2994f4c8ccbb16db80adb8`. Resultado normalizado `receipts/q85-tool-canary-attempt-05-result.json`.

## Canario · intento 6 preregistrado · 2026-10-24T15:56:31Z

- Diagnóstico de una sola variable frente al intento 5: agregar `enum` al JSON Schema de `path` (`source.txt` para lectura y `result.txt` para escritura). Se conserva named choice, thinking-off, TP=2, KV pin 3 GB/worker, DFlash2, fixture, sampling, seed y topes de tokens.
- El recibo incluirá sólo metadatos y booleanos/tipos de validación; no almacenará ruta, argumentos, contenido de respuesta ni clave. El runner y wrapper quedaron fijados por SHA-256 `08e63592c79ba460089e485e823299474bc4223ed82f3d3d37825050d286ad40` y `911950d0291c27dd8385d2acd6435ed2ce49557775941c84270ce09fa3ed6056`. AST, enum y `bash -n` pasan.
- Una corrida, sin reintento automático ni Tool-Eval. Aunque pase, todavía hará falta un canario `tool_choice=auto` antes de habilitar la suite. Preregistro: `receipts/q85-tool-canary-attempt-06-preregistration.json`.


## Canario · intento 6 · 2026-10-24T16:00:07–16:01:08Z

- La unidad transitoria inició el contenedor TP=2, pero vLLM rechazó el worker antes de health: GPU0 tenía 21,86/23,61 GiB libres y solicitaba 21,95 GiB con `GPU_UTIL=0,93` (faltaron ~92 MiB). No se enviaron requests; el schema enum no llegó a evaluarse y no hubo Tool-Eval.
- La captura del preflight a 15:59:50Z había mostrado 22.764 MiB libres; la diferencia confirma que el margen era inestable con el escritorio activo. El wrapper guardó log redacted modo 0600 y detuvo el contenedor; a 16:01:50Z Docker no tenía contenedores activos y 18142 estaba libre.
- Log `receipts/q85-server-boot-20261024T160108Z.log`, SHA-256 `3260b002130417ec75d1a3d71754761bca66ed468a7d38af11e734d92caad82d`; recibo normalizado `receipts/q85-tool-canary-attempt-06-result.json`. Sin benchmark ni inferencia de calidad.

## Canario · intento 7 preregistrado · 2026-10-24T16:03:47Z

- Un cambio controlado frente al intento 6: `GPU_UTIL=0,91` por override de entorno de la unidad, sin editar el Compose fijado ni `.env`. El objetivo es añadir margen al compositor de escritorio; TP=2/ambas 3090, KV 3 GB/worker, DFlash2, contexto, enum, named, thinking-off, fixture, sampling, seed y límites quedan fijos.
- A 0,91 la reserva estimada es ~21,49 GiB por GPU; frente a los 21,86 GiB que vLLM observó en GPU0 quedarían ~0,37 GiB. El preflight se repite antes del arranque y una nueva negativa detendrá esta corrida sin reintento automático.
- Una corrida; no Tool-Eval hasta un canario válido y una prueba posterior con selección `auto`. Preregistro `receipts/q85-tool-canary-attempt-07-preregistration.json`.


## Corrección de configuración · intentos 6–7 · 2026-10-24T16:06:29Z

- Auditoría posterior del comando systemd y del `docker compose config` reveló que la unidad del intento 6 no recibió `KV_MEM=3000000000`; Compose resolvió `single.environment.KV_MEM` vacío. La preregistración esperaba KV pin de 3 GB, por lo que el intento 6 queda clasificado como desviación de configuración y fallo de startup; el error de admisión de GPU0 fue real, pero no se evaluó el perfil preregistrado ni el schema enum. Recibo de corrección `receipts/q85-tool-canary-attempt-07-preregistration-amendment-01.json`.
- Antes de ejecutar intento 7 se añadió al overlay local `compose.q85.yaml` la propagación explícita `GPU_UTIL: ${GPU_UTIL:-0.93}`; su SHA-256 es `19f7eeda73463e794ec853708d1fa4fe60a165c39c049583977b9fd77a8967b6` (antes `70fb2a3ac22e1b00fbccb9c4a3bd557fd96e51e373d586738d71b73d5017d7d0`). No se tocó `.env`, imagen ni fuente upstream. Intento 7 debe fijar `GPU_UTIL=0.91` y `KV_MEM=3000000000` en el unit environment y confirmar ambos en config readback antes de GPU.


## Intento 7 · gate de entorno Compose verificado · 2026-10-24T16:08:36Z

- Readback CPU-only dentro de una unidad transient user-systemd: `GPU_UTIL=0.91`, `KV_MEM=3000000000`, `GPU_COUNT=2`, `--tensor-parallel-size 2`, `MAX_LEN=65536`, `MAX_SEQS=8`. No se imprimieron claves ni valores secretos.
- La unidad de intento 7 ejecutará primero un guard que falla cerrado si cualquiera de esos valores difiere y luego el runner preregistrado. SHA del guard `0e062973c5bc3106bb83f55b45ed26519ad2c0ec97b0a137c3ff9d612e6911d1`; overlay pinned local `19f7eeda73463e794ec853708d1fa4fe60a165c39c049583977b9fd77a8967b6`.
- Recibo `receipts/q85-attempt07-compose-readback.json`. Esto sólo habilita el siguiente preflight; aún no hay inferencia nueva ni resultado del canario.


## Intento 7 · error de invocación antes del servidor · 2026-10-24T16:09:54Z

- El gate CPU-only de Compose volvió a pasar (TP=2, `GPU_COUNT=2`, `GPU_UTIL=0.91`, `KV_MEM=3000000000`), pero systemd terminó con código 126 porque el helper hizo `exec` directo a un script sin bit ejecutable. No se inició contenedor, servidor, inferencia, requests ni Tool-Eval.
- Reparación de launcher solamente: invocar el runner con `/usr/bin/bash`; hash actualizado `6919d4d461ca90b86aee195596af0e539f2c307968b5a7828e1098d8b00c6b48`. El tratamiento del canario no cambió. Repetir lectura de instrucciones, lock, preflight fresco y gate de Compose antes de ejecutar la única corrida preregistrada. Recibos `receipts/q85-attempt07-launcher-failure.json` y `receipts/q85-tool-canary-attempt-07-preregistration-amendment-02.json`.


## Canario · intento 7 · resultado · 2026-10-24T16:11:22Z–2026-10-24T16:11:29ZZ

- Arrancó y pasó health con TP=2 en ambas RTX 3090; el startup frío tomó ~72 s. El guard systemd resolvió `GPU_COUNT=2`, `--tensor-parallel-size 2`, `GPU_UTIL=0.91` y `KV_MEM=3000000000`; preflight mostró 2×3090/128 GB, GPU0 22.998 MiB libres y GPU1 24.068 MiB, sin otro servidor.
- Canario nombrado thinking-off: una llamada `read_file`, 453 tokens de prompt, 256 de completion, 6.881 s y `finish_reason=length`. El argumento era string, pero no coincidió con el enum; por eso el fixture no se leyó ni se escribió. No se ejecutó Tool-Eval ni benchmark comparativo. Los argumentos/respuesta crudos siguen omitidos.
- Limpieza PASS: contenedor/parada propia, puerto 18142 libre y memoria GPU regresó al uso de escritorio. Recibos `receipts/q85-tool-canary-attempt-07-result.json`, `receipts/q85-tool-canary-20261024T161122Z.json`, preflight 07-2 y log redacted SHA `460804e5b411265d79bab1ab6d0fd8c6cd2dfee1de81eb7b85594ee33ea3108f`.
- El log registra `tool_strict_level=parameter`, pero el resultado viola el esquema esperado. vLLM 0.31 documenta schema constraints en llamadas nombradas; esta observación local apunta a revisar la interacción concreta modelo/parser/esquema, no a una conclusión general del runtime: https://docs.vllm.ai/en/v0.31.0/features/tool_calling/.
- Siguiente diagnóstico propuesto, aún no ejecutado: una sola variable, ampliar `max_tokens` 256→512; mantener TP=2 y todo lo demás fijo para distinguir truncación de incompatibilidad de tool args.


## Intento 8 preregistrado · pendiente · 2026-10-24T16:16:52Z

Se fijó un único diagnóstico de truncación: subir el max_tokens de las dos etapas named de 256 a 512, manteniendo TP=2 en ambas GPU y el resto igual. No inició; no implica resultado ni habilita Tool-Eval. Preregistro `receipts/q85-tool-canary-attempt-08-preregistration.json`.


## Canario · intento 8 · resultado · 2026-10-24T16:19:04Z–2026-10-24T16:19:12ZZ

- TP=2 pasó health con las dos RTX 3090; GPU_UTIL=.91, KV_MEM=3GB/worker, GPU_COUNT=2; el guard de Compose confirmó el token cap 512.
- Named read_file: una llamada, 453 prompt tokens, 309 completion, 8.179 s, `finish_reason=stop`; path fuera del enum. El fixture no se leyó ni escribió y no corrió Tool-Eval. Subir 256→512 descartó el tope como explicación suficiente; no es un score ni benchmark.
- Cleanup PASS, puerto 18142 libre, VRAM retornó al escritorio. Recibos `receipts/q85-tool-canary-attempt-08-result.json`, canary 161904Z, preflight 08 y boot log SHA `c37686541035b21321a5676ab8e7773fef7b20d68ff10189a690e9f1dfb2a487`.
- No repetir el mismo loop sin cambio material. Se preregistrará un canario prompt-only que enuncia literalmente las rutas permitidas; si falla, bloquear agent tool loop y no correr Tool-Eval.


## Intento 9 preregistrado · pendiente · 2026-10-24T16:21:35Z

Canario prompt-only de alineación al esquema, TP=2; pendiente de preregistro y preflight. No habilita Tool-Eval por sí mismo.


## Canario · intento 9 · 2026-10-24T16:24–16:26Z

- Corrida en HyperQwen TP=2, ambas RTX 3090; Compose confirmó `GPU_UTIL=0.91`, `KV_MEM=3000000000`, `GPU_COUNT=2`, `--tensor-parallel-size 2`. Health y `/v1/models` pasaron. Durante carga se observaron ambas tarjetas con ~14 GB y ~13 GB ocupados; después de cleanup quedaron ~1.05 GB y 110 MiB usados por el escritorio.
- El cambio preregistrado de prompt alineando rutas exactas corrigió el argumento de `read_file`: 489/26 tokens, 1.214 ms, `finish_reason=stop`, path válido. `write_file` emitió una llamada, pero alcanzó el tope de 512 tokens (`finish_reason=length`; 561 prompt, 512 completion, 12.856 ms) con path inválido y `content` no-string. El fixture temporal no se escribió y el grader no se ejecutó. No se almacenaron rutas, argumentos ni texto bruto.
- Cleanup PASS: unidad detenida, cero contenedores, puerto 18142 libre, temperaturas 49/30 °C y GPU memory regresó al nivel de escritorio. No se ejecutó `tool_choice=auto`, Tool-Eval, ni benchmark de calidad/velocidad. La conclusión se limita a este canario y perfil; no es resultado comparativo. Por la política preregistrada, bloquear el loop hasta cambio material del parser/runtime.
- Recibos: `receipts/q85-tool-canary-attempt-09-preregistration.json`, `...attempt-09-preflight.json`, `...attempt-09-result.json`, canario `q85-tool-canary-20261024T162554Z.json` SHA-256 `36ad57604a6d5296eda9daed31975e6446e05a79f0076d61a5d7eb4a6a094a35`, log redacted `q85-server-boot-20261024T162608Z.log` SHA-256 `14ebc0f8236e5f8daa3eeb6167a6ab5043d9c48733197bc098d2fc354f909649`.
