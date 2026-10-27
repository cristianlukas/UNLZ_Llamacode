# Q167 · Screen de generación de código HyperQwen vs SOL, sin tools

## Motivo y alcance

El usuario pidió reanudar las pruebas después de cerrar PeritoSoft. El escaneo actual no encontró la aplicación ni servidores de inferencia de PeritoSoft. Q85 ya demostró que HyperQwen no completa el contrato read/write en el canario; ese bloqueo sigue vigente para agentes y no se vuelve a ejecutar el mismo loop.

Q167 responde una pregunta distinta: **¿el perfil HyperQwen TP=2 merece un seguimiento como generador directo de código, sin tools, frente al perfil SOL?** Se usa el mismo fixture BCB-Hard-8 y un solo seed para filtrar. No evalúa herramientas, seguridad de agentes, contexto largo, adopción ni reemplazo general de SOL/ASTRA. Un pase sólo habilita una confirmación de tres seeds; no promueve perfiles.

## Perfiles fijados

**Control SOL:** Qwen3.8-27B Frozenlock AutoRound INT4/W4A8; vLLM v0.27.1 (imagen fijada por digest `sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967`); ambas RTX 3090, TP=2; `MAX_MODEL_LEN=262144`, `GPU_MEMORY_UTILIZATION=0.90`, `MAX_NUM_SEQS=8`, `MAX_NUM_BATCHED_TOKENS=8192`, MTP `SPEC_N=4`; pensamiento habilitado y `reasoning_effort=medium`. Sampling `temperature=0.6`, `top_p=0.95`, `top_k=20`, `min_p=0`, `repetition_penalty=1`, `presence_penalty=0`. Se inicia en contenedor aislado con loopback y nombre/proyecto Q167; los pesos se montan solo lectura y las cachés de compilación se separan en HDD extra. El servicio productivo no se reutiliza.

**Candidato HyperQwen:** HyperQwen commit `ce9615c4f2309be727407918a6c979bd67968069`, imagen `ghcr.io/syv-ai/hyperqwen@sha256:0acd4b9625473e51c9bab56406c30814bc0d0d7e0a38deb408c62664b5a77669`; `dbirks/Qwen3.8-27B-W4A16-AutoRound` revision `1f05c441c4e64ae0549de44fa9ea5a6d43610314` más drafter DFlash2 revision `4d30ec736ffc6b8688dc2ae2b502d9b48bdec279`. Ambas RTX 3090, TP=2; `GPU_UTIL=0.91`, `KV_MEM=3000000000` por worker, `MAX_LEN=65536`, `MAX_SEQS=8`, DFlash2 con 7 draft tokens, pensamiento habilitado. No se cambia código de producción ni drivers.

Ambos brazos usan el mismo prompt, fixture, orden preregistrado, seed `4242`, temperatura/top-p/top-k/min-p/repetition/presence y esfuerzo de razonamiento `medium` pasado al template Qwen. Se comparan perfiles completos; las diferencias de engine, cuantización y especulación forman parte del tratamiento, así que no se atribuye un efecto causal a los pesos por separado.

## Protocolo

- Fixture fijo: `artifacts/bigcodebench-hard-ubuntu-8.json`, SHA-256 `11279cde14113fc8527f141c53e14cb5ccf0dba65749081a4f914408e391c268`.
- Una pasada de cada perfil, 8 tareas y un seed. SOL recorre el orden del fixture; HyperQwen el orden inverso para reducir sesgo de orden. Servidores levantados uno por vez y detenidos inmediatamente al acabar su brazo.
- Una petición de calentamiento por servidor, fuera de puntuación. El runner transmite y califica la respuesta sin guardar contenido/código bruto. El grader queda en bubblewrap, PID namespace y seccomp de denegación de red; se guardan sólo estado, IDs, tiempos y conteos.
- Medición primaria: exactitud BCB-Hard-8 y mediana E2E por tarea entre IDs que ambos perfiles resuelvan. Registrar tokens y `TTFT`; prefill/decode sólo como proxies cliente si el endpoint entrega usage en streaming. No convertirlos en velocidad nativa del kernel.
- La orquestación corre como una unidad transitoria de `systemd --user` por brazo, con journal y recibos en disco. Si Codex se cierra, la corrida no depende del proceso de la app y puede retomarse consultando la unidad; cada unidad tiene duración máxima de seis horas, maneja SIGTERM con limpieza y termina solo sus grupos de proceso/Compose Q167. El cierre de grupo propio pasó un smoke con `sleep`; no se envían señales a procesos ajenos.
- Guardia de evaluación: el monitor AMD05/Q121 ya usado en Q127; muestreo continuo de RAM/PSI/OOM/cgroup/VRAM/temperatura. Sin límite artificial de RAM, sin presión inducida y sin matar procesos de escritorio. Sólo limpiar los servicios/containers Q167 propios.
- La descarga de pesos candidatos va a la carpeta de evaluación en HDD extra, revisión fijada y hashes LFS contrastados con el recibo Q85; no modifica ni borra ASTRA, SOL, PeritoSoft ni otros modelos. Requerir al menos 40 GiB libres allí tras descargar y los pisos de almacenamiento de Q85 antes de servir.

## Gate preregistrado

El screen continúa sólo si ambos brazos tienen 8/8 transportes, cero fallos del sandbox y cero respuestas vacías; HyperQwen queda como máximo una tarea por debajo de SOL; hay al menos seis tareas resueltas por ambos; y la mediana E2E de HyperQwen en las tareas emparejadas resueltas es al menos 20% menor. Si falla cualquier gate, cerrar Q167 sin ampliar seeds. Si todos pasan, registrar un nuevo preregistro de tres seeds antes de ejecutarlos. Ningún resultado de Q167 anula el bloqueo de tools de Q85 ni autoriza adopción de agentes.

## Preflight y limpieza

Antes de cada brazo: releer AGENTS.md, README.md, WORK_QUEUE.md y WORK_QUEUE.lock; confirmar token del lock Q146; confirmar cero procesos/listeners/containers de inferencia ajenos; comprobar ambas RTX 3090, RAM libre ≥80 GiB, SwapFree ≥1 GiB, temperaturas <80 °C, Docker ≥8 GiB y HDD ≥40 GiB. Si falla un gate, no arrancar ese brazo. Verificar hashes de modelo/control y compose. Iniciar el monitor antes del container. Al terminar o fallar: capturar logs con redacción, `compose down` sólo del proyecto propio, comprobar puerto sin LISTEN, contenedor ausente y GPU liberada. No reiniciar automáticamente.

## Antecedentes y límites

- Q85 (`Q-20261024-VF-ITERATION-85`) detuvo la evaluación de agentes tras nueve canarios fallidos; no produjo score BCB ni TPS de HyperQwen. Q167 no retoma ese protocolo ni repite sus tools.
- SOL Q34 tuvo 30/30 solicitudes de velocidad; Q127 verificó el perfil/archivos y una solicitud real. Q167 vuelve a ejecutarlo sólo como control BCB emparejado.
- No se comparan PeritoSoft ni se escriben datos en sus archivos. No se termina ningún proceso si no se identifica como server o contenedor propio de Q167.

## Evidencia al inicio

- `WORK_QUEUE.lock`: tarea `Q146 resume justified VF-20261019-01 tests`, token `2242863e-c78e-4fa9-9649-c1d1541f3919`.
- Escaneo 2026-10-27T12:50Z: cero procesos/listeners/containers PeritoSoft/llama-server/vLLM/NInfer/Strata. No se envió ninguna señal. `nvidia-smi pmon` registra Xorg, Compiz, Codex, Brave y `artcraft-launcher` (207 MiB), sin proceso de inferencia; la GUI permanece activa según instrucción del usuario. Se guardó el recibo `receipts/process-scan.json`.
- El preflight estático resolvió ambos Compose como proyectos Q167 y loopback 127.0.0.1:18167. SOL queda fijado al digest local de vLLM v0.27.1, pesos read-only y cachés propias en HDD extra. HyperQwen tiene pesos read-only y caché/tmp propios; Compose down retira su volumen temporal.
- `receipts/download-progress.json`: descarga HyperQwen completa desde el revision fijado `1f05c441c4e64ae0549de44fa9ea5a6d43610314`; los nueve archivos fijados suman 19.472.769.333 B y todos coinciden en tamaño y SHA-256 con Q85. Corrió en `systemd --user`, exit 0, pico de memoria 20,1 GiB y swap 0; no usó GPU.
- Post-descarga: HDD extra 293.798.199.296 B libres; root/Docker 9.377.968.128 B. Cero servicios de inferencia durante la descarga. SOL/ASTRA y la carpeta de PeritoSoft no se alteraron.
