# Qwen3.8 Flash-Next, zram y comparación contra SOL — 2026-09-19

## Conclusión

zram no mejora la calidad del modelo ni aumenta la velocidad efectiva. En esta
máquina sólo resultó útil como colchón temporal para evitar que la carga inicial
muriera inmediatamente cuando el modelo Flash-Next consume casi toda la RAM.
Cuando la carga llegó a ocupar el zram, el proceso entró en thrashing y no
ofreció un endpoint utilizable. No se debe activar zram como optimización del
perfil productivo.

SOL permanece como default: BCB 8/8, HE20 20/20, visión 4/4, tool-use estable,
262K validado y aproximadamente 74 tok/s narrativos y 102 tok/s en código.

## Entorno

- Ryzen 9 9950X3D.
- 2 × RTX 3090, TP2/P2P.
- 123 GiB de RAM.
- Flash-Next: `Flash-Next-W4A16-FP8PLE-albucino`, 116,21 GiB, 25 shards
  safetensors, arquitectura `Qwen4ExpForConditionalGeneration`.
- Runtime experimental: vLLM dev `0.1.dev20073+g8e685d198`, imagen
  `qwen38-flash-next-2x3090:vision-nomtpp`.
- El host no tuvo límite `--memory` de Docker ni cgroup artificial.

La configuración temporal de zram fue:

```text
/dev/zram0  lzo-rle  32 GiB  prioridad 100
/swap.img   swap     8 GiB   prioridad -1
```

Después de cada corrida se retiró zram y se restauró el swap normal de 8 GiB.

## Corridas reproducidas

### Flash-Next, texto, MTP3, sin zram

Configuración: 131K, KV 2,25 GiB, 24 GiB de CPU offload, hot cache 60,
`max_num_seqs=1`, MTP3, visión desactivada.

| Caso | Tiempo / tokens | Velocidad de pared | Resultado |
| --- | ---: | ---: | --- |
| Prime | 4,956 s / 192 | 38,74 tok/s | Python correcto |
| Bugfix | 5,432 s / 192 | 35,34 tok/s | Funcional |
| JSON | 3,689 s / 87 | 23,58 tok/s | Salida no conforme al esquema |
| Plan | 4,782 s / 192 | 40,15 tok/s | Funcional |

La aceptación MTP observada fue aproximadamente 82,1 %, con longitud media
aceptada 3,46. Tool-use produjo correctamente `add(2,3)`, pero no existe todavía
un BCB8 ejecutado con este candidato.

### Flash-Next, visión, sin MTP, zram, 131K

Configuración: 131K, KV 2,25 GiB, 24 GiB de CPU offload, hot cache 60, visión
activa, `MTP_DEPTH=0`, una imagen y hasta 1.048.576 píxeles.

La prueba multimodal respondió correctamente `red blue 5` sobre una imagen
sintética con rectángulos rojo/azul y el texto `def add(a,b): return a+b`.
Tiempo observado: 3,866 s para 438 tokens de prompt y 5 tokens de salida.

En el mismo servidor, las pruebas de texto sin MTP dieron:

| Corrida | Tokens | Tiempo | Velocidad de pared |
| --- | ---: | ---: | ---: |
| 1 | 128 | 3,119 s | 41,03 tok/s |
| 2 | 128 | 4,602 s | 27,82 tok/s |
| 3 | 128 | 6,561 s | 19,51 tok/s |

La degradación coincide con el aumento de presión de zram; no es una mejora de
rendimiento. Esta variante demuestra visión funcional, pero no calidad agentiva
comparable con SOL.

### Flash-Next, visión, MTP3, 131K, sin límite artificial

La carga de modelo y PLE terminó, pero el warmup falló con:

```text
ScatterGatherKernel.cu:203 Assertion idx_dim >= 0 ...
Triton Error [CUDA]: device-side assert triggered
```

El contenedor no quedó marcado como `OOMKilled`. El fallo es compatible con la
interacción entre MTP y embeddings multimodales externos en esta revisión del
runtime, no con falta de memoria. Por eso no se debe combinar MTP3 y visión en
este perfil experimental.

### Flash-Next, texto, MTP3, zram 32 GiB, 131K

La carga de los pesos principales terminó y el contenedor no fue marcado como
`OOMKilled`, pero el servicio nunca alcanzó `health=200`:

- RAM usada: aproximadamente 114–116 GiB.
- zram usado: aproximadamente 31,5 GiB de datos, 27–28 GiB comprimidos.
- swap total usado: prácticamente 39 GiB.
- El proceso quedó preparando/cargando la cabeza MTP, sin endpoint operativo.

Esto confirma que zram extiende la carga, pero no vuelve viable esa receta. La
latencia de paginación domina antes de poder medir TG de forma honesta.

### Flash-Next, visión, MTP3, 262K

La corrida previa sin límite cgroup terminó con `OOMKilled=true` durante la
carga/P​​LE. Es un OOM real del contenedor/host, no una política artificial de
Docker. No se convirtió en un benchmark de velocidad porque nunca llegó a
servir solicitudes.

### Prueba de plantilla Jinja y protocolo multimodal

Se probó la plantilla segura de LlamaCode
`assets/chat-templates/qwen38-tools-fixed.jinja` con el runtime experimental,
primero en texto y luego con visión, manteniendo MTP desactivado para aislar la
variable de plantilla.

- Texto: el servidor cargó correctamente a 131K y el tool-call `add(2,3)` salió
  con argumentos JSON válidos. En cuatro smoke-tests la velocidad de pared fue
  25,39 / 30,49 / 20,09 / 27,39 tok/s; no es comparable directamente con el
  MTP3 nativo porque esta corrida no usó MTP.
- Visión: con una imagen sintética conocida, la plantilla produjo 64 tokens de
  `!` tanto con thinking por defecto como con
  `chat_template_kwargs.enable_thinking=false`. No describió los colores ni el
  dígito esperados. La carga del encoder sí completó y el servidor llegó a
  `health=200`, por lo que el fallo está en el protocolo/renderizado o en la
  interacción plantilla-modelo, no en la disponibilidad de GPU.

Conclusión: `qwen38-tools-fixed.jinja` no debe aplicarse a Flash-Next. La
plantilla nativa del checkpoint sigue siendo la única receta multimodal local
validada para este candidato. La canonicalización de schemas MCP de LlamaCode
se conserva como mejora de prefix-cache, pero no se reemplaza la plantilla de
Flash-Next por la de Qwen3.8 estándar.

## Comparación resumida

| Perfil | Contexto | Visión | MTP | Velocidad observada | Calidad comparable | Decisión |
| --- | ---: | --- | --- | ---: | --- | --- |
| SOL | 262K | 4/4 | MTP4 | 74 narr. / 102 código | BCB8 8/8, HE20 20/20, tools estable | Default |
| Flash-Next texto | 131K | No | MTP3 | 23,6–40,2 tok/s pared | Sin BCB8; JSON no conforme en smoke | Experimental |
| Flash-Next visión | 131K | Funcional | Sin MTP | 19,5–41,0 tok/s en smoke | Sin BCB8 | Experimental multimodal |
| Flash-Next visión + MTP | 131K | No operativo | MTP3 | Sin métrica | Crash CUDA en warmup | No usar |
| Flash-Next 262K + visión | 262K | No operativo | MTP3 | Sin métrica | OOM real durante carga | No usar |

Las velocidades no son una sustitución del BCB: son tiempos de pared de
smoke-tests con prompts distintos de los ocho casos oficiales. No hay evidencia
de que Flash-Next sea más inteligente que SOL; de hecho, el único resultado
estructurado observado fue inferior al contrato JSON esperado.

## Decisiones y próximos límites

1. No cambiar el default SOL.
2. No activar zram automáticamente desde LlamaCode: puede evitar una muerte
   inmediata, pero aumenta la latencia y puede dejar el sistema en thrashing.
3. Si se conserva Flash-Next, hacerlo sólo como perfil experimental de visión
   sin MTP y con 131K; no anunciarlo como perfil de calidad.
4. No volver a probar MTP+visión hasta contar con una revisión de vLLM que
   corrija la ruta de embeddings multimodales de Qwen4Exp.
5. No aumentar contexto a 262K en este checkpoint mientras la carga real ya
   consume casi toda la RAM y el caso multimodal termina en OOM.

## Investigación upstream y límites actuales

La imagen utilizada sigue siendo `vllm` dev
`0.1.dev20073+g8e685d198`; el tag oficial `qwen38-flash-next` resolvió al mismo
digest durante la comprobación, por lo que no había un binario más nuevo para
instalar sin cambiar de runtime.

- [vLLM #54764](https://github.com/vllm-project/vllm/issues/54764) documenta el
  pico de memoria de PLE durante prefills de longitudes mixtas. El parámetro
  `--long-prefill-token-threshold 8192` puede reducir ese pico, con posible
  aumento de TTFT; no es una mejora de calidad y no se activó en SOL.
- [vLLM #55515](https://github.com/vllm-project/vllm/issues/55515) mantiene la
  restricción de pipeline parallel para el PLE de Qwen4Exp.
- [PR #56444](https://github.com/vllm-project/vllm/pull/56444) propone transporte
  de PLE para pipeline parallel, pero no estaba integrado en la revisión
  probada.
- [vLLM #56088](https://github.com/vllm-project/vllm/issues/56088) enumera los
  bloqueos actuales para DFlash/DSpark con Qwen4Exp. No hay un drafter DFlash
  compatible localmente para probar esos parches.

Por tanto, no se promovió Flash-Next, no se cambió el default SOL y no se
modificó el perfil productivo. La única mejora segura que queda para una futura
iteración es probar un runtime que incorpore explícitamente esos parches, con
MTP, visión y el contexto evaluados por separado.

Al finalizar la campaña se retiró el contenedor experimental, se desactivó
`/dev/zram0` y se dejó activo SOL en el puerto 8113. Se verificó `health=200`,
Compiz activo y la memoria libre del host recuperada.

## Campaña adicional de calidad: IQ1_S e IQ4_XS — 2026-09-19

Se reabrieron los artefactos que todavía existen en Disco D; las rutas antiguas
de la documentación estaban desactualizadas:

- `Flash-Next-ASTRA-IQ1_S/UD-IQ1_S`: aproximadamente 68 GiB.
- `Flash-Next-ASTRA-IQ4_XS/UD-IQ4_XS`: aproximadamente 88 GiB.

La comparación se ejecutó con el binario `llama-server` del checkout
`llama.cpp-lazy-28136`, commit `c6a9e5c9`, arquitectura `qwen4exp`, split por
capas, dos RTX 3090, KV Q8/Q8, Flash Attention, mmap, 32K de contexto, una
sesión y sin límite cgroup artificial. Se utilizó el mismo pack de ocho tareas
BigCodeBench-Hard de LlamaCode y el mismo evaluador Python.

### IQ1_S, plantilla nativa, sin MTP

| Variante | BCB directo | TG promedio | Resultado |
|---|---:|---:|---|
| Primera respuesta, extracción segura de fences | **1/8** | **57,6 TG** | Sólo pasó 870; los demás tuvieron errores semánticos en CSV, archivos, tipos, fechas o validaciones. |
| Tres reparaciones con el error del test | **1/8** | 57–61 TG | No corrigió los casos restantes; un ciclo llegó a perder la definición de `task_func` por truncamiento. |
| Tests completos expuestos al modelo, sólo diagnóstico | **7/8** | ~59,5 TG | No es BCB válido porque filtra las pruebas; aun así falló 509. |
| Thinking activado, 4096 tokens | **0/1 evaluable** | ~55,9 TG | Consumió el presupuesto en `reasoning_content` y dejó `content` vacío. Se canceló para no contaminar la campaña. |

El resultado 7/8 es un techo diagnóstico de protocolo, no una validación de
calidad. La mejora de harness de extraer fences funcionó, pero no transformó
los errores semánticos en soluciones correctas. La reparación informada por
tests tampoco alcanzó BCB8.

### IQ4_XS, reparto CPU-MoE real

Con offload total a GPU, IQ4_XS intentó reservar aproximadamente 31,5 GiB en
una sola RTX 3090 y falló con `cudaMalloc out of memory` antes de generar. No se
alteró artificialmente la memoria para ocultarlo. Con `--n-cpu-moe 31`, la carga
fue operativa, pero el BCB directo quedó en **1/8** y la velocidad media fue
**23,2 TG**, frente a aproximadamente 57,6 TG de IQ1_S. No apareció ninguna
señal de calidad superior que justificara el coste de 88 GiB y el offload a
CPU.

### Reparación focalizada del caso 509

Se ejecutó además una cadena aislada con temperatura 0,1 y hasta tres
reparaciones, esta vez mostrando el código exacto de los tests sólo después del
primer fallo. El caso siguió fallando por el contenido del diff CSV; dos
reparaciones intermedias devolvieron código truncado/sin `task_func`. Esto
descarta que una simple plantilla de reparación o más reintentos convierta
IQ1_S en un agente 8/8.

### Comparación de calidad y decisión

| Perfil | BCB comparable | HE20 / tools | Velocidad útil | Decisión |
|---|---:|---|---:|---|
| **SOL** | **8/8** | HE20 20/20; tools estable; visión 4/4 | 74 narr. / **102 código** | Default |
| **ASTRA IQ1_S** | **1/8**; 7/8 sólo filtrando tests | Tool-call puntual; sin visión compatible validada | **57,6 TG** directo | No supera; sólo laboratorio de contexto/consumo |
| **ASTRA IQ4_XS** | **1/8** | Sin validación multimodal comparable | **23,2 TG** con CPU-MoE | No supera; más pesado y más lento |

No se encontró una configuración superior a SOL en calidad. Por lo tanto no se
modificaron perfiles, plantillas productivas, binarios de LlamaCode ni el
default. Las únicas conclusiones transferibles al harness son: mantener la
extracción segura de fences, no considerar tests filtrados como BCB y limitar
las reparaciones para evitar truncamiento. Al cierre se detuvo el runtime
experimental, se restauró el contenedor `vllm-qwen38-27b-dual-fast`, se verificó
su endpoint de salud, se dejó sólo el swap de disco normal y no quedó zram
activo.

## Campaña adicional: plantilla nativa, razonamiento bajo y muestreo conservador — 2026-09-19

Se repitieron casos del mismo pack directo con el runtime safetensors de
Flash-Next, sin MTP, sin visión, contexto 131K, KV de aproximadamente 1,9 GiB,
`--enforce-eager`, sin límite cgroup y con zram de 64 GiB para evitar que la
presión de la tabla PLE terminara en un OOM real. Se conservaron la plantilla
nativa del modelo y el protocolo de extracción de fences. La receta nueva fue:
`enable_thinking=true`, `reasoning_effort=low`, `temperature=0.2`,
`top_p=0.95`, `top_k=20`, `max_tokens=4096`.

| Caso | Resultado | Tiempo de pared | Observación |
|---|---|---:|---|
| 509 | Código sintácticamente válido | 113,7 s | La respuesta ya no terminó vacía; requiere ejecutar los tests ocultos para cerrar semántica. |
| 857 | Código sintácticamente válido | 49,9 s | Implementación plausible de copia por extensión. |
| 492 | Código sintácticamente válido | 56,6 s | Implementación plausible de generación de ventas. |
| 310 | Sin contenido evaluable | 95,9 s | `finish_reason=stop`, pero la respuesta fue vacía. |
| 310, sin thinking, greedy | Código corrupto | 95,7 s | Tokens no-Python y caracteres inválidos; cambiar muestreo no lo reparó. |

Los casos 800 y 123 también produjeron texto con sintaxis válida en la misma
receta, pero no se aceptan como BCB hasta ejecutar el grader oculto; en pruebas
anteriores ambos habían fallado semánticamente. El resultado no permite
promover Flash-Next: el mismo pack ya produjo **1/8** en la campaña directa,
incluyendo corrupción en varios casos, mientras SOL mantiene **8/8** con
HE20 20/20, tool-use estable y visión 4/4.

La prueba simple de `reasoning_effort=low` sí generó código correcto, por lo que
la plantilla nativa y el modo de razonamiento no están completamente rotos.
Sin embargo, el fallo reproducible del caso 310 con thinking bajo, thinking
desactivado y greedy demuestra que el problema restante es de calidad/robustez
del modelo o del runtime Qwen4Exp, no de zram, contexto, temperatura o falta de
memoria. MTP+visión continúa bloqueado por el `ScatterGatherKernel` y MTP a
262K por OOM real; no se activó en producción.

Se intentó reanudar la descarga local de GALACTA/DeepSeek V4 Flash IQ3_S para
validar la única alternativa con BCB histórico 8/8. La descarga quedó parcial:
los shards 2 y 3 siguen incompletos y no se ejecutó el modelo. No se usa esa
referencia histórica para cambiar el default.
