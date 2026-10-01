# Auditoría de QwFN-hybrid para LlamaCode — 2026-10-01

## Decisión

**No agregar un perfil ni cambiar el harness, Computer Use o Ingi Charla con la
evidencia actual.** QwFN-hybrid es un motor especializado para
Qwen3.8-Flash-Next y un quant IQ3_XXS, no una receta portable de `llama.cpp`.
Sus resultados publicados justifican conservarlo como candidato de benchmark
para equipos NVIDIA de 16 GB, pero no prueban que supere los perfiles vigentes
de LlamaCode en esta notebook ni en calidad agentiva.

La idea que sí incorporo al procedimiento de benchmarking es medir fidelidad
de distribución y ruido natural al comparar dos runtimes con el mismo modelo,
como etapa complementaria a HE0 → HE20 → BCB. Esa medición no sustituye los
benchmarks de tarea.

## Qué reporta el proyecto

El README de [QwFN-hybrid](https://github.com/thomaskleiven/QwFN-hybrid)
describe un fork de QwFNfer/ggml para Qwen3.8-Flash-Next IQ3_XXS. Su máquina
de referencia tiene RTX 5060 Ti 16 GB, Core Ultra 7 265F, 32 GB DDR5, NVMe
PCIe 4 y KV Q8. Coloca expertos calientes en VRAM, otros en RAM y los restantes
en SSD; usa MTP, prelectura y snapshots para reusar prefijos. Esto requiere el
fork y sus cambios al motor: los flags publicados no convierten la receta en
un perfil equivalente de `llama-server` upstream.

| Medición publicada | llama.cpp de control | QwFN-hybrid | Lectura |
|---|---:|---:|---|
| Prefill, 512 tokens | 104 tok/s | 98 tok/s | QwFN queda 6% por debajo |
| Prefill, 16K | 165 tok/s | 620 tok/s | QwFN reporta 3,76× |
| Decode, generación libre 128 | 9,9 tok/s | 15,9 tok/s; 19,0 con MTP | Hasta 1,92× en prompt corto |
| Decode a profundidad 16K | 10,0 tok/s | 12,7 tok/s; el texto probado con MTP dio 12,4 | +27%; MTP no ayudó en ese caso |
| Replays de código/agente/razonamiento | No hay tabla base publicada por workload en el README | 26,4 / 21,3 / 21,8 tok/s | Son medias de tres replays teacher-forced, no scores de tareas |
| Long context, 21K | — | 17,7 tok/s | Sin A/B de calidad publicado para ese caso |

El mismo README indica que la versión release supera **4 de 5** escenarios de
paridad: el escenario de razonamiento falla el límite de NLL shift en la corrida
principal (0,0031 frente al máximo 0,0021). El autor atribuye la diferencia a
redondeo por ejecutar expertos en CPU/GPU; una repetición de 3.000 tokens cae
dentro del límite, pero conserva una pequeña inclinación negativa. No es una
prueba de equivalencia bit a bit.

También informa un único tipo de tarea de OpenCode que resolvió en todas sus
corridas. Eso no equivale a HE20, BCB8, LC-H1, una suite de schemas de tools ni
una comparación del harness completo. El README advierte que respuestas de
tools de 1K tokens pueden tardar unos 7 segundos en servidor caliente y que un
primer prompt de 4K puede tardar unos 11 segundos mientras se leen expertos del
SSD: el throughput de decode no representa la latencia completa de un ciclo
agentivo.

## Transferencia a LlamaCode

| Área | Qué aporta | Qué falta para cambiar LlamaCode |
|---|---|---|
| Perfil/modelo | Mejor prefill reportado a 16K y decode reportado hasta 1,92× frente a `llama.cpp` en una RTX 5060 Ti | Sólo se midió IQ3_XXS en esa máquina. Nuestro equipo tiene 2× RTX 3090 y 123 GiB RAM; no hay A/B local equivalente ni inferencias locales. El head MTP terminó de descargarse, pero los dos shards siguen incompletos. |
| Harness de coding | Snapshots rápidos de prefijo y una tarea de OpenCode repetida | No hay LC-H1, HE20/BCB8, tasa de tool calls ni latencia end-to-end comparable. No cambiar perfil/harness por el smoke anecdótico. |
| Computer Use | El fork sí tiene entrada de imágenes vía `--mmproj` y el servidor procesa `image_url`; no incluye ejecución de escritorio ni evaluación de Computer Use/seguridad | La visión permite probar el corpus visual de LlamaCode, pero no demuestra una mejora hasta medir exactitud, seguridad y latencia con esas mismas tareas. |
| Ingi Charla | Un decode más rápido podría bajar una parte del tiempo de respuesta | No mide STT, TTS, latencia fin de habla→primer audio, conversación por turnos ni español. No hay reemplazo de la arquitectura de voz actual. |
| Backend | Expone API compatible con OpenAI/Anthropic | Usa binario y argumentos propios, tiene soporte sólo para Linux/NVIDIA y una arquitectura de modelo; todavía no está validado como runtime administrado por los perfiles de LlamaCode. |

El repositorio del fork muestra 0 estrellas y 5 commits al momento de esta
revisión; esto describe su madurez pública, no la corrección de las mediciones.
Su README deja `MODEL_URL` como marcador pendiente, pero el quant exacto sí está
publicado por [ISTA-DASLab](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF)
(75,8 GB en dos shards); el head MTP compartido Q8 está en
[Unsloth](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF/tree/main/MTP).
El 2026-10-01 inicié esas descargas para intentar la medición local. Son
anónimas. El head MTP Q8 terminó (2,5 GiB); la descarga IQ3_XXS quedó
interrumpida: los archivos parciales ocupan 33 GiB y 21 GiB en disco según
`du`, y conservan sus mapas `.aria2`; aria2 seguía marcando ambos como
incompletos. No se intentó cargarlos.
El NVMe del directorio NTFS reportó esperas largas de escritura
(`ntfs_file_write_iter`, `balance_dirty_pages` y `folio_wait_bit_common`); los
procesos de descarga quedaron esperando en el kernel pese a señales de
terminación. Había 146 GiB libres, así que el bloqueo observado fue de I/O, no
de capacidad. Reanudar desde esos archivos y mapas cuando el volumen vuelva a
aceptar escrituras; no volver a descargar desde cero.

El código del motor compiló localmente en
`/home/cristian/.cache/qwfn-hybrid-eval-20261001` contra
`unslothai/llama.cpp` `ca1426903`, con el fork QwFN-hybrid en
`6b26989f8a2bdefd6c541ba0d0586c80b9e3b011`. Su `scripts/check_rules.sh`
terminó en `PASS` con warnings-as-errors. No se pudo ejecutar inferencia, medir
paridad ni throughput sin ambos shards completos; el build no justifica
promover un modelo o perfil.

## Evidencia local revisada; no repetir

Se revisaron las corridas ya documentadas, sin duplicarlas:

- [Strata Qwen3.8-Flash-Next Q2_0, 2026-09-29](strata-qwen38-evaluation-20260930.md): 1/8 en BCB-Hard repetido con sampling conservador; needle 3/3 en 8K/32K/110K; smoke de un round-trip de tool. No corrió Computer Use ni voz. No repetir esa misma matriz Q2_0.
- [Flash-Next frente a SOL, 2026-09-19](flash-next-vs-sol-iterative-audit-20260919.md): IQ1_S, IQ4_XS y EXL3 no superaron la calidad agentiva validada de SOL; SOL conserva BCB 8/8, HE20 20/20 y tool-use estable.
- [Qwen3.8 GSQ-RCO + DFlash2, 2026-09-18](qwen38-gsq-rco-dflash2-q2-audit-20260918.md): DFlash2 mejoró decode del target local, pero no completó LC-H1; queda experimental.
- [Ingi Charla local, 2026-09-18](ingicharla-local-voice-audit-20260918.md): la ruta actual ya separa STT/LLM/TTS y mide latencia; el candidato QwFN no se probó con audio.
- [Computer Use sandwich](computer-use-sandwich.md): sus suites separan exactitud, validez, seguridad, transporte y latencia; QwFN no se ejecutó en esos corpus.

La carpeta local `models/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` sólo contiene
un README; no contiene los pesos Coder IQ1_M que se estaban esperando para la
campaña de Strata. Los shards IQ3_XXS y el head MTP de QwFN-hybrid se están
descargando a una carpeta separada bajo `models/QwFN-hybrid-IQ3-XXS-20261001`.
En la inspección del 2026-10-01, las GPU estaban libres
(RTX 3090: ~1.0 GiB y ~0.1 GiB usados), había 123 GiB de RAM y 204 GiB libres
en el volumen de modelos. No se inició una descarga: el IQ1_M de Strata y el
IQ3_XXS de QwFN-hybrid son artefactos y motores distintos, así que descargar
el primero no validaría el reporte de QwFN.

## Próxima validación; evitar duplicados

No repetir Strata Q2_0 ni ejecutar la matriz anterior de Flash-Next con sus
antiguos quants. La prueba nueva es específica de QwFN-hybrid y usa IQ3_XXS, el
head MTP Q8 y su commit `6b26989f8a2bdefd6c541ba0d0586c80b9e3b011`; no se debe
confundir con el modelo Coder IQ1_M de Strata ni con los ensayos previos de
ASTRA. La descarga de IQ3_XXS y MTP se inició el 2026-10-01; si no termina en
esta sesión, se debe reanudar desde la carpeta registrada arriba en lugar de
descargar una copia nueva.

Primero comparar el build con su `llama.cpp` base en los mismos prompts
tokenizados y registrar NLL shift, top-k KL, top-1, throughput, null-run spread
y los casos que no pasan los límites. Después, y sólo si carga estable y supera
la puerta de paridad, conectar el endpoint a una campaña nueva de LlamaCode:

1. HE0 → HE20 → BCB8 bajo el mismo harness, grader y sampling del perfil de
   referencia; guardar tool calls y latencia end-to-end.
2. Si supera coding, correr los corpora existentes de Computer Use y su gate
   de seguridad. El fork debe aceptar imágenes antes de considerarlo allí.
3. Para Ingi Charla, hacer una campaña separada de voz-a-voz con el mismo STT,
   TTS y corpus en español, midiendo WER/CER, p50/p90 de latencia y memoria.

Una comparación que sólo supera throughput sigue siendo candidata experimental;
la promoción requiere calidad funcional y una integración estable con LlamaCode.
