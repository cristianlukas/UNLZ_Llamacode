# Resultados — Q-20261015-DUAL5070TI-VLLM

## Estado actual (retest 2026-10-16)

**Screening cerrado sin promoción: HE0 no pasa a contexto 32.768.** Esta
prueba corrige el defecto del intento anterior: el contexto alcanza para el
prompt y los schemas nativos, y la KV permite una secuencia completa. Aun así,
LlamaCode no creó el archivo solicitado: el stream del agente repitió `duct`
hasta que el detector `stream_repetition` detuvo la generación. El
control directo del mismo código también repitió `duct` con el muestreo
recomendado. No lo atribuyo a falta de contexto. Los controles directos de
aritmética y de una llamada de herramienta simple sí pasaron, así que el fallo
queda acotado a generación de código con este checkpoint/configuración.

HE0 terminó **0/1 en 154,435 s**, sin timeout, sin archivos y sin llamadas de
herramienta, tras tres reparaciones. El smoke previo de respuesta `OK` era
demasiado superficial para medir coding; se canceló y no se cuenta como prueba
de calidad. Para obtener una comprobación útil se lanzó la tarea HE0 completa
como diagnóstico. Como HE0 falló, **HE20 y BCB8 no se ejecutaron**. No se
promovieron el perfil ni HarnessSpec. El
resultado 0/1 previo a 8.192 sigue descartado como medición de calidad; el
screening actual sí llegó a la tarea con contexto suficiente y es un fallo
válido de esta configuración.

## Estado de la primera ejecución (2026-10-15)

**Bloqueada en HE0; sin promoción.** Se completaron los smokes de API y el
intento de HumanEval 0 en LlamaCode. El backend vLLM respondió bien a una
llamada de herramienta directa, pero el harness LlamaCode no pudo producir la
salida de agente: sus schemas nativos de herramientas (~21.766 tokens) no
entran en el contexto configurado de 8.192. HE0 terminó 0/1 después de tres
reparaciones. Ese 0/1 se debe tratar como fallo de configuración del harness,
no como una medición de calidad del modelo. HE20, BCB8, ADV y TaskFlow no se
iniciaron porque la compuerta HE0 exige pasar primero.

## Almacenamiento y runtime

Los pesos completos del target (~29,56 GB) y del drafter (~1,28 GB) están en
la partición `/dev/nvme0n1p2`, en:

`/media/cristian/Disco local/Models/LlamaCodeEval/Q-20261015-DUAL5070TI-VLLM/models/`

Al cerrar, esa partición tenía 84 GiB libres; `/` tenía 16 GiB libres y el
volumen del checkout 149 GiB. El entorno vLLM quedó en el directorio aislado de
la tarea y pasó `uv pip check` (198 paquetes compatibles). No se cambiaron los
perfiles productivos ni el código de LlamaCode.

## Pruebas ejecutadas

- vLLM 0.30.0 TP2 cargó el target W8A16/DFlash2 fijado en
  `receipts/source-lock.json` y sirvió `qwen3.8-27b`.
- GET `/v1/models` respondió 200. El smoke de texto contestó `4` a `2 + 2`.
- El smoke directo del API OpenAI produjo una llamada válida a `record_sum`
  con argumentos `{"a": 2, "b": 2}`. Las respuestas crudas están en
  `receipts/chat-smoke.json` y `receipts/tool-smoke.json`.
- LlamaCode se probó con una copia de perfil aislada, `agent-maximo` y contexto
  8.192. El registro del agente documenta que los schemas nativos (~21.766
  tokens) exceden `n_ctx`, cambia al protocolo textual y termina con respuesta
  vacía (`finish=length`, cero tokens); no creó archivos ni llamadas de
  herramientas. Ver `receipts/agent-short-smoke.json`.
- HumanEval 0 en contexto 8.192 finalizó en 583,445 s: score 0/1, primera
  pasada 0/1, tres reparaciones, cero archivos y cero llamadas de herramienta.
  El criterio falló porque no se creó `solution_HumanEval_0.py`. Corrida:
  `HumanEval_1_tem_20261015_180255`; recibo:
  `receipts/HE0-context8192-resumed/result.json`.
- Los intentos con contextos 4.096–7.000 se rechazaron al exceder el límite
  entre prompt y tokens de salida. Son fallos de presupuesto de contexto, no
  puntajes de calidad. El primer intento a 8.192 fue interrumpido por el límite
  de duración del daemon aislado; se reanudó con un daemon de mayor duración y
  el resultado final indicado arriba sí completó.

## Por qué las demás etapas no arrancaron

En la primera ejecución, HE0 quedó bloqueado por contexto 8.192 insuficiente.
En el retest corregido la solicitud sí cupo, pero HE0 falló por salida repetida
y ausencia del archivo/calls esperados. La cobertura marca HE20 y BCB como
`pending`; no se iniciaron porque la compuerta HE0 exige éxito. Un nuevo intento
de coding requiere corregir y verificar la configuración/checkpoint con la
tarea completa; no basta con subir `n_ctx`.

No se repitió la task bank privada de `capy-flash` (4,28 h): ese runtime sigue
requiriendo GPUs `sm_120a`, que estas RTX 3090 `sm_86` no tienen. No se cambió
ninguna recomendación de perfil ni HarnessSpec. Computer Usage E2E, audio,
visión y evaluación de contexto largo no se cubrieron en esta continuación.

## Cierre operativo de la primera ejecución

El servidor vLLM y el daemon aislado de LlamaCode se detuvieron. Los puertos
18888 y 8877 quedaron libres y las dos GPUs quedaron sin carga de inferencia.
Los intentos y resultados crudos se conservaron en `receipts/`.

## Retest corregido y evidencias (2026-10-16)

La crítica del usuario es correcta: iniciar con el contexto heredado de 4.096 y
subirlo gradualmente hasta 8.192 fue un mal diseño para este agente. El log ya
mostraba que no alcanzaba para los schemas nativos de herramientas, por lo que
el resultado 0/1 de HE0 no evaluó al modelo como agente.

El guard de LlamaCode usa `historial + schemas + 1.024 tokens de reserva` para
decidir si cambia a protocolo textual. Los recibos registran ~21.766 tokens de
schemas y un prompt de HE0 de ~4.684 tokens; eso exige al menos ~27.474 tokens
antes de margen para salida. El próximo intento se fija en `n_ctx=32.768`, con
verificación de la capacidad de KV, conteo de tokens real y smoke del agente en
protocolo nativo antes de repetir únicamente HE0. Si el prompt real o la reserva
no caben, no se puntúa la suite.

El usuario autorizó detener los tres `llama-server` que ocupaban ambas RTX
3090 sin trabajo en sus `/slots`: PID 2476143 (Qwen3.5-9B, 8033), PID 2476814
(Qwen3.5-9B, 8081) y PID 3381124 (Gemma-4-12B, 8083). Los tres terminaron con
SIGINT. Después se cargó el modelo fijado en `receipts/source-lock.json` con
vLLM 0.30.0 TP2. La primera carga falló antes de cargar pesos por la ruta IPC
demasiado larga; la segunda fue rechazada por el guard de VRAM a `GPU_UTIL`
0,95; la tercera cargó con `GPU_UTIL=0,93`.

- **Capacidad:** `max_model_len=32768`; KV real 37.159 tokens; concurrencia
  máxima 1,13 para una solicitud de 32.768. `/health` y `/v1/models`
  respondieron 200. Fuente: `runtime/logs/vllm-context32768-startup-2.log` en
  la partición secundaria. El perfil cloud aislado de LlamaCode informó
  contexto 32.768.
- **Smoke de agente:** se envió `Responde exactamente OK, sin usar herramientas.`
  y se canceló tras 414,6 s de generación sin texto. No se usa como puntaje ni
  como prueba de coding; evidencia en `receipts/agent-short-smoke-32k.json`.
- **HE0 de LlamaCode:** con contexto 32.768 y `thinkingEnabled=false`, el
  stream terminó en `stream_repetition` con `ductduct…`; cero llamadas,
  cero archivos y tres reparaciones. El harness no agotó el timeout y
  `solution_HumanEval_0.py` faltó. Evidencia completa en
  `receipts/HE0-context32768-thinking-off-diagnostic/result.json`.
- **Control directo de coding:** se envió HumanEval/0 con la función, los
  criterios de aceptación y muestreo `temp=0,6`, `top_p=0,95`, `top_k=20`,
  `min_p=0`, penalizaciones 1/0 y reasoning desactivado. Produjo 512 tokens
  `duct` repetidos (`finish_reason=length`) en 28,4 s. Recibo:
  `receipts/HE0-context32768-direct-control.json`.
- **Controles API:** el mismo servicio contestó `4` a `2+2` en 0,263 s y
  llamó `record_sum(a=2,b=2)` correctamente en 0,769 s. Recibos:
  `receipts/api-text-control-context32768.json` y
  `receipts/api-tool-control-context32768.json`. En el smoke corto de
  herramienta, DFlash2 aceptó 31 de 42 tokens propuestos; es una sola muestra,
  no una medición de rendimiento.

La conclusión queda acotada: **el transporte vLLM y una llamada simple de
herramienta funcionan; la generación de código de este checkpoint/configuración
degenera tanto por el agente LlamaCode como en generación directa.** La suite
no demuestra por sí sola cuál es la causa interna entre checkpoint, template o
decodificación. No sirve para coding/agentes en este estado. No se extrapola a
Computer Usage, visión, audio, contexto largo ni al runtime NInfer.

## Cierre operativo del retest

Se detuvieron el servidor vLLM de esta tarea y el daemon aislado de LlamaCode.
Quedaron libres los puertos 18888, 8877, 8033, 8081 y 8083; no quedaron
procesos compute de inferencia. Las GPUs mostraron 829/108 MiB ocupados,
108 GiB de RAM disponible. Se conservaron los pesos y cachés en
`/media/cristian/Disco local`; se movió el clon del fork a
`/media/cristian/Disco local/Models/LlamaCodeEval/Q-20261015-DUAL5070TI-VLLM/source/`
y se actualizó el launcher. La raíz quedó con 4,5 GiB libres, p2 con 84 GiB y
el volumen del checkout con 143 GiB. Se mantuvieron las entradas del directorio
temporal compartido porque no se podía asignar su propiedad a esta corrida.
Recibo: `receipts/postflight-20261016-context32768.json`.
