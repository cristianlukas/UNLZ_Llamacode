# Plan — Q-20261009-STRATA-COLD-PREFILL-128K

- **Estado:** completa bajo el lock `WORK_QUEUE.lock`, token `75464b9f-13b0-4ce2-b640-9bc55c2d3344`; 6/6 corridas válidas técnicamente, 3 pares A/B, cierre 2026-10-12.
- **Pregunta:** cuánto tarda un prefill nuevo cerca de 128K, y cuánto de ese prefijo se vuelve a procesar al pedir una compactación de conversación Codex con la opción de caché de compactación de Strata apagada frente a encendida.
- **Antecedente técnico local:** Strata 0.1.41 documenta `codex_compaction_cache` opt-in. En la API Responses, conserva la asociación `session_id`/`thread_id` y las tools del último turno de esa conversación para volver a renderizarlas sólo en el prompt de compactación. No cambia las tools que recibe el parser ni las de la respuesta. La opción se probará aislada y no se promoverá a defaults.

## Perfiles y control

Control y candidato son **el mismo perfil completo**, con una sola diferencia preregistrada:

| Brazo | Perfil/modelo | Cambio |
|---|---|---|
| A, control | ASTRA calibrado Qwen3.8-Flash-Next IQ3_S, Strata 0.1.41 | `codex_compaction_cache=false` |
| B, candidato | El mismo ASTRA IQ3_S, runtime, argumentos y hardware | `codex_compaction_cache=true` |

- Pesos locales existentes: revisión IQ3_S ya inventariada en el registro canónico; shard 1 SHA-256 `4c1eb2ceb4915e1192f4f386021897bde56a97f40a0bb78bb86465e0f7d2aca3`, shard 2 `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`. No descargar ni duplicar modelo. Packs IQ3_S, MTP y tokenizer ya locales.
- Runtime fijo: Strata 0.1.41, commit `fb58e0dbc8399662c0e47c76578c6e878b14f6cf`, binario SHA-256 `770ecf303a4c6271654339c639392ecb455de3a999bf5d2e8dbc73c879103602`.
- Hardware reservado: ambas RTX 3090 de 24 GiB, sin concurrencia; una sola instancia del servidor a la vez. Contexto máximo 131072, MTP4, KV int8, KV resident 32768, expert cache auto, prefill auto, `spec-min-p=0.70`, PCIe fraction 0, split auto. Muestreo conservador idéntico en ambos brazos: temp 0.6, top-p 0.95, top-k 20, min-p 0, repeat penalty 1.0, presence penalty 0.0; seed 42.
- Copiar configuración a `configs/` del artefacto y cambiar únicamente el booleano de caché entre A y B. Registrar hashes de ambas configuraciones, fuentes, prompts y script.

## Protocolo preregistrado

1. Confirmar pesos, packs y tokenizer locales, endpoints libres, RAM/swap y estado de GPU. No modificar el QSettings, perfiles productivos ni cachés compartidas.
2. Crear un diálogo sintético determinista con hechos de control ubicados cerca del comienzo, centro y final. Medir el prompt **renderizado/tokenizado** por Strata y ajustar el cuerpo para que el primer turno quede entre 120000 y 125000 tokens, con espacio para respuesta y solicitud de compactación debajo de 131072. Guardar el texto exacto, SHA-256 y posiciones de los hechos.
3. Para cada corrida, iniciar un servidor limpio con el brazo asignado. Registrar carga/model initialization por separado. Enviar un turno con tools definidas, `tool_choice=auto` y la instrucción explícita de no llamar herramientas, un `session_id`/`thread_id` fijos y metadata Codex `request_kind=turn`; pedir respuesta mínima y registrar tokens de prompt, `reused`, `read`, tiempo y velocidad de prefill. `auto` es necesario para que Strata registre las tools del prompt normal y permita medir la opción; no se ejecuta ninguna acción externa.
4. En la misma conversación, volver a enviar el historial exacto más el pedido de compactación, ahora con `tools=[]` y metadata `request_kind=compaction`. Registrar de forma separada tokens efectivos, reutilizados/leídos, latencia/prefill, salida, tokens generados, estado HTTP y recuperación de hechos sembrados.
5. Medir tres pares válidos A/B con reinicio de servidor entre corridas y orden balanceado `A-B`, `B-A`, `A-B`. El reinicio vacía KV/prompt cache del engine; **no** se vaciará a la fuerza la page cache del sistema operativo. Distinguir cold-KV/prefix de estado frío/caliente de archivos, pesos y expertos, y anotar el orden de corrida.
6. Capturar logs crudos del engine, stdout/stderr del servidor, request/response JSON, telemetría `nvidia-smi`, hashes, timing y estado de la API. Excluir como inválida cualquier corrida con truncamiento, error HTTP/engine, OOM o fallo de contexto; repetir sólo esa pareja si los recursos siguen libres.

## Métricas y criterio de lectura

- **Prefill frío:** primer turno tras inicio limpio, `reused` exacto, `read` exacto, latencia de lectura de prompt, prompt tok/s y tiempo total de request; carga del modelo se reporta aparte.
- **Compactación:** cantidad y porcentaje del prompt reutilizado, tokens que debió leer de nuevo, prefill tok/s, TTFT/latencia de respuesta, tokens de salida y recuperación de los hechos sembrados.
- No declarar una mejora estable con menos de tres pares válidos. Reportar cada par, mediana y rango. Una señal esperada de activación es que B reutilice la mayor parte de la conversación y A relea una fracción mucho mayor; no se asumirá el resultado de la medición publicada.
- **Cierre de calidad:** ambas respuestas deben terminar normalmente, sin truncamiento/context overflow, y conservar los hechos requeridos en el resumen. La suite no mide calidad general de coding ni recuperación larga en otras quants.
- Decisión prevista: evidencia experimental sobre el flag en este perfil/config. No cambiar HarnessSpec, perfiles o defaults en esta tarea.

## Estado de preflight

- GPU observada libre de inferencia: GPU0 ~1167 MiB por escritorio/Xorg, GPU1 108 MiB; ambas en 0% al momento de reservar. No hay servidores Strata, vLLM ni llama-server.
- ASTRA IQ3_S calibrado y receta Strata 0.1.41 existen localmente. El sistema de archivos de modelos tiene aproximadamente 132 GiB libres; no se requiere descarga.
- La revisión del source local confirma la opción `codex_compaction_cache`, metadatos Codex requeridos y la salida de logs `prompt N = reused + read ...`; también advierte que reutilización de KV no equivale a page cache fría.
- Gate de prompt real aprobado (Strata 0.1.41 tokenizer + `ChatTemplate` + Responses renderer): primer turno **120412** tokens; compactación cache off **120216** y cache on **120478**; máximos de salida 16/512, todo bajo 131072. Prompt `scenario.json` SHA-256 `aeee353da01f15a6e9e8930353a0b21627c4027e88cb1c9ef69d00fb1e6d24d3`; 6000 líneas y cuatro hechos sembrados. El control inicial usa `tool_choice=auto` con instrucción de no llamar la tool para que Strata registre el prompt con tools; la compactación trae `tools=[]`. Thinking está desactivado explícitamente (`reasoning.effort=none`).
- Arreglos documentados antes de inferencia: helper CPU añadía `source/tools` para importar el tokenizer de referencia; se corrigió el import de `messages_for_compaction`; el ajuste binario ahora retiene el punto más cercano; y se corrigió el campo Responses de reasoning para que el prompt medido coincida con la petición ejecutada. No hubo carga ni uso de GPU en estos preflights.
- Recursos justo antes del primer lanzamiento: RTX 3090 0: 1133 MiB usados por entorno gráfico, 0% GPU; RTX 3090 1: 108 MiB, 0%; RAM disponible 106 GiB; swap usado 1.7/8 GiB, bajo la guarda operativa de 2 GiB. Puerto 8352 libre. El runner registra telemetría por GPU y separa la inicialización del modelo del tiempo de request.
- **Resultado de prefill:** en A (off), compaction volvió a leer 120216 tokens, media de 33,348 s (mediana 33,227). En B (on), reutilizó 120405–120415 de 120478 tokens y leyó 63–73; lectura media 0,448 s (mediana 0,465). Prefill inicial de 120412 tokens: A 33,904 s/3551,6 tok/s; B 33,649 s/3578,5 tok/s. La latencia API completa de compaction fue A 33,849 s media y B 1,759 s.
- **Calidad:** las seis respuestas iniciales fueron `READY`; las seis compactaciones acabaron HTTP 200/`completed`. A recuperó 4/4 hechos en 3/3; B recuperó 4/4 en 2/3, y en B-3 produjo texto corrupto y perdió los cuatro. Esa corrida sigue siendo válida de calidad con un fallo funcional, no se repitió ni se ocultó. Sin OOM/CUDA/timeout/transporte roto. Resultado y clasificación por corrida en `RESULTS.md` y `receipts/comparison.json`.
- **Decisión:** mantener `codex_compaction_cache` apagado por defecto. La reducción de prefill está confirmada para este perfil y fixture; la fiabilidad de resumen queda provisional por un fallo en tres corridas. Ningún cambio productivo.
- **Cierre de recursos:** seis servidores terminaron con exit code 0, puerto 8352 cerrado; las GPU volvieron a idle. Suma de duración de las corridas: 589,522 s incluyendo carga de modelo por corrida; no se limpió la page cache del SO.
