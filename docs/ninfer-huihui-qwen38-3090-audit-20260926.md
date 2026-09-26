# Auditoría NInfer Huihui Qwen3.8 en RTX 3090 — 2026-09-26

## Pregunta y alcance

El post describe Qwen3.8-27B Huihui Abliterated en una RTX 5090 de 32 GB con
NInfer, MTP y cuantización NVFP4/groupwise-int. Se evalúa qué se puede trasladar
a esta máquina (2× RTX 3090 de 24 GB, SM86) y si hay evidencia para cambiar
perfiles de coding/harness, visión/Computer Use o Ingi Charla.

Fuentes: [post de Reddit](https://www.reddit.com/r/LocalLLM/comments/1woxb4n/ninfer_qwen_3827b_uncensored_on_rtx_5090_175_toks/),
[guía NInfer-3090 para Windows](https://github.com/Don-Chad/ninfer-3090/blob/master/docs/rtx-3090-windows.md),
[runtime NInfer-3090 v0.6.1](https://github.com/Don-Chad/ninfer-3090/releases/tag/v0.6.1-rtx3090),
[artefacto Huihui groupwise-int](https://huggingface.co/Barding-Defense/Qwen3.8-27B-huihui-abliterated-groupwise-int-NInfer)
y [artefacto NVFP4 del autor del post](https://huggingface.co/lyf/Qwen3.8-27B-Huihui-Abliterated-NVFP4-MTP-VL).

## Qué dice el post y qué no demuestra

El autor reporta ~175 tok/s y contexto de 262K en una RTX 5090. Su único dato
de prefill a contexto alto es 247.802 tokens, 1.675 tok/s, con groupwise-int,
KV int8 y una prueba needle-in-a-haystack al 90 %. No reporta BCB/HE, calidad
de coding, exactitud de tool calls ni resultados de Computer Use. Su estimación
de 2.500–3.000 tok/s a 150K es una extrapolación, no una medición.

El NVFP4 del post apunta a Blackwell/sm_120; la RTX 3090 es Ampere/sm_86 y no
puede ejecutar esa receta NVFP4. Para la prueba local se usa el artefacto
groupwise-int del mismo checkpoint Huihui con el fork NInfer que sí declara
soporte SM86. Por tanto, cualquier resultado de abajo pertenece a
**groupwise-int + NInfer-3090**, no al NVFP4 del post. La cifra de 175 tok/s y
los 262K tampoco se consideran metas transferibles a una 3090.

## Perfiles opt-in

Se añadieron a `assets/system_profiles.json` tres entradas de benchmark:

- `sys-bench-ninfer3090-huihui-groupwise-mtp3-32k`: texto, MTP3, KV int8,
  32K, RTX 3090 única.
- `sys-bench-ninfer3090-huihui-groupwise-mtp3-vision-32k`: mismo modelo y
  parámetros, con visión habilitada.
- `sys-bench-ninfer3090-huihui-groupwise-nospec-32k`: control pareado sin
  MTP/draft.

Se fijó el dispositivo NInfer 1 para aislar la evaluación del servidor que ya
ocupaba GPU 0. Sampling: temperature 0.60, top-p 0.95, top-k 20, min-p 0,
presence penalty 0; repetición queda en el default del runtime. La variante de
visión está separada del perfil de texto para que el coste del projector y sus
reservas no contamine esa comparación.

## Resultados locales

Se descargó el archivo de 18.210.531.328 bytes y su SHA-256 coincidió con el
model card (`8c9f9d67a07ac97506978f6db6695d8074f78dec0fb80c4a85a8fb6fbedd7f03`).
El ZIP NInfer-3090 v0.6.1 también coincidió con el checksum del release.

El primer arranque de `sys-bench-ninfer3090-huihui-groupwise-mtp3-32k` recibió
`cudaMalloc failed: cudaErrorMemoryAllocation: out of memory` durante el inicio,
cuando coincidió con otro proceso local de Mica en GPU 1. No se detuvo ese
proceso ni el `llama-server` ajeno que usaba GPU 0. Después, con ambas GPU
disponibles, el modelo cargó bien (16,67 GiB de pesos y reserva KV de 32K), pero
falló en warm-up con `cudaErrorInvalidValue` en
`gqa_attention_prefill.cu:64`. El mismo error se repitió con el launcher C1
publicado (64K, prefill 1024), con el control sin MTP y con el launcher de
visión (32K, prefill 512); en todos los casos las reservas de pesos/KV
terminaron antes del fallo. Ningún servidor llegó a health ni aceptó requests.

La hipótesis de incompatibilidad del artefacto/kernel con el fork NInfer-3090
en esta RTX 3090 queda **confirmada para esta configuración**; el log no permite
atribuir el defecto a una sola capa del modelo o del runtime. Esto es un fallo
operativo, no un resultado de calidad del modelo. La secuencia completa y los
logs están en el artifact JSON.

| Prueba | NInfer Huihui groupwise-int | Control/comparación | Conclusión |
|---|---:|---:|---|
| Compatibilidad/runtime | Pesos 16,67 GiB y KV 32K/64K cargan; MTP3, sin MTP y visión dan el mismo `cudaErrorInvalidValue` en warm-up | NInfer-3090 v0.6.1 Windows, RTX 3090 SM86; settings de los launchers upstream | **INFERIOR en compatibilidad operativa** frente al perfil NInfer Qwen3.8 histórico que sí llegó a inferencia; este artefacto Huihui no llega a health. |
| HE0 → HE20 → BCB/8 LC-H1 | No ejecutado | Mismo harness/agente requerido | Sin evidencia de calidad; no atribuir cero. |
| Decode / prefill y aceptación MTP | No ejecutado | A/B MTP3 vs. mismo perfil sin MTP | Sin evidencia de velocidad. |
| Imagen / tool-call Computer Use | El perfil `--vision` carga pesos/proyector, pero falla en warm-up antes de recibir una imagen | Fixture y schema `desktop_*`; acción sin ejecutar | **No usable con este runtime**; grounding no evaluado. |
| Ingi Charla | No ejecutado | STT/TTS local no cambia con el LLM | No sustituye el LLM de Charla validado ni evalúa voz fin-a-fin. |

La referencia histórica de NInfer Qwen3.8 normal (otro checkpoint) es BCB 3/8,
~73–75 tok/s en 8K, 50,1 tok/s a 80K y 62,9 tok/s a 120K; SOL mantiene BCB
8/8. No son un A/B pareado con Huihui ni con este runtime/artefacto y quedan
como contexto histórico, no como comparación numérica válida. El intento y sus
hashes están en
[`ninfer-huihui-qwen38-3090-20260926.json`](../artifacts/ninfer-huihui-qwen38-3090-20260926.json).

## Lectura por superficie

- **Harness/coding:** la hipótesis de contexto largo puede facilitar tareas
  extensas, pero el post no contiene evaluación de código. BCB/8 LC-H1 local es
  el gate de calidad; HE0 y HE20 son gates previos.
- **Computer Use con visión:** el formato incluye visión; eso acredita capacidad
  técnica de recibir imágenes, no grounding correcto ni mejor uso de
  `desktop_*`. Se mide con una fixture del proyecto y se inspecciona el
  contrato de tool-call sin ejecutar el click.
- **Ingi Charla:** el post evalúa un LLM de texto. No trae WER/CER, STT, TTS ni
  latencia fin-a-fin de voz. Cambiar el LLM no mejora por sí mismo Parakeet,
  Whisper, VAD ni Pocket TTS.
- **Consulta a modelos cloud:** no se incorpora el patrón narrado de reformular
  prompts para evadir guardrails de un proveedor. Cualquier fallback a
  `ask_teacher` requiere una petición legítima y debe conservar las políticas
  del servicio consultado.

## Decisión

**Inferior en compatibilidad operativa en la pila SM86 medida; no se pudo medir
calidad ni velocidad.** El perfil Huihui no desplaza al NInfer Qwen3.8 histórico
que sí ejecutaba requests, y falla también sin MTP y en la variante de visión.
La evidencia de la prueba se conserva para el historial; no se promueve ni queda en la cola activa.
No cambia el perfil recomendado, Ingi Charla, Computer Use ni el harness. Las
cifras del post siguen siendo de NVFP4/RTX 5090 y no se asignan a esta variante.

El 2026-09-26, a pedido del usuario, se eliminó el archivo local de pesos (18.210.531.328 bytes) y se retiraron del catálogo las tres entradas Huihui. Se conserva esta evidencia histórica; el paquete del runtime no se borró.
