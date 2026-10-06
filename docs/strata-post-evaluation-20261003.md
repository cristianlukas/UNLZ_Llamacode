# Evaluación del post de Strata: configuración y claims

Evaluación en Ubuntu del 2026-10-03 para separar afirmaciones trasladables a
LlamaCode de mediciones dependientes de la GPU del autor. Los scripts y recibos
de las pruebas nuevas están en
[`artifacts/strata-post-evaluation-20261003`](../artifacts/strata-post-evaluation-20261003/).

## Máquina y perfil de referencia

Ryzen 9 9950X3D, 124 GiB RAM, 2× RTX 3090 de 24 GiB, driver 610.57.04, CUDA
12.8. ASTRA usa Strata 0.1.35 con Qwen3.8-Flash-Next IQ3_S, contexto 131072,
KV int8 con 32768 tokens residentes, MTP4, expert-cache auto, prefill auto,
layer-split auto, visión activa y reserva de 700 MiB. Este es el perfil base
comparado en LC-H1; no se modificó su configuración de producción.

## Afirmaciones del post y evidencia local

| Afirmación o propuesta | Comprobación local | Decisión |
|---|---|---|
| Strata acelera mucho prefill/decode en una RTX 5090. | No es extrapolable a dos RTX 3090; los datos del post usan otra GPU, límite de potencia, RAM, contexto y carga. Nuestro microbenchmark mide cambios de flags sobre ASTRA ya instalado. | No copiar los tok/s publicados como expectativa local. |
| El setup auto-calibra PCIe/MTP/workers. | El setup 0.1.35 sí ofrece `--calibrate`; corrimos su calibrador sin editar el perfil. Confirmación intercalada: defaults (`pcie-frac .25`, `spec-min-p .5`) mediana 91.87 tok/s; candidato `.00/.70` 99.47 tok/s (+8.3%). Workers 15/10/8 no superaron umbral de 3%. | La mejora sólo es de microbenchmark; no promovida sin mejora end-to-end. |
| Guardar la tabla PLE de 320 M filas en RAM (`--ple-io ram`). | Con `.00/.70`: `direct` mediana 97.264 tok/s, `ram` 96.889 tok/s (−0.4%). Cargar la tabla RAM tardó 68.6 s y `mlock` falló por el límite del host. | Mantener `direct`; no añadir una opción al perfil. Recibo: `ple_io_measurements.json`. |
| `--max-context 262144` se cuelga y 262136 funciona. | En el perfil IQ3_S, ambas configuraciones respondieron correctamente al mismo prompt de 261733 tokens de entrada, recuperaron `STRATA_LIMIT_NEEDLE_20261003` y salieron con código 0. Hubo un arranque fallido en 262136 mientras otro servidor ocupaba VRAM; el reintento serial completó. | El supuesto cuelgue no se reprodujo. No subir el default de 131072: el coste de KV/memoria y pérdida de caché no se justifican para el uso normal. Recibos en `context_limit_results.json` y logs asociados. |
| Invertir prioridad 3090/5090 y ajustar `--vram-reserve-mib 1600`. | Esta máquina tiene dos 3090 idénticas; ASTRA IQ3_S ya reserva 700 MiB para visión y detecta el encoder. El candidato Unsloth Q4 no soporta visión y sólo usa una GPU. | No hay comparación de topología aplicable. No cambiar la reserva del perfil actual. |
| Subir concurrencia para tener varios agentes a la vez. | Los ensayos LC-H1 comparan un slot secuencial. No existe evidencia local de throughput multi-sesión de Strata; la cola FIFO de ASTRA no equivale a paralelismo. | Mantener el slot actual; cualquier cambio requiere un benchmark de concurrencia separado que mida latencia, calidad y VRAM bajo carga. |
| Usar Qwen3.8-Flash-Next como agente en vez de SOL. | A/B LC-H1 con `agent-maximo`, seed 4242, temperature 0.1, thinking, reasoning medium, mismo HarnessSpec y suites HE20/BCB8/Adversarial. SOL: 37/38, 1534.2 s; ASTRA IQ3_S: 38/38, 1840.8 s; Swift 1.5: 38/38, 2195.8 s. Una corrida por suite/modelo. | ASTRA empató el mejor resultado final y aventajó a SOL por una tarea, con 20% más de tiempo total. No cambiar suite, harness, sampling ni concurrencia por una sola pasada. Detalle en [`strata-swift-vs-sol-lch1-20261003.md`](strata-swift-vs-sol-lch1-20261003.md). |
| Q4 UD de Unsloth puede mejorar la calidad. | No se había probado en el entorno anterior. El setup upstream v0.1.35 lo marca experimental, sólo NVIDIA, una GPU, sin visión; requiere cuatro shards (111.3 GB), pack compatible y MTP. Se inició una instalación de prueba aislada con hashes de revisión fijados y contexto objetivo 131072 para mantener la comparación con ASTRA. | Pendiente hasta validar pesos, arranque y LC-H1. No añadir a perfiles instalados ni reemplazar ASTRA antes del resultado end-to-end. Ver estado/recibos Q4 en este directorio de artefactos. |
| Las mejoras ayudan a Ingi-Charla o Computer Use. | Strata no incluye ASR/TTS; Ingi-Charla usa el pipeline de voz existente. Computer Use no se ejecutó en esta evaluación nueva. IQ3_S obtuvo previamente 72/72 decisiones de Computer Use y 63/63 decisiones seguras sobre corpus sintético, sin automatización GUI real. | Sin cambio de Ingi-Charla. El modelo Unsloth Q4 no ofrece visión, por tanto no puede sustituir al perfil de Computer Use. Auditorías previas: [`ingicharla-local-voice-audit-20260918.md`](ingicharla-local-voice-audit-20260918.md) y [`strata-v0135-vs-sol-astra-audit-20261002.md`](strata-v0135-vs-sol-astra-audit-20261002.md). |

Las capacidades y requisitos de UD-Q4 se contrastaron con el documento upstream
[Unsloth Q4 experimental de Strata](https://github.com/Niko1221/Strata/blob/main/docs/UNSLOTH_Q4.md)
y el [setup de Strata](https://github.com/Niko1221/Strata/blob/main/setup.py),
que fijan la revisión del repositorio y los hashes de cada shard.

## Calibración y A/B end-to-end

La calibración se ejecutó sobre una copia lógica de `strata-iq3_s.json`; no
alteró el JSON de producción. El barrido inicial de `pcie-frac` dio 97.4 tok/s
en `.00`, 92.4 en `.20`, 94.2 en `.25`, 90.0 en `.35`, 85.2 en `.55` y 79.7
en `.75`. El barrido de `spec-min-p` dio 93.2 (`.30`), 94.3 (`.50`) y 97.1
(`.70`). Las confirmaciones intercaladas redujeron el riesgo de variación
temporal: default 91.87 vs candidato 99.47 tok/s mediana. El ensayo de workers
marcó mediana 96.95 (15), 97.56 (10) y 97.89 (8), diferencia insuficiente.

El candidato `.00/.70` se lanzó mediante el gestor ASTRA real de LlamaCode en
un puerto aislado y pasó HE0 (1/1, tras una reparación). La comparación siguió
con la misma suite y harness del perfil base:

| Suite | ASTRA base final / inicial | Ajustado final / inicial | Segundos base / ajustado |
|---|---:|---:|---:|
| HE20 | 20/20, 18/20 | 20/20, 19/20 | 709.5 / 715.7 |
| BCB8 | 8/8, 2/8 | 8/8, 3/8 | 570.5 / 651.0 |
| Adversarial | 10/10, 7/10 | 10/10, 7/10 | 560.8 / 490.4 |
| **Total** | **38/38, 27/38** | **38/38, 29/38** | **1840.8 / 1857.0** |

El ajuste acabó 0.9% más lento en total y mantuvo 38/38 después de reparación;
por eso no se promovió. Los resultados por suite tienen distinta dirección, una
pasada por perfil y cuatro llamadas más del candidato ajustado (121 vs 117).
No justifican cambiar el ASTRA de producción.

## Regla para no repetir estas pruebas

- No repetir la matriz PLE `direct`/`ram` con estos flags, tabla PLE y hardware:
  ya fue medida en tres rondas por modo y no mostró ganancia.
- No repetir el needle test de 262136/262144 con el mismo Strata 0.1.35, IQ3_S,
  prompt de 261733 tokens y hardware: ambas longitudes terminaron limpias.
- No volver a correr la calibración `.00/.70` como si fuera una comparación de
  calidad: el A/B LC-H1 ya mostró el resultado integral (38/38, +0.9% de tiempo).
- Repetir un benchmark sólo si cambia el motor/versión, cuantización, contexto,
  harness/suite, límite de concurrencia o el comportamiento observado; mantener
  entradas, semilla, temperatura, thinking, reparaciones y HarnessSpec alineados.


## Actualización con repetición del 5 oct. de 2026

El A/B calibrado no se promovió originalmente por una única corrida y +0,9% de tiempo. La repetición adicional con los mismos pesos, harness y suites finalizó 38/38; obtuvo 31/38 en primera pasada y 1880,8 s, frente a 29/38 y 2331,5 s para la repetición del perfil base. Swift IQ3_XXS también obtuvo 38/38 y 29/38 en primera pasada (2023,5 s). Con dos rondas por perfil, recomiendo provisionalmente ASTRA IQ3_S calibrado como perfil Flash-Next principal, manteniendo Swift como alternativa compacta y el base como rollback de configuración. La dispersión de tiempos impide tratar el promedio como una garantía. No se modificó producción ni el harness. Ver [comparación de repetición y recibos](strata-swift-vs-sol-lch1-20261003.md#repetición-flash-next-lc-h1--5-oct-2026) y [`results.json`](../artifacts/flashnext-repeat-20261005/results.json).

### Aislamiento de los flags ASTRA

La ablación posterior de `pcie-frac` y `spec-min-p` cambió cada opción por separado, una ronda por variante. No demostró que un flag aislado mejore calidad: `.00/.50` fue 27/38 y más rápido en una muestra; `.25/.70` quedó con BCB bloqueado antes de herramientas y no superó HE20/ADV. Se mantiene ASTRA combinado `.00/.70` como recomendación provisional por las dos rondas completas que dieron 31/38 y 29/38 en primera pasada frente a 29/38 y 27/38 de base; el ensayo no atribuye causalidad ni cambia producción o harness. La guardia BCB se documentó para estudiar en una prueba separada. Ver [`informe de ablación`](../artifacts/flashnext-ablation-20261005/report.md).
