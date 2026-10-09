# Evaluación Qwen3.8-27B Unsloth UD-IQ4_XS · 196K · 2026-10-09

## Veredicto

El candidato cargó en una RTX 3090 con contexto de 196.608, MTP4 y KV `q8_0`, y recuperó correctamente tres datos en un prompt efectivo de 194.338 tokens. En el benchmark de agente TaskFlow ULTRA obtuvo 12/13 criterios después de tres reparaciones, pero falló el self-test (`SELF_TEST_FAIL: 2020-02-01`). No alcanza para reemplazar SOL ni ASTRA: el mejor resultado repetido de ASTRA para esta misma suite es 13/13. No se cambió ningún perfil productivo ni HarnessSpec.

La prueba de SOL iniciada como control pareado quedó inválida: el agente recibió `Connection closed` y el worker vLLM cayó con `CUDA error: device-side assert triggered` durante una solicitud MTP. No se cuenta como score de calidad.

## Evidencia del post

El archivo que se descargó es el GGUF `Qwen3.8-27B-UD-IQ4_XS.gguf`, de 14.252.845.984 bytes y SHA-256 `40fac4050e940397dbf13087afd50f4734a11805bf9d65ef8ddd7483470e6199`. [La ficha de Unsloth](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/blob/287999af67436bfaa4f4ee09dc34af328a495ba6/Qwen3.8-27B-UD-IQ4_XS.gguf) confirma tamaño y hash.

El post describe un resultado de una tarea Rust y un seed. La nota del autor describe esos 40/43 tests ocultos como un datapoint, no una clasificación; la publicación de contexto mide memoria/recuperación y tampoco clasifica calidad. DeepSWE define 113 tareas con entornos aislados y verificadores programáticos, una base mucho más amplia que una sola corrida ([repositorio oficial](https://github.com/datacurve-ai/deep-swe), [nota de contexto del autor](https://ai.ttindall.com/blog/27b-24gb-context-ceiling/), [nota de evaluación SWE del autor](https://ai.ttindall.com/blog/deepswe-local-confidence/)).

No fue una réplica exacta de DeepSWE: aquí se usó la suite interna TaskFlow ULTRA, `LlamaAgent` y el template del GGUF. El template `qwen3.8-midsystem.jinja` mencionado por el post no estaba disponible. Por eso los resultados internos no validan ni desmienten el 40/43 publicado.

## Configuración y resultado del candidato

- Runtime: llama.cpp `b11115`, commit `d5f66492e661b63e6c74822c2b72f5146053994e`, CUDA 12.0 / SM86.
- Una RTX 3090 de 24 GB; alias local `qwen3.8-27b-iq4xs`.
- Servidor: `--ctx-size 196608`, `--spec-type draft-mtp --spec-draft-n-max 4`, `-ctk q8_0 -ctv q8_0`, Flash Attention, razonamiento activo y budget 4096; template integrado seleccionado con `--jinja`.
- LlamaCode: `agent-maximo`, seed 4242, temperatura efectiva 0,1 y thinking activo. Estos son los valores efectivos del benchmark; el `--temp 1.0` del servidor era su valor por defecto y fue sobrescrito por el agente.
- La corrida usó la suite `Qwen3.8 ASTRA IQ3_S calibrado vs SOL · TaskFlow ULTRA E2E`, 13 criterios (10 archivos y 3 comandos), y el mismo HarnessSpec que los resultados históricos: `sha256:cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`.

| Medición | Resultado |
|---|---:|
| Primer intento | 0/13 |
| Final tras 3 reparaciones | 12/13; `passedAfterRepair=false` |
| Criterio fallido | `python -m taskflow_ultra.main --self-test` → `SELF_TEST_FAIL: 2020-02-01` |
| `py_compile` | aprobado |
| `unittest` | 33/33 aprobados |
| Tiempo total | 315,419 s |
| TPS medios reportados por LlamaCode | 72,47 |

Como contexto, SOL histórico obtuvo 11/13 en 589,364 s y ASTRA cerró 13/13 en dos corridas de 287,296 s y 333,456 s. El candidato superó por un criterio la corrida histórica de SOL, pero no el mejor perfil existente; con una corrida, cero checks en el primer intento y un self-test fallido, no hay una mejora estable para promover. El detalle de SOL y los reintentos ASTRA se conserva en [la evaluación TaskFlow previa](qwen38-astra-sol-taskflow-ultra-20261006.md).

## Prueba de contexto largo

Se construyó un prompt sintético repetitivo con tres códigos sembrados al inicio, a mitad y cerca del final. El tokenizador contó 194.287 tokens de contenido; llama.cpp informó 194.338 tokens de prompt tras el template y generó 119 tokens. La respuesta fue exactamente `OLIVE-7392 COBALT-1846 AMBER-5503`; no hubo truncamiento ni error de contexto.

El prefill tomó 354,816 s (547,71 tokens/s). La salida decodificó a 41,26 tokens/s; MTP aceptó 92 de 116 propuestas (79,31%, media 4,17 tokens aceptados por propuesta). Esto acredita que esa configuración procesó una solicitud cerca del límite; el filler repetitivo no equivale a una prueba general de recuperación en repositorios ni al benchmark NIAH del post.

## Control SOL inválido

El control usó el launch temporal del perfil SOL, el mismo agente, suite y HarnessSpec. Un smoke directo de 32 tokens a `/v1/chat/completions` devolvió HTTP 200. En el benchmark de agente hubo dos intentos: `[error: Unknown error]` y luego `[error: Connection closed]`, ambos con 0 archivos y sin evaluación útil. El log del segundo muestra `prompt_token_ids_len=15740`, MTP `num_spec_tokens=4`, `max_tokens=32768`, `temperature=0.1`, seguido de `EngineDeadError` y un assert CUDA dentro de `synchronize_input_prep()`. Se detuvo el contenedor; las dos GPU quedaron libres.

Este fallo identifica una inestabilidad del control vLLM/MTP en esta ejecución. No se cambió el perfil por un solo fallo ni se atribuye al GGUF candidato.

## Transferencia a otros usos y decisión de harness

La evaluación cubrió generación de código de texto. No usó imágenes, `mmproj`, audio, ASR ni TTS, así que no da evidencia para Computer Usage ni Ingi-Charla.

La práctica útil del post —separar pass binario, fracción de tests, tests existentes y tests nuevos— ya está cubierta por los criterios de archivo/comando y los campos `firstAttemptScore`, `qualityScore`, `passedAfterRepair` y `failureKind` de LlamaCode. No se cambió HarnessSpec.

## Artefactos y no repetición

El manifiesto y recibos de esta campaña están en [`artifacts/qwen38-unsloth-iq4xs-196k-eval-20261009/`](../artifacts/qwen38-unsloth-iq4xs-196k-eval-20261009/). Los workspaces completos de LlamaCode quedan bajo `/home/cristian/.qttest/share/LlamaCode/LlamaCode/benchmark-runs/` en este host. El modelo y el build de llama.cpp quedan en las rutas de `runtime-config.json` para que el candidato se pueda inspeccionar sin volver a descargarlos.

No repetir la suite TaskFlow ULTRA con este launch ID y HarnessSpec como si fuera evidencia nueva. Para reevaluar calidad, usar un subconjunto DeepSWE fijado o una tarea distinta, registrar el verifier y mantener el mismo perfil/harness en cada brazo; antes, resolver por separado el crash vLLM/MTP de SOL.
