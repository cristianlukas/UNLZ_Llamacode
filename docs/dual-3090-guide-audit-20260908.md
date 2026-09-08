# Auditoría de la guía Dual 3090 — Ubuntu — 2026-09-08

Se contrastó la guía aportada con el equipo real (2× RTX 3090), el runtime CUDA
que usa LlamaCode y los perfiles instalados. Las recomendaciones de vLLM no se
trasladan automáticamente a `llama-server`: usan otro scheduler, kernels,
formato de pesos y, en varios casos, artefactos que no están instalados.

## Estado físico comprobado

| Señal | Resultado | Consecuencia |
|---|---|---|
| GPU | 2× RTX 3090 de 24 GiB, driver 595.71.05, límite 350 W | La capacidad combinada sirve para modelos grandes, pero cada proceso sigue limitado por la topología y el reparto real. |
| `nvidia-smi topo -m` | `GPU0↔GPU1: PHB` | La ruta física es PCIe/PHB; no se puede aplicar la ganancia de 35–49% atribuida a un enlace NVLink. |
| `nvidia-smi topo -p2p r/w` | `OK` en ambas direcciones | El driver P2P sí está activo sobre PCIe. La app ahora lo detecta por separado de la topología. |
| `nvidia-smi nvlink -s` | todos los enlaces inactivos | P2P PCIe funciona, pero no equivale a tener un bridge NVLink. |
| NCCL | `libnccl.so.2` y `libnccl-dev` instalados | Es una dependencia disponible, pero el runtime actual no expone un modo NCCL/all-reduce que permita convertir esta topología en NVLink. |
| Runtime | `split-mode layer` disponible; `tensor` figura como experimental | Se conserva `layer`, que es el camino validado para este equipo. |

## Recomendaciones auditadas

| Idea de la guía | Veredicto para LlamaCode | Evidencia/acción |
|---|---|---|
| Qwen3.6/Qwen3.8 en vLLM TP=2, FP8/NVFP4 y KV FP8 | No se promueve | No hay vLLM ni artefactos AutoRound/NVFP4 locales. NVFP4/A8 no es una ruta válida para estas RTX 3090 SM86 en el runtime actual. |
| MTP de los compose vLLM | No se copia | La advertencia GDN de vLLM no es una garantía para llama.cpp; ASTRA ya mostró fallas con MTP/cache y queda sin drafter. SOL y sus variantes MTP ya tienen pruebas separadas. |
| Sampling Qwen: `temp 0.6`, `top-p 0.95`, `top-k 20`, `min-p 0` | Aplicado donde corresponde | SOL y TERRA conservan el muestreo conservador. ASTRA usa `temp 1.0` porque su perfil es de razonamiento largo; no se alteró Windows. |
| Preferir contexto sobre `max-num-seqs` | Aplicado | Los perfiles operativos usan `parallel=1`; ASTRA 196K, SOL 131K y TERRA 131K. El KV disponible depende de VRAM real, no sólo del techo declarado. |
| Prefill largo puede degradar decodificación concurrente | Mitigado parcialmente | LlamaCode mantiene `parallel=1` para estos perfiles. Un proxy/admission-control de vLLM no se puede incorporar al `llama-server` sin cambiar la arquitectura. |
| NVLink/P2P para activar tensor parallel | Detectado, pero no promover tensor | P2P PCIe está disponible, pero la prueba real de Qwen3.8-27B con tensor split abortó durante la carga: `llama_params_fit is not implemented for SPLIT_MODE_TENSOR` y luego `ncclAllReduce`. |
| Prefix caching/KV reuse | Ya funciona | Una prueba real en TERRA reutilizó 5.064 de 5.068 tokens del prefijo: la segunda petición bajó de 0,658 s a 0,068 s. No hace falta agregar otra capa de caché. |
| `--split-mode layer` explícito | Promovido en Linux | Se añadió explícitamente a ASTRA, SOL, TERRA, LUNA y METEOR. Aunque P2P esté activo, `layer` es el único camino estable validado para estos perfiles. Windows no cambia. |
| Gemma-4-31B, Tess-4-27B, Qwen-AgentWorld-35B-A3B | No se agregan | La guía los describe para otros backends/artefactos. No hay una medición local comparable ni un perfil LlamaCode validado que justifique descargar/agregar modelos grandes. |

## Prueba adicional: Qwen3.6-35B-A3B dual

La única variante de la guía que podía cambiar la tabla sin duplicar SOL era el
MoE Qwen3.6-35B-A3B. Se descargó `Intel/Qwen3.6-35B-A3B-int4-mixed-AutoRound`
(~20 GiB) y se probó con vLLM TP=2, P2P PCIe, KV FP8 E4M3 (8 bits), visión y
sin MTP. La receta local recomienda no usar MTP en este MoE dual: la
sincronización adicional entre las dos GPU supera la ganancia de aceptación.

| Prueba | Resultado local | Lectura |
|---|---:|---|
| Decode narrativo, una sesión | **129,27 tok/s** | 2,0× el SOL histórico llama.cpp y claramente superior a LUNA/TERRA anteriores |
| Decode código, una sesión | **129,66 tok/s** | Muy estable; CV 0,6% |
| Prefill 10K / 90K | **7.755 / 4.756 tok/s** | Más rápido que SOL en prefill |
| N=4 agentes | **295,9 tok/s agregado / 102,3 por agente** | 4/4 sin errores, 99,0% de retención |
| N=8 agentes | **100,2 tok/s agregado / 31,8 por agente** | 8/8 sin errores; 97,8% de retención, apenas bajo el umbral estricto de 98% |
| Contexto | **240.660 tokens recuperados** | 2/2 needles; 262K es techo asignable, ~200K–240K es operativo |
| Herramientas y formas de agente | **5/5 stress** | Tool call, multi-turn, IDE, coding y razonamiento pasaron |
| Visión | **4/4** | Imagen reconocida correctamente |

El techo de 262K queda limitado en la práctica por margen: a 240K quedaron
~484 MiB libres. El modelo es un candidato fuerte para un perfil de
concurrencia/visión, pero no se le asigna todavía una puntuación BCB ni se
reemplaza TERRA hasta correr HE0, HE20 y BCB dentro del mismo harness de
LlamaCode. Quedó agregado como perfil opcional `QWEN35-A3B` en Linux; SOL y
Windows permanecen sin cambios.

## Medición operativa de control

El servidor TERRA activo (Ling 3.0 Tiny, no Qwen; se conserva como perfil del
usuario) respondió correctamente con la plantilla de herramientas y registró:

- prompt: aproximadamente **737 tok/s** en la prueba corta;
- decode: aproximadamente **195 tok/s**;
- reutilización de prefijo: **5.064/5.068 tokens** en la segunda petición;
- sin speculative decoding activo en TERRA;
- `KV q8_0`, `parallel=1`, `batch=1024`, `ubatch=256` en Linux.

La prueba adicional con el mismo runtime CUDA y Qwen3.8-27B Q4_K_M, contexto
32K, K/V `q8_0`, B512/U64 y P2P activo fue:

| Modo | Resultado |
|---|---|
| `split-mode tensor`, `tensor-split 1,1` | No inicia; aborta por `SPLIT_MODE_TENSOR`/`ncclAllReduce`. |
| `split-mode layer`, P2P activo | Inicia y responde; control corto de generación: **37,02 tok/s**. |

El A/B histórico de la matriz de benchmarks, que desactivó las copias peer en
un binario aislado, midió `60,75` tok/s medios con P2P frente a `60,61` sin P2P
en `layer`: una diferencia de aproximadamente **0,2%**, dentro del ruido de la
prueba. Esto es esperable: en `layer` las GPU intercambian principalmente una
activación por pasada; P2P ayuda a la transferencia, pero no elimina el límite
dominante de ancho de banda de VRAM.

Estos números no deben compararse directamente con los números vLLM de la guía:
son otro modelo, otro backend y otra carga.

## Decisión final

No se instalaron vLLM, NVFP4, Marlin ni nuevos modelos: no había artefacto local
ni una prueba que demostrara una mejora segura para LlamaCode. Se implementó la
única mejora general y de bajo riesgo respaldada por la evidencia: detectar
correctamente P2P PCIe en el diagnóstico y fijar `--split-mode layer` en Linux
para los perfiles principales. Se mantienen los límites del proyecto: pesos
como máximo Q8, KV como máximo `q8_0`, Windows sin cambios y ASTRA experimental.
