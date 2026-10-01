# Revisión local de Qwen3.8 INT8 + DFlash2 — 2026-10-01

## Conclusión

La receta sigue siendo un candidato interesante para velocidad, pero no quedó
validada en esta notebook. No hay evidencia local que permita compararla con el
perfil SOL ni promoverla en LlamaCode. No se cambiaron perfiles ni código.

El modelo publicado especifica un vLLM nightly fijado y parches propios. El
intento exploratorio con el wheel estable vLLM 0.29.0 no cargó el checkpoint
INT8 completo: falló en los embeddings cuantizados. Ese fallo no demuestra que
el modelo sea incompatible con el runtime nightly documentado.

## Entorno y artefactos

- Hardware local: 2× RTX 3090, PCIe P2P; NVLink no está activo.
- Target descargado: `lued/Qwen3.8-27B-INT8-W8A16-DFlash2`, revisión
  `2971c64ba386dd3faa6884cc215f67b3b2477a3e`, 6 shards safetensors (~29.5 GB).
- Drafter W8 descargado: `lued/Qwen3.8-27B-DFlash2-W8`, revisión
  `f454fa8e6a84387bf006f849584f72541cc29118` (~2.17 GB).
- Drafter W4 descargado para comparación exploratoria:
  `syvai/Qwen3.8-27B-DFlash2-W4A16`, revisión
  `4d30ec736ffc6b8688dc2ae2b502d9b48bdec279` (~1.28 GB). Su metadata declara
  `compressed-tensors` pack-quantized de 4 bits; no GPTQ.
- Los pesos viven en los volúmenes de modelos; no se copiaron al checkout.

## Pruebas realizadas

1. Se verificó la identidad, integridad y compatibilidad de ABI del artefacto
   FA2 FP8-KV para SM86. La instalación reportó vLLM 0.29.0 y aceptó el layout
   de su API. El parche local `vllm#51581` también aplicó sobre el archivo
   DFlash de ese runtime.
2. Se inspeccionaron las configuraciones del target y de W4. El target usa
   `Qwen3_5ForConditionalGeneration`, pesos `compressed-tensors` W8A16 y una
   regla cuantizada `group_embed`; W4 declara la arquitectura
   `DFlash2DraftModel`.
3. El arranque dual TP=2 no pasó el chequeo de memoria inicial: vLLM encontró
   sólo 4.84 GiB libres en GPU0 frente a 21.67 GiB solicitados. En ese momento
   otro proceso del usuario (`qwfn-server`) ocupaba ~17.7 GiB de esa tarjeta.
   No se lo detuvo ni se le enviaron solicitudes.
4. En un intento aislado en GPU1, con TP=1, offload a RAM y contexto de 8K, el
   motor reconoció el target, FA2 y DFlash2, pero la carga falló al asignar
   `model.language_model.embed_tokens.weight_packed`: el `Qwen3_5Model` del
   wheel 0.29.0 no expuso ese parámetro. El checkpoint sí lo declara en su
   índice, junto a `weight_scale` y `weight_shape`. Esta configuración no
   corresponde a la receta dual; sólo sirvió como diagnóstico de carga.
5. La ficha técnica del modelo pide el nightly
   `vllm/vllm-openai:nightly-5a4c8d99242e9e069b604d0e9b969e77f7dd501d` y los
   parches `vllm-pr52816-dflash2` y `vllm-pr48375-mamba-drop-eagle-block`.
   El segundo existe en el checkout de club-3090 revisado; el primero ya no
   está en su HEAD actual bajo ese nombre. La instalación exploratoria con
   vLLM 0.29.0 fue una desviación del entorno fijado por la ficha.

## Límites que impidieron completar la matriz

- El volumen `containerd` tiene 63 GB en total y sólo ~2.1–2.7 GB libres (la
  cifra varía mientras Docker opera). El pull de `vllm/vllm-openai:v0.29.0`
  falló con `no space left on device`. No se borraron imágenes ni cachés.
- No se pudo iniciar el nightly fijado por la ficha ni correr el target TP=2.
- No se ejecutaron el control autoregresivo, mediciones de decode/prefill,
  aceptación DFlash2, contexto real de 262K, BCB, Computer Use, contrato de
  herramientas, visión ni evaluación del harness de LlamaCode.
- Por lo tanto no hay comparación válida de calidad, velocidad o uso de memoria
  entre la receta y el perfil actual. Tampoco se midió impacto en Ingi Charla.

## Lectura para LlamaCode

La idea sólo sirve como backend experimental optativo si se reproduce con el
nightly y los parches requeridos, con ambas GPU disponibles. En esta máquina la
receta tampoco recibe el beneficio de NVLink citado en la publicación. El
resultado no justifica cambiar el perfil actual ni los flujos de Computer Use o
Ingi Charla. El siguiente intento debe usar el entorno exacto de la ficha y
comparar autoregresivo frente a DFlash2 con la misma suite de agente.
