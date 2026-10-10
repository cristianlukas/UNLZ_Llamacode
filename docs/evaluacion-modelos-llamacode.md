# Evaluación continua de modelos y harness de LlamaCode

Registro acumulativo. Actualizado: 2026-10-10. La evidencia se conserva en los
informes por campaña y en `artifacts/evaluacion-modelos-llamacode/<TASK-ID>/`.
Los resultados históricos no se reemplazan; una recomendación nueva debe
referir su evidencia y sus límites.

## Resumen y decisiones vigentes

| Uso | Recomendación vigente | Estado y evidencia |
|---|---|---|
| Coding y agentes | **SOL**, Qwen3.8-27B AutoRound INT4, vLLM TP2/P2P, MTP4/KV FP8. | Confirmado como perfil principal en la matriz local: BCB 8/8 y contexto 262K; la presente campaña no cambia el perfil. Ver [matriz por caso de uso](profile-use-case-stars-20260908.md). |
| Computer Usage | ASTRA como perfil general; Swift IQ3_XXS como alternativa de menor latencia en decisiones textuales cortas. | Provisional: 216 prompts con exactitud/validez/seguridad 100% en ambos, pero sin acciones GUI reales, capturas ni verificación E2E. La IQ3_XXS ISTA de esta campaña no fue probada en escritorio. Ver [auditoría de Computer Use](flashnext-computer-use-20261006.md). |
| Ingi-Charla | Qwen3.5-9B con el pipeline local de STT/TTS ya integrado. | Provisional para calidad acústica: los tests de código validan integración, no WER ni escucha humana. Flash-Next no aporta ASR/TTS y no se deriva calidad de voz desde texto. Ver [auditoría de voz local](ingicharla-local-voice-audit-20260918.md). |
| Visión | SOL con vLLM TP2/P2P para el uso multimodal validado; Qwen3.5-A3B/TERRA según el caso. | Confirmado para las recetas documentadas (SOL 4/4); **Flash-Next/Strata CPU vision no evaluado localmente** en esta campaña. Strata documenta `--vision cpu`; eso acredita una ruta de ejecución, no calidad visual del perfil. |
| Contexto largo | ASTRA Qwen3.8-Flash-Next UD-Q2_K_XL en su receta de 256K. | Provisional/exploratorio: matriz local registra 256K y needle/passkey 4/4 en posiciones 25/50/75/95. La IQ3_XXS tenía `max-context=131072`, pero la sonda de 115.015 tokens se cortó por transporte al procesar 65.536; no hay retrieval válido. El smoke separado de 262K para el post 4×P100 se bloqueó antes de cargar por swap 3,253 GiB >2 GiB. |
| Rendimiento | No hay ganador global nuevo. | IQ3_XXS tuvo TTFT menor en dos pasadas, pero decode se solapa con ASTRA y n=2. En ADV v1 empató 10/10 tras reparaciones, con menor primera pasada y más tiempo/llamadas. No justifica promoción. |

**Cambios promovidos por esta evaluación: ninguno.** Mantener los defaults y
perfiles productivos. La comparación ISTA IQ3_XXS vs ASTRA IQ3_S es una
comparación de perfiles completos con el mismo backend Strata, no una
comparación universal entre cuantizaciones.

## Inventario de candidatos y controles

| Perfil/modelo | Estado | Uso / evidencia principal |
|---|---|---|
| SOL — Qwen3.8-27B AutoRound INT4, vLLM TP2/P2P | Principal | Coding/agentes y visión en la matriz local; [perfil por uso](profile-use-case-stars-20260908.md). |
| ASTRA — Qwen3.8-Flash-Next UD-Q2_K_XL, 256K | Experimental validado para su receta | Contexto largo; no confundir con el control IQ3_S calibrado de la campaña actual. [Matriz](profile-use-case-stars-20260908.md). |
| ASTRA calibrado IQ3_S / Strata v0.1.41 | Control válido, una corrida por suite en esta campaña | Control para el candidato ISTA IQ3_XXS; [informe de esta evaluación](qwen38-flashnext-iq3xxs-strata-20261009.md). |
| ISTA-DASLab IQ3_XXS / Strata v0.1.41 | Evaluación provisional; no promovido | Coding/agentes inferior en BCB8 y TaskFlow, empate final en ADV después de reparaciones; sin evidencia GUI, audio ni visión. [Informe de esta evaluación](qwen38-flashnext-iq3xxs-strata-20261009.md). |
| Swift 1.5 IQ3_XXS | Alternativa provisional para decisiones cortas de Computer Use | Sólo comparación textual; no confundir con ISTA IQ3_XXS. [Informe de Computer Use](flashnext-computer-use-20261006.md). |
| Qwen3.5-9B local | Recomendado para Ingi-Charla | Conversación con STT/TTS integrados; evaluación acústica externa pendiente. [Auditoría de voz](ingicharla-local-voice-audit-20260918.md). |

La publicación investigada es el [post de r/Qwen_AI sobre IQ3_XXS en RTX 4060
Laptop de 8 GB](https://www.reddit.com/r/Qwen_AI/comments/1x097l9/strata_is_the_best_magic_qwen38_fn_iq3_xxs_on_a/).
El autor reporta 64 GB DDR5, Ryzen 7 7840HS, NVMe, Windows, visión en CPU y
contexto configurado a 131.072: ~180 tok/s de prefill y 27–32 tok/s de decode
con IQ3_XXS; ~430 y 29–35 con IQ2_XS. Es evidencia anecdótica sin prompts,
medición de longitud efectiva o protocolo reproducible. La documentación de
[Strata](https://github.com/Niko1221/Strata/blob/main/docs/AI_SETUP.md)
confirma las opciones de contexto y `--vision cpu`; su [tabla de modelos](https://github.com/Niko1221/Strata/blob/main/docs/MODELS.md)
lista IQ3_XXS en ~47 GB de RAM+VRAM y cifras de otras máquinas. El [model card
oficial de Qwen](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) declara 262.144
tokens nativos. Ninguna de esas fuentes valida por sí sola calidad o velocidad
en el perfil local.

La solicitud posterior agrega un [post distinto de r/LocalLLM sobre Flash-Next
Q4, KV q8, contexto 262K y 4× Tesla P100](https://www.reddit.com/r/LocalLLM/comments/1wx3g89/strata_takes_the_promise_of_moe_models_just_need/).
El autor afirma alrededor de 2× la velocidad de Qwen 27B y 5× la de un
Flash-Next con llama.cpp modificado, pero no aporta configuración efectiva,
prompts, recibos crudos ni comparación reproducible. La documentación primaria
de [Strata para GPUs antiguas](https://github.com/Niko1221/Strata/blob/main/docs/OLDER_GPUS.md)
describe CUDA experimental para P100 y un reporte comunitario separado de
2×P100, IQ3_S y 128K; no valida Q4/4×P100/262K. La
[guía multi-GPU](https://github.com/Niko1221/Strata/blob/main/docs/MULTI_GPU.md)
explica que cada GPU mantiene pesos densos, estado/KV y buffers propios, mientras
la RAM alberga el arena compartido de expertos y la CPU calcula los misses: no
es una suma fungible de VRAM y RAM. Nuestra campaña 2× RTX 3090 IQ3_XXS/ASTRA a
131K no replica ese post. El smoke local de 262K quedó bloqueado antes de cargar
el engine por la guarda de swap; el resultado del post queda **inconcluso
localmente**, no refutado.

Lectura por uso para ese reclamo: el post no presenta un benchmark reproducible
de coding/agentes; no prueba Computer Usage E2E ni reporta voz; para visión sólo
alude a capacidades del runtime, sin corpus ni métricas; configura 262K, pero no
aporta longitud efectiva o retrieval verificable; y las razones de velocidad
carecen de prompts, protocolo y recibos crudos. La documentación de Strata
confirma rutas técnicas para hardware antiguo/multi-GPU, no esas métricas ni la
calidad del modelo. Así, la publicación sirve como hipótesis de compatibilidad
y rendimiento para equipos antiguos, no como evidencia para cambiar perfiles o
harness de LlamaCode.

## Registro de tareas

| ID / fecha | Objetivo y candidatos | Estado | Resultado y límites | Artefactos |
|---|---|---|---|---|
| `Q-20261009-FLASHNEXT-IQ3XXS-AB` · 2026-10-09/10 | Evaluar la publicación inicial de IQ3_XXS/Strata y la solicitud añadida sobre Q4/4×P100/262K para coding/agentes, CU, voz, visión, contexto y velocidad; comparar ISTA IQ3_XXS con ASTRA IQ3_S. | Completa como screening; IQ3_XXS no promovido. Afirmación P100 inconclusa localmente. | HE0 prerequisito 1/1 ambos. HE20+BCB8: IQ3_XXS 24/28 y ASTRA 28/28 finales. ADV v1 complementaria: ambos 10/10 tras dos reparaciones; primera pasada 7/10 y 8/10. TaskFlow ULTRA: 11/13 vs 13/13. Suma descriptiva HE20+BCB8+ADV+TaskFlow: 45/51 vs 51/51; una corrida válida por perfil. Server Speed (n=2): decode 126,59 vs 122,09 tok/s (rangos solapados); TTFT 370,63 vs 451,00 ms. La sonda 115K se cortó por transporte a 65.536/115.015 tokens; sin resultado válido. El smoke 262K del post P100 se bloqueó antes de cargar por swap 3,253 GiB >2 GiB; no es fallo del modelo. Sin GUI E2E, acústica ni evaluación real de imágenes. | [Plan y recibos de esta tarea](../artifacts/evaluacion-modelos-llamacode/Q-20261009-FLASHNEXT-IQ3XXS-AB/); [informe](qwen38-flashnext-iq3xxs-strata-20261009.md); [post P100](https://www.reddit.com/r/LocalLLM/comments/1wx3g89/strata_takes_the_promise_of_moe_models_just_need/). |
| `flashnext-computer-use-20261006` · 2026-10-06 | ASTRA IQ3_S frente a Swift 1.5 IQ3_XXS para Computer Use. | Provisional; reemplaza sólo la decisión previa de latencia textual corta cuando exista prueba GUI E2E. | 216 prompts, ambos 100% exactitud/validez/seguridad; Swift 22,8–23,9% menos mediana de latencia. No hubo escritorio real, OCR/UIA ni recuperación E2E. | [Informe](flashnext-computer-use-20261006.md), [recibos](../artifacts/flashnext-computer-use-20261006/). |
| `ingicharla-local-voice-audit-20260918` · 2026-09-18 | Auditar arquitectura de voz y modelo conversacional local. | Recomendación provisional vigente. | Mantener Qwen3.5-9B y STT/TTS integrados; tests de integración no sustituyen corpus acústico/medición WER. | [Auditoría](ingicharla-local-voice-audit-20260918.md). |
| `profile-use-case-stars-20260914` · 2026-09-14 | Consolidar perfiles por caso de uso en Ubuntu. | Baseline vigente; modificar sólo con nueva evidencia. | SOL coding/agentes y visión; ASTRA 256K; Qwen3.5-A3B para contexto/visión/concurrencia; perfiles restantes según matriz. | [Matriz](profile-use-case-stars-20260908.md). |

### Detalle de calidad del candidato actual

Las etapas de coding terminaron normalmente y cuentan como resultados válidos de
calidad. No son tres repeticiones emparejadas, así que no permiten afirmar una
mejora estable.

| Suite | ISTA IQ3_XXS | ASTRA IQ3_S |
|---|---:|---:|
| HE0 | 1/1 → 1/1 | 1/1 → 1/1 |
| HE20 | 20/20 → 20/20 | 20/20 → 20/20 |
| BCB8 | 4/8 → 4/8; 3 reparaciones | 3/8 → 8/8; 2 reparaciones |
| ADV v1 · complementaria | 7/10 → 10/10; 2 reparaciones | 8/10 → 10/10; 2 reparaciones |
| TaskFlow ULTRA | 11/13 → 11/13; 3 reparaciones | 10/13 → 13/13; 2 reparaciones |

TaskFlow ULTRA son 10 criterios de existencia de archivos más tres comandos:
`py_compile`, `unittest` generado en el workspace y `--self-test`. En IQ3_XXS,
los diez archivos y `--self-test` pasaron, pero `py_compile` falló por un
`SyntaxError` en el test que produjo el agente; `unittest` también falló al
cargar ese archivo. El fallo fue de calidad, no de infraestructura. Los tests
son en parte escritos por el propio agente y no validan por sí solos el
comportamiento real; ASTRA pasó los 13 criterios después de dos reparaciones.
Los resúmenes guardados no conservan puntaje independiente tras cada reparación
intermedia, sólo primera pasada, final y cantidad de reparaciones.

ADV v1 usa 10 tareas con graders ocultos, mismo agente `agent-maximo`, thinking,
seed 4242, HarnessSpec, timeout 1800 s y máximo de tres reparaciones. ASTRA
completó 8/10 en la primera pasada y 10/10 tras dos reparaciones, en 773,404 s
y 63 tool calls, sin timeout/caída. IQ3_XXS completó 7/10 al principio y 10/10
tras dos reparaciones, en 977,519 s y 105 tool calls, también sin timeout ni
caída. El control ASTRA ya estaba en marcha al reanudar la sesión, antes de
localizar el plan correcto; se conserva la desviación de preregistro. El par es
un screening: empate final tras reparaciones, con menor primera pasada y mayor
tiempo/llamadas del candidato; no demuestra mejora estable.

## Registro de decisiones

| Fecha | Decisión | Uso | Evidencia y confianza | Límites / supersesión |
|---|---|---|---|---|
| 2026-10-10 | No promover ISTA IQ3_XXS/Strata a perfil productivo; mantener ASTRA como candidato provisional Flash-Next y SOL como perfil global vigente. | Coding/agentes y general. | Una corrida válida por perfil: HE20+BCB8 24/28 vs 28/28; ADV complementaria 10/10 ambos; TaskFlow 11/13 vs 13/13. Server Speed n=2 señala TTFT menor para IQ3_XXS, pero decode con rangos solapados. | Una sola pareja de calidad; faltan repeticiones para una mejora estable. La sonda 115K quedó inválida por transporte y el smoke 262K se bloqueó por guarda de swap; ninguno decide contexto ni refuta el post P100. No se toca SOL ni HarnessSpec. |
| 2026-10-06 | Swift IQ3_XXS puede usarse como alternativa rápida sólo para decisiones cortas textuales de CU. | Computer Usage. | Provisional; 216 solicitudes por perfil. | No prueba GUI E2E; no generalizar a escritorio, OCR o apps. No reemplaza perfiles de coding. |
| 2026-09-18 | Mantener Qwen3.5-9B y el pipeline de voz integrado para Ingi-Charla. | Voz. | Provisional; integración local validada. | Falta medir WER/CER, latencia end-to-end y escuchar muestras con el mismo corpus. |

## Próximas pruebas

- Si se retoma el contexto del post P100, repetir el smoke de 262K sólo cuando
  se cumplan las guardas preregistradas (`MemAvailable` ≥32 GiB y swap usado
  <2 GiB). El intento del 2026-10-10 se bloqueó antes de cargar el modelo; no
  modificar swap para forzar la prueba. Aun un éxito local con IQ3_XXS/2×3090
  sería sólo un smoke, no réplica de Q4/4×P100.
- Diagnosticar y, cuando el endpoint pueda completar el prefill, repetir el
  retrieval sintético preregistrado de 115K para IQ3_XXS y después ASTRA bajo
  `max-context=131072`. El primer intento de IQ3_XXS llegó a 65.536/115.015
  tokens antes de la desconexión, sin respuesta ni uso de tokens; por tanto no
  produce score. Es una sonda de retrieval, no una evaluación integral de
  razonamiento largo.
- Para declarar mejora estable de coding/agents: al menos tres corridas válidas
  por perfil, emparejadas por tareas y seed, incluyendo gates de calidad
  independientes. No repetir fingerprints idénticos salvo para medir variación.
- Para Computer Usage: prueba E2E en más de una app, estado final verificable,
  acciones/capturas/errores/recuperación, y variaciones de idioma, resolución,
  tema y distribución.
- Para Ingi-Charla/visión: mantener estado **no evaluado** para Flash-Next hasta
  usar audios/imágenes reales con corpus común, métricas definidas y registros de
  salida; no inferirlo de coding o velocidad de texto.

## Índice para no repetir

**Hashes de modelos:** IQ3_XXS es ISTA-DASLab GSQ-RCO, revisión
`1c04b8102ca5346f1faf4d9914503e378d713021`, shards SHA-256
`219ea929900dfa9ef091f3aa473fdba6874b65fcb36526d7d851ac9e95856d15` y
`316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`.
ASTRA calibrado IQ3_S: shard 1 SHA-256
`4c1eb2ceb4915e1192f4f386021897bde56a97f40a0bb78bb86465e0f7d2aca3`; shard 2
es idéntico al shard 2 de IQ3_XXS, SHA-256
`316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`.

| Huella | Perfil/config | Harness / suite | Seed | Estado |
|---|---|---|---:|---|
| IQ3_XXS `446cce937a86a65e99674718c58690435bfaf07a9f74558e469b4e7f33345c26` ↔ ASTRA `864c6ba74e684940f34b5519c5e53a36412e386a9b160fb22ed7c2640ee85fa4` | LC-H1, Strata v0.1.41, agent-maximo, thinking, R4096 | HarnessSpec `cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`; HE0 `7883f319c341fa82eb40fa4d1b665bbbf8c4b67b980fc93a28ad25d7eae64330`, HE20 `ed91a742cc8dca01bfe893933de5ed66fc4e4c2b529e53943a2bf1d939ffc3d7`, BCB8 `42771136b447b7b5619e04a1ea211f663222cd6752ca38d995083b5a4d207574` | 4242 | Una por perfil; ya ejecutadas. |
| IQ3_XXS `f85628050b115904a00a831669f50c197739ffd932546639eb4b70fc59e56bd9` ↔ ASTRA `41ca933b1ec0518ea74dfb8de13dbc788c5868f85479dc3a235e23669ced9cab` | TaskFlow ULTRA, R8192 | Suite hash `f04febb440208d5bf74c01e84d78f5127e57c164fabece2acbfb346215dc0c17`; HarnessSpec anterior | 4242 | Una por perfil; no repetir sin propósito de variabilidad. |
| IQ3_XXS `446cce937a86a65e99674718c58690435bfaf07a9f74558e469b4e7f33345c26` / ASTRA `864c6ba74e684940f34b5519c5e53a36412e386a9b160fb22ed7c2640ee85fa4` | ADV v1, R4096 | Suite hash `2f0f30c863606fd443a161ac6946658129b31d874229a61ffd719f75df36ee87`; HarnessSpec anterior | 4242 | Una corrida por perfil; ASTRA heredada con desviación; par cerrado, sin mejora estable. |
| IQ3_XXS `9f943104b2c4be86df3a9754e3dfded8bddefebb182e58e46a85276c75f0e6d8` + `446cce...` / ASTRA `9d9a4883ca04ae7045fad9aafaba53aedae6d4b54d2fde128ae5d18fbd239afe` + `864c6...` | Server Speed v1, dos pasadas por perfil | corpus SHA-256 `4bad8a5d24ce11096eb9634f7d03f24b83734c3f454031efb28d5fa259c996e9`; versión v1 | 424242 | Dos pasadas por perfil; cada una tuvo 32/32 muestras válidas. Los fingerprints están separados por pasada. |
| IQ3_XXS ↔ ASTRA IQ3_S | Context Retrieval v1, `max-context=131072` | Prompt SHA-256 `ea4cd4a48080b0191273c4dfe4df54d69535a131d1e0117a31a3c75377d8ec84`; expected SHA-256 `89cd8df5fcf636c53436db4f4fdc9e8e2166a98e1c9c5d284428da4d23362d25`; 10 preguntas/posiciones; no HarnessSpec | 4242 | IQ3_XXS intentado una vez, inválido por transporte a 65.536/115.015; sin score. Retomar tras diagnosticar endpoint; ASTRA sigue pendiente. |

| IQ3_XXS / Strata | Context smoke 262K para el post P100 | Config SHA-256 `654e9345320843bee40321e79b8430b535184ae1165026909fc2090ed7a3e7dc`; prompt no generado/enviado; no HarnessSpec | 4242 | Bloqueado antes de cargar por swap usado 3,253 GiB >2 GiB; no es fallo de modelo. Reintentar sólo al cumplir la guarda. |

Configuración de servidor comparada: Strata v0.1.41, commit
`fb58e0dbc8399662c0e47c76578c6e878b14f6cf`, build local CUDA 12.8.93 / SM86,
dos RTX 3090 de 24 GiB, RAM física 123,6 GiB; `MTP4`, expert cache/prefill
automáticos, spec-min-p 0,70, PCIe fraction 0,00, KV int8/resident 32768,
contexto máximo 131072, una solicitud concurrente. El sweep de velocidad llegó
a 38.804 tokens, no a 131K.
