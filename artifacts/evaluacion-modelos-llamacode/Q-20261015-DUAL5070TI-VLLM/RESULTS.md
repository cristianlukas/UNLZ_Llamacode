# Resultados — Q-20261015-DUAL5070TI-VLLM

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

La cobertura final del harness registra HE0 como `blocked`, con HE20 y BCB
`pending`. El backend de inferencia y su API están operativos; el bloqueo está
en el tamaño del contexto que LlamaCode necesita para las definiciones de
herramientas. Subir sólo `n_ctx` puede aumentar el uso de KV cache en estas dos
RTX 3090, así que antes de retomar se debe reducir/compactar el schema del
harness o probar una configuración que quepa completa y pase el smoke. Después
se repite **sólo HE0**; HE20 y BCB8 arrancan únicamente si ese gate pasa.

No se repitió la task bank privada de `capy-flash` (4,28 h): ese runtime sigue
requiriendo GPUs `sm_120a`, que estas RTX 3090 `sm_86` no tienen. No se cambió
ninguna recomendación de perfil ni HarnessSpec. Computer Usage E2E, audio,
visión y evaluación de contexto largo no se cubrieron en esta continuación.

## Cierre operativo

El servidor vLLM y el daemon aislado de LlamaCode se detuvieron. Los puertos
18888 y 8877 quedaron libres y las dos GPUs quedaron sin carga de inferencia.
Los intentos y resultados crudos se conservaron en `receipts/`.

## Revisión del diseño y retest pendiente (2026-10-16)

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

Ese retest todavía no se ejecutó: el 2026-10-16 había servidores de modelos de
la aplicación usando ambas RTX 3090 y ocupando ~11–12 GiB por tarjeta. Se
preservaron esos procesos; no se intentó cargar un modelo de 30,84 GB sobre el
espacio VRAM restante. La prueba queda pendiente hasta que las GPUs estén libres.
