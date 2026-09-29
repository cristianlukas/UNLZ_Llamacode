# Swift-Qwen3.8 Genesis GGUF — evaluación local

Fecha: 2026-09-29. Estado: **en evaluación; perfiles manuales agregados, no promover**.

## Pregunta y conclusión provisional

Se evaluó si `LuffyTheFox/Swift-Qwen3.8-27B-Genesis-GGUF`, mencionado en
[r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1wrx5sa/luffythefoxswiftqwen3827bgenesisgguf/), puede superar los perfiles locales
para coding/harness, Computer Use o Ingi Charla.

El GGUF usa el checkpoint inicial `ukisai/Swift-Qwen3.8-27B-GGUF` y agrega la
transformación de pesos “Genesis”; la tarjeta de este fork no publica resultados
reproducibles de calidad, tareas agentivas, velocidad o ablation antes/después.
La promesa de 262K/MTP4 es verificable como carga de servidor, pero la primera
petición con esa configuración cayó en CUDA antes de producir una respuesta.
Todavía no hay evidencia local para cambiar un perfil recomendado ni el
harness. Se agregaron dos perfiles manuales `benchmark=true`, ambos con
contexto inicial de 64K: split `layer` como primera prueba y split `tensor` para
un A/B posterior. Ninguno es `best` ni se ofrece como perfil automático.

## Fuentes y distinción entre modelos

- [GGUF Genesis consultado](https://huggingface.co/LuffyTheFox/Swift-Qwen3.8-27B-Genesis-GGUF):
  tarjeta revisada el 2026-09-29, revisión `489bc45881179c25539b169734627b8c3c83eab1`. Enumera `Swift-Qwen3.8-27B-Genesis-NVFP4-v4.gguf` (15.764.903.360 bytes),
  un archivo `noMTP`, y `mmproj-Swift-Qwen3.8-27B-F16.gguf` (927.606.976 bytes).
  Declara contexto nativo 262.144, MTP integrado, visión y sugiere 128K como
  mínimo para razonamiento.
- La misma tarjeta dice explícitamente que Genesis parte de
  [`ukisai/Swift-Qwen3.8-27B-GGUF`](https://huggingface.co/ukisai/Swift-Qwen3.8-27B-GGUF),
  no de Swift 1.5. Esto importa: Genesis-v4 no se debe etiquetar ni comparar
  como Swift 1.5. La tarjeta describe “reparación” de tensores mediante SVD y
  Marchenko–Pastur, pero no entrega un benchmark antes/después ni un protocolo
  que permita reproducir esa afirmación.
- UkisAI sí publicó resultados de Swift inicial frente al Qwen base; su informe
  usa BF16 y cinco corridas en varios benchmarks. Esa evidencia describe el
  checkpoint upstream, no prueba el GGUF Genesis ni el quant NVFP4 de este fork.
- En otra discusión sobre un Genesis anterior de Qwen3.8, una comparación
  comunitaria puntual encontró más tokens generados que Unsloth; es una señal
  débil y no corresponde a este Swift Genesis v4:
  [prueba previa de Genesis](https://www.reddit.com/r/LocalLLaMA/comments/1wbmo0k/comment/p8rtyp8/).

## Pruebas locales anteriores que no se repiten

La auditoría local de Swift del 2026-09-14 evaluó el GGUF upstream Q4_K_M,
no Genesis NVFP4: obtuvo 71,79 tok/s en decode corto con MTP3, respondió un
marcador a 55.032 tokens, pasó un smoke de tool-use y una prueba visual, y logró
**1/8 en BigCodeBench-Hard**. El resultado no basta para juzgar la nueva
cuantización/transformación, pero sí evita volver a descargar y repetir la misma
corrida sobre el mismo artefacto. Ver
[`docs/swift-qwen38-audit-20260914.md`](swift-qwen38-audit-20260914.md).

El control actual para coding es la familia Qwen3.8-27B: SOL tiene BCB 8/8,
HE20 20/20 y tool-use estable en el perfil principal; la matriz local también
contiene variantes con resultados dispares según quant y receta. La evidencia
agentiva de SOL usa LC-H1, así que el BCB directo que ejecutaremos a Genesis es
un filtro inicial, no una comparación suficiente para promoverlo. En Computer
Use hay pruebas previas con 48/48 decisiones y 29/29 casos de seguridad en
Qwen3.8; hay que comparar el mismo corpus y protocolo antes de cambiar prompts
o harness. Ingi Charla usa Qwen3.5-9B y una arquitectura independiente de
STT/TTS. Qwen3.8 ofrece visión, pero no agrega ASR ni TTS; el 27B tampoco tiene
evidencia de menor latencia conversacional que justifique reemplazar al 9B.

## Artefacto fijado

- Repositorio/revisión: `LuffyTheFox/Swift-Qwen3.8-27B-Genesis-GGUF@489bc45881179c25539b169734627b8c3c83eab1`.
- Archivo: `Swift-Qwen3.8-27B-Genesis-NVFP4-v4.gguf`.
- SHA-256 esperado y verificado: `bc032e9f2148b990125b67c00f5900460be581a9ec2954eb98ab4fd8ab68afdc`.
- Archivo de visión: `mmproj-Swift-Qwen3.8-27B-F16.gguf`.
- SHA-256: `daa1116c9422fa390cc8688495da0e91781f92841dfc3b31a378ff252571745a`.
- Ubicación local de los modelos: `/media/cristian/Disco local/Models/llamacpp/Swift-Qwen3.8-27B-Genesis-GGUF/` (fuera del repo).
- Hardware: 2× RTX 3090 de 24 GB. Había servidores Qwen3.5 residentes en las GPU durante la prueba.
- Runtime probado: llama.cpp `1 (67849b6)`, CUDA; sampling de coding conservador, KV K/V Q8, MTP draft máximo 4, mmproj en CPU.

## Pruebas de esta corrida

| Prueba | Resultado | Interpretación |
|---|---|---|
| Carga GGUF en CPU y suma `19 + 23` | Carga correcta; respondió `42`; decode 2,39 tok/s | Smoke de compatibilidad solamente; sin MTP ni rendimiento GPU. |
| Servidor con ctx 262.144, KV Q8, mmproj RAM y MTP4 | El servidor cargó y quedó healthy. Primer request cayó en `ggml_cuda_flash_attn_ext_mma_turbo_case` / `cudaFuncSetAttribute(MaxDynamicSharedMemorySize)`, código CUDA OOM. | Carga válida no equivale a inferencia funcional. GPU0/GPU1 tenían aprox. 2–3 GB libres por otros procesos. |
| Reintento ctx 262.144 con flash-attention apagado | Rechazado antes de servir: llama.cpp exige flash-attention para V cache Q8. | Configuración incompatible; no cuenta como resultado de calidad. |
| Decode speed, 5 repeticiones | 0 respuestas: la primera request provocó el crash anterior; las siguientes encontraron el puerto cerrado. | No hubo medición de tok/s. El runner ahora extrae timings del stream SSE para una repetición futura válida. |

El uso de memoria durante la carga de la candidata llegó a unos 14,5 GB en GPU0
y 15,7 GB en GPU1; las instancias residentes ocupaban otros 6,4 GB por GPU.
La sesión no detuvo ni reinició esas instancias. Por tanto, el OOM no demuestra
que 262K sea imposible con GPU despejada ni que el GGUF sea inválido; documenta
que la receta no pudo generar en las condiciones reales de esta notebook.

## Matriz preparada y archivos para continuar

En `assets/system_profiles.json` quedaron registrados estos candidatos, fijados
al mismo GGUF NVFP4 y al mmproj del artefacto evaluado:

- `sys-bench-qwen38-genesis-nvfp4-layer-mtp4-64k`: primera prueba; 2× RTX 3090,
  KV Q8, Flash Attention, MTP4 y visión.
- `sys-bench-qwen38-genesis-nvfp4-tensor-mtp4-64k`: A/B tensor con el mismo
  contexto y cuantización; correr sólo si el perfil layer genera correctamente.

Ambos son `manualOnly`, `extra`, `benchmark=true`, `best=false`, y requieren
48 GB de VRAM. Esto evita seleccionarlos como default o disparar su descarga
automática. El perfil tensor requiere además una build compatible y mantiene
`--cache-ram 1024` según la política de los perfiles tensor locales.

Los scripts de la corrida están en
[`artifacts/swift-genesis-evaluation-20260929/`](../artifacts/swift-genesis-evaluation-20260929/):

- `run_bcb.py`: BigCodeBench-Hard/8 ya fijado en
  `artifacts/bigcodebench-hard-ubuntu-8.json`; califica dentro de bubblewrap, sin
  red y sin montar `/home` ni `/media` en el sandbox.
- `run_tool_contract.py`: cinco pasadas del contrato `read_file(README.md)` →
  `write_file(tool_contract.txt, CONTRACT_OK)`, simuladas sin tocar archivos.
- `run_vision_tool.py`: fixture visual de Computer Use que propone el toggle
  semántico; nunca ejecuta la acción.
- `run_decode_speed.py`: 5 repeticiones, extrae timings del streaming API.
- La suite textual existente es
  `tools/benchmark_computer_use_prompt_order.py` sobre los 24 estados fáciles y
  difíciles, con tres órdenes de prompt y cinco pasadas.

Estas suites todavía no se ejecutaron en GPU porque el primer request crasheó
y los servidores Qwen3.5 de otra sesión siguen ocupando VRAM. Al reanudar, no
repetir la configuración exacta `flash-attn off + KV V Q8`: el server la rechaza.
Primero liberar VRAM o reducir explícitamente el número de capas GPU, y luego
probar 262K con `flash-attn on` en la build compatible; registrar por separado
cualquier offload CPU. Si la inferencia full-context vuelve a fallar, probar
una configuración menor para calidad y mantener aparte el fallo del claim de
262K.

## Decisión pendiente

**No promover Genesis a perfil, default de coding, harness ni Ingi Charla con
los datos actuales.** La continuación requerida es ejecutar BCB, contrato de
tools, suite textual y fixture visual con generación funcional. Si los filtros
directos no muestran regresiones, antes de tocar el harness se necesita una
comparación LC-H1 apareada contra el perfil SOL y Computer Use con su mismo
corpus/semillas. Sólo considerar perfil si la calidad no baja y el coste de
latencia/VRAM ofrece una ventaja concreta. No repetir el BCB histórico del Swift
Q4_K_M salvo que se cambie el dataset o se necesite un control apareado nuevo.
