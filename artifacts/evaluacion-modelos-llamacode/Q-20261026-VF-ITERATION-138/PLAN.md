# Q138 — Fixture legal para reverse engineering con Qwen3.8-27B

## Objetivo

Desbloquear la acción local pendiente `vf-qwen-ghidra-open-fixture-20261025` con un binario sintético escrito para esta prueba, un oráculo determinista y análisis Ghidra reproducible. Si las comprobaciones de runtime pasan, comparar como perfiles completos Qwen3.8-27B Q4_K_M y Qwen3.8 Flash-Next ASTRA IQ2_XS sobre las mismas preguntas, respuestas correctas y semillas. No es una afirmación de calidad general ni cambia perfiles productivos.

## Prerregistro

- Tarea: Q138; lock exclusivo `q138-re-fixture-bda789bf8eb8993f45f6bdc7`.
- Pregunta de decisión: si Qwen3.8-27B aporta valor como especialista de reverse engineering sobre ASTRA en un fixture pequeño con comportamiento conocido.
- Fixture: código C original propio, sin firmware, juegos ni binarios de terceros; fuente, inputs, resultados ejecutados y oráculo se archivarán bajo `fixtures/`.
- Análisis: Ghidra headless oficial 12.2, asset `ghidra_12.2_PUBLIC_20261016.zip`, 569.712.708 bytes, SHA-256 `2c2cd776db3c1f6a097ba418922378ac3649cadd5e844a6f5f088ae628a7be67`. El archivo se instalará fuera del repo bajo `Disco local/Tools/Ghidra-12.2`; se aborta si tamaño/hash difieren o el espacio de esa unidad baja de 2 GiB. Java 21 está presente.
- Perfil candidato: `/media/cristian/Disco local/Models/llamacpp/Qwen3.8-27B-GGUF-Q4_K_M/Qwen3.8-27B-Q4_K_M.gguf`, hash declarado en Inventario de modelos `c600de0300ae8a0eb3a6c0b8b5561b8b96f16bd2c863c2a66c42de29d391a747`.
- Control: los shards existentes de Qwen3.8 Flash-Next ASTRA IQ2_XS y runtime Strata existente. No se escribirán, borrarán ni reemplazarán pesos, packs, perfiles ASTRA/SOL ni modelos usados por PeritoSoft.
- Host solicitado: ambas RTX 3090 visibles, 128 GiB RAM; ambas GPU asignadas a cada perfil por separado. Sólo un inference server/proceso de prueba a la vez. Revalidar servidor, VRAM, memoria disponible, PSI, OOM, puertos y storage antes de cada perfil.
- Harness: prompts idénticos contra APIs OpenAI-compatible, 12 preguntas con oráculo exacto × 3 semillas registradas por perfil, secuencial; sampling conservador `temperature=0.6`, `top_p=0.95`, `top_k=20`, `min_p=0`, `repeat_penalty=1`. Guardar raw outputs, latencias, tokens y logs; puntuar respuestas exactas/códigos, sin juez LLM.
- Gate de informe: comparar accuracy exacta pareada y latencia E2E total; no promover Qwen27B salvo ≥10 puntos porcentuales de ventaja media, sin regresión crítica de seguridad/precisión y con E2E ≤1,25× ASTRA. Si no cruza el gate, cerrar como piloto sin promoción. Ningún resultado cambia los defaults.
- Aislamiento: usar el wrapper/versionado Q121/AMD05 vigente o el mismo cgroup/systemd guard verificado; abortar sólo el proceso propio por hard-stop, no matar GUI ni procesos ajenos. Sin presión de memoria artificial.
- No iniciar llamadas a modelos hasta validar que Ghidra obtuvo el hash esperado, que el fixture pasa sus oráculos, que las APIs contestan health/model identity y que los gates del worker fijado pasan. Sin descargas de modelos.

## Pruebas planeadas y salidas

1. Compilar el fixture con GCC y comprobar sus vectores contra el oráculo independiente.
2. Decompilarlo con Ghidra headless y fijar hashes de binario, script y salida.
3. Hacer preflight de perfiles, worker, disco y procesos; no inference server previo.
4. Si todo pasa, ejecutar el A/B en serie y puntuar los 72 casos (36 por perfil).
5. Reconciliar resultado, inventario/accionables y Sheets; verificar limpieza de procesos y puertos.

## Enmienda de runtime — 2026-10-26T02:35:45.638232+00:00

Ghidra 12.2 requiere JDK 25; el JDK 21 disponible fue rechazado antes de importar el binario. Se preregistra Temurin 25.0.5+8 oficial, con verificación exacta de tamaño y SHA-256 antes de extracción, en `Disco local/Tools`. No se instalará en el sistema ni se harán llamadas de modelo en esta fase. Recibo: `artifacts/evaluacion-modelos-llamacode/Q-20261026-VF-ITERATION-138/receipts/amendment-03-jdk25-dependency.json`.

## Gate fixture/Ghidra — PASS — 2026-10-26T02:40:46.423980+00:00

El fixture propio pasó 12/12 oráculos. Ghidra 12.2 (JDK Temurin 25.0.5+8 verificado) importó y analizó el ELF; el post-script omitió los ocho bloques externos que generaban pcode errors. Corpus final: 22 funciones, 9082 bytes, SHA-256 `fd64ae63b1e0add2a1f842e349a6cfc54a8f3b841e69a1a34bd9af190337cadd`; están presentes los cuatro bloques de comportamiento requeridos. El output crudo de attempt04 se conserva separado. No hubo inferencia ni GPU. Recibo `artifacts/evaluacion-modelos-llamacode/Q-20261026-VF-ITERATION-138/receipts/ghidra-final-gate.json`.

## Enmienda 01 — prompt contextual y perfil completo — 2026-10-26T03:44:10Z

La revisión del fixture detectó que las 12 preguntas originales no incluían el código decompilado; por sí solas medían aritmética, no reverse engineering. Antes de consultar modelos, el runner adjuntará a cada pregunta el corpus Ghidra exacto (9082 bytes; SHA-256 `fd64ae63b1e0add2a1f842e349a6cfc54a8f3b841e69a1a34bd9af190337cadd`) y mantendrá el oráculo y las opciones sin cambios. La respuesta puntuable debe ser sólo una letra A–D; el texto adicional cuenta como incorrecto. Esto corrige el estímulo y no consume inferencia.

Perfiles fijados como comparaciones de sistemas completos, no de pesos aislados:

- Control productivo ASTRA Flash-Next IQ2_XS: Strata 0.1.41, commit `fb58e0dbc8399662c0e47c76578c6e878b14f6cf`, ejecutable SHA-256 `770ecf303a4c6271654339c639392ecb455de3a999bf5d2e8dbc73c879103602`; shards SHA-256 `92cee27ae5bbadcd732416a0f7a7f0acc092399dbbe8f5a5efa707c2ec0a49d7` y `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`; pack IQ2_XS SHA-256 de manifiesto `27701fec3423719c23ee88c93ffae0f5f5c60ad29b6e46b7589fa9df5f20c880`; expert profile SHA-256 `8f59b4aa8873209dff11c11e37bcda9529a1335b724a1afeea37bf6388975baf`; MTP-4 IQ3XXS existente, manifiesto SHA-256 `77cbf37be386ef28e496dc161ed07c4e5ce677cb495261c343c4fd2acf3bbae8`; 1,048,576 contexto, YaRN 4 desde 262,144, KV int8 y 32,768 residentes, muestreo productivo `0.6/0.95/20/0/1/0`. Config derivada sólo para el puerto y log de Q138, SHA-256 esperado `7ca521655fcb8e01f57049754f1497c440b347aa065080937d9fddcc2f537c08`.
- Candidato Qwen3.8-27B Q4_K_M: llama.cpp server b11554/commit `966baae76`, ejecutable SHA-256 `fe8a7d6073d3e3a276193fcaec162cbf280d2572ad2016c9100fd924be19c6ed`; GGUF SHA-256 `c600de0300ae8a0eb3a6c0b8b5561b8b96f16bd2c863c2a66c42de29d391a747`; plantilla Qwen tools SHA-256 `03c3e852d2c349ce306ed9ecd870c83487bf123918843387b179ead1fcce93af`; 32,768 contexto, batch/ubatch 512, KV q4_0, flash attention, split 1,1, capas GPU 999, temperatura 0.6/top-p 0.95/top-k 20/min-p 0/repeat 1/presencia 0, reasoning medium y presupuesto de 1024 tokens.

Cada perfil hará las mismas 12 preguntas × semillas 4242/5051/6061, en serie, mismo prompt contextual y máximo de salida de 1024. El orden de preguntas queda preregistrado y compartido. Capturar por respuesta el texto raw, coincidencia exacta, tokens, latencia de solicitud, timings de prefill/decode reportados por el motor si existen, además de logs, arranque/parada y telemetría RAM/PSI/swap/OOM/VRAM; si un motor no informa una métrica, se registrará N/D sin estimarla. El runtime y plantilla difieren, por lo que la conclusión corresponde a estos perfiles completos y este fixture pequeño.

El runner se ejecutará como servicio transitorio del gestor systemd de usuario, en `background.slice`, con `KillMode=control-group`, `OOMPolicy=kill` y contabilización cgroup. No se fijará `MemoryHigh`, `MemoryMax` ni `MemorySwapMax`, ni se inyectará presión; el límite AMD05 sólo vigila y, si corresponde, termina el servidor de prueba propio. Así el trabajo puede completar y escribir recibos aunque cierre Codex, sin alterar los perfiles ni limitar la memoria disponible del host.

Gates antes de cualquier inferencia: lock Q138 vigente; corpus/oráculo y hashes correctos; runtimes, modelos, pack, expert profile, MTP y plantilla presentes y verificados; ningún inference server/listener externo; puertos 18138/18139 libres; ambas 3090 visibles, bajo 80 °C y con al menos 20 GiB libres; MemAvailable ≥88 GiB, SwapFree ≥1 GiB y telemetría válida; servicio user-systemd y cgroup sin límites validado. Si falla un gate, detenerse sin llamada de modelo y registrar recibo. No se detendrá ArtCraft ni otra GUI. Tras el A/B, limpiar sólo el unit y los procesos/puertos propios, y confirmar ASTRA y SOL productivos intactos.

Recibo completo de la enmienda: `receipts/amendment-01-runtime-and-prompt-correction.json`. No hubo llamadas de modelo ni uso de GPU al registrar esta corrección.


## Enmienda 02 — intento pre-request y directorio de logs — 2026-10-26T03:58:38Z

Attempt01 terminó en infraestructura antes de cargar pesos o enviar una pregunta: Strata no pudo crear `runs/astra-control/strata-engine.log` porque faltaba su directorio padre. Quedó 0/72; el servicio transitorio, los procesos propios y ambos puertos se limpiaron, sin cambios de modelo ni límites de memoria. Se conservaron los recibos de ese intento. A02 preregistra crear el padre del log antes de iniciar el proceso y ejecutar una sola campaña explícita en `runs/attempt02`, con progreso/resultado en recibos nuevos. Configuración, perfiles, contextos, muestreo, semillas, orden, puertas y worker sin límites no cambian. No habrá reintento automático ni otra repetición en Q138 si este intento vuelve a fallar. Recibo: `receipts/amendment-02-attempt02-log-directory-fix.json`.


## Enmienda 03 — ruta absoluta del lanzador — 2026-10-26T04:00:00Z

La primera invocación systemd de A02 terminó antes de que Python pudiera abrir el runner: systemd ejecuta desde `/home/cristian`, por lo que la ruta relativa del comando no existe allí. No se inició el runner, servidor ni modelo; se enviaron 0/72 solicitudes y no se escribió progreso. El journal registra `status=2/INVALIDARGUMENT`; se confirmó que el servicio quedó eliminado y los puertos 18138/18139 libres. A03 preregistra una sola invocación corregida del mismo campaign A02, usando ruta absoluta del script y `WorkingDirectory` explícito del repo. Se mantienen los perfiles, artefactos y gates A02; no se repite ninguna llamada de modelo porque la invocación anterior no llegó al runner. Si el runner corregido inicia un servidor y luego falla, no se hará otro campaign Q138. Recibo: `artifacts/evaluacion-modelos-llamacode/Q-20261026-VF-ITERATION-138/receipts/amendment-03-launch-path.json`.


## Enmienda 04 — referencia AMD05 en preflight — 2026-10-26T04:04:00Z

La campaña A02 alcanzó el runner tras corregir la ruta de systemd, pero la comprobación de artefactos falló antes de escribir preflight o iniciar un servidor: `verify_artifacts()` conservaba referencias `prereg["guard"]` luego de renombrar el objeto a `profile_prereg`, generando `NameError` y 0/72 requests. Se preservan `campaign-attempt02-*`. A04 preregistra cambiar esa referencia al recibo de perfil original, añadir una regresión estática contra el nombre indefinido y ejecutar una sola vez con salidas nuevas `attempt03`. Los modelos, configuración, preguntas y worker sin caps no cambian. Si attempt03 inicia un server y falla, Q138 no tendrá otra campaña. Recibo `artifacts/evaluacion-modelos-llamacode/Q-20261026-VF-ITERATION-138/receipts/amendment-04-runner-prereg-name-fix.json`.


## Enmienda 05 — directorio del log configurado por Strata — 2026-10-26T04:08:00Z

Attempt03 pasó preflight completo, pero el wrapper Strata falló antes de API READY y de cargar modelos: el config fijado apunta a `runs/astra-control/strata-engine.log`; el runner sólo creaba el directorio del log general bajo `runs/attempt03/logs`. Quedó 0/72, sin API lista, VRAM devuelta al baseline, servicio/puertos limpios y sin presión host (113,05 GiB disponibles; PSI 0). A05 preregistra leer el config ya verificado, crear exactamente el padre del log configurado, probar esa ruta en CPU y ejecutar una campaña nueva `attempt04`. No se cambia perfil ni configuración. Recibo `artifacts/evaluacion-modelos-llamacode/Q-20261026-VF-ITERATION-138/receipts/amendment-05-astra-config-log-parent.json`.


## Enmienda 06 — ventana de arranque ASTRA — 2026-10-26T04:29:07Z

Attempt04 usó 900 s y terminó antes de API READY, con 0/72 solicitudes. La telemetría registró hasta 46,7 GiB de memoria del worker, al menos 59,1 GiB disponibles, sin swap/OOM y sin hard-stop de la guarda; la PSI severa quedó en diagnóstico. Q117 completó el mismo ASTRA 1M: Strata reportó 33,02 GiB de expertos cargados en 282 s, la petición duró 442,448 s, el RSS máximo fue 51,306 GiB y MemAvailable mínima 58,698 GiB, sin OOM ni swap del worker. La hipótesis de caché fría/latencia de arranque es plausible, no confirmada. A06 preregistra un único attempt05 con timeout de health de 1800 s y cola de log en el diagnóstico; conserva attempt04, no cambia perfiles ni límites y mantiene el criterio de parada real. Si API READY no llega en 30 minutos, guardar logs y limpiar sólo el proceso de prueba. Si llega, continuar la campaña A/B serial ya fijada.

Recibo: `receipts/amendment-06-startup-timeout-preregistration.json`.


## Enmienda 06 — resultado de attempt05 — 2026-10-26T05:05:26Z

Attempt05 pasó preflight dentro de `background.slice`, llegó a READY y completó el A/B serial 72/72. ASTRA: 22/36, prefill mediano 1.543,8 tok/s, decode 139,1 tok/s, latencia mediana 8,118 s, inicio 495,32 s. Qwen27B: 31/36, prefill 1.547,6 tok/s, decode 34,6 tok/s, latencia mediana 23,065 s, inicio 33,03 s. Qwen gana 11 pares y pierde 2; diferencia de exactitud +25 pp. Cumple la señal de calidad, falla el gate E2E de ≤1,25× (mediana 2,84×) y no hay preguntas de seguridad/criticidad. No promover; ASTRA/SOL productivos intactos.

Memoria: cgroup de campaña máximo 83,7 GiB, MemAvailable mínima 59,0 GiB, swap/OOM del worker 0 y hard-stop nunca activo. Se observó PSI diagnóstica alta durante el arranque, pero no detuvo el proceso. Al cierre el swap global estaba 7,94/8,00 GiB usado sin atribución por proceso, mientras MemAvailable era ~110 GiB; el worker cgroup no consumió swap. `A05` tardó 495 s en cargar, lo que confirma que el timeout previo de 900 s era insuficiente para algunos inicios; el mecanismo de presión no causó el timeout.

Ver `RESULTS.md`, `receipts/ab-analysis-attempt05.json`, `receipts/campaign-attempt05-final.json` y `receipts/amendment-06-startup-timeout-preregistration.json`. La sincronización de esta medición a Google Sheets queda pendiente antes del cierre de Q138.
