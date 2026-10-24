# Q85 · HyperQwen Qwen3.8-27B en dual RTX 3090

## Pregunta

¿HyperQwen con Qwen3.8-27B W4A16 y DFlash2, ejecutado con TP=2 en ambas RTX 3090, mejora la calidad y el tiempo end-to-end de coding/agentes frente al ASTRA Flash-Next configurado por defecto en LlamaCode, sin empeorar seguridad ni herramientas?

## Diseño preregistrado

### Candidato y revisiones fijadas

- HyperQwen `syv-ai/HyperQwen` commit `ce9615c4f2309be727407918a6c979bd67968069`.
- Imagen Linux/amd64 `ghcr.io/syv-ai/hyperqwen:sha-ce9615c`; manifest digest `sha256:0acd4b9625473e51c9bab56406c30814bc0d0d7e0a38deb408c62664b5a77669`. El manifiesto reporta 4.667.917.348 B comprimidos; la documentación del proyecto estima ~9,5 GB desplegados.
- Base `dbirks/Qwen3.8-27B-W4A16-AutoRound`, HF revision `1f05c441c4e64ae0549de44fa9ea5a6d43610314`, licencia Apache-2.0, ~19.472.769.333 B remotos.
- Drafter preparado `syvai/Qwen3.8-27B-DFlash2-W4A16`, HF revision `4d30ec736ffc6b8688dc2ae2b502d9b48bdec279`, licencia Apache-2.0, 1.280.633.960 B. Su archivo safetensors publicado tiene SHA-256 `ec26996e6a0745ab5edb857117220ce1e219ad524f71e6e149b703804947d8e7`.
- Descargar base y drafter sólo desde esas revisiones; verificar hashes/tamaños antes de `prepare`. No permitir que el script descargue `main` sin pin. `FAST_VARIANT=0`; conservar DFlash2.

### Perfil de servicio

- `GPU_COUNT=2`, `EXTRA_ARGS="--tensor-parallel-size 2"`; ambas RTX 3090. No usar TP=1 en la comparación principal, no modificar drivers/P2P/NVLink.
- Single-user, `SPEC=dflash2`, `PREFIX_CACHE=1`, `DFLASH_TOKENS=7`, `CTX=fast`, `MAX_LEN=65536`, `MAX_SEQS=8`, `GPU_UTIL=0.93`, visión apagada, parser `qwen3_coder`, salida de tools estructurada. Registrar el KV pool por GPU y fijar `KV_MEM` antes de medir, siguiendo la documentación multi-GPU. Si no puede fijarse sin reducir el perfil a una configuración distinta, detener y corregir el preregistro.
- API sólo en loopback, puerto 18142; `.env` local con permisos `0600` y API key aleatoria; no guardar la clave en logs/recibos. Repositorio, modelos, cache, `/tmp` y resultados voluminosos en HDD extra; logs del contenedor limitados a 2×100 MB. `prepare` es CPU-only; la inferencia usa las dos GPU.
- Ejecutar el runner y monitor como unidades user-systemd durables con identidad Q85, journal y estado de una sola ejecución; no relanzar automáticamente una corrida incompleta para evitar duplicar efectos. No imponer un límite de memoria que cambie la prueba.

### Control y comparabilidad

- Control confirmado: `LlamaCode.conf` tiene `lastLaunchId=sys-astra-iq2xs-default`, el perfil marcado como nuevo default por el recibo de instalación Q-20261013. Config `/home/cristian/.config/LlamaCode/astra-iq2xs-strata.json`, SHA-256 `b4a55b263ad8bf1df809afb76603c23d55c1471c2e7cac6997e979bd3ad5e38f`; Flash-Next IQ2_XS, GPU `[0,1]`, `layer_split=auto`, sampling `0.6/0.95/20/0/1/0`. Ambos hashes actuales coinciden con el recibo: `92cee27ae5bbadcd732416a0f7a7f0acc092399dbbe8f5a5efa707c2ec0a49d7` y `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`.
- El control permite `--max-context 1048576`, `--yarn-orig-ctx 262144`, KV int8 y 32768 residentes. Los ensayos de coding sólo cuentan como comparables si todos los prompts del fixture caben en 65536 tokens. Esto no valida ni reemplaza el perfil ASTRA de hasta 1M; el contexto largo queda en accionable separado.
- Gate de control aprobado antes de inferencia: config/fingerprint y hashes de ambos shards ASTRA verificados; `lastLaunchId` confirma el default local. Si el usuario identifica otro servidor productivo, añadir ese control antes de emitir un claim de adopción.
- Harness congelado: Tool-Eval Bench 2.8.0, commit `0a1ba68c7709f429298bc92417a9e003f61de4e3`, Hard Mode TC-70–TC-97, seeds 42/43/44, `variant-seed=20261010`, temperature 0.6, top-p 0.95, top-k 20, min-p 0, repeat-penalty 1, reasoning `medium`, timeout 120 s, max turns 8, parallel 1. Reutilizar las tareas y grader congelados de Q29; validar su hash antes de correr.
- Primero un canario aislado de lectura→escritura para comprobar `tool_choice`, parser y respuesta final. Si no produce la llamada/archivo esperado o falla el cleanup, no correr la suite.
- Después 3 pares de seeds, un servidor a la vez y sin procesos de inferencia ajenos. Orden balanceado: seed 42 ASTRA→HyperQwen, 43 HyperQwen→ASTRA, 44 ASTRA→HyperQwen. Calentar el servidor antes de puntuar; registrar por separado carga/JIT y latencia de servicio. Medir score, pass/fail por escenario, final correcto, reparaciones, E2E por seed, TTFT, prefill/decode, KV pool, VRAM por tarjeta, RAM, temperaturas, OOM y estabilidad.

## Umbrales

- Una decisión de piloto requiere 3/3 pares válidos, media HyperQwen ≥3 puntos sobre ASTRA, gana al menos 2/3 seeds, no falla TC-74/TC-84/TC-92 y no produce errores nuevos de herramientas/aislamiento.
- Un claim de velocidad requiere además una reducción ≥10% en mediana E2E hasta respuesta correcta y calidad no inferior a ASTRA por más de 1 punto. Un piloto no cambia el perfil predeterminado: una promoción necesita una confirmación posterior con semillas nuevas.
- Si no pasa calidad/seguridad, no se completa la suite de velocidad/concurrencia y no se adopta. TP=1 queda opcional, después del brazo primario, sólo si su medición puede cambiar la decisión de asignación.

## Guardas y gates de espacio

- Pre-pull: comprobar config Compose resuelta, paths reales, port 18142 libre y cero inference servers; GUI no se cierra ni cuenta como servidor. No usar ni terminar procesos ajenos.
- Containerd pre-pull: exigir ≥20 GiB libres. Post-pull: exigir ≥18 GiB. El manifiesto registra 4.668 GB comprimidos y el proyecto estima ~9,5 GB desempaquetados; contando ambas copias, el remanente conservador actual sería ~20,8 GB (19,4 GiB), por lo que el gate inicial de 20 GiB post-pull no era alcanzable. Enmienda Q85: 18 GiB deja ~1,4 GiB sobre ese cálculo; todos los modelos y la cache se montan desde HDD, `/` queda para metadata/logs acotados y conserva ≥8 GiB, y se aborta si el espacio medido cae debajo de 18 GiB. HDD extra para base/preparación/drafter/cache: exigir ≥20 GiB después de cada paso.
- Último estado observado antes de Q85: containerd 34.984.570.880 B libres; HDD extra 60.377.710.592 B; `/` 10.213.027.840 B. Image estimada ~9,5 GB y modelos ~20,8 GB más outputs temporales. Repetir `df` inmediatamente antes y después de cada descarga/preparación; sin limpieza automática ni `docker prune`.
- Antes de cada fase GPU: releer `AGENTS.md`, `README.md`, `WORK_QUEUE.md`, verificar token Q85 y lock, hacer `nvidia-smi`/topología sin matar GUI, comprobar ausencia de inference servers/listeners y medir RAM/espacio. Sólo iniciar nuestro server después de pasar el gate; terminarlo entre brazos.
- Abortos: listener ajeno, control/hashes cambiados, menos de 20 GiB en los filesystems de pesos/imagen, `/` <8 GiB, OOM, corrupción de salida, temperatura >85 °C o server persistente tras cleanup. Guardar logs y resultado parcial; no reanudar automáticamente.

## Fuentes/evidencia

- HyperQwen pinned source: https://github.com/syv-ai/HyperQwen/tree/ce9615c4f2309be727407918a6c979bd67968069
- Multi-GPU and KV pin: https://github.com/syv-ai/HyperQwen/blob/main/docs/multi-gpu.md
- Docker sizing/paths: https://github.com/syv-ai/HyperQwen/blob/main/docs/docker.md
- Single-user DFlash2 profile: https://github.com/syv-ai/HyperQwen/blob/main/single-user/README.md
- Product control: local config plus prior Q72 ASTRA canary and Q29 matched Tool-Eval evidence.
- Reported upstream rates remain hypotheses; do not treat them as local outcomes.

## Protocolo del canario preregistrado · 2026-10-24T15:13:38Z

- Antes de Tool-Eval se ejecutará una sola interacción secuencial en el servidor TP=2: `read_file("source.txt")` → resultado real de lectura → `write_file("result.txt", contenido leído)` → respuesta final no vacía.
- Fixture fijo sin newline: `Q85-CANARY-READ-THEN-WRITE-314159`. El workspace será un directorio temporal único bajo el HDD extra; el adaptador sólo permite las rutas exactas `source.txt` y `result.txt`, y elimina el directorio al cerrar.
- Sampling: temp 0.6, top-p 0.95, top-k 20, min-p 0.0, seed 42; `tool_choice=auto`, `parallel_tool_calls=false`; hasta 256 tokens por llamada y 128 para el cierre. Una corrida, sin reintentos.
- Pasa sólo si el servidor health/model endpoint responde, produce exactamente la secuencia esperada con IDs de llamada presentes, escribe bytes idénticos al fixture, devuelve respuesta final no vacía y el wrapper detiene el contenedor al terminar. En cualquier fallo no se ejecuta Tool-Eval.
- Registrar latencia de cada llamada, tokens reportados, hashes y bytes del archivo; no guardar contenido de respuesta, claves ni datos fuera del fixture. Éste es un gate del protocolo de tools de HyperQwen, no un test end-to-end de LlamaCode ni una comparación de calidad/rendimiento.
- Scripts preregistrados: `runner/q85_tool_canary.py` SHA-256 `4e4f11a835e7f51ca7bf5ca540e2fb35453e8f299e8a97780780d01ba5ecf27c`; para el intento 2, `runner/run_q85_tp2_canary.sh` SHA-256 `b0ff13ab4afe1074b7fcb4ab41ebd9dbf33029f603e6a95df2ed177469b383b2` (wrapper reforzado tras el fallo del intento 1 para guardar logs redacted y detectar OOM/worker death). Python AST y `bash -n` pasan.
- El intento 1 sí inició el servidor TP=2 pero falló antes de health con CUDA OOM; no emitió requests de canario ni comparaciones.

## Reintento 2 preregistrado · 2026-10-24T15:25:30Z

- Diferencia única frente al intento 1: fijar `KV_MEM=3000000000` bytes por worker TP, manteniendo imagen, revisiones, TP=2, 65.536 tokens, 8 secuencias, GPU_UTIL=0.93, DFlash2 y sampling. El nuevo override Compose mapea `KV_MEM` explícitamente; el readback de `docker compose config` confirma `3000000000` en el servicio `single`.
- Motivo: el primer startup confirmó pool sin pin y acabó en OOM; la guía multi-GPU del commit fijado recomienda leer/pinear el KV en TP>1. Los 3 GB son una asignación diagnóstica conservadora, no un óptimo medido; la corrida fallida no permite afirmar la causa definitiva.
- Un solo arranque y canario; no retry automático. El wrapper actualizado captura log redacted antes de `compose down`, lo deja en modo `0600` y aborta si encuentra errores CUDA/worker incluso cuando el contenedor aún aparece `running`.
- Receipt del protocolo y hashes: `receipts/q85-tool-canary-attempt-02-preregistration.json`; readback Compose: `receipts/q85-compose-kv-pin-config-validated.json`. Si health/KV falla, detener y analizar el log antes de cambiar otra variable. Si canario pasa, se puede continuar al A/B con el KV fijado y medido; no promover el perfil.

## Diagnóstico de tool-call nombrada

- El intento 3 pasó health pero en `tool_choice=auto` emitió cero tool calls y alcanzó `max_tokens=256`. No repetir el mismo fixture auto como si fuera independiente.
- Preregistrar una llamada de diagnóstico con `tool_choice` nombrada para cada etapa (`read_file`, `write_file`), seguida por `tool_choice=none` para el texto final. Mantener el fixture, seed, sampling, modelo, TP=2, GPU_UTIL=0.93, KV pin y DFlash2 iguales. Guardar sólo metadatos de respuesta (finish reason, tokens, longitud de texto y nombres de tools), nunca el contenido bruto.
- Esta prueba determina si el servidor/parser puede emitir una llamada estructurada cuando el API la exige; no prueba que el modelo elija tools correctamente en `auto`, por lo que no habilita Tool-Eval ni adopción por sí sola. vLLM documenta las llamadas nombradas: https://docs.vllm.ai/en/latest/features/tool_calling/.

## Diagnóstico de presupuesto de razonamiento

- El intento 4 también alcanzó `max_tokens=256` con `finish_reason=length`. La plantilla local activa razonamiento por defecto y solicita xhigh si no recibe `reasoning_effort`; no se había desactivado en ninguno de los canarios.
- Preregistrar intento 5: repetir llamada nombrada con el mismo modelo, TP=2, KV=3 GB, GPU_UTIL=0.93, DFlash2, fixture, seed, sampling y `max_tokens`; única diferencia `chat_template_kwargs={"enable_thinking": false}`. Registrar `enableThinking` y resúmenes seguros de cada response. vLLM 0.31 documenta `chat_template_kwargs` por request y el ejemplo `enable_thinking=false`: https://docs.vllm.ai/en/v0.31.0/api/vllm/entrypoints/openai/chat_completion/protocol/ y https://docs.vllm.ai/en/v0.31.0/api/vllm/entrypoints/launchers/cli_args/.
- Aunque pase, esto sólo valida el loop estructurado en modo thinking-off; `auto` aún necesita una prueba funcional. No correr Tool-Eval ni inferir superioridad todavía.

## Intento 2: salida antes de health y siguiente paso

- El KV pin sí llegó a vLLM. El rechazo fue el gate previo de memoria: GPU0 tenía 21.91 GiB libres y `GPU_UTIL=0.93` pedía 21.95 GiB; diferencia ~41 MiB. `OOMKilled=false`, sin generación ni canario.
- Se terminó sólo el proceso oculto `artcraft-launcher` (209 MiB GPU reportados; ~232 MiB liberados en la lectura posterior), con autorización explícita del usuario. La GUI/Xorg/Codex siguen abiertos. No se mató ningún servidor de inferencia ajeno.
- Se arregló el runner para buscar contenedores detenidos (`docker compose ps --all -q`) y así guardar logs/salir inmediatamente si un worker cae. Intento 3 se preregistra con el mismo perfil TP=2/KV=3 GB/GPU_UTIL=0.93; única diferencia de entorno es haber liberado ese proceso no-inferencia, y se conserva el límite de un solo arranque sin retry automático.

## Validación del paso systemd · 2026-10-24T15:33:19Z

- La lectura de `docker compose config` desde una unidad transient user-systemd pasó y confirmó `KV_MEM=3000000000`, `--tensor-parallel-size 2` y `GPU_COUNT=2`. Fue CPU-only; no inició servicio ni inferencia. Un intento previo usó un shell de login que cambió el directorio a `/home/cristian` y falló antes de Compose; el comando corregido fijó `WorkingDirectory` y pasó. No hubo cambios en el estado del modelo.


## Intento 6 preregistrado · enum de rutas seguras

- Pregunta: ¿el canario nombrado puede completar el mismo read→write si el schema limita `path` a los nombres de archivo exactos del fixture?
- Diferencia controlada frente al intento 5: `path.enum=["source.txt"]` para `read_file` y `path.enum=["result.txt"]` para `write_file`. No cambia el selector de herramienta, thinking-off, modelo, TP=2/ambas 3090, `KV_MEM=3000000000`, GPU_UTIL=0.93, DFlash2, fixture, sampling, seed ni límites de tokens.
- El runner registra `fixturePathEnum=true` y resúmenes seguros (tipo y coincidencia booleana; para write, también si el contenido coincide), sin guardar valores de ruta, argumentos o texto generado. AST/enum/`bash -n` pasan; hashes y criterios están en `receipts/q85-tool-canary-attempt-06-preregistration.json`.
- Ejecutar una sola vez tras un preflight fresco de lock, almacenamiento, GPU y ausencia de servidores/listeners. Si pasa, el próximo gate será otro canario con `tool_choice=auto`, sin enum en la ruta productiva; si falla, analizar el recibo antes de tocar otra variable. Tool-Eval no corre hasta que el camino auto haga lectura, escritura y finalización correctamente.


## Intento 7 preregistrado · margen de VRAM con escritorio activo

- El intento 6 no evaluó el enum: vLLM rechazó el startup porque GPU0 tenía 21,86 GiB libres frente a 21,95 GiB pedidos por `GPU_UTIL=0,93`. El preflight anterior había pasado, por lo que se requiere más margen para variación del compositor.
- Única variable: override de proceso `GPU_UTIL=0,91` para el servicio Compose. No se cambia `.env`, Compose pinned, modelos ni runtime; se mantiene TP=2 en ambas RTX 3090 y todas las demás variables del canario. La reserva estimada baja a ~21,49 GiB por placa.
- Repetir lock/README/WQ, Compose y preflight de storage, listeners, RAM, VRAM, temperatura y dos GPUs. Una sola corrida con enum path; si llega a health, ejecutar el canario. Sin retry automático ni Tool-Eval si falla. Este valor queda registrado para todas las comparaciones posteriores si el perfil avanza.


## Enmienda preregistrada 7.1 · corrección de env injection · 2026-10-24T16:06:29Z

- Se detectó que intento 6 omitió `KV_MEM` en `systemd-run`: el config readback posterior mostró valor vacío, contra la expectativa de 3.000.000.000 B/worker. Ese arranque no cuenta como ejecución del perfil preregistrado ni evalúa el enum.
- Antes del intento 7, el overlay local pasó a mapear `GPU_UTIL` desde el entorno al servicio. El unit debe establecer `GPU_UTIL=0.91` y `KV_MEM=3000000000`; un readback CPU-only de Compose debe confirmar ambos valores, imagen pinned y TP=2 antes de iniciar GPU. La `.env` permanece intacta en 0.93 para otros usos.
- El tratamiento experimental sigue siendo GPU_UTIL 0.91 frente al perfil preregistrado KV-pinned; pasar KV_MEM explícitamente restaura una constante que el intento 6 debía tener. Enmienda `receipts/q85-tool-canary-attempt-07-preregistration-amendment-01.json`.


## Intento 7 · gate de Compose resuelto

A 2026-10-24T16:08:36Z, una unidad transient user-systemd propagó y resolvió por Compose `GPU_UTIL=0.91`, `KV_MEM=3000000000`, `GPU_COUNT=2` y `--tensor-parallel-size 2`. Se añadió `runner/run_q85_attempt07_with_config_gate.sh` para repetir el readback y abortar antes de GPU ante cualquier discrepancia; hash `0e062973c5bc3106bb83f55b45ed26519ad2c0ec97b0a137c3ff9d612e6911d1`. Recibo `receipts/q85-attempt07-compose-readback.json`. El próximo paso es un preflight fresco en ambas 3090; una sola corrida, sin reintentos automáticos.


## Intento 7 · error de invocación antes del servidor · 2026-10-24T16:09:54Z

- El gate CPU-only de Compose volvió a pasar (TP=2, `GPU_COUNT=2`, `GPU_UTIL=0.91`, `KV_MEM=3000000000`), pero systemd terminó con código 126 porque el helper hizo `exec` directo a un script sin bit ejecutable. No se inició contenedor, servidor, inferencia, requests ni Tool-Eval.
- Reparación de launcher solamente: invocar el runner con `/usr/bin/bash`; hash actualizado `6919d4d461ca90b86aee195596af0e539f2c307968b5a7828e1098d8b00c6b48`. El tratamiento del canario no cambió. Repetir lectura de instrucciones, lock, preflight fresco y gate de Compose antes de ejecutar la única corrida preregistrada. Recibos `receipts/q85-attempt07-launcher-failure.json` y `receipts/q85-tool-canary-attempt-07-preregistration-amendment-02.json`.


## Diagnóstico posterior al intento 7 · 2026-10-24T16:15:30Z

El canario TP=2 pasó health y usó ambas 3090, pero el named `read_file` terminó a 256 tokens con argumento path fuera de enum. No ejecutar Tool-Eval. La documentación vLLM 0.31 especifica schema constraints para llamadas nombradas; por ello el fallo local requiere separar truncación de una interacción modelo/parser/esquema concreta, sin generalizar la causa. Candidato a siguiente experimento, una sola diferencia: `max_tokens=512` en el mismo canario; conservar TP=2, enum, GPU_UTIL=.91, KV pin, DFlash2, thinking-off, sampling y seed. Ejecutar sólo tras preregistro y preflight fresco. Fuente primaria: https://docs.vllm.ai/en/v0.31.0/features/tool_calling/.


## Intento 8 preregistrado · presupuesto de tool-call 512 · 2026-10-24T16:16:52Z

- El intento 7 usó ambas RTX 3090 y pasó health, pero el `read_file` nombrado terminó a 256 tokens y no cumplió el enum. Se preregistra una sola diferencia: `max_tokens=512` para ambas etapas de tool; se mantienen TP=2, GPU_UTIL=.91, KV pin 3 GB/worker, modelo, DFlash2, enum, thinking-off, fixture, sampling y seed.
- Hipótesis: el límite de salida pudo truncar la llamada; el cambio puede confirmar o descartar esa explicación. Si vuelve a fallar el contrato, no correr Tool-Eval ni otro retry del mismo loop sin identificar un cambio material.
- vLLM 0.31 documenta constrained outputs para named tool calls y schema params: https://docs.vllm.ai/en/v0.31.0/features/tool_calling/. El HyperQwen pinned README documenta `qwen3_coder` + `tool_strict_level=parameter`; el log local confirma ese nivel. Resultado previo local sigue siendo específico de esta integración.
- Preregistro `receipts/q85-tool-canary-attempt-08-preregistration.json`; runner Python `378ec45eeed16a393c863f19f8d94754881f2600e4669e4c95215d8232b2c91e` y guard `168654da609f25f7bcd5bdde9061c0ffa42737f8f54455774026ab943532bd57`.


## Intento 9 preregistrado · alineación explícita del esquema · 2026-10-24T16:21:35Z

Intento 8 refutó que el límite de 256 tokens explicara el path: con 512 tokens, `finish_reason=stop` a 309 y pathMatchesEnum siguió false. El siguiente canario cambiará una sola cosa, agregando al system prompt las rutas exactas `source.txt` y `result.txt` sin prefijos/caracteres extra; TP=2 ambas 3090, .91 GPU_UTIL, KV=3GB/worker, DFlash2, enum, named, thinking-off, tokens 512, sampling/seed y fixture permanecen fijos. Una corrida. Si falla, bloquear herramientas hasta cambio de parser/runtime; no ejecutar Tool-Eval. vLLM 0.31 recomienda alinear prompt y schema: https://docs.vllm.ai/en/v0.31.0/features/tool_calling/.


## Resultado del intento 9 · 2026-10-24T16:26Z

La alineación explícita del prompt hizo válido el path de `read_file`, pero no completó el loop. `write_file` consumió sus 512 tokens y terminó por límite con path inválido y contenido no-string. Cleanup completo; fixture sin escribir. Se aplica la política preregistrada: parar canarios `named`/`auto` y Tool-Eval hasta un cambio material de parser/runtime. No hubo comparación de calidad/velocidad ni adopción. Ver `receipts/q85-tool-canary-attempt-09-result.json`.
