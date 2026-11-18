# Q193 — Qwen3.6-35B-A3B · NInfer-3090 v0.17.1 Linux · pipeline dual

**Estado inicial:** preregistrado; aún sin descargar el runtime ni ejecutar inferencia. El tercer artefacto DeepSeek FP8 Engram incompleto que aparecía en una captura ya fue retirado en Q190/Q192; no forma parte de esta prueba.

## Pregunta de decisión

¿El runtime distinto NInfer-3090 v0.17.1 Linux puede ejecutar el mismo artefacto Qwen3.6-35B-A3B ya evaluado en Q190, en pipeline `--devices 0,1` sobre las dos RTX 3090, y ofrecer una alternativa de throughput/Q172 que justifique conservar el perfil? No volver a descargar el modelo ni mezclarlo con los resultados Q190 de NInfer-all v3, llama.cpp, otro quant o otra revisión.

El valor de la prueba es resolver el soporte local de pipeline en dos dispositivos distintos: el README de v0.17.1 documenta `--devices 0,1` y resultados de pipeline, pero también marca el engine de contexto actual con dispositivos distintos como no verificado. Por eso el primer gate es un smoke mínimo de carga y respuesta dual; no se salta al ladder si falla.

## Preregistro de runtime y pesos

- Runtime fijado: `ashalliants/ninfer-3090`, release `v0.17.1-rtx3090`, Linux x86-64, archive `ninfer-rtx3090-linux-x64-0.17.1-rtx3090.tar.gz`, 1,048,862,833 bytes, SHA-256 `2f469d9171fa9a1e6fca1de85f6a5d5cfb7326302f69a0561dcd9ef81415febb`.
- El archive descargado se conserva en HDD extra; la expansión de 2,356,558,649 B se hace junto al modelo en Disco local D, como recomienda el README, para evitar el acceso lento al HDD durante arranque. D tiene 87,414,194,176 B libres antes de la expansión, conserva el piso preregistrado de 10 GB y no se duplica ningún peso del modelo.
- Pesos: `qwen3_6_35b_a3b.ninfer`, v3, ruta `/media/cristian/Disco local/Modelos-eval/Qwen3.6-35B-A3B-NInfer-all-20261101/qwen3_6_35b_a3b.ninfer`, tamaño esperado 22,790,484,480 bytes, SHA-256 esperado `3e33297645dc33557751be1a3c407a74ed7c00f34909b5d4e8cfdce91b3dbe84` (confirmado en Q190). El archivo parcial antiguo de 124,428,288 bytes queda excluido y no se sobrescribe.
- Perfil: Linux nativo, CUDA 12.8, SM86, **2× RTX 3090** por pipeline de etapas `--devices 0,1`; no llamarlo tensor parallel. La configuración base sigue el launcher Qwen3.6 del release (KV `rk4v4`, MTP3 + draft head, visión activa, prefill cuBLAS chunk 4096); se fijará a una solicitud para la ladder/Q172. Toda desviación para hacer el smoke seguro se anotará antes del primer request y se conservará idéntica en Q173 y Q172.
- **Aclaración de lanzamiento, preregistrada antes de GPU (2026-11-02T02:35:44Z):** `run.sh qwen36-35b-a3b` no expone `--devices`; el launcher rechaza `NINFER_DEVICES` porque esa variable es específica del perfil Flash-Next. La ayuda del `ninfer-serve` 0.17.1 sí ofrece `--devices N,M,...`. Para poder probar Qwen3.6 dual sin cambiar el wrapper ni reutilizar un perfil Flash-Next, Q193 lanzará directamente `ninfer-serve` con los argumentos de abajo. La limitación upstream sobre pipeline en dos dispositivos distintos permanece explícita y el smoke es una compuerta de parada.
- **Args exactos del smoke 8K y base Q173/Q172:** `ninfer-serve <modelo> --host 127.0.0.1 --port 18503 --devices 0,1 --max-concurrency 1 --max-context <contexto> --kv-capacity <contexto> --kv-dtype rk4v4 --spec mtp --draft-tokens 3 --lm-head-draft --mtp-experts-q4 --gdn-state-fp16 --prefill-cublas --prefill-chunk 4096 --vision --vision-residency overlay --host-context-mib 8192 --min-p 0.03 --presence-penalty 0.5`. En el smoke, `<contexto>=8192`; en Q173 se sustituye por cada nivel preregistrado, incluido 261888 como máximo. No se pasan `--stage-layers`, `--fit-context` ni el env `NINFER_DEVICES`; el particionado por defecto del motor se valida en logs antes de seguir.
- Request smoke: Chat Completions a `127.0.0.1:18503`, prompt `Respond exactly PONG and nothing else.`, `temperature=0`, `max_tokens=16`. Aprobar sólo si la salida es válida/no vacía, el log demuestra stages en GPU0 y GPU1 y ambas tarjetas muestran uso de compute por este PID. Fallar/parar si una GPU no recibe etapas, hay error, salida vacía, OOM/Xid o CUDA fault.
- Puerto reservado de evaluación: `127.0.0.1:18503`.
- Comparador local: Q190 NInfer-all v3 con los mismos pesos — Q173 media P/D 5155.87/230.02 tok/s y cold/hot 46.776/44.597 s; Q172 seeds 73/70/79, media 74/100, safety FAIL 3/3. Es una comparación entre engines y perfiles distintos, no un reemplazo retroactivo de esos datos.

## Secuencia y métricas preregistradas

1. Verificar lock Q193, ningún inference server/puerto en conflicto, GPU0+GPU1 visibles, ASUS quarantine 1636/1636, P2P bidireccional, `gpu_unlock` en ambas tarjetas, al menos 32 GiB `MemAvailable`, al menos 10 GB libres en D, 20 GB en HDD y 2 GB en `/`. Confirmar artefacto por tamaño/SHA. Si cualquier gate falla, detener antes de inferencia.
2. Descargar el archive oficial sólo después del preregistro; comprobar el SHA publicado. Extraer en HDD, comprobar `ninfer-serve --version/--help`, `run.sh --help`, `ldd` sin dependencias faltantes. No compilar ni instalar paquetes del sistema.
3. **Smoke dual de parada:** iniciar el comando directo preregistrado arriba con contexto/capacidad 8192; enviar el request determinista preregistrado; confirmar salida no vacía, logs de asignación de etapas a GPU0 y GPU1, memoria/utilización en ambas, proceso sólo en el puerto 18503 y ausencia de Xid/OOM/fault. Apagar sólo el proceso Q193. Si falla, registrar evidencia y detener; no repetir en una GPU.
4. Sólo si smoke PASS: medir cold/hot y ejecutar Q173 ladder 8192 (3 repeticiones), 32768, 65536, 131072 y 261888 (1 cada uno), con 128 tokens de salida exactos, serial, sin 523K. Calcular medias por nivel y media equiponderada de niveles. Registrar TTFT, decode, tokens reales, errores y ambas GPUs. Actualizar la pestaña Resultados y Modelos locales por peso después de cada hito válido; leer cada rango de vuelta antes de continuar.
5. Sólo al cerrar Q173: Q172 Tool-Eval Hard Mode 2.8.0, seeds 42/43/44 seriales, 28 escenarios, timeout 120 s, `fail_on_safety`; publicar cada semilla y actualizar Accionables / Modelos locales por peso tras cada una. Comparar seguridad por separado del score.
6. No borrar ni sobrescribir el modelo por este experimento. Sólo proponer retiro si una comparación válida demuestra dominancia simultánea en prefill, decode y Q172 y no hay consumidor PeritoSoft; si no, preservar los archivos y reportar la decisión.

## Criterios de parada

Detener ante lock cambiado, servidor ajeno, falta de una GPU, gates de arranque no verdes, fingerprint incorrecto, `MemAvailable` <32 GiB, pisos de disco incumplidos, GPU no usada, salida vacía/incorrecta, tokens fuera del conteo pedido, OOM/Xid/CUDA/runtime fault, o resultados no persistidos. No matar procesos ajenos ni la GUI; detener sólo el servidor Q193 iniciado por esta evaluación.

## Fuentes primarias

- Release Linux y versión/verificación: https://github.com/ashalliants/ninfer-3090/releases/tag/v0.17.1-rtx3090
- README fijado a `v0.17.1-rtx3090`: https://raw.githubusercontent.com/ashalliants/ninfer-3090/v0.17.1-rtx3090/README.md
- Modelo y fingerprint Q190: `artifacts/evaluacion-modelos-llamacode/Q-20261029-VF-ITERATION-190/profiles/qwen36-ninfer-all-v3/PLAN.md` y `receipts/hf-artifact-verified.json`.

## Enmienda activa Q202 — protocolo de conteo exacto y ladder (2026-11-02)

Esta enmienda reemplaza para Q193 el endpoint heredado `/v1/completions`, los prompt IDs y cualquier capacidad que varíe con el nivel de entrada. La secuencia original se conserva como registro histórico. Recibo preregistrado antes de nuevos requests/GPU: `artifacts/evaluacion-modelos-llamacode/Q-20261103-VF-RESUME-202/receipts/prereg-amendment-q193-prompt-count-20261102.json`.

- Se usará `POST /v1/responses/input_tokens` (conteo sin generación) con el texto candidato y `reasoning.effort=none`; ajustará el mismo corpus de fixtures local hasta que el servidor reporte el objetivo exacto, incluido el chat template. La petición de generación usará el mismo texto en una sola entrada de usuario vía `POST /v1/chat/completions`, `reasoning_effort=none`, y sólo se acepta si `usage.prompt_tokens` vuelve a coincidir exactamente. El smoke Q197 ya reprodujo offline 20 tokens para la plantilla no-thinking y el servidor reportó 20.
- Todas las mediciones usarán capacidad fija `--max-context 262144 --kv-capacity 262144`; el mayor objetivo es 261888 tokens de entrada y el máximo de salida es 128, total 262016. 523904 queda excluido. Se agrega `--no-prefix-reuse` para que las repeticiones no aprovechen prefijos guardados y `--request-log-jsonl` para conservar los tiempos/token counts por petición.
- Cada generación será Chat Completions en streaming, `max_tokens=128`, `ignore_eos=true`, `stream_options.include_usage=true`, `reasoning_effort=none`, `temperature=0.6`, `top_p=0.95`, `top_k=20`, `min_p=0`, presencia/frecuencia `0`, semilla 42+repetición. NInfer v0.17.1 no expone `repeat_penalty`; no se enviará un campo desconocido. Esta limitación se anota en todos los resultados y no se presentará como comparación de muestreo idéntico con runtimes que sí lo implementan.
- Niveles seriales: 8192×3, 32768×1, 65536×1, 131072×1 y 261888×1. Un conteo desviado, una salida distinta de 128 tokens, contenido visible vacío, uso de prefijo, falta de etapa/uso en una GPU, error CUDA/Xid/OOM o gate de recursos aborta; no se agregan puntos inválidos.
- Se guardarán TTFT de cliente y tiempos crudos `request_done`; el Prefill efectivo conserva la definición Q190 (`prompt_tokens / TTFT hasta primer contenido`) y se etiqueta como efectivo, no kernel puro. Decode se publica con numerador/denominador crudos del log del runtime. Q172 Tool-Eval Hard 2.8.0 (28 escenarios, seeds 42/43/44, serial, timeout 120 s, `fail_on_safety`) sólo empieza después del ladder válido y sincronizado.
- El contrato upstream v0.17.1 documenta `POST /v1/responses/input_tokens` como el mismo prompt path sin generación, Chat Completions `ignore_eos`, `--no-prefix-reuse` y los logs estructurados `request_done.timings_seconds`; el binario local confirma las rutas/opciones usadas. Fuente: https://github.com/Don-Chad/ninfer-3090/blob/master/docs/serving.md.

## Enmienda Q202.04 — materialización de prompts y medición verificable de caché

Preregistrada en `artifacts/evaluacion-modelos-llamacode/Q-20261103-VF-RESUME-202/receipts/prereg-amendment-04-q193-prompt-and-init-method.json`, antes de cualquier request nuevo.

- El entorno Python no tiene el paquete `tokenizers` y los JSON fuente bajo `/mnt/q190` no están presentes. No se instalará ninguna dependencia. En su lugar, se decodificará el corpus Q190 de 275627 IDs con el mapa inverso GPT-2 ByteLevel construido desde el tokenizer Qwen3.6 fijado (SHA `5f9e4d49…81cb42`), respetando los 161 segmentos y uniéndolos con dos saltos de línea. Validación CPU-only: 161/161 longitudes coinciden con el manifiesto; recibo `prompt-corpus-decode-q193-q202.json`.
- El texto se ajustará por prefijos de caracteres usando `POST /v1/responses/input_tokens` y `reasoning.effort=none`. Sólo se generará si el request equivalente de Chat Completions devuelve exactamente el objetivo en `usage.prompt_tokens`; en caso contrario el punto se aborta antes de generar.
- Para cold se aplicará `POSIX_FADV_DONTNEED` únicamente al archivo de pesos, después de verificar su SHA. El arranque se etiqueta cold sólo con `mincore` ≤5% inmediatamente antes de lanzar; nunca se limpia la caché global.
- Para hot se conserva la caché del archivo tras detener el servidor propio y se mide `mincore`. Se exige residencia ≥95%; si falta, se solicita `POSIX_FADV_WILLNEED` para ese archivo, máximo 60 s y sin bajar de 32 GiB MemAvailable. Si no se alcanza el umbral, hot queda sin validar y no se publica como tal.
- Cold y hot usan el mismo comando, puerto, contexto y KV capacity fijos (262144), modelo/runtime con hashes fijados, y sólo se considera listo cuando `/health` da 200, el modelo esperado aparece y el PID propio mantiene ≥1 GiB en cada 3090.

## Enmienda Q202.05 — conservar la concatenación exacta del corpus Q190

La composición con dos saltos de línea de la enmienda 04 queda supersedida antes de cualquier inferencia. El runner Q190 concatenó directamente los IDs tokenizados de 161 segmentos en un solo vector, sin delimitadores. Para preservar el fixture, Q193 decodifica el vector plano de 275627 IDs en el mismo orden, sin insertar espacios o saltos de línea. La validación CPU-only del tokenizer fijado da 1,173,318 caracteres, igual a la suma del manifiesto de segmentos. Recibo: `artifacts/evaluacion-modelos-llamacode/Q-20261103-VF-RESUME-202/receipts/prompt-corpus-flat-decode-q193-q202.json`.

Cada contexto se calibrará sobre prefijos del vector plano mediante `/v1/responses/input_tokens`, y luego se enviará exactamente el mismo texto a Chat Completions. Ambos conteos deben coincidir exactamente con el objetivo antes de aceptar el punto. El preregistro está en `artifacts/evaluacion-modelos-llamacode/Q-20261103-VF-RESUME-202/receipts/prereg-amendment-05-q193-flat-token-prompt.json`; todavía no se ha enviado ningún request.

## Enmienda Q202.06 — runner serial y guardas de ejecución

Antes de iniciar inferencia se preregistró `scripts/q193_runner.py` (SHA-256 `b78ee4300415fa6caa251cfee0cc4aa71a5badad2d12ab3101825fb4706b2778`). Validación local CPU-only PASS: corpus 275.627 IDs, decodificación plana 1.173.318 caracteres, tokenizer/model/runtime con sus hashes fijados. No inicia servidor durante `validate`.

El runner vuelve a verificar que el lock pertenezca a Q202, hashes, proceso/puerto y aplicaciones CUDA antes de actuar; sólo detiene el PID cuyo `cmdline`, modelo, binario y puerto coinciden con su manifiesto. La secuencia queda fijada: init cold (residencia modelo ≤5%), smoke de capacidad fija 262144, stop del proceso propio, init hot (residencia ≥95%, precarga por archivo limitada a 60 s si hace falta), y luego ladder Q173 serial. Se usa `/v1/responses/input_tokens`; el mismo texto se manda por Chat Completions y ambos `usage.prompt_tokens` y JSONL `request_done` deben dar el objetivo, sin prefijo reutilizado, `computed_prefill_tokens=prompt_tokens`, y 128 tokens de salida. Cada punto genera recibo antes de sincronizar/readback de Accionables; no continuar al siguiente sin ese readback. Las opciones de muestreo de la solicitud se fijan a temperatura 0,6, top-p 0,95, top-k 20, min-p 0, presencia/frecuencia 0, `ignore_eos`, semilla 42+repetición y `reasoning_effort=none`; `repeat_penalty` sigue ausente por limitación del binario. No se modifica el inventario Q190.

El contrato de conteo, readiness y JSONL se verificó en la documentación primaria fijada al tag `v0.17.1-rtx3090`: `docs/serving.md`, secciones “Responses input token count”, “Startup readiness” y “Structured request log”. El runner está preregistrado en `artifacts/evaluacion-modelos-llamacode/Q-20261103-VF-RESUME-202/receipts/prereg-q193-runner-execution-20261103.json`. Todavía no se inició el proceso de inferencia Q193.


### Q202 Amendment 07 — verificar mincore antes de continuar

El intento de init cold falló antes de Popen con ENOMEM. Se preregistra arreglar el ABI ctypes de mmap/mincore/munmap y consultar el modelo por ventanas de 512MiB; no cambiar los gates de residencia. Runner preparado con SHA-256 d3a46b1c51e3b75463a967841107845fca8af3beead776f0af3351e94ac26a7e. Antes de otro inicio, correr py_compile y el subcomando cache-probe, ambos sin inferencia/CUDA; registrar y sincronizar el resultado. Si pasa, preflight completo y continuar cold→smoke→hot→Q173.


## Q202 Amendment 09 — calibrar la ruta Chat Completions con tokenizer local fijo

La calibración previa por `POST /v1/responses/input_tokens` no encontró el objetivo 8192 (sondas 8188/8196). La documentación v0.17.1 garantiza que ese conteo reproduce **Responses Create**, no afirma paridad con **Chat Completions**. Por eso no se acepta como prueba suficiente para el ladder Chat.

Antes de nuevas requests, se preregistra usar el tokenizador y `tokenizer_config.json` fijados para contar localmente el prompt Chat completo (una entrada de usuario, reasoning deshabilitado), aplicando el branch de plantilla Qwen correspondiente. El control CPU-only debe reproducir el prompt del smoke conocido de 20 tokens. Después se buscarán prefijos por puntos de código del corpus plano Q190, sin separadores ni texto sintético, hasta obtener el conteo objetivo exacto. Se guardarán todas las sondas, longitud de prefijo, hash del texto renderizado y conteo.

El ladder seguirá generando por Chat Completions y conservará las mismas opciones, capacidad/KV, outputs, seeds, logs y orden ya preregistrados. Cada respuesta debe confirmar el conteo exacto en `usage.prompt_tokens` y JSONL; cualquier diferencia invalida el punto y detiene la secuencia. No se usará un request de un token como calibrador para no calentar el estado antes de la primera muestra. Empezar por 8K×3 serial; completar luego 32K, 64K, 128K y 261888 con sincronización/readback de Sheets entre puntos. 523904 sigue excluido.

Preregistro completo: `artifacts/evaluacion-modelos-llamacode/Q-20261103-VF-RESUME-202/receipts/prereg-amendment-09-q193-chat-template-calibration.json`. Fuente primaria: [NInfer v0.17.1 serving docs](https://raw.githubusercontent.com/ashalliants/ninfer-3090/v0.17.1-rtx3090/docs/serving.md).


## Q202 Amendment 10 — buscar ventanas contiguas exactas del corpus Q190

El control local de plantilla pasó (smoke=20), pero no hay prefijo inicial que dé 8192: las 1034 sondas más cercanas dieron 8191/8193. Se preregistra una búsqueda CPU-only de una **misma ventana contigua** del corpus Q190 para todo el ladder, sin insertar texto ni separadores. Se probarán inicios reproducibles 0,64,…,2048 puntos Unicode; desde cada inicio se buscará el final exacto para 8192, 32768, 65536, 131072 y 261888, y sólo se aceptará un inicio común si resuelve todos los niveles. Cada sonda y cada inicio rechazado se guardarán.

El conteo local selecciona prompts; no sustituye el gate de `usage.prompt_tokens` y JSONL del Chat Completions real. La generación sigue bloqueada hasta que los cinco tamaños exactos estén calibrados, el hash del script actualizado esté preregistrado y la hoja tenga readback. Después: preflight fresco, Q173 serial con sincronización tras cada nivel; Q172 seeds 42/43/44 sólo tras cerrar el ladder. 523904 sigue excluido. Preregistro: `artifacts/evaluacion-modelos-llamacode/Q-20261103-VF-RESUME-202/receipts/prereg-amendment-10-q193-contiguous-window-search.json`.
