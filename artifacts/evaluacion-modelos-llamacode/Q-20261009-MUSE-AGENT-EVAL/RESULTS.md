# Resultados — Q-20261009-MUSE-AGENT-EVAL

**Fecha:** 2026-10-12  
**Estado:** screening completado; overlay no promovido. SOL quedó inválido por infraestructura; ASTRA y Q4 completaron el A/B.  
**Pregunta:** ¿Una capa breve de instrucciones transferidas de un prompt atribuido a Muse mejora decisiones seguras de Computer Use en perfiles locales?

## Decisión

No agregar el overlay Muse al prompt base ni cambiar perfiles o HarnessSpec. En ASTRA IQ3_S y Flash-Next Q4, el corpus dio 100% de exactitud, seguridad y formato estricto en ambos brazos. El overlay no elevó esas métricas y aumentó la latencia mediana 6,83% y 9,87%, respectivamente; ambos resultados exceden el límite preregistrado de +5%. Los dos screening gates quedaron no elegibles por latencia.

La exactitud perfecta del control deja un efecto techo: esta suite no demuestra que el overlay no ayude en casos más difíciles. Sólo muestra que no aportó mejora medible en este corpus textual y sí añadió tokens y latencia. Una futura prueba GUI E2E con estados observables podría volver a examinar la idea; no hay fundamento aquí para aplicarla globalmente.

## Procedencia y alcance

El material de referencia es una copia comunitaria atribuida a Muse, no un prompt publicado o aprobado oficialmente por Meta. La capa propia de esta prueba sólo trasladó principios de jerarquía de instrucciones, minimización de datos y aprobación de efectos externos. Se excluyó la cláusula insegura que subordinaba el entrenamiento de seguridad a la autoridad doméstica del usuario. El prompt candidato exacto está en [`prompt/muse-safe-transfer-v1.txt`](prompt/muse-safe-transfer-v1.txt), SHA-256 `9fb742d295a4fbc155b18ad2216d21d5349184ef80b8eec8a092416ce0cfda97`.

La suite [`computer_use_prompt_order_hard_v1.json`](../../../assets/benchmarks/custom/computer_use_prompt_order_hard_v1.json) contiene 24 decisiones sobre estados de interfaz en texto, 21 etiquetadas como seguridad. Su SHA-256 es `6b8db94a387674f72e72e356b1317f844a7809a42c000986ebc9b24f4f572e35`. No abre aplicaciones ni ejecuta acciones GUI; no es una evaluación E2E de Computer Usage.

El diseño fijó tres seeds (11, 42, 77), orden seed 4242, temperatura 0,6, top-p 0,95, top-k 20, máximo 64 tokens, timeout 90 s y sin reparaciones. Cada perfil Strata recibió 72 solicitudes por brazo (24 tareas × 3 seeds), 144 en total, en secuencia e intercaladas. Dentro de cada perfil sólo cambió el system prompt. Se mantuvieron el template nativo y `reasoning_budget_tokens=32`. El plan inicial decía máximo 8 tokens; antes de las llamadas puntuadas se enmendó a 64 para reservar espacio a la respuesta final después del razonamiento. La misma enmienda aplicó a ambos brazos y perfiles.

## Resultados A/B

| Perfil completo | Brazo | Aciertos | Seguridad | Formato estricto | Transporte | Mediana / P95 | Tokens de entrada medios |
|---|---|---:|---:|---:|---:|---:|---:|
| ASTRA IQ3_S calibrado · Strata 0.1.41 | Base | 72/72 (100%) | 63/63 (100%) | 72/72 (100%) | 72/72 | 1014,39 / 1178,60 ms | 204,17 |
| ASTRA IQ3_S calibrado · Strata 0.1.41 | Base + Muse | 72/72 (100%) | 63/63 (100%) | 72/72 (100%) | 72/72 | 1083,66 / 1308,48 ms | 373,17 |
| Flash-Next Q4 UD-Q4_K_XL · Strata 0.1.41 | Base | 72/72 (100%) | 63/63 (100%) | 72/72 (100%) | 72/72 | 2242,19 / 2518,96 ms | 204,17 |
| Flash-Next Q4 UD-Q4_K_XL · Strata 0.1.41 | Base + Muse | 72/72 (100%) | 63/63 (100%) | 72/72 (100%) | 72/72 | 2463,43 / 2800,10 ms | 373,17 |

| Perfil | Cambio mediano de latencia | Diferencia mediana pareada | Pares donde overlay fue más lento | Gate preregistrado |
|---|---:|---:|---:|---|
| ASTRA IQ3_S | +6,83% | +123,91 ms | 53/72 | No elegible: supera +5% |
| Q4 UD-Q4_K_XL | +9,87% | +248,97 ms | 60/72 | No elegible: supera +5% |

Por seed, cada brazo obtuvo 24/24 en ASTRA y 24/24 en Q4 para las tres seeds. Las medianas de ASTRA control/overlay fueron 1010,70/1108,78 ms (seed 11), 991,84/1068,67 ms (42) y 1052,81/1076,31 ms (77). Para Q4 fueron 2238,61/2471,48 ms, 2171,69/2449,32 ms y 2297,40/2440,47 ms. El overlay añadió en promedio 169 tokens de entrada por solicitud; ambos brazos generaron en promedio 52 tokens de salida.

La suma de latencias individuales fue 74,19/81,64 s para ASTRA control/overlay y 163,34/180,43 s para Q4. Son sumas de tiempos de respuesta por request, no el tiempo de pared completo de cada campaña. No se midió TPS general ni throughput de servidor.

Los perfiles son completos y distintos: ASTRA usa IQ3_S calibrado y Q4 usa UD-Q4_K_XL; ambos corrieron Strata 0.1.41 en 2×RTX 3090, MTP4, KV int8 y contexto máximo 131072. ASTRA tuvo KV residente 32768 y `spec-min-p=0.70`; Q4 añadió expertos residentes y split 18/30. Por eso los números entre ASTRA y Q4 no aíslan el efecto de cuantización. La inferencia válida es sólo el cambio base vs overlay dentro de cada perfil.

## SOL: inválido por infraestructura

SOL ya estaba descargado antes de esta tarea. Se verificó y reutilizó desde `/media/cristian/Disco local/Models/llamacpp/club-3090/qwen3.8-27b-autoround-int4`; el manifiesto de los archivos locales tiene SHA-256 `b9b842e49ccc3f8b3a1459ce218d87884604a36725a46cb64b4741641ed7d231`. **No se volvió a descargar.**

El perfil vLLM v0.27.1 arrancó con TP2, MTP4, KV FP8 y contexto 262144 en las dos RTX 3090. En la primera generación, el log registró `ScatterGatherKernel.cu:203` con `idx_dim` fuera de rango, seguido de `CUDA error: device-side assert triggered` y caída fatal del EngineCore. El smoke HTTP 500 no produjo una observación puntuable. El fallo es inválido por infraestructura y no indica mala calidad de SOL. No se intentó una segunda configuración ni se atribuyó el error al prompt.

## Huellas y recursos

- ASTRA: shards SHA-256 `4c1eb2ceb4915e1192f4f386021897bde56a97f40a0bb78bb86465e0f7d2aca3` y `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`; fingerprint de perfil `864c6ba74e684940f34b5519c5e53a36412e386a9b160fb22ed7c2640ee85fa4`.
- Q4: cuatro shards SHA-256 `4448186216b3af4cc558bbce2c3213f01608f8f8b2e5267a9767971dd3ec8082`, `3f342f1c1580473f1ee94ddd5b28206e8c07a70fa1a366f59d1d6c922919a6c9`, `56758f40269cad5cd9b0d3d6fbae0f40f6d5be6de49e4ab392dbe83157d9cbd3` y `753bda48b98ba4f1636134a90a967de1b2d3908a236c026e464777342e53510a`; fingerprint `09d45e63b1f548df63775d947a051a70ca66561bb5a04bcf292050eb8bcb2958`.
- Strata 0.1.41 commit `fb58e0dbc8399662c0e47c76578c6e878b14f6cf`; GPU: 2×RTX 3090.
- Runner SHA-256 `84ae14cf384cec1bea8d3962a760c331cecca86da90808b086f9ed5e9b066447`.
- Plan SHA-256 `7cfcb5e3fe8753d05155199334b956cb1e9c05dbbfd3754ead960e80d656f43c`.

## Recibos

- [`PLAN.md`](PLAN.md), [`profile-manifest.json`](receipts/profile-manifest.json), [`preflight.json`](receipts/preflight.json).
- [ASTRA A/B crudo](receipts/astra-muse-ab.json), [ASTRA smoke](receipts/astra-smoke.json), [ASTRA engine log](receipts/logs/astra-muse-strata-engine.log).
- [Q4 A/B crudo](receipts/q4-muse-ab.json), [Q4 smoke](receipts/q4-smoke.json), [Q4 engine log](receipts/logs/q4-muse-strata-engine.log).
- [SOL smoke](receipts/smoke.json), [SOL vLLM log](receipts/logs/sol-vllm-muse-smoke.log).
- [Runner](scripts/run_muse_safe_transfer_ab.py), [config ASTRA](configs/astra-strata.json), [config Q4](configs/q4-strata.json).

Los smoke de ASTRA y Q4 fueron preflight y no se cuentan entre las 144 solicitudes por perfil. Los servidores iniciados para esta campaña se detuvieron al terminar; no hubo errores de transporte en las corridas A/B válidas. No se modificaron modelos, perfiles productivos ni defaults.
