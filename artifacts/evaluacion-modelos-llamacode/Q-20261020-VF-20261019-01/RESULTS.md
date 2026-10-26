# Resultado de evaluación — lote VF-20261019-01

## Fuente #1: concurrencia de Strata

**Estado:** screen directo del servidor completado; sin ganancia de throughput demostrada. La prueba de tareas completas en el harness y la política de subagentes no se midieron. No se cambia el perfil ni la configuración productiva.

La fuente de Reddit habla de throughput agregado en cuatro Radeon con varias sesiones. Esa cifra no se transfiere a las RTX 3090 locales. Se formuló la prueba para contestar sólo si dos solicitudes concurrentes mejoran el throughput del servidor Strata local de un slot.

### Intento 01: abortado antes de medir

El runner lanzó directamente `strata --serve`. El motor completó la carga y escribió `READY`, pero salió limpiamente antes de que el runner observara el puerto; el recibo registra cero warmups y cero solicitudes. La causa probable fue no mantener abierto el stdin de control: el wrapper local `serve/server.py` inicia el motor con `stdin=subprocess.PIPE` y mantiene ese canal durante la vida del API. No hubo OOM; después del cierre quedaron libres los procesos/puertos propios. Se preservaron los recibos del intento.

### Intento 02: screen medido

- Modelo Qwen3.8-Flash-Next Unsloth UD-IQ4_XS; Strata 0.1.41; perfil `q14-udiq4xs-he0`, fingerprint `185d554a488e661980a6500e64b2752fc86a863c5d666eb570a2d7c0db0bdc47`; contexto 32768, KV int8, MTP/spec4, GPU0. Una secuencia; no se intentó un segundo slot.
- Servidor oficial `serve/server.py`, loopback `127.0.0.1:8354`, en un network namespace privado. El preflight de 60 s pasó con 13 muestras: MemAvailable mínimo 120.746.472 KiB, OOM delta 0, sin apps compute ajenas, puertos libres y namespace funcional.
- Carga del modelo: 892,1 s. Medición: dos warmups excluidos y 20 pares balanceados, con los mismos prompts y seeds por condición. Cada condición completó 40 solicitudes (3840 tokens reportados); hubo 40/40 HTTP 200 y cero errores.
- Las 82 generaciones, warmups incluidos, terminaron con `finish_reason=length`, 96 tokens y contenido final vacío: el presupuesto se agotó mientras Qwen seguía pensando. Por eso esto es un screen de servicio/throughput con generación truncada; no mide calidad ni tareas útiles.

| Condición | p50 por solicitud | p95 por solicitud | Tiempo agregado de 40 solicitudes | Tokens reportados | Throughput agregado |
|---|---:|---:|---:|---:|---:|
| Serial | 1,912 s | 2,552 s | 79,251 s | 3840 | 48,45 tok/s |
| Dos solicitudes simultáneas | 2,702 s | 4,589 s | 79,976 s | 3840 | 48,01 tok/s |

La condición simultánea quedó 0,91% por debajo en throughput agregado; su latencia p50 fue 41% mayor y p95 80% mayor. En los 20 pares, cada condición tuvo menor tiempo de ola en 10 pares. No hay una dirección repetible que justifique habilitar concurrencia; el resultado favorece mantener la cola serial y la configuración de un slot. No demuestra nada sobre la delegación real de subagentes en LlamaCode ni sobre calidad de respuestas.

El runner informó inicialmente tok/s 1000 veces mayor por dividir por `wall_s/1000` aunque `wall_s` ya estaba en segundos. Se corrigieron los dos resúmenes derivados, se preservó el JSON original del runner y se corrigió la fórmula para usos futuros. Los vectores de solicitudes y tiempos crudos no cambiaron.

### Cierre de recursos y siguiente paso

Postflight a las 03:27:22Z: sin procesos Strata/runner ni apps compute, puertos 8354/8350/8352/18354/18111/18112 libres, MemAvailable 120.848.740 KiB, OOM sin cambio; GPU0 volvió a 705 MiB de uso de escritorio y GPU1 quedó en 108 MiB. No hubo cambios C++/QML, builds, suites de producto, descargas ni cambios de perfil.

La prueba E2E de dos tareas de coding y subagentes sólo merece ejecutarse si una decisión de producto depende de permitir tareas simultáneas; requeriría un holdout determinista y comparar tiempo hasta aceptación, reparaciones, delegación y recursos. No se debe presentar este screen como esa prueba.

## Recibos

- Plan y preregistro: [`PLAN.md`](PLAN.md).
- Intento técnico fallido: `receipts/concurrency-screen-attempt01.json`, `receipts/strata-concurrency-server-attempt01.log`.
- Intento medido corregido: `receipts/concurrency-screen-attempt02.json`; salida original preservada como `receipts/concurrency-screen-attempt02-runner-output.json`.
- Preflight y postflight: `receipts/preflight-retry-attempt02.json`, `receipts/postflight-attempt02.json`.
- Wrapper y config: `receipts/strata-server-config.json`.
- Runner usado en el experimento: SHA-256 `c171da152d4b4b421a0748605fcb6c26543e4b02cb296ddf4179973bfdf0cf04`. Fórmula corregida después del run: SHA-256 `5352b40190a287eeeaa6b300c4d0cf253c6acb84881ef55fc1dd48d2ce88b9a4`.

## Fuente #57 y contexto de los enlaces #14, #18, #22, #27, #52 y #55

**Resultado:** el contexto se puede ampliar por perfil, pero no hay base para elevar un límite global ni para transferir la capacidad entre quants o modelos.

- ASTRA DEFAULT / ISTA IQ2_XS ya quedó configurado a 1.048.576 tokens mediante YaRN ×4 (origen nativo 262.144). El screen local previo procesó 996.163 tokens y recuperó 10/10 hechos sintéticos en una corrida. Es evidencia de operación y retrieval sintético, no de calidad general ni estabilidad; un servidor ya cargado debe reiniciarse para tomar la configuración. [Q-20261014-ASTRA-YARN-1M](../Q-20261014-ASTRA-YARN-1M/RESULTS.md).
- ISTA Flash-Next IQ3_XXS / Strata 0.1.41 / RTX 3090 ejecutó tres prompts nuevos con 254.994 tokens de tokenizador (255.005 `prompt_tokens` de API) bajo su contexto nativo de 262.144. Recuperó exactamente 3/3 valores en cada corrida (nueve campos de nueve); todas dieron HTTP 200 y `finish_reason=stop`. Los tiempos totales fueron 73,79 s, 74,48 s y 71,41 s; prefill 3.481,8 / 3.449,6 / 3.365,9 tok/s, con 49 tokens de salida por corrida. La tercera reutilizó 16.384 tokens de prefix cache. El recibo conserva respuestas y score previos; se corrigió el comparador de la primera corrida para aceptar el valor decimal JSON 482.75, que coincidía exactamente con el valor pedido aunque estuviera tipado como número y no string.
- Postflight: 123.702.530.048 B disponibles (~115,2 GiB), OOM sin incremento, PSI de memoria avg10 0, sin procesos compute propios y GPU0/GPU1 en 692/108 MiB. El servidor y los puertos de la tarea quedaron cerrados.
- El resultado valida el holdout sintético de retrieval a ~255K para este quant/runtime. No prueba coding, razonamiento general, calidad a 1M ni autoriza cambiar perfiles productivos. SOL y QWEN35-A3B conservan 262K; TERRA conserva 64K; S57 ya verificó el contexto efectivo 1M y una generación corta tras el arranque; esto no añade un retrieval largo ni evidencia de calidad general.

Fuentes analizadas: #14/#18 reportan cambios de memoria/runtime para Flash-Next y son duplicados entre sí; #22/#27 describen KV offload para ROCm y son duplicados, sin ruta transferible al host CUDA RTX 3090; #52 es un reporte de IQ3_XXS a 262K en hardware distinto; #55 aporta la afirmación de 700K y #56 un retrieval cercano a 248K en RTX 5090, ambos con configuraciones que requieren holdouts locales propios. El pedido #57 queda respondido por perfil: ASTRA IQ2_XS tiene un screen previo a 996.163 tokens/10 de 10 hechos sintéticos en una corrida; IQ3_XXS tiene ahora validación local 3/3 cerca de 255K nativos; S55 (IQ3_XXS/700K) recuperó 15/15 hechos en tres prompts ~680K, con una violación de JSON crudo en la tercera (2/3 bare JSON); S56 (UD-IQ4_XS/~248K) cerró sin score tras cuatro intentos; no extrapolar ni elevar defaults globales. La matriz `docs/profile-use-case-stars-20260908.md` ya refleja 1M configurado para ASTRA; la nota del inbox que decía 131K era obsoleta. S57 confirmó que el runtime carga ASTRA IQ2_XS con contexto efectivo 1.048.576, origen nativo 262.144 y YaRN ×4; el endpoint expuso el modelo esperado y completó una solicitud de 19 tokens con HTTP 200/stop. Esto confirma activación y generación corta, no retrieval adicional ni calidad a 1M; el NIAH previo no se repitió. Adenda 2026-10-20: el usuario indicó que la interfaz gráfica abierta no bloquea estas pruebas. Antes de cada carga, comprobaré que no exista un servidor de inferencia activo y correré un único ensayo a la vez; no se necesita liberar la reserva gráfica de GPU1. S57 queda autorizado para preflight y ejecución. La evidencia anterior no cambia.

Planes, fixtures, recibos y postflights: [`PLAN.md`](PLAN.md), [`PLAN-source-55.md`](PLAN-source-55.md), [`PLAN-source-56.md`](PLAN-source-56.md) y [`receipts/`](receipts/), en particular `receipts/source-57-review.json`, `receipts/source-57-prereg.json`, el screen IQ3_XXS 262K y su `preflight-iq3xxs-context262k-resume01.json`.

## Fuente #2: DigUp / EmbeddingGemma 2

El post describe DigUp como búsqueda local de archivos con EmbeddingGemma 2. La fuente primaria del proyecto confirma que ya ofrece builds beta para Linux y Windows además de macOS, con un motor común; la vieja propuesta Linux que dejaba image/audio/video como stubs fue cerrada al salir ese port oficial. El proyecto divide PDF por página, documentos por pasajes, audio en ventanas de 30 s y video en fotogramas/escenas. El model card oficial confirma un espacio compartido de embeddings de 768 dimensiones y una ventana de 8.192 tokens para las cuatro modalidades.

En LlamaCode ya existe `hybrid_search` (BM25 + embeddings opcionales), `semantic_search` y extracción de documentos. La evaluación local `Q-20261010-EMBEDDINGGEMMA2-EVAL` probó la ruta textual/code: en 519 chunks y 21 consultas, EG2 plano subió nDCG@5 de 0,4588 a 0,6594, pero sigue siendo un screen sin holdout ni E2E. No se encontró una necesidad de producto que justifique instalar DigUp o repetir el modelo textual en este lote. La diferencia multimodal sólo amerita otra prueba si se decide incorporar búsqueda semántica sobre imágenes/audio/video; esa función no se infiere del benchmark de código ya medido.

**Resultado de la fuente:** sin prueba nueva aplicable en este host/lote; conservar EG2 textual como candidato provisional y no promoverlo. Fuentes primarias: [README de DigUp](https://github.com/ARahim3/DigUp), [cierre del port Linux #5](https://github.com/ARahim3/DigUp/issues/5), [model card oficial de EmbeddingGemma 2](https://huggingface.co/google/embeddinggemma-2). Evidencia local: `Q-20261010-EMBEDDINGGEMMA2-EVAL/RESULTS.md`, `src/core/agent/AgentToolRunner.cpp` y `docs/context-graph.md`.

## Fuente #3: DS41Engine para RX 7900 XTX

El repositorio primario es una implementación/fork de Strata para DeepSeek-V4.1-Flash GSQ con ROCm/HIP `gfx1100` y una RX 7900 XTX. Su README fija un caso de referencia de 24 GB VRAM, 128 GB RAM, 355 GB de artefactos y ~570 GB libres durante la descarga; los números de throughput y ajustes corresponden a ese equipo, no son comparables con nuestros perfiles Qwen/RTX.

La auditoría local existente `docs/deepseek-v41-flash-feasibility-20260914.md` ya concluye que el modelo/runtime V4.1 no carga con llama.cpp normal y no es ejecutable por el setup local. El host usa dos RTX 3090/CUDA, no una GPU AMD con ROCm; el volumen de modelos tiene 83,6 GB libres. No se encontró el modelo/engine exactos instalados. No descargar, compilar ni adaptar HIP/CUDA para este lote: eso no sería una comparación del mismo software ni un cambio de configuración con un resultado útil para la decisión actual.

**Resultado de la fuente:** bloqueada por una condición externa concreta: disponer del hardware AMD `gfx1100` y del espacio para los artefactos, o de un port CUDA y artefactos compatibles. Hasta entonces, usar la factibilidad local existente; no se propone prueba de inferencia. Fuente primaria: [DS41Engine README](https://github.com/vincalkr/DS41Engine).

## Fuente #4: Qwen3.8-27B NInfer RTX 5080 frente a Flash-Next

El post describe una sola tarea de código sin fixture, salida, seeds ni logs comparables. La ficha primaria del artefacto citado lo identifica como `qwen3_8_27b.ninfer`, 16.461.267.456 B, SHA-256 `c4a7e9ab593a7f42d58208fa0065d67a82d61921107686cc9f6ed1ec6b050e21`, context/KV 131.072, Q4 group64, MTP3, quantización mixta ~3,953 BPW. El runtime que respalda sus cifras es NInfer v1.5 / CUDA 13.4 para RTX 5080 Blackwell; el 112,2 tok/s y el prompt de 118K miden rendimiento, no coding.

Localmente existe `sys-ninfer3090-qwen38` pero se refiere a otro repositorio/artefacto histórico y a un perfil experimental; el `.ninfer` Qwen3.8 no está en el volumen local. La tabla de perfiles registra BCB 3/8 para la variante NInfer local, mientras ASTRA IQ2_XS tiene suites y fingerprints propios; no se comparan como una réplica de la nueva receta RTX 5080. La evidencia local más próxima ya compara Flash-Next IQ2_XS con Qwen3.8-27B Q4 en Hard Mode (77,98 vs 77,38), pero no es este artefacto NInfer v1.5.

**Resultado de la fuente:** candidato interesante, pero su prueba local queda bloqueada hasta disponer de una variante NInfer explícitamente compatible con RTX 3090/SM86 o soporte upstream comprobado; el artefacto actual y su runtime están validados para RTX 5080/SM120. Si se cumple esa condición, el test decisivo es un holdout de coding con el mismo harness/tareas/semillas contra el perfil productivo y un gate HE0→HE20 antes de ampliar. No inferir superioridad por la anécdota ni por sus TPS. Fuentes primarias: [ficha del modelo](https://huggingface.co/ninfer-5080/Qwen3.8-27B-RTX5080), [runtime y registros de validación](https://github.com/toddballinger/ninfer-5080). Evidencia local: `assets/system_profiles.json`, `docs/profile-use-case-stars-20260908.md` y `Q-20261009-STRATA-QWEN38-27B-AB`.

## Fuente #5: tuning hipBLASLt de Strata

El post calibra tablas hipBLASLt para dos RX 7900 XTX (`gfx1100`) con ROCm. El autor indica que tras el tuning el prompt processing quedó normalmente por encima de 2.100 tok/s donde antes rara vez superaba 2.100; decode fue similar. Sólo cambiaron 3 de 43 filas según el comentario del mismo autor. No es un A/B de calidad.

La guía se refiere al backend HIP: la fuente primaria de Strata construye `tune_hipblaslt` bajo `STRATA_ENABLE_HIP`, y el archivo de tabla declara arquitectura Radeon y versión de hipBLASLt. El checkout local Strata 0.1.41 tiene únicamente ese tuner HIP; no hay herramienta equivalente para la build CUDA/RTX 3090 del lote. La tabla `gfx1100` no es aplicable a NVIDIA.

**Resultado de la fuente:** sin prueba local aplicable; no ejecutar el tuner HIP ni importar esa tabla en CUDA. Reabrir sólo si el perfil de evaluación usa ROCm y el mismo device arch/hipBLASLt, o si upstream publica un tuner/table path para el backend CUDA. Fuente primaria: [CMake de Strata](https://github.com/Niko1221/Strata/blob/main/CMakeLists.txt). Fuente del claim: [post de tuning](https://www.reddit.com/r/LocalLLM/s/r41gtoLNKS).

## Fuente #6: DeepSeek V4.1 Flash 1017, GGUF Unsloth de 1 bit

El post apunta a la guía de Unsloth para `DeepSeek-V4.1-Flash-1017`. El modelo oficial declara una ventana de 1.048.576 tokens; la guía describe quants GGUF, Engram en SSD y una tabla de requisitos combinados RAM+VRAM de 128–145 GB para 1 bit. La variante mínima `UD-IQ1_S` ocupa 233,0 GB en disco y lleva una tabla Engram de 110,6 GB; la guía también advierte que el runtime y el contexto pueden requerir memoria adicional. El 88,2 % citado para `UD-IQ1_M` es top-1 agreement con el modelo original en `long17k`, no una tasa de éxito en coding ni una medición independiente del harness local.

La fuente propone usar una rama aún Draft de llama.cpp (#30817), o Unsloth. En la máquina de evaluación hay 123 GiB de RAM, dos RTX 3090 de 24 GiB y no aparecen artefactos de este modelo en el árbol inspeccionado. El NVMe de evaluación tiene 78 GiB libres, menos que los 110,6 GB de Engram que la guía manda mantener en SSD; el HDD extra tiene 220 GiB libres, casi lo justo para los 233 GB del pack, sin margen razonable. El runtime habitual Strata no ofrece esta arquitectura localmente y no se construyó otro runtime.

**Resultado de la fuente:** bloqueada por almacenamiento y soporte del runtime. No descargar, compilar ni ejecutar inferencia. Reabrir cuando haya SSD libre suficiente para el Engram y espacio completo del pack, y un runtime compatible validado para el backend local. Entonces hacer un screen de contexto/recuperación en 256K, 512K y 1M con el mismo holdout de hechos y controles, midiendo exactitud, prefill, decode y memoria; para decidir si reemplaza al productivo hace falta además una comparación de coding con el mismo harness. El resultado previo IQ3_XXS a ~255K respalda sólo esa configuración y no se extrapola a este modelo.

Fuentes primarias: [modelo DeepSeek](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017), [guía Unsloth y tabla de tamaños/requisitos](https://unsloth.ai/docs/models/deepseek-v4.1-flash), [GGUF Unsloth](https://huggingface.co/unsloth/DeepSeek-V4.1-Flash-1017-GGUF), [PR de llama.cpp #30817 (Draft)](https://github.com/ggml-org/llama.cpp/pull/30817). Fuente recibida: [post de r/unsloth](https://www.reddit.com/r/unsloth/comments/1xa0xph/run_deepseek_v41flash1017_locally/).


## Fuente #7: Qwen3.8 Flash-Next Coder IQ1_M actualizado

El enlace apunta a una revisión del artefacto ISTA-DASLab Coder. La revisión fijada `bba88856f8c3c0c9e40e45f82d05e228b814ac43` cambia el shard principal y mantiene el shard n-gram. Los dos shards GGUF y el sidecar se descargaron en serie y sus tamaños/hashes coincidieron con la API oficial de Hugging Face. El pack se preparó dentro de una copia aislada de Strata 0.1.41; el perfil productivo y los archivos de usuario no se tocaron.

Se corrió el screen preregistrado BCB-Hard-8, una corrida por brazo, mismo host dual RTX 3090, Strata 0.1.41, contexto 65.536, KV int8, una solicitud a la vez, MTP y suffix lookup apagados, temperature 0,6, top-p 0,95, top-k 20, min-p 0, penalties neutrales y máximo 6.144 tokens.

| Caso | Control IQ2_XS | Coder IQ1_M | Tokens del control | Tokens del candidato | Tiempo control | Tiempo candidato |
|---|---:|---:|---:|---:|---:|---:|
| 870 | pasa | falla | 433 | 6144 | 5.2 s | 81.8 s |
| 509 | falla | falla | 575 | 6144 | 6.5 s | 81.3 s |
| 857 | falla | falla | 360 | 6144 | 4.1 s | 81.7 s |
| 310 | falla | falla | 315 | 547 | 3.7 s | 7.5 s |
| 800 | falla | falla | 441 | 312 | 5.0 s | 4.5 s |
| 123 | falla | falla | 326 | 6144 | 3.8 s | 81.4 s |
| 952 | falla | falla | 274 | 6144 | 3.3 s | 81.6 s |
| 492 | falla | falla | 390 | 479 | 4.5 s | 6.6 s |

**Resultado:** control 1/8 y Coder IQ1_M 0/8; ambos 8/8 en transporte. El preregistro exigía al menos 3/8 para abrir una prueba extensa, por lo que el gate no se cumplió. El candidato consumió los 6.144 tokens en cinco de ocho respuestas; esto es evidencia de esta configuración/fixture, no una conclusión general sobre el modelo. No se ejecutan Hard Mode 28×3, instrucciones en español ni promoción de perfil. La recomendación operativa es conservar el perfil productivo actual y no reemplazarlo con esta revisión sobre la evidencia disponible.

No se midió latencia como objetivo ni se comparan tasas de tokens entre modelos: varias respuestas del candidato terminaron por límite de longitud. Las respuestas, grades y tiempos por caso están en `results/source-07-control-bcb.json` y `results/source-07-candidate-bcb.json`; hashes, gate y postflight en `receipts/source-07-screen-result.json`. El servidor propio se detuvo; GPU sin procesos compute, puerto 8038 libre, OOM=0 y MemAvailable 123.489.447.936 bytes.

El primer intento de arranque se rechazó antes de READY porque el pack IQ requiere `--spec >=2`; se conservó `--spec 4`, con `--mtp` ausente y `--suffix-draft 0` en ambos brazos. La primera invocación del runner falló antes de requests por una raíz de corpus mal resuelta; quedó corregida y se fijó la huella final antes de medir. Recibos técnicos: `source-07-control-start-attempt-01.json`, `source-07-config-correction.json` y `source-07-runner-preflight.json`.


## Fuente #8: Qwen3.8 en hardware de consumo, tabla de costo y replay agente

El post resume métricas de una sola solicitud y un replay de 53 turnos; la métrica más útil es el tiempo total del flujo, no un ranking de tok/s aislado. Su tabla de Flash-Next usa 2×RTX 5070 Ti 16 GB, 96 GB RAM, Strata 0.1.45 y capy-flash v0.6.0: el README del repositorio describe el replay como tres sesiones sintéticas, 11 subagentes, hasta 81K tokens y 256 tokens de salida por turno, con 177 s para capy NVFP4, 197 s para Strata IQ3_S y 268 s para Strata NVFP4. Son cifras del autor en el mismo equipo/día, no mediciones transferibles a este host.

La incompatibilidad decide la aplicabilidad: capy-flash documenta como requisito dos GPUs SM120; este equipo tiene dos RTX 3090 SM86. No hay runtime ni pesos capy-flash en el árbol de modelos de evaluación. El post también cita 27B tqLLM/ExLlamaV3 a 1×3090; no fija aquí un artefacto, revisión ni condiciones suficientes para convertir esos TPS en una prueba de calidad o de agente.

La evidencia local ya cubre la decisión de modelo: `Q-20261010-STRATA-QUANTS-89TASKS/RESULTS.md` compara los perfiles locales IQ2_XS, IQ3_S y Qwen3.8-27B AutoRound en Hard Mode con tres seeds; `Q-20261009-FLASHNEXT-IQ3XXS-AB/RESULTS.md` conserva el A/B de Flash-Next/Strata en dos RTX 3090. No son la reproducción del replay de 53 turnos, pero no justifican repetir esas suites con el runtime/hardware ajenos. Los controles locales también arrastran fallos de aislamiento TC-92, que impiden convertir el promedio de score en recomendación de producción para herramientas/tenants.

**Resultado:** sin prueba local aplicable y sin recomendación de compra basada en los precios EU del post. Reabrir si hay hardware SM120 disponible o un build/artifact de capy explícitamente compatible con Ampere, y si una decisión concreta requiere comparar el tiempo de una trayectoria agente común. Recepción, límites y revisión de duplicados: `receipts/source-08-review.json`. Fuentes: [post](https://www.reddit.com/r/LocalLLaMA/comments/1x9tzf1/qwen3827b_and_flashnext_on_consumer_hardware/) y [README de capy-flash](https://github.com/ValerioDolci/capy-flash).


## Fuente #9: DFlash2 para Qwen3.8 Flash-Next

El post enlaza el drafter oficial incoai/Qwen3.8-Flash-Next-DFlash2. La tarjeta primaria aclara que es un drafter BF16 de 0,6B, no un modelo de chat independiente. Su evaluación compara autoregresivo, MTP y DFlash2 sobre el target Qwen3.8-Flash-Next-FP8 con SGLang en una GB300 TP1; además fija un commit de SGLang y un patch de captura de features de Flash-Next. La tarjeta publica una ventaja de throughput de DFlash2 frente a MTP en ese entorno. El comentario de Reddit sobre RTX 3090 usa otra ruta ExLlamaV3, otro quant del target, draft BF16 y una tabla n-gram en RAM; es un resultado anecdótico que no identifica nuestro target/runtime.

La revisión local encontró DFlash2 para Qwen3.8-27B base en perfiles vLLM/llama.cpp y evaluaciones previas, pero no el drafter IncoAI para Flash-Next, el target oficial Flash-Next-FP8 ni el SGLang con el patch requerido. Los DFlash2 locales no se pueden emparejar con Flash-Next; las evaluaciones Flash-Next existentes usan otros caminos de MTP/Strata. No es duplicado de #7 (IQ1_M Coder actualizado) ni de #8 (tabla/replay en hardware de consumo), aunque comparte la familia Flash-Next.

**Resultado:** bloqueada por ausencia del par exacto de artefactos y runtime. No se inicia inferencia ni se descarga/compila otro motor porque no podría responder si DFlash2 mejora el perfil local con el target actual. Reabrir cuando haya un target Flash-Next y drafter DFlash2 exactos, junto con SGLang que incluya el patch de captura requerido y pase carga/API preflight en RTX 3090. Entonces preregistrar un screen MTP contra DFlash2 con el mismo target, prompt/harness y medidas de calidad/latencia; no mezclar la cifra GB300 ni el comentario ExLlama con resultados locales.

Fuentes primarias: [post](https://www.reddit.com/r/LocalLLaMA/comments/1x9rq3r/incoaiqwen38flashnextdflash2/) y [tarjeta oficial y receta SGLang](https://huggingface.co/incoai/Qwen3.8-Flash-Next-DFlash2). Evidencia local: docs/qwen38-flash-next-mtp-release-audit-20260914.md, docs/qwen38-gsq-rco-dflash2-q2-audit-20260918.md y assets/system_profiles.json. Recibo: receipts/source-09-review.json.


## Fuente #10: familias adicionales para PolyStrata

El post pide priorizar cuatro MoE: Nemotron 3.5 Bolt 74B-A9B-24GB, Nemotron 3.5 Super-VL 120B-A12B, Mellum2.1 12B-A2.5B-Thinking y MiMo V2.6 Flash MOPD. El issue primario de PolyStrata aclara que cada arquitectura necesita su propio port y que el motor no busca dense o modelos que ya caben cómodamente en VRAM.

| Modelo | Fuente primaria: forma/licencia | Ajuste para PolyStrata y prueba local |
|---|---|---|
| Nemotron 3.5 Bolt | 74B total / 9B activos, LatentMoE híbrido Mamba-2/Transformer, IQ2 GGUF de NVIDIA, hasta 256K, OpenMDW 1.1. El GGUF oficial da recetas de 28GB para 65K (GPU de 32GB+) y 32GB para 262K (48GB+); la compatibilidad publicada lista Ada/Blackwell. | Mejor candidato de la lista para priorizar un port de arquitectura MoE grande. El mantenedor dice que falta añadir nemotron_h_moe. No es un candidato local confirmado: 2×RTX3090 es Ampere SM86 y queda fuera de la lista oficial; no hay pesos exactos/runtime local. |
| Nemotron 3.5 Super-VL | 120B / 12B activos, MoE híbrido, imágenes/video, contexto 1M y MTP; licencia OpenMDW 1.1. El checkpoint BF16 declara 4×H100 o 2×GB200. | No es test local para 2×3090; soporte/quant/runtime tendrían que preceder cualquier prueba. |
| Mellum2.1 Thinking | 12B / 2,5B activos, contexto 131K, Apache-2.0. El card oficial BF16 dice que GGUF está por venir; hay quants comunitarios. | El mantenedor dice que Mellum2 cabe en VRAM y no encaja con el propósito de PolyStrata. Podría ser otro screen llama.cpp independiente, pero no responde al pedido de port del motor ni tiene uso/prioridad definida en este lote. |
| MiMo V2.6 Flash MOPD | MoE 309B / 15B activos, 1M, texto/imagen/video/audio, MTP de cinco capas, MIT. | No se encontró GGUF oficial ni pesos/runtime locales; la ficha oficial presenta rutas Transformers y SGLang/vLLM. No hay test local aplicable hoy. El MiMo Distill-Qwen-9B evaluado antes es otro checkpoint. |

**Resultado:** revisión de compatibilidad terminada; no se baja modelo ni se usa GPU. Como posible solicitud a PolyStrata, priorizaría Bolt para análisis de port de arquitectura, sujeto a comprobar luego Ampere; eso no lo recomienda como reemplazo del perfil productivo. Reabrir el test local sólo cuando haya un port PolyStrata con soporte nemotron_h_moe/SM86, los GGUF y auxiliares exactos, y espacio de almacenamiento con margen. Después: smoke de carga/endpoint y, sólo si estable, A/B de coding-agent contra el productivo con el mismo harness.

Fuentes primarias: [issue PolyStrata #16](https://github.com/VecSzn/PolyStrata/issues/16), [Bolt GGUF y receta de memoria/runtime](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB-GGUF), [Super-VL](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16), [Mellum2.1](https://huggingface.co/JetBrains/Mellum2.1-12B-A2.5B-Thinking) y [MiMo V2.6 Flash MOPD](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Flash-MOPD). Fuente recibida: [post](https://www.reddit.com/r/LowEndLocalAI/comments/1x7cmhb/additional-models-on-polystrata/). Recibo: receipts/source-10-review.json.


## Fuente #11: KLD y cuantización de KV para Qwen3.8-27B

El autor comparte 189 cálculos de KLD/perplejidad (21 variantes × 9 cuantizaciones K/V). El método sirve para fidelidad de distribución del siguiente token, pero no mide coding, tool-use o éxito de agente. En los datos crudos enlazados, la fila Qwen3.8-27B-UD-Q4_K_M da KLD medio 0,008847 para q8_0/q8_0, 0,009371 para q5_1/q5_1, 0,009873 para q8_0/q4_0 y 0,010067 para q4_0/q8_0. Eso respalda q5_1 frente a esas dos mezclas en esa fila, pero q8_0/q8_0 queda mejor; no hay una receta universal que se pueda importar.

El candidato local relacionado era QWEN38-Q8 UD-Q8_K_XL, cuyo archivo fue retirado y no está activo. Sus registros históricos son de otra cuantización/protocolo: q8_0 tuvo smoke a 8K y 262K; 64K/131K dieron SIGABRT en fused CUDA RMS norm con una build específica. No hay evidencia de que el tipo de KV cause ese aborto ni de que reducirlo lo repare. SOL usa otra ruta de runtime y KV FP8; no mezclar sus resultados con el estudio GGUF. El lote ya tiene evidencia de recuperación local 3/3 cerca de 255K con IQ3_XXS y ASTRA 1M configurado, que responde a la pregunta de capacidad de contexto sin necesitar este perfil retirado.

**Resultado:** sin prueba local aplicable ahora. No descargar/restaurar el Q8 ni ejecutar KLD mientras no sea candidato a una decisión concreta. Reabrir si vuelve el GGUF exacto y una pregunta de memoria/contexto requiere elegir KV; entonces comparar en el mismo artefacto y runtime, midiendo KLD/NLL y una guarda funcional de recuperación/coding. El resultado del post no prueba calidad de agente.

Fuentes: [post](https://www.reddit.com/r/LocalLLM/comments/1x6fttm/i_tested_qwen38_27b_kld_for_21_models_at_9/) y [tabla cruda del autor](https://pastebin.com/TixNsaby). Evidencia local: docs/profile-validation-matrix-20260914.md, docs/profile-validation-update-20260915.md, docs/benchmark-results.md y documentos de contexto Qwen3.8. Recibo: receipts/source-11-review.json.


## Fuente #12: DeepSeek-V4.1-Flash-1017 GSQ con Xolotl

El post enlaza una cuantización GSQ orientada a coding/agentes y afirma 153 GiB, KV FP4 y contexto 512K. La tarjeta del artefacto la identifica como una cuantización del checkpoint DeepSeek-V4.1-Flash-1017 (763,2B), exclusiva del motor Strata/Xolotl: requiere mapa de precisión por experto, rank.bin, capas Engram y sidecar DSpark; no es un GGUF estándar para llama.cpp, Ollama, vLLM o SGLang. El post mezcla el tamaño de pesos con el requisito de ejecución: Xolotl indica que, además de unos 152 GiB del quant, la ruta completa requiere alrededor de 200 GB de Engram en NVMe rápido. La tarjeta del artefacto enumera dos chunks de 90 y 73 GiB, 5,3 GiB de sidecar y dos tablas Engram de 95 GiB cada una; por lo tanto, su lista de archivos no coincide con el presupuesto de 153 GiB y el conjunto runtime suma aproximadamente 358,3 GiB antes de espacio temporal. La capacidad de 512K figura como configuración soportada, pero los resultados publicados de código/herramientas no muestran una evaluación de recuperación a 512K.

Xolotl declara Linux/NVIDIA, CC 7.5+, CUDA 12/13, 24 GB de VRAM y 90 GB de RAM para el ejemplo de DeepSeek. Sin embargo, la tarjeta de esta cuantización mide el modelo en una RTX PRO 5000 de 72 GB y receta de serving con una GPU de 72 GB; eso no demuestra que este artefacto exacto cargue en las RTX 3090 locales. La memoria del host (123 GiB) supera el ejemplo de RAM publicado, pero no resuelve el requisito de almacenamiento ni la falta de compatibilidad demostrada para la combinación exacta.

**Evidencia local y duplicados:** las búsquedas no encontraron el checkpoint 1017 GSQ, los chunks, Engram, sidecar, rank.bin ni un checkout/runtime Xolotl. A la lectura del preflight más reciente hay 24 GB libres en /media/cristian/Disco local y 131 GB en el volumen Windows montado; ninguno alcanza el artefacto principal anunciado, mucho menos las dependencias Engram. El historial #6 trata el mismo linaje general DeepSeek V4.1-Flash-1017, pero es otra cuantización Unsloth UD-IQ1_S, otra ruta/runtime y un pedido de contexto de 1M; no es un duplicado ni permite transferir scores. Los perfiles locales DeepSeek V4 0731 son checkpoints distintos.

**Resultado:** bloqueada por falta del paquete y del runtime compatible, con almacenamiento insuficiente. No se descarga, compila ni ejecuta inferencia; tampoco se puede afirmar que 512K sea mejor para el perfil productivo. Reabrir cuando exista espacio rápido verificado para los archivos exactos y el espacio de recombinación, y una ruta documentada de la cuantización 1017 GSQ sobre RTX 3090/Ampere. Entonces hacer primero smoke de carga/API y recuperación en varios tamaños hasta 512K con guardas de calidad y memoria; sólo si pasa, preregistrar un A/B de coding/agente frente al productivo con el mismo harness. Las cifras del autor se mantienen como evidencia de su hardware, no como predicción local.

Fuentes: [post recibido](https://www.reddit.com/r/LocalLLM/comments/1x9jobm/xolotl_strata_the_new_deepseekv41flash1017_a_153/), [tarjeta del quant 1017 GSQ](https://huggingface.co/kaushikvira/DeepSeek-V4.1-Flash-1017-GSQ-agentic-strata), [runtime Xolotl y requisitos](https://github.com/Indras-Mirror/Xolotl). Recibo: receipts/source-12-review.json.


## Fuente #13: Harness², autoajuste del harness con pesos fijos

Harness² propone que un agente modifique ocho partes del harness —prompt, guardrails, memoria, guía de tools, subagentes, skills, scripts y plugins— y use ejecuciones de referencia/probes para componer una variante. El repositorio reporta mejoras en tres benchmarks públicos con cuatro configuraciones model-harness; los números del README son hasta +11,5 puntos en WorkBuddy-Bench, +4,5 en JobBench y +11,8 puntos porcentuales en el pass parcial de LAB. Esos resultados son de las configuraciones publicadas (Gemini/GLM y sus harnesses), no de los perfiles locales de LlamaCode. El flujo con modelo incurre en llamadas de solver/improver/judge; la guía menciona que el stream completo de LAB tiene 1.143 tareas. El demo determinista local prueba el paquete y su mecanismo, no que mejore tareas de LlamaCode.

**Evidencia de seguridad y de encaje local:** Harness² indica que el executor no restringe egress y que Codex corre con sandbox deshabilitado. Sus benchmarks y rúbricas son públicos; el propio proyecto aconseja aplicar reglas de red a nivel de host para impedir que el agente descargue rúbricas/respuestas. El setup se orienta por defecto a Vertex AI; el executor Codex permite un endpoint Responses API personalizado, por lo que un backend local podría explorarse, pero no hay una integración Harness² presente en el repo ni se ha validado el endpoint/model routing. LlamaCode sí tiene un sandbox `strong` opt-in para workers en Unix con bubblewrap y red no compartida cuando se desactiva `allowNetwork`; si se habilita, la política de red es todo o nada y no ofrece egress por host ni mediación de secretos. No asumir que esa política envuelve automáticamente el Codex CLI que Harness² lanza.

**Resultado:** idea accionable para un posible experimento de mejora de harness, pero bloqueada antes de ejecutar modelo/dataset. No correr benchmarks públicos ni conectarlo al repo productivo: con la configuración documentada existe riesgo de fuga de rúbricas y de acceso al host. El demo offline no decide utilidad local, por lo que no se instala ni ejecuta. Reabrir cuando haya commit/dependencias fijados, un endpoint local compatible, una copia descartable sin credenciales ni datos productivos, un holdout sintético/no público y aislamiento de host que permita sólo el endpoint de inferencia y bloquee acceso exterior/rúbricas. Entonces preregistrar un piloto de una tarea, comparar baseline y harness adaptado con el mismo modelo, y aceptar mejoras sólo tras evaluación independiente con múltiples seeds y guardas de regresión. Prioridad baja hasta definir qué componente de LlamaCode se quiere mejorar.

Fuentes primarias: [repositorio y README](https://github.com/google-research/harness2), [guía de experimentos y egress](https://github.com/google-research/harness2/blob/main/docs/EXPERIMENTS.md), [setup y endpoint Codex configurable](https://github.com/google-research/harness2/blob/main/docs/SETUP.md). Fuente recibida: [post](https://www.reddit.com/r/machinelearningnews/comments/1x8xz38/google_opensources_harness%C2%B2_agents_that_rewrite/). Evidencia local: docs/harness.md, src/core/agent/HarnessSandbox.cpp, docs/openshell-evaluation-20260928.md. Recibo: receipts/source-13-review.json.

#### Iteración 2026-10-21 — canary local de tool calling

Se validó el aislamiento exacto y el grader de diez casos con una referencia correcta (10/10), pero el canary ASTRA no produjo evidencia de modelo: las cargas a 32K y 8K fueron abortadas antes de readiness al superar PSI full avg10 >25% en cuatro muestras consecutivas. La de 8K llegó a 52,58%; MemAvailable bajó a 82,9 GB, el scope alcanzó 37,3 GiB y 0 B de swap; postflight sin procesos/listeners propios. No hubo solicitud API, llamada de herramienta, holdout de ASTRA ni piloto Harness² de calidad. Mantenerlo bloqueado hasta disponer de una ruta de carga/runtime materialmente distinta que respete el guard PSI; no relajar el guard ni repetir este camino. El piloto de calidad además requiere un workflow LlamaCode y holdout sintético fijo. Resultado y recibos: `artifacts/evaluacion-modelos-llamacode/Q-20261021-VF-ITERATION-3/RESULTS.md`.


## Fuente #14: Qwen3.8 Flash-Next IQ4_XS, contexto y route-tail skip

El post describe una sola RTX 4090 con Strata 0.1.45, 64 GB RAM y Unsloth UD-IQ4_XS: contexto nativo 262K, q4_0 KV, MTP, y needle tests con recuperación a 36K y 136K. También sostiene que `STRATA_ROUTE_TAIL_SKIP=7` elevó el KL contra Q8 para los archivos Unsloth y recomienda ponerlo en 0. La cifra 87–98 tok/s y el resultado de contexto pertenecen a ese equipo/fixture; no prueban mejor coding ni reemplazo local.

La revisión primaria de Strata confirma que el route-tail skip fue incorporado en v0.1.42 y queda activo por defecto en ciertos modos CUDA; `STRATA_ROUTE_TAIL_SKIP=0` lo apaga. La documentación del PR explica que el flag omite expertos no residentes de rangos bajos, así que cambia las salidas, además de cambiar velocidad/KL. En el issue del mantenedor sobre v0.1.41 se describe la diferencia de defaults entre 0.1.41 y versiones posteriores. La corrida local comparable de UD-IQ4_XS fijó Strata 0.1.41; por eso no hay el mismo switch que aislar y no corresponde exportar una variable desconocida ni atribuir el post a nuestra versión.

**Contexto y resultado local:** el pedido de ampliar contexto ya se abordó en la fuente #57: Flash-Next IQ3_XXS nativo, 262K, recuperó el holdout de hechos en 3/3; ASTRA IQ2_XS quedó configurado a 1.048.576 con YaRN ×4 y un NIAH sintético 10/10 en una corrida, evidencia de configuración/retrieval sintético, no calidad general. No se transfiere ese resultado a IQ4_XS. El perfil local IQ4_XS sí completó HumanEval/20 20/20 en Strata 0.1.41; BCB8 tuvo dos cierres por timeout y ADV/TaskFlow quedaron incompletos, sin score. No se justifica repetir HE20 ni dar por aprobado el coding gate.

**Resultado:** sin prueba nueva aplicable al runtime actual. La hipótesis del flag sí puede cambiar el tradeoff calidad/velocidad al migrar a Strata 0.1.42+; antes de hacerlo, reparar la ruta de harness que dejó suites incompletas y fijar una suite corta con score válido. Si se decide evaluar una versión nueva, preregistrar A/B `STRATA_ROUTE_TAIL_SKIP=7` frente a `0`, mismo artefacto IQ4_XS, endpoint, sampling explícito, prompts y orden intercalado; medir score, completitud, latencia y errores, y avanzar sólo con una guarda de calidad. No cambiar el perfil ni inferir nada sobre 512K/1M a partir de este post.

Fuentes: [post recibido](https://www.reddit.com/r/LocalLLM/comments/1x8utw2/32gb_to_64gb_of_ram_took_qwen38flashnext_from_iq2/), [PR de route-tail skip y mediciones del mantenedor](https://github.com/Niko1221/Strata/pull/1668), [notas del mantenedor sobre los defaults frente a 0.1.41](https://github.com/Niko1221/Strata/issues/1878), [Unsloth UD-IQ4_XS](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF/tree/main/UD-IQ4_XS). Evidencia local: `Q-20261014-ASTRA-YARN-1M/`, `Q-20261015-IQ3XXS-REMAINING-SCREENS/` y `Q-20261019-STRATA-UDIQ4XS-REMAINING/`. Recibo: receipts/source-14-review.json.


## Fuente #15: comparación Pi / DeepSeek Harness en tareas personales

El autor compara configuraciones sobre su benchmark privado core10-v1.3: 10 tareas reales de su trabajo, tres corridas por configuración y verificadores ocultos. El leaderboard fija Pi 0.85.1, Codex 0.118.0, DeepSeek Harness 0.2.1-rc.1 y otras herramientas. Para el modelo hosted DeepSeek-V4.1-Flash-1017, Pi/high pasó 30/30; DeepSeek Harness/low hizo 29/30 en los intentos individuales y 27/30 pass-all-3 (90%), pero usó ~75% más tokens y más pasos que Pi/low, cuyo pass-all-3 también fue 90%. Estos datos muestran que harness, esfuerzo, tokens y tiempo cambian el resultado en ese benchmark; no prueban que DeepSeek 1017 sea mejor que los modelos/productivos locales.

La guía del autor usa tareas extraídas de su historial de trabajo, verificadores deterministas y aislamiento Harbor; valida cada verificador con solución oracle, no-op, near-miss y alternativa correcta, y elimina tareas triviales o ambiguas. La suite y las tareas exactas son privadas, así que no pueden replicarse aquí ni auditarse independientemente con el material recibido.

**Evidencia local y duplicados:** LlamaCode ya conserva una comparación Hard Mode de 28 escenarios × 3 semillas en `Q-20261010-STRATA-QUANTS-89TASKS`, además de suites por perfil con harness/verificadores y recibos. Esa suite no duplica core10-v1.3: cambia tareas, modelos y runtimes; pero sí cubre la necesidad general de repeticiones y comparación local. También queda una diferencia relevante: el Hard Mode ya registra fallos de aislamiento TC-92/TC-74 en perfiles locales, así que un score no puede promover un agente mientras esos gates fallen. Ningún DeepSeek-V4.1-Flash-1017 de la API del post ni su dataset oculto está en las raíces locales.

**Resultado:** no repetir suites locales ya cerradas ni pagar llamadas API para intentar replicar una colección privada. Como metodología, adoptar el esquema sólo si una decisión futura no queda cubierta por los holdouts actuales: seleccionar diez tareas de usuario no sensibles o sintetizadas, construir verificadores deterministas y ocultos, validarlos con oracle/no-op/near-miss/alternativa correcta, aislar cada tarea y correr tres réplicas pareadas por perfil. Registrar pass@1, pass-all-3, tiempo, tokens y fallos del sandbox; los gates de seguridad prevalecen sobre el score. No extraer sesiones privadas ni crear ahora un fixture nuevo: no hay decisión específica ni candidato local nuevo que justifique el costo de curación.

Fuentes: [post recibido](https://www.reddit.com/r/LocalLLaMA/comments/1x8mq6f/deepseek_v41_flash_1017_vs_v41_flash_pi_vs/), [leaderboard core10-v1.3](https://ibragim.dev/leaderboard/), [guía de creación y validación de tareas](https://ibragim.dev/writing/agent-sessions-to-evals/). Evidencia local: `Q-20261010-STRATA-QUANTS-89TASKS/RESULTS.md`, `Q-20261010-STRATA-QUANTS-89TASKS/PLAN.md` y recibos Hard Mode/TaskFlow. Recibo: receipts/source-15-review.json.

## Fuente #16: calculadora de VRAM y velocidad StudioTV

La calculadora desglosa pesos, KV, estado recurrente y reserva del motor por modelo, contexto, concurrencia, GPU y servidor. El sitio reporta, según su propia validación diaria contra 133 lanzamientos de InferenceX, brechas medianas de 1,3% en pesos por GPU, 1,8% en KV y 13,2% en velocidad por solicitud; la página advierte ±30–50% para la estimación de velocidad. Esos valores no son una calibración independiente de LlamaCode/Strata.

**Cruce local comparable, limitado a pesos:** la ficha Qwen3.8-27B presenta 15,4 GiB como pesos Q4_K_M en la tabla de memoria, pero en la sección de GGUF da 17,7 GiB para el archivo exacto `ggml-org/Qwen3.8-27B-GGUF`. El manifiesto local fija esa revisión y el archivo local verificado tiene 18.973.870.528 bytes (17,67 GiB), alineado con 17,7 GiB y 2,27 GiB (14,7%) por encima de la cifra resumida de 15,4 GiB. La misma página dice que para GGUF publicados cuenta el tamaño exacto del archivo, por lo que conviene usar el dato de archivo y aclarar esta diferencia antes de tomar una decisión con el renglón resumido.

La corrida histórica más cercana es Qwen3.8-27B Q4_K_M / llama.cpp 0.4.1-dev, un slot y contexto configurado 131.072, servida sobre 2×RTX 3090. Sus recibos confirman checkpoint, quant, runtime y contexto; no conservan el pico de VRAM por perfil mientras el modelo estaba cargado. El registro de `nvidia-smi` posterior al apagado (854/108 MiB) no mide ese pico. Sólo hay un perfil razonablemente comparable y no 2–3 mediciones de memoria simultáneas con la predicción; velocidades entre GPUs/engine/condiciones distintas tampoco sirven para calibrar el valor publicado. No se afirma una validación global del calculador.

**Resultado:** herramienta útil como filtro inicial de capacidad, con margen y verificación de tamaño exacto del artefacto; no usar su velocidad para elegir un modelo ni tomar el resumen de pesos como sustituto de la medida de carga real. No se justifica iniciar una nueva carga para esta fuente: no cambiaría la decisión de perfil y la calibración completa carece de registros comparables. Si una decisión de compra o de asignación de GPU depende de una diferencia estrecha, preregistrar una calibración con 2–3 perfiles locales, mismo modelo/quant, engine, contexto, concurrencia y hardware; capturar pico de VRAM, RAM, KV y velocidad por separado, en corridas seriales, y comparar los tamaños de GGUF exactos.

Fuentes: [post recibido](https://www.reddit.com/r/LocalLLM/comments/1x6tx45/which_models_fit_on_my_gpu_i_made_a_tool_that/), [calculadora y método](https://studiotvai.com/llm-vram-calculator), [ficha Qwen3.8-27B y tamaños GGUF](https://studiotvai.com/vram-requirements/qwen3-8-27b). Evidencia local: `Q-20261014-IQ2XS-MISSING-MODALITIES/RESULTS.md`, `receipts/model-source-manifest.json`, `receipts/server-speed/q4/metadata.json` y `receipts/session-cleanup.json`. Recibo: receipts/source-16-review.json.

## Fuente #17: Qwen3.8 Flash-Next IQ3_S con Strata `unify` y NVMe

El autor muestra un despliegue de 131K en una RTX 4070 Super de 12 GB, 30,4 GiB RAM, zram y SSD NVMe. Su README atribuye a su rama privada/pública `bodhi37/strata` (`unify`, base Strata 0.1.44.1 con cambios propios) 48,4 tok/s en 20 prompts, 1.350–1.450 tok/s de prefill frío y 18,8K tok/s efectivos en hits de prefijo. El A/B mostrado es contra su propia rama anterior `orca-port` en el mismo equipo, no contra Strata upstream sin modificaciones. Un comentario del hilo describe un intento parecido en laptop con OOM y 3–4 tok/s; el autor atribuye sensibilidad a RAM del sistema y SSD. Es evidencia de una receta de tiering de expertos para equipos limitados, no de ventaja de modelo en LlamaCode.

**Artefacto y calidad:** el README usa `SC117/Qwen3.8-Flash-Next-GSQ-RCO-abliterated-GGUF`, 83,86 GB para IQ3_S, con shard de n-gram común y parámetros de runtime; reemplaza 144 tensores de residual por valores de una variante OrcaRouter y mantiene los otros 1.079 byte a byte. La ficha de SC117 aclara que elimina el vector de rechazo y advierte que carece de guardrails integrados fiables. La tabla de IQ3_S frente a BF16 combina AIME25, GPQA-Diamond y LiveCodeBench; el propio autor dice que la ligera diferencia de promedio (93,26 frente a 93,12) cae en variación y debe leerse como paridad, no superioridad. Su chequeo de comportamiento del abliteration es sólo una prueba puntual.

**Evidencia local y duplicados:** hay GGUF IQ3_S stock de ISTA-DASLab, no el artefacto SC117 abliterated ni el fork `unify`. El IQ3_S local medido en Strata 0.1.41 obtuvo 71,43/100 en Hard Mode (28 escenarios × 3 semillas; 133,1 tok/s media), con fallos de aislamiento TC-92; no puede sustituir el artefacto ni comprobar la receta low-VRAM. El ASTRA DEFAULT actual es IQ2_XS sobre 2×RTX 3090, con 1M YaRN configurado y recuperación sintética 10/10 en una corrida; esa evidencia tampoco es comparable con IQ3_S abliterated y tiene fallos TC-92/TC-74. La receta de 131K/12GB no mejora el límite de contexto configurado local. La #8 también trata Qwen3.8/Strata pero su prueba era un replay capy-versus-Strata en RTX 5070 Ti; #14 era IQ4_XS y route-tail skip, y #57 la solicitud general de contexto. Relacionadas, no duplicadas.

**Resultado:** sin prueba local aplicable al host/decisión actuales. No descargar el checkpoint de 83,86 GB ni construir el fork: el diseño optimiza una caja con 12 GB VRAM y 30 GB RAM, mientras LlamaCode dispone de 2×RTX 3090/123 GiB RAM; el post no indica una nueva capacidad o decisión que esta receta vaya a cambiar y el checkpoint quita resguardos de rechazo. Si surge una necesidad concreta para un equipo de 12 GB, primero fijar commit y hashes del GGUF/runtime, revisar seguridad y uso previsto, y medir en ese hardware; no trasladar su score/tok/s al perfil actual. Si la pregunta futura pasa a ser sólo si `unify` acelera la IQ3_S stock local, preregistrar un A/B de runtime con mismo GGUF, contexto, sampling, prompts y perfil, y mantener los gates de seguridad: eso no replicaría el modelo abliterated del post.

Fuentes: [post recibido](https://www.reddit.com/r/LocalLLaMA/comments/1x7sbdc/qwen38flashnextgsqrco_iq3_s_4050_toksec_decode/), [receta y comparación del autor](https://github.com/bodhi37/Qwen3.8-Flash-12GBRAM-32GBVRAM-SSD-Recipe), [fork Strata `unify`](https://github.com/bodhi37/strata/tree/unify), [tarjeta del GGUF abliterated](https://huggingface.co/SC117/Qwen3.8-Flash-Next-GSQ-RCO-abliterated-GGUF), [cuantización stock ISTA](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF). Evidencia local: `Q-20261010-STRATA-QUANTS-89TASKS/RESULTS.md`, `assets/system_profiles.json` y los GGUF stock bajo `ASTRA-IQ3_S-calibrated-20261006`. Recibo: receipts/source-17-review.json.

## Fuente #18: crosspost IQ4_XS y contexto 262K

El enlace de r/LocalLLaMA resuelve al post `/1x8l18e/` de Distinct-Pie2389. Es un crosspost del #14, cuyo permalink de r/LocalLLM es `/1x8utw2/`: coinciden autor, título y cuerpo sustantivo. Los IDs y comentarios son distintos. El texto repite la receta de una RTX 4090/64 GB, Strata 0.1.45, Unsloth UD-IQ4_XS y contexto configurado a 262K; informa needle retrieval a 36K y 136K, pero no aporta un retrieval poblado al final de 262K. El modelo oficial declara 262.144 tokens nativos y extensión hasta 1M; eso es el límite publicado de arquitectura, no validación local de cada quant.

Los comentarios agregan que el cambio de sampling por defecto en Strata 0.1.45 afecta solicitudes que omiten esos campos. El perfil local `q14-udiq4xs-he0` fija sampling explícito y usa Strata 0.1.41; no depende de ese default. El ensayo IQ4_XS local previo usó 32.768 de contexto. El test IQ3_XXS a 262K y la configuración ASTRA IQ2_XS a 1M no se transfieren a UD-IQ4_XS.

**Resultado:** duplicado/crosspost de #14 y sin benchmark nuevo. No cambia el límite operativo actual ni justifica otra corrida para un perfil IQ4_XS que no fue promovido. Si UD-IQ4_XS se selecciona para un despliegue donde 262K importe, abrir un screen aislado con el GGUF local, Strata 0.1.41 y un holdout fresco de recuperación a 262K antes de cambiar el perfil.

Fuentes: [crosspost r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1x8l18e/32gb_to_64gb_of_ram_took_qwen38flashnext_from_iq2/), [post r/LocalLLM #14](https://www.reddit.com/r/LocalLLM/comments/1x8utw2/32gb_to_64gb_of_ram_took_qwen38flashnext_from_iq2/), [model card oficial Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next), [quant UD-IQ4_XS](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF/tree/main/UD-IQ4_XS). Recibo: `receipts/source-18-review.json`.

## Fuente #19: QUASAR NVFP4 para Qwen3.8-27B

El post anuncia un checkpoint QUASAR-QAT de Qwen3.8-27B en NVFP4 W4A4 (19,7 GB) y reporta GPQA-Diamond 90,9 frente a 91,4 para BF16, junto a métricas de quantización. También enumera Qwen3.5-4B, Gemma 4 y Muse Glimmer con otros formatos, incluidos GGUF Q4_0 para algunos. Las cifras del autor son de quantización/benchmarks generales y no miden coding, llamadas a tools ni tareas agentivas de LlamaCode.

La tarjeta oficial afirma que el checkpoint sirve con vLLM, pero requiere una GPU NVIDIA con soporte FP4: Blackwell y compute capability 10.0+. La documentación oficial de LLM Compressor también asigna NVFP4 a Blackwell/SM100. `nvidia-smi` confirmó en este host dos RTX 3090 de 24 GiB, compute capability 8.6. En el directorio local revisado hay otros artefactos Qwen3.8-27B GGUF, no el QUASAR NVFP4; sustituirlos no probaría este checkpoint.

**Resultado:** bloqueada por incompatibilidad determinista de hardware antes de descargar o inferir. No hay prueba local que cambie la decisión con SM86 ni motivo basado en coding/agentes para cambiar de familia a partir de este post. Reabrir con GPU SM100+ o con una representación compatible con Ampere y un holdout agentivo preregistrado.

Fuentes: [post recibido](https://www.reddit.com/r/Qwen_AI/comments/1x7897s/quasar_4bit_qat_checkpoints_for_qwen35_gemma_4/), [model card QUASAR](https://huggingface.co/QUASAR-QAT/Qwen3.8-27B-QUASAR-NVFP4), [requisitos de NVFP4 en LLM Compressor](https://docs.vllm.ai/projects/llm-compressor/en/0.12.0.1/steps/choosing-scheme/), [código del proyecto](https://github.com/vincentcounathe/quasar-qat). Recibo: `receipts/source-19-review.json`.

## Fuente #20: frontier como planificador y modelo local como ejecutor

El post pregunta cómo repartir tareas entre una suscripción frontier y un modelo local. Los comentarios presentan experiencias incompatibles: algunas personas dicen reducir el uso frontier delegando ejecución, otras describen más correcciones, espera y trabajo de configuración. No hay conjunto fijo de tareas, hidden tests, comparación pareada, costo total ni tiempos reproducibles; el hilo no identifica un modelo local mejor.

**Ajuste al producto local:** README documenta backends OpenAI-compatible y una cadena de escalamiento `profile`/`http`/`cli`, en modo manual, automático tras fallos o ambos. También documenta que Privacy mode bloquea delegación/escalamiento, pero no es un firewall ni garantiza aislamiento de red. El concepto se puede probar sin cambiar producto, midiendo el flujo entero y no sólo los tokens locales o frontier.

**Accionable, preregistrado pero pendiente de condición externa:** `VF-20261019-01-S20-ROUTE-AB`. Comparar seis mini-repos sintéticos en brazo local-only y brazo frontier-plan → ejecución local → revisión frontier, con orden aleatorio y una corrida pareada por tarea. Registrar aceptación y tests ocultos, revisión fija, intentos/reparaciones, tokens y costo externo, latencia final y campos transmitidos. Si el screen resulta positivo, sólo entonces hacer tres semillas por brazo dentro de un techo de gasto configurado. El piloto se limita a datos sintéticos; no incluye repositorios, credenciales ni logs reales.

**Bloqueo actual:** el material no identifica proveedor/modelo, endpoint/keyRef ni techo de gasto, y no define qué datos pueden salir del equipo. Por eso no se hizo ninguna llamada externa ni se cargó contenido del repositorio. Reabrir cuando esos campos estén configurados y se preserve la frontera sintética en un perfil aislado. No hay benchmark de modelo que ejecutar mientras falte esa condición.

Fuente: [post recibido](https://www.reddit.com/r/LocalLLM/comments/1x82s4f/i_have_both_a_frontier_subscription_and_the/). Evidencia del producto: [README, privacidad](../../../README.md#modo-privacidad) y [README, cloud + supervisor](../../../README.md#backends-cloud--secretstore). Recibo: `receipts/source-20-review.json`.


## Fuente #21: DeepSeek V4.1 Flash 1017 en OpenCode Go

El post expresa la esperanza de que la versión 1017 esté disponible en OpenCode Go; sus comentarios especulan sobre FP2 y disponibilidad y no aportan una comparación reproducible. DeepSeek anunció oficialmente el lanzamiento 1017 y documenta que su API sirve esa versión bajo el alias `deepseek-flash`. OpenCode Go actualmente lista `DeepSeek V4.1 Flash` con el ID `opencode-go/deepseek-v4.1-flash`, pero su documentación no confirma que ese alias sea exactamente 1017. El anuncio oficial resume una gráfica de DeepSWE v1.1/mini-swe-v2; no alcanza para inferir rendimiento en las suites de LlamaCode.

**Accionable condicional:** candidato para reutilizar el A/B preregistrado `VF-20261019-01-S20-ROUTE-AB`; no abrir una suite aparte. Si se elige OpenCode Go, fijar antes de la corrida el ID y verificar versión efectiva. Comparar seis mini-repos sintéticos contra el brazo local-only y conservar las métricas de aceptación, tests, reparaciones, tokens/costo y latencia.

**Bloqueo:** faltan cuenta/keyRef autorizada, techo de gasto y frontera de datos; tampoco está confirmado el mapeo de OpenCode Go a la build 1017. No se llamó a ninguna API, no se incurrió en gasto y no se transmitió código. OpenCode Go es un servicio opcional de pago y sus límites/precios pueden cambiar; este post no justifica contratarlo. La vía local de #12 sigue bloqueada por artefacto/espacio/runtime y no se sustituye por un proveedor hospedado.

Fuentes: [post recibido](https://www.reddit.com/r/opencodeCLI/comments/1x88v51/deepseek_v41_flash_1017/), [anuncio oficial DeepSeek 1017](https://api-docs.deepseek.com/news/news261017/), [API y alias oficial del modelo](https://api-docs.deepseek.com/quick_start/pricing/), [modelos e IDs actuales de OpenCode Go](https://dev.opencode.ai/v2/docs/console/go). Evidencia local: [README, privacidad](../../../README.md#modo-privacidad) y [resultado de #12](#fuente-12-deepseek-v41-flash-1017-gsqxolotl). Recibo: `receipts/source-21-review.json`.


## Fuente #22: streaming KV ROCm en RX 9070 XT

El autor informa Qwen3.8-27B IQ4_XS con KV Q8_0/Q4_0 y contexto de 262.144 en una RX 9070 XT de 16 GB, mediante un fork ROCm/HIP, caché KV completa en RAM host y kernels RDNA4. Los números del post bajan a 9,5 tok/s target-only y 31,1 tok/s con MTP al llegar a 262K; los 80+ tok/s del titular corresponden a contextos de 1–4K. No hay prueba de passkey/NIAH ni resultado de calidad a 262K. La página del fork ROCm que enlaza el autor no se pudo recuperar en esta consulta, por lo que los números quedan como reporte de autor.

**Sin prueba local aplicable:** este host usa CUDA y RTX 3090 (SM86); no se compila ni se prueba el port ROCm/RDNA4. LlamaCode ya tiene un antecedente distinto de streaming KV en CUDA: Qwen3.8 UD-Q4 hasta 131K en una 3090, con 5,25 tok/s decode a 131K y passkey no exacta en ambos runtimes. Es evidencia de capacidad de ejecución y límite de calidad del fork anterior, no confirmación de esta rama ni de 262K. El pedido de contexto #57 ya registra pruebas de 255K por IQ3_XXS y ASTRA 1M, sin extrapolarlas a otros quants.

El repo padre enlazado desde el post mantiene una rama CUDA V2; su README califica end-to-end el RTX 5070 Ti/SM120, pero sólo describe calificación selectiva de operadores/modelo en SM86. Probar esa rama en la 3090 sería un experimento separado, con commit fijado y preregistro propio; no se inicia a partir del reporte ROCm. El inbox marca preliminarmente a #27 como duplicado; se confirmará al revisarlo en orden.

Fuentes: [post recibido](https://www.reddit.com/r/LocalLLaMA/comments/1x89ptz/qwen_27b_iq4_xs_q8q4_kv_at_full_262k_context_on_a/), [repo padre adaptive-KV con su matriz CUDA](https://github.com/RaymondHuang210129/llama.cpp-adaptive-kv-streaming). Evidencia local: [matriz de benchmarks](../../../docs/benchmark-profile-matrix.md) y [auditoría Qwen/KVMem](../../../docs/qwen38-gsq-rco-kvmem-audit-20260918.md). Contexto por perfiles: [Fuente #57](#fuente-57-y-contexto-de-los-enlaces-14-18-22-27-52-y-55). Recibo: `receipts/source-22-review.json`.


## Fuente #23: PLE FP8 separada para Qwen3.8 Flash-Next

El autor muestra dos prompts visuales del mismo IQ3_S, primero con PLE IQ4_NL incluida y luego con PLE FP8 E4M3 aparte. Dice notar menos errores sin cambio de velocidad, pero no hizo benchmark ciego/controlado. Hay contraevidencia en el hilo: otro usuario no vio cambios de código, HMMT ni DeepSWE Mini al pasar a PLE Q8, aunque sí pequeñas diferencias de prosa en inglés/polaco. Esos resultados no prueban que FP8 no ayude; tampoco trasladan el beneficio anecdótico a coding en español.

**A/B preregistrado:** `VF-20261019-01-S23-PLE-FP8-AB`, mismo target IQ3_S y misma configuración, cambiando sólo PLE stock por PLE FP8 oficial. Screen de ocho tareas de coding/tool-use, cuatro inglés y cuatro español, tres pares por brazo y orden aleatorio. Medir tests/aceptación, herramientas, errores, latencia y almacenamiento. Sólo ampliar si el brazo FP8 gana ≥2/8 tareas sin regresiones de seguridad/tool-use y mantiene decode dentro de 5% del control. No extrapolar a IQ2_XS ni IQ4_XS.

**Resultado parcial (1/3 pares; sin decisión):** se recuperó/verificó el pack oficial y se generó el sidecar FP8 E4M3 de 51.200.246.112 B; paridad CPU exacta en 128 filas. En seed 23001 ambos brazos completaron transporte 8/8: FP8 pasó 2/8 tareas y stock IQ4_NL 0/8 (seis empates, dos victorias FP8, cero derrotas). Medianas: decode 124,60 vs 144,25 tok/s (-13,6% FP8), prefill 319,25 vs 328,35 tok/s; wall mediano 4.931,27 vs 2.356,49 ms. Una única semilla no satisface el gate preregistrado de tres; no se concluye superioridad ni se promueve. Stock/23002 attempt01 quedó interrumpido en startup; attempt02 llegó a 23 s de carga sin readiness, resultado ni requests puntuadas.

**Registro histórico de la pausa por presión de memoria del host:** el 20-10-2026 a las 20:37:47−03:00 `systemd-oomd` terminó 21 procesos de un scope Chromium al superar el slice 55,50% (>50% durante más de 20 s). A las 20:55:53−03:00 volvió a intervenir sobre otro scope Chromium; ese cgroup usaba 50,2 GiB y el slice estaba al 62,95%, con presión de memoria intensa. Un segundo después el kernel registró `Cannot map memory ... 0xbb5d0a pages`; no se encontró OOM-kill del kernel, segfault, ni dump reciente atribuible a ChatGPT/Codex. El proceso ChatGPT observado después seguía vivo (iniciado 21:15:26−03:00). Estos registros muestran presión y terminaciones de Chromium, pero **no prueban que Codex haya crasheado por OOM**. En Q20 se retomó el screen sólo después de validar `--mmap-experts` bajo límites de memoria/PSI. Los seis brazos llegaron a READY y completaron; la PLE FP8 quedó empatada en 3/24 frente a 3/24 stock. El resultado completo está debajo; no se promueve.

Fuentes: [post recibido y comentarios](https://www.reddit.com/r/LocalLLaMA/comments/1x8am0i/why_not_run_qwen_38_flash_next_with_the_full/), [packer oficial `ple_fp8_pack.py`](https://github.com/Niko1221/Strata/blob/main/tools/ple_fp8_pack.py), [checkpoint oficial Qwen FP8](https://huggingface.co/Qwen/Qwen3.8-Flash-Next-FP8/tree/main). Evidencia local: [perfil ASTRA IQ3_S](../../../assets/system_profiles.json) y [matriz de benchmarks](../../../docs/benchmark-profile-matrix.md). Recibo: `receipts/source-23-review.json`.

## Fuente #24: el ranking compuesto Agentic Coding Index

El post afirma que DeepSeek V4.1 Flash 1017 lidera los modelos de pesos abiertos. El propio sitio del índice actualmente muestra 77,5 puntos para 1017; Qwen3.8 Flash Next figura con 59,7 en esa misma vista. La página explica que el Agentic Coding Index combina 12 benchmarks con pesos distintos: DeepSWE v1.1 (14%), Terminal-Bench v4.0 (13%), FrontierCode 1.1 (11%), SWE-bench Pro (11,5%), Code Migration de Vals-AI (10%), Code Arena Elo (8%), Terminal-Bench v2.1 (8%), Program-Bench (6%), SRE-Bench de Vals-AI (6%), Terminal-Bench v3.0 (5%), SciCode (4,5%) y LiveCodeBench v6 (3%). También indica que CWLE imputa puntuaciones faltantes usando covarianza empírica entre benchmarks. El autor del post confirma que agrega resultados de proveedores y evaluadores externos y que el JSON exportado incluye los orígenes. No inspeccioné ese JSON, así que no atribuyo una cobertura observada/imputada concreta a la fila 1017.

El 77,5 es un resultado del compuesto particular, no una corrida única ni una tasa de éxito transferible al harness local. Pesos, harnesses, fechas, proveedor y cobertura de datos difieren entre componentes, y valores imputados pueden afectar la clasificación. La tarjeta oficial de DeepSeek publica resultados propios por benchmark bajo condiciones de harness específicas; esos valores no se deben confundir con los 77,5 puntos agregados del sitio. El índice sirve como señal para seleccionar un candidato, no demuestra que 1017 supere a ASTRA o Qwen3.8 Flash Next en LlamaCode, y su condición de modelo de pesos abiertos tampoco elimina los bloqueos de hardware/runtime para ejecutarlo localmente.

**Resultado:** accionable sólo para mantener DeepSeek 1017 como candidato del A/B híbrido sintético ya preregistrado `VF-20261019-01-S20-ROUTE-AB`, junto con la disponibilidad/API revisada en #21. No crear otro benchmark ni cambiar el modelo productivo por el ranking. El A/B existente continúa bloqueado: faltan proveedor/modelo y versión efectiva, keyRef autorizada, techo de gasto y frontera de datos. No se hicieron llamadas, gasto ni transmisión de código. La ruta local sigue sujeta a los bloqueos de artefacto, espacio y runtime registrados en #12. Si se habilita el experimento existente, registrar los resultados del brazo 1017 por separado; el índice no sustituye los tests ocultos ni la aceptación de repos sintéticos.

Fuentes primarias: [post y explicación del autor](https://www.reddit.com/r/LocalLLaMA/comments/1x8bb6b/deepseek-v41-flash-1017-now-leads-openweight/), [metodología y vista actual del Agentic Coding Index](https://www.ai-leaderboard.dev/), [tarjeta oficial DeepSeek V4.1 Flash 1017 y tabla de benchmarks](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017/blob/main/README.md). Evidencia local: [A/B de routing #20](#fuente-20-frontier-como-planificador-y-modelo-local-como-ejecutor), [disponibilidad del API/OpenCode Go #21](#fuente-21-deepseek-v41-flash-1017-en-opencode-go) y [factibilidad local #12](#fuente-12-deepseek-v41-flash-1017-gsqxolotl). Recibo: `receipts/source-24-review.json`.

## Fuente #25: cuantización, temperatura y tiempo total de tarea

El post prueba tres quants de Qwen3.8 Flash-Next (Q3_XXS, Q3_S y Q4_XS) en un minijuego Tetris dentro del navegador. Para cada quant compara la receta recomendada de thinking (temp 1, top-p 0,95, top-k 20 y penalties neutrales) con temp 0, fijada en los JSON de Strata y Pi y sin los demás parámetros de sampling. Indica tres ejecuciones por cada combinación modelo/temperatura y evalúa requisitos funcionales, tokens de salida, velocidad de decode y tiempo total con pruebas y llamadas a herramientas. Su conclusión es que quants menores generaron más tokens y consumieron más tiempo total pese al decode más rápido; no vio cambio de calidad atribuible al quant y cree que temp 0 podría dar más consistencia, pero declara que la muestra es insuficiente. Hay una ambigüedad de conteo: el texto habla de “12 test tasks”, pero 3 quants × 2 temperaturas × 3 ejecuciones son 18 celdas/ejecuciones, y no aclara si 12 es número de prompts distintos o total de tareas. El brazo temp 0 también omite top-p, top-k y penalties, así que no aísla el efecto de temperatura. La figura presenta resultados agregados, sin desglose de los prompts/artefactos verificables en el post.

La tarjeta oficial de Qwen recomienda para thinking temp 1, top-p 0,95, top-k 20, min-p 0, presencia 0 y repetición 1. En LlamaCode, la prueba previa `Q-20261014-STRATA-IQ2XXS-SAMPLING` ya comparó el perfil local IQ2_XS con temperaturas efectivas 0,1/0,6/1, manteniendo constantes los demás parámetros y usando Strata 0.1.41, TaskFlow ULTRA (tres seeds por brazo) y un smoke de coding. Los tres brazos dieron el mismo bucle repetido, 0/13 en TaskFlow y 0/6 en el smoke; el tiempo mediano de TaskFlow fue 19,275/19,372/19,079 s. Por tanto, para el perfil local actualmente seleccionado no hubo una razón observada para cambiar el sampling. Esa evidencia es más directamente comparable al harness local que el Tetris del post, pero sólo cubre IQ2_XS; no se extrapola a Q3_XXS, Q3_S ni Q4_XS.

**Resultado:** sin prueba adicional para la decisión actual. No repetir IQ2_XS ni cambiar su sampling por el post: la pregunta de temperatura ya se examinó localmente con parámetros controlados y la corrida no produjo mejora. La comparación del post sirve como recordatorio de medir tokens y tiempo total de agente, no sólo tok/s. Si se decide evaluar alguno de esos quants exactos como reemplazo, reabrir con el artefacto/versiones fijados y un A/B pareado del mismo harness; mantener top-p/top-k/min-p/penalties y límites iguales entre brazos, variar sólo temperatura, y medir aceptación/tests, tokens, reparaciones, tool calls y tiempo total. El material no justifica iniciar esa prueba sin una decisión de quant pendiente.

Fuentes: [post recibido y comentarios](https://www.reddit.com/r/LocalLLaMA/comments/1x88fvj/qwen_flash_next_quant_and_temp_comparison/), [tarjeta oficial Qwen3.8-Flash-Next y parámetros recomendados](https://huggingface.co/Qwen/Qwen3.8-Flash-Next). Evidencia local: [plan y resultados del A/B de sampling IQ2_XS](../../../artifacts/evaluacion-modelos-llamacode/Q-20261014-STRATA-IQ2XXS-SAMPLING/RESULTS.md). Recibo: `receipts/source-25-review.json`.


## Fuente #26: cartuchos internos en Qwen2.5-72B

El post afirma que tres cartuchos de unos 10K tokens cada uno se pueden cargar dentro de un Qwen2.5-72B congelado mediante H3 y las claves/valores de las capas 0–3, sin volver a procesar el texto fuente. También describe 11/11 comprobaciones físicas en una sola A100-80GB.

**La evidencia primaria no confirma la corrida que relata el post.** El script [`MAM_full_QWEN_72B.py`](https://github.com/ceceli33/titan-cognitive-core-v3/blob/main/MAM_full_QWEN_72B.py) denomina la implementación “candidate v1.5 — not a published or validated release”; declara que el autor no la ejecutó en GPU y que el estado es simulación CPU. El preflight del mismo script exige una A100-80GB y prevé descargar alrededor de 145 GB de pesos. Además, el README del repositorio define su registro publicado actual como Mistral-7B CUT6 y el antecedente Qwen como Qwen2.5-7B CUT3, no el escalado Qwen2.5-72B. En el protocolo medido comparable, el cartucho y el control que lee juntos el mismo texto obtienen los mismos scores estrictos; el README no reclama ventaja de velocidad ni razonamiento general.

Esto tampoco demuestra ampliar la ventana nativa: los ~30K tokens citados son posiciones de cartucho interno, mientras la [ficha oficial Qwen2.5-72B](https://huggingface.co/Qwen/Qwen2.5-72B-Instruct) declara contexto completo de 131.072 tokens y hasta 8.192 tokens de generación. No se reporta retrieval/calidad por encima de ese límite. En LlamaCode, el perfil ASTRA activo usa Qwen3.8-Flash-Next IQ2_XS en Strata sobre 2×RTX 3090 y está configurado a 1.048.576 con YaRN ×4; #57 ya cubre la evidencia local de ampliación por perfil. `MemoryStore`, `GraphStore`, `KnowledgePacket` y `context_scout` resuelven otra pregunta con recuperación textual y evidencia local. Las activaciones/cartuchos son modeloespecíficos; el README del propio proyecto indica que no son portables entre arquitecturas.

**Resultado: bloqueada para prueba local; prioridad baja.** No hay un experimento que pueda cambiar la configuración actual: el target/hardware no coinciden, el código enlazado no verifica una ejecución GPU de Qwen2.5-72B y el post no demuestra contexto mayor que el nativo. No se descargó código o modelo, no se instaló nada, no se construyó ni se usó GPU. No es duplicado de #1–#25; está relacionado temáticamente con la memoria/RAG local y la solicitud #57.

**Reapertura concreta:** sólo cuando exista un run GPU reproducible con hashes de modelo y engine y una decisión real de adoptar cartuchos para un perfil compatible. Preregistrar entonces un holdout con hechos sintéticos o posteriores al entrenamiento que el modelo no haya visto, y comparar sin memoria, lectura conjunta del texto, RAG y cartucho con el mismo modelo/contexto. Medir exactitud, contaminación, latencia total, coste de creación/almacenamiento e integridad append; calibrar el corte para esa arquitectura.

Fuentes: [post recibido](https://www.reddit.com/r/LocalLLM/comments/1x872ux/we_completely_bypassed_rag_and_context/), [script enlazado Qwen2.5-72B](https://github.com/ceceli33/titan-cognitive-core-v3/blob/main/MAM_full_QWEN_72B.py), [README e informe de resultados publicados](https://github.com/ceceli33/titan-cognitive-core-v3), [ficha oficial Qwen2.5-72B](https://huggingface.co/Qwen/Qwen2.5-72B-Instruct). Evidencia local: [`assets/system_profiles.json`](../../../assets/system_profiles.json), [`README.md`](../../../README.md#índice-y-preflight-de-contexto) y [solicitud general #57](#fuente-57-y-contexto-de-los-enlaces-14-18-22-27-52-y-55). Recibo: `receipts/source-26-review.json`.


## Fuente #27: repost del streaming KV ROCm de la fuente #22

El permalink de r/LocalLLM resuelve a un post separado en `/1x7wack/`, pero su autor, título, cuerpo, receta y tabla de rendimiento coinciden con el post r/LocalLLaMA `/1x89ptz/` ya analizado en #22. Los dos enlaces reportan el mismo Qwen3.8-27B IQ4_XS, RX 9070 XT/RDNA4, fork ROCm/HIP y cifras a 262K. Los comentarios forman parte de conversaciones distintas, pero no aportan un benchmark de calidad reproducible ni una medición aplicable al host CUDA local.

**Resultado: duplicada de #22.** Se conserva este recibo para relacionar el segundo enlace con la fuente canónica; no se repite la prueba ni se cuentan otra vez las cifras. La incompatibilidad ROCm/RDNA4 frente a RTX 3090/CUDA ya está documentada en #22.

Fuentes: [permalink r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1x7wack/qwen_27b_iq4_xs_q8q4_kv_at_full_262k_context_on_a/), [post canónico r/LocalLLaMA #22](https://www.reddit.com/r/LocalLLaMA/comments/1x89ptz/qwen_27b_iq4_xs_q8q4_kv_at_full_262k_context_on_a/). Recibo: `receipts/source-27-review.json`.


## Fuente #28: una migración Flutter→SwiftUI frente a Opus 5.5

El autor cuenta un único intento de migrar varias pantallas de una app productiva de Flutter a SwiftUI. Informa unos 60 minutos para Qwen3.8-Flash-Next Q4_K_XL y 50 para Opus 5.5 xhigh, y califica el resultado local como casi idéntico, aunque menos pulido y quizá necesitado de 2–3 rondas extra. No publica el repositorio, cambios, pruebas, prompt completo, versiones/hash de los artefactos ni rúbrica. También cambian cuantización, hardware/runtime y harness: el post usa un Gufo port en Windows/OpenCode v2 y Claude Code para Opus. Los comentarios son opiniones contrapuestas, no una réplica. La [ficha oficial Qwen](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) y la [página oficial Anthropic](https://www.anthropic.com/claude/opus) confirman los productos, pero no validan ese caso particular.

**Evidencia local ya disponible:** el perfil candidato Qwen3.8-Flash-Next UD-Q4_K_XL obtuvo 77,38/100 en Hard Mode 28×3, frente a 77,98/100 del IQ2_XS ASTRA en la misma suite y semillas; IQ2_XS superó por 0,62 puntos porcentuales. Q4_K_XL promedió ~65,3 tok/s y el IQ2_XS ~154,19 tok/s. La suite local usa herramientas simuladas, por lo que no reproduce la migración de una app real ni permite inferir equivalencia con Opus. ASTRA conserva además los fallos de aislamiento TC-92/TC-74: el score no habilita uso con datos sensibles ni entre tenants.

**Resultado:** no repetir el screen local ni promover Q4_K_XL a partir de este post. Una comparación directa Qwen-vs-Opus sí podría cambiar una decisión, pero queda bloqueada hasta tener un fixture sintético o snapshot autorizado/sanitizado con pruebas independientes, versiones/harness/permisos equivalentes, keyRef de Claude Code y techo de gasto explícito. El A/B de routing #20 no sustituye esta comparación de migración. No se hicieron llamadas externas ni se transmitió código productivo.

Si se habilita más adelante, usar al menos tres corridas pareadas del mismo fixture para ambos modelos; medir tests/aceptación, reparaciones y llamadas a tools, tiempo total, tokens y costo. Las cifras de una sola corrida de la fuente no son evidencia de superioridad o paridad.

Fuentes: [post recibido](https://www.reddit.com/r/LocalLLM/comments/1x85v8g/unsloth_qwen_38_flash_next_is_insane_can_be/), [model card oficial Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next), [página oficial Claude Opus](https://www.anthropic.com/claude/opus). Evidencia local: [`assets/system_profiles.json`](../../../assets/system_profiles.json), [Hard Mode comparativo Qwen3.8](../Q-20261009-STRATA-QWEN38-27B-AB/PLAN.md) y [A/B de routing #20](#fuente-20-frontier-como-planificador-y-modelo-local-como-ejecutor). Recibo: `receipts/source-28-review.json`.


## Fuente #29: DeepSeek V4.1 Flash 1017 y reportes comunitarios de lectura de secretos

La [ficha oficial](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) describe el modelo upstream con 763B parámetros y contexto anunciado de 1M. Eso no demuestra recuperación correcta a un millón de tokens ni se transfiere automáticamente al empaquetado GSQ/Xolotl de #12, que es un artefacto/runtime distinto. La capacidad de contexto ya está cubierta por la petición y evidencia local #57.

Un comentario del hilo dice que “4.1 flash” a veces intentó leer archivos secretos pese a una instrucción de no hacerlo. No fija revisión, harness, permisos, contenido, logs ni pasos de reproducción; por lo tanto no permite atribuir el episodio al checkpoint 1017 ni medir su incidencia. Sí refuerza una práctica que ya es parte del diseño documentado: no depender de una instrucción de prompt para proteger credenciales. El [README de LlamaCode](../../../README.md#modo-privacidad) aclara que Privacy Mode no es aislamiento del sistema operativo y no restringe comandos arbitrarios de `run_shell`, otros procesos o harnesses externos. La evidencia local TC-92/TC-74 ya muestra fallos de aislamiento entre tenants.

**Resultado: sin prueba específica aplicable ahora.** El checkpoint exacto sigue bloqueado para ejecución local por los límites de artefacto/espacio/runtime de #12, y la ruta API de #20–#21 carece de proveedor/version fijados, keyRef, techo de gasto y frontera de datos. Probar una instrucción de “no leas secretos” con otro modelo no caracterizaría 1017; tampoco se necesita otra corrida para sostener la política ya documentada. No se usó GPU ni API, no se enviaron datos y no se expusieron secretos. Reabrir sólo con el checkpoint/runtime exactos o un endpoint autorizado, y un test preregistrado en workspace descartable con señuelos sintéticos, sin secretos reales ni egress público, que evalúe controles efectivos de filesystem/tools. La prueba de contexto a 1M debe permanecer separada y medir retrieval, no sólo carga.

Fuentes: [post recibido](https://www.reddit.com/r/LocalLLaMA/comments/1x84po4/deepseekaideepseekv41flash1017_hugging_face/), [ficha oficial DeepSeek](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017). Evidencia local: [README, modo privacidad](../../../README.md#modo-privacidad), [fuente #12](#fuente-12-deepseek-v41-flash-1017-gsqxolotl) y [solicitud general de contexto #57](#fuente-57-y-contexto-de-los-enlaces-14-18-22-27-52-y-55). Recibo: `receipts/source-29-review.json`.


## Fuente #30: Flash-Next Q4 frente a Qwen3.8-27B Q8 en Tetris

El autor compara Qwen3.8 Flash-Next UD-Q4_K_XL con Qwen3.8-27B Q8 en una máquina de cuatro RTX 3090 mediante dos solicitudes: crear un Tetris para Windows y luego agregar modo local para dos jugadores. Dice que usó el harness de DeepSeek. Reporta que una corrida de Strata de cuatro horas no terminó en un ejecutable jugable, y luego acotó las corridas a una hora; la 27B tuvo dos defectos en el primer prompt, corregidos durante el segundo. No publica repositorio/diff, tests, binarios, logs íntegros, fingerprints ni una matriz por ejecución. Se cambian modelo y quant, y la evidencia no permite comprobar límites de tiempo ni configuración efectiva iguales. Aunque los comentarios cuestionan parámetros greedy, el autor respondió que había cambiado los parámetros al preset recomendado antes de la prueba.

La tarjeta oficial Qwen diferencia el sampling recomendado para thinking del instruct. El [PR #1274 de Strata](https://github.com/Niko1221/Strata/pull/1274) documenta el problema de clientes que no enviaban parámetros, el uso explícito de presets y la posterior corrección en la línea 0.1.45; el PR se cerró cuando su autor indicó que el commit `a8091f4` ya resolvía el problema. Esto no establece qué sampler recibió el post, y no basta para atribuir el resultado al greedy.

**Evidencia local relacionada:** Hard Mode 28×3 ya comparó Flash-Next Q4, ASTRA IQ2_XS y Qwen3.8-27B AutoRound INT4. Sus medias fueron 77,38, 77,98 y 66,07 respectivamente, aunque 27B usó vLLM y Flash-Next/ASTRA Strata, por lo que tampoco es una comparación aislada de pesos. La prueba local de sampling #25 mantuvo el resto de parámetros fijos para IQ2_XS y no encontró diferencia que justificara cambiar el perfil actual. No encontramos instalado el Qwen3.8-27B Q8 exacto del post; el host evaluado tiene dos RTX 3090, distinto del equipo de cuatro GPU reportado.

**Resultado: sin prueba nueva aplicable.** La decisión actual ya tiene una comparación local más amplia entre perfiles disponibles; replicar dos tareas de Tetris con otro quant ausente requeriría descarga y GPU, pero no cambiaría la recomendación de perfiles con la evidencia actual. El post sí recuerda medir ejecución de tests, reparaciones y tiempo total, no sólo tok/s; esos campos ya están contemplados en los informes locales. Reabrir si el Q8 exacto queda disponible y existe una decisión concreta de reemplazo; usar fixture, sampler, contexto, harness, permisos, seeds y tope de tiempo fijados, y comparar perfiles completos cuando no sea posible igualar runtimes.

Fuentes: [post recibido y comentarios](https://www.reddit.com/r/LocalLLaMA/comments/1x7uf15/i_dont_get_the_qwen_38_flash_next_hype/), [tarjeta oficial Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next), [historial de presets de sampling en Strata #1274](https://github.com/Niko1221/Strata/pull/1274). Evidencia local: [Hard Mode 28×3](../Q-20261010-STRATA-QUANTS-89TASKS/RESULTS.md) y [A/B de sampling IQ2_XS](../Q-20261014-STRATA-IQ2XXS-SAMPLING/RESULTS.md). Recibo: `receipts/source-30-review.json`.


## Fuente #31: DS41Engine, fork ROCm/HIP para DeepSeek V4.1 Flash

El enlace de Reddit apunta a `vincalkr/Strata-DSV4.1`, que ahora redirige a [`vincalkr/DS41Engine`](https://github.com/vincalkr/DS41Engine), fork de Indras-Mirror/Xolotl con un engine y servidor propios para DeepSeek-V4.1-Flash GSQ. El README declara licencia MIT, Linux/ROCm/HIP 7.14 y una RX 7900 XTX `gfx1100`; dice que otras GPUs no están probadas. Los números publicados son de esa máquina: 16,5–18,6 tok/s en decode corto y 10–12 tok/s en sesiones agentic de 18–41K. No son resultados transferibles a CUDA/RTX 3090.

El set local documentado requiere 152 GiB de GSQ y 189 GiB de Engram (355 GiB en disco) y alrededor de 570 GB libres en el pico de descarga. El equipo local tiene 2×RTX 3090 CUDA/SM86, sin GPU AMD `gfx1100`, y búsqueda read-only no encontró el engine, el GSQ ni las tablas Engram. El preflight actual dejó 25.187.364.864 bytes libres en NVMe, 140.084.998.144 en el volumen NTFS del workspace y 15.193.993.216 en raíz. RAM local (~123 GiB) es de clase similar a los 122 GiB del autor, pero no corrige las incompatibilidades de GPU ni almacenamiento.

**Resultado: bloqueada antes de clonar, descargar o compilar.** El repositorio no ofrece ruta NVIDIA/SM86 calificada; el paquete excede el almacenamiento disponible. El hilo menciona explorar un segundo Radeon con PCIe x8, no una ruta CUDA. #12 ya bloqueó otro paquete DeepSeek/Xolotl por artefacto/espacio/runtime; esta rama no es duplicado exacto, pero comparte esa familia y tampoco cabe en el host. No se clonó ni descargó, no se compiló y no se usó GPU. Reabrir con una ruta CUDA para SM86 probada end-to-end o hardware ROCm `gfx1100` y almacenamiento NVMe suficiente para los modelos y el pico temporal; fijar hashes antes de un smoke test.

Fuentes: [post recibido](https://www.reddit.com/r/LocalLLM/comments/1x7l69h/github_vincalkrstratadsv41_deepseekv41flash_gsq/), [repo DS41Engine y README](https://github.com/vincalkr/DS41Engine). Evidencia local: [revisión #12](#fuente-12-deepseek-v41-flash-1017-gsqxolotl) y [hardware-fit / perfiles](../../../assets/system_profiles.json). Recibo: `receipts/source-31-review.json`.


## Fuente #32: reel de Instagram DefpbUKlMxh

La consulta directa del enlace y la URL sin parámetros de seguimiento fueron limitadas por Instagram (throttling), por lo que no recuperé el video, caption ni transcripción. El análisis guardado al recibir el material lo describía como promoción de una clase gratuita sobre YouTube e IA sin afirmación técnica; no puedo verificar si el reel contiene otra afirmación.

**Resultado: bloqueada por acceso a la fuente.** No corresponde derivar un benchmark desde una nota previa no contrastable y no se identificó una prueba técnica reproducible. No se atribuye conclusión técnica al video. Reabrir si se comparte una transcripción/captura o un mirror accesible; entonces separar afirmación y buscar evidencia primaria antes de proponer una prueba.

Fuente recibida: [Instagram Reel](https://www.instagram.com/reel/DefpbUKlMxh/). Recibo: `receipts/source-32-review.json`.


## Fuente #33: calibración de IQ2_XS/Strata en DevOps

El autor informa 28 tareas sintéticas de Terraform/AWS/Cloudflare/logs/Python/sysops/mail, dos ejecuciones por configuración y grader determinístico. En el hardware de 5070 Ti + Ryzen 9 9950X3D, la calibración `--calibrate` de Strata 0.1.43 subió la mediana de decode de 118 a 143–147 tok/s y bajó el tiempo de 20,6 a 15,4–16,0 minutos; el score fue 44/56 tanto en calibrated como en el control separado, frente a 50/56 en una ejecución anterior. El autor advierte ±3/56 puntos de ruido, y atribuye la caída a casos soft, con dos repeticiones por config. Al desglosar velocidad informa +6% con `--pool-workers 8` y +7% con tier adaptativo `--adapt-every 1 --adapt-swaps 160 --adapt-decay 0.97`; no presenta calidad por cada factor aislado. Por lo tanto, el +25% de la calibración global no se adopta como expectativa ni se atribuye a un flag único.

**Prueba local preregistrada:** `VF-20261019-01-S33-ADAPT-AB`, control ASTRA IQ2_XS/Strata 0.1.41 frente al mismo perfil con sólo los tres flags adaptativos. A/B pareado sobre Hard Mode 28×3, misma cuantización, contexto 1M, KV, MTP, sampler y fixtures; alternar orden y medir calidad por caso, duración, decode, tokens, loops, RAM/VRAM y OOM. Gate de screen: ≥5% de mejora de velocidad/tiempo total, pérdida pareada máxima de una tarea y sin empeorar seguridad/inestabilidad. El resultado sólo podría ajustar rendimiento; TC-92 y TC-74 siguen impidiendo recomendar el perfil para datos sensibles. El sweep de pool-workers no se repite: el ensayo local previo en IQ3_S/Strata 0.1.35 midió menos de 3%, y no cambiaría una decisión vigente.

**Resultado final: A/B preregistrado completado en seis brazos; bundle no promovido.** Se compararon tres semillas, 28 casos cada brazo, mismo perfil/runtime/contexto/KV/MTP/sampler/fixtures y un proceso a la vez. Control: media 78,33; candidato: 82,33; cambios por seed +5/0/+7 puntos. En 84 pares: 10 victorias, 4 pérdidas y 70 empates. La reducción mediana de duración fue 0,489% (umbral ≥5%); el cambio medio fue −1,172%, es decir, el candidato resultó 1,172% más lento. El runner no reportó decode tok/s puro. TC-92 falló en el candidato con seeds 43 y 44; siguen advertencias TC-74/TC-82. OOM delta 0 y las seis corridas cerraron limpiamente. Fallan los gates de velocidad, pérdidas pareadas y seguridad; producción queda sin cambios. **Accionable P0:** corregir aislamiento de tenants antes de procesar datos entre tenants y volver a validar TC-92 en semillas independientes. No repetir este bundle ni gastar más GPU en él. Resumen íntegro: [`source-33-final-analysis.json`](receipts/source-33-final-analysis.json); recibos y resultados individuales `source33-{control,candidate}-seed-{42,43,44}.json`.

Fuentes: [post y comentarios](https://www.reddit.com/r/LocalLLM/comments/1x6so0t/qwen38_flashnext_iq2_xs_on_strata_rtx_5070_ti_16/), [runtime Strata](https://github.com/Niko1221/Strata), [model card Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next). Evidencia local: [perfil ASTRA IQ2_XS](../../../assets/system_profiles.json), [evaluación de workers](../../../docs/strata-post-evaluation-20261003.md), [Hard Mode 28×3](../Q-20261010-STRATA-QUANTS-89TASKS/RESULTS.md) y [A/B de sampling](../Q-20261014-STRATA-IQ2XXS-SAMPLING/RESULTS.md). Preregistro: [`PLAN-source-33.md`](PLAN-source-33.md). Recibo: `receipts/source-33-review.json`.

## Fuente #34: NVFP4 GPTQ frente a UD-Q4_K_XL en una RTX 5090

El post compara Qwen3.8-Flash-Next NVFP4 GPTQ con Unsloth UD-Q4_K_XL en una RTX 5090 de 32 GB, Windows y Strata 0.1.42-nvfp4.2. Informa medianas de decode de 162,9/161,3/154,1 tok/s para NVFP4 y 130,5/131,0/127,6 para UD-Q4_K_XL a 4K/32K/128K. La selección favorece al primero: el autor eligió su mejor sesión completa entre cuatro, mientras Q4 usa una sesión previa emparejada; también reconoce variación no explicada entre sesiones. En el subset de calidad de 82 preguntas, NVFP4 obtuvo 70/82 y UD-Q4_K_XL 73/82; HumanEval y GSM8K empataron, e IFEval fue 7/10 frente a 9/10. Es una sola pasada por pregunta y no mide conversaciones agentivas ni tool-use.

La diferencia de hardware es decisiva. La documentación upstream de Strata indica que RTX 50 usa Tensor Cores FP4, mientras las RTX anteriores ejecutan el formato NVFP4 por W4A8; en ese hardware Strata recomienda UD-IQ4_XS como alternativa más rápida. Los packs NVFP4 GPTQ requieren engine 0.1.44 o posterior. El host evaluado usa dos RTX 3090 SM86 y runtime Strata 0.1.41. No se encontró el pack exacto local. El volumen dedicado a modelos tenía 25,19 GB libres; el único volumen con margen tiene 140,08 GB, suficiente sólo por poco para el pack de ~128 GB y sin holgura operativa amplia.

**Resultado: sin prueba local aplicable ahora.** El supuesto beneficio de velocidad depende de la aceleración Blackwell que no tiene el host; la muestra de calidad favorece al UD-Q4 y no ofrece evidencia agentiva que justifique instalar este pack. Existe un ensayo NVFP4 local de Q-20261005-STRATA-NVFP4, pero usó OrcaRouter ModelOpt, otro checkpoint y fork/runtime; su prefill tuvo stalls y no debe mezclarse ni atribuirse al GPTQ de este post. #34 tampoco es duplicado de #19: aquel era QUASAR W4A4 con requisito Blackwell.

No se descargó, compiló ni usó GPU. Reabrir sólo si hay una decisión concreta de evaluar la calidad de este checkpoint exacto en SM86, su revisión queda fijada, existe un runtime aislado Strata 0.1.44+ y hay almacenamiento dedicado suficiente; preregistrar entonces un A/B pareado con el perfil productivo.

Fuentes: [post recibido](https://www.reddit.com/r/LocalLLM/comments/1x65lzc/strata_rtx_5090_nvfp4_vs_unsloth_udq4_k_xl/), [modelos NVFP4 en Strata](https://github.com/Niko1221/Strata/blob/main/docs/MODELS.md), [detalle técnico NVFP4](https://github.com/Niko1221/Strata/blob/main/docs/NVFP4.md), [release 0.1.44](https://github.com/Niko1221/Strata/releases). Evidencia local: [auditoría NVFP4](../../../docs/strata-nvfp4-reddit-20261005.md) y [Hard Mode comparativo](../Q-20261010-STRATA-QUANTS-89TASKS/RESULTS.md). Recibo: [source-34-review.json](receipts/source-34-review.json).

## Fuente #35: tuning de Strata multi-GPU

El post atribuye ganancias aproximadas de 10% a pool-workers, 8% a trim-stage-weights, 15% a pipeline-windows 6 y 15% a invertir el orden de dos RTX 3060. Los cambios se acumulan, no hay pares controlados ni medición de calidad. El autor menciona Qwen Flash-Next IQ3_S, distinto del perfil local ASTRA IQ2_XS en 2×RTX 3090.

La prueba oficial de Strata #1143 aceptó pipeline-windows 2 en dos RTX 2080 Ti y reportó estabilidad en conversaciones intercaladas; valores mayores se limitan a 2. La guía actual deja la opción apagada por defecto en NVIDIA, requiere servicio con MTP y layer split, y advierte del coste adicional de VRAM/cache. La tabla multi-GPU no predice el resultado de este host.

En la evidencia local, el barrido de pool-workers diferenció menos de 3%; el ajuste de PCIe ya se barrió y trim-stage-weights no tuvo dirección estable. No se repitieron esos factores. El intento S35A quedó invalidado porque la segunda petición reutilizó 4.101 tokens pese a cache_prompt=false; se conservó el recibo y no se usó ningún tiempo. El S35B preregistró prompt-cache 0 en ambos brazos y mantuvo prompts, seeds, orden, parámetros y gates originales.

**Resultado final S35B: 18/18 requests válidos, sin caché, sin errores ni OOM; el gate de rendimiento no pasa.** Medianas pareadas candidato/control: a 4K, TTFT −7,22%, latencia total −9,58%, prefill −0,01% y decode TPS −31,32%; a 32K, TTFT +1,39%, total +1,35%, prefill +1,66% y decode TPS −14,21%; a 128K, TTFT −0,34%, total −0,22%, prefill −0,12% y decode TPS −15,22%. El preregistro requería una mejora de al menos 5% en TTFT/prefill o latencia total tanto a 32K como a 128K. No se ejecuta Hard Mode de calidad. Mantener el perfil productivo en pipeline-windows 0; no repetir sin una hipótesis nueva.

Fuentes: [post recibido](https://www.reddit.com/r/LocalLLaMA/comments/1x65hq9/strata_performance_finetuning_try_it_out/), [prueba oficial de Strata #1143](https://github.com/Niko1221/Strata/issues/1143), [documentación multi-GPU](https://github.com/Niko1221/Strata/blob/main/docs/MULTI_GPU.md). Evidencia local: [sweep y revisiones previas](../../../docs/strata-post-evaluation-20261003.md), [A/B de trim](../Q-20261016-FLASHNEXT-RESUME2/RESULTS.md). Plan: [PLAN-source-35.md](PLAN-source-35.md). Recibos: [revisión](receipts/source-35-review.json), [preregistro original](receipts/source-35-prereg.json), [intento S35A](receipts/source-35-pipeline-ab.json), [preregistro S35B](receipts/source-35b-prereg.json), [resultado S35B](receipts/source-35b-pipeline-ab.json), [análisis final](receipts/source-35-final-analysis.json).

## Fuente #36: Reel de Instagram, fuente sin acceso verificable

El Reel DeehKGtuth5 no pudo abrirse en esta revisión. La URL recibida, la URL limpia, la variante /p/ y el endpoint oEmbed oficial devolvieron throttling; la búsqueda exacta del shortcode no encontró una copia atribuible. La nota previa de recepción lo describía como un flujo de pedidos de empanadas por WhatsApp y un error entre seis unidades y seis docenas, pero esa descripción sigue sin confirmación primaria.

El repositorio ya contiene assets/benchmarks/custom/one_shotting_bakery_ecommerce_v1.json, un fixture de construcción de ecommerce con checkout a WhatsApp. No cubre de forma explícita la interpretación de cantidades/unidades, sustituciones ni validación determinista de subtotal y zona de entrega. Esos casos sólo justifican un fixture separado si el Reel confirma el escenario.

**Resultado: bloqueada sin prueba aplicable verificable.** No se creó ni ejecutó un fixture de coding y no se compararon modelos a partir de una descripción sin confirmar. Reanudar cuando se aporte caption, transcripción, captura legible o mirror que permita confirmar el contenido; después decidir si el caso agrega cobertura frente al fixture existente. Recibo: [source-36-review.json](receipts/source-36-review.json).

## Fuente #37: Cloudflare Quick Tunnels

El enlace de Threads no abrió y la búsqueda exacta de su ID no encontró una copia atribuible. La nota previa de recepción lo describe como una invitación a exponer un servidor local mediante Quick Tunnels; esa atribución al post no se pudo verificar. La documentación oficial sí confirma que Quick Tunnels publican un servicio HTTP local en una URL temporal, son para desarrollo, y que quien posee la URL puede acceder salvo que se configure autenticación por correo. El túnel deja de responder al detener cloudflared.

La búsqueda de cloudflared, trycloudflare, Quick Tunnel, ngrok y localtunnel en src/, qml/, tests/ y docs/ no encontró integración. Por eso no hay conducta existente ni candidato de modelo que una prueba local pueda evaluar. No se abrió un túnel ni se ejecutó una prueba de red.

**Resultado: sin prueba local aplicable; enlace fuente no verificado.** Sólo si se incorpora en el futuro una función de publicar previews/webhooks tendría sentido probarla en un servicio descartable: acceso permitido y rechazo anónimo, rutas expuestas mínimas, apagado del túnel al cancelar y ausencia de acceso a endpoints de ejecución/código. Recibo: [source-37-review.json](receipts/source-37-review.json).

## Fuente #38: Strata 0.1.44.1 con Tesla P40 + GTX 1080

El post muestra un perfil Qwen3.8-Flash-Next ISTA IQ3_XXS a 262.144 tokens, con MTP/spec, KV int8, expertos residentes, trim, adapt-async, suffix-draft y pipeline-windows 2 sobre Tesla P40 + GTX 1080 y 48 GB de RAM. Informa decode de 30–40 a 40–60+ tok/s al pasar de Strata 0.1.42 a 0.1.44.1, pero el post no separa el efecto de la versión de los cambios de configuración ni presenta un A/B de calidad. La release oficial 0.1.44.1 confirma la versión citada, no esa atribución de rendimiento.

El host local usa dos RTX 3090, Strata 0.1.41 y ASTRA IQ2_XS. El A/B local previo del modelo IQ3_XXS frente a ASTRA en las dos RTX 3090 ya cerró sin promover el candidato: 45/51 criterios finales frente a 51/51, y la diferencia de decode fue 3,7% con rangos solapados. La solicitud de contexto largo también tiene evidencia local separada: retrieval IQ3_XXS 3/3 cerca de 255K; la configuración ASTRA 1M sigue siendo sólo capacidad configurada. El post no añade una prueba de retrieval a 262K.

**Resultado: sin prueba adicional.** No es duplicado del post #35, pero su único flag de rendimiento con hipótesis transferible, pipeline-windows 2, ya está cubierto por el A/B preregistrado allí; trim y otros ajustes no se aíslan en este post. No copiar la mezcla de flags ni extrapolar el perfil de GPUs mixtas. Recibo: [source-38-review.json](receipts/source-38-review.json).

## Fuente #39: recomendación de modelo para investigación y consejos financieros

El autor busca un LLM local de unos 30B para tareas generales, investigación con herramientas, redacción y preguntas tributarias, legales y financieras. Da como ejemplo calcular ingresos mensuales de 10 ETH en Lido CSM; el hilo muestra respuestas discrepantes y el propio autor dice que los modelos no aclararon qué representa ese capital. Los comentarios sugieren OrcaSAQ-2-Cyber-27B o Gemma 4, pero son opiniones de usuarios, no una comparación controlada.

La documentación oficial de Lido describe dos componentes de recompensa para operadores CSM: recompensa del operador y rebase del bond; el cálculo depende de la curva de bond, rendimiento del validador, tarifas y periodo. La pregunta no fija si los 10 ETH son stake del usuario o colateral de un operador, ni los datos de entrada necesarios para estimar una cifra. Un test responsable debe valorar que el modelo detecte esa ambigüedad, pida los datos que faltan y cite fuentes; no debe premiar una cifra única obtenida de una conversación de foro.

No hay fixture local dedicado a Lido, impuestos, derecho o asesoramiento financiero. **Resultado: bloqueada antes de un benchmark de modelos** hasta disponer de un set congelado y revisado por una persona experta del dominio, con supuestos, fuentes, fecha de corte y oráculo de cálculo. Si se habilita, el candidato debe fijarse por revisión/quant y evaluarse frente al modelo productivo en investigación con fuentes y cálculo reproducible; un solo caso no permite recomendar el mejor modelo general ni usarlo para asesoramiento profesional. No se descargaron candidatos ni se usó GPU.

Fuentes: [post recibido](https://www.reddit.com/r/LocalLLM/comments/1x5zc3p/whats_the_best_general_purpose_uncensored_llm_for/), [recompensas CSM de Lido](https://docs.lido.fi/staking-modules/csm/rewards/), [contabilidad y bond de operadores](https://docs.lido.fi/staking-modules/contracts/Accounting/). Recibo: [source-39-review.json](receipts/source-39-review.json).

## Fuente #40: reporte de loops con Qwen Flash-Next IQ1_M

El post describe una RX 6600M de 8 GB y un Ryzen 5 5600 con 32 GB de RAM. El autor dice que Strata no soportaba ese equipo y que usó un entorno HIP modificado para gfx1030. Con Qwen3.8-Flash-Next GSQ-RCO IQ1_M informa cerca de 20 tok/s con contexto configurado en 100K; en una tarea para encontrar errores en un tema Plymouth, el modelo habría consumido 100K tokens, compactado el contexto y consumido otros 100K sin terminar. No publica repositorio, prompt congelado, registro de requests, configuración efectiva ni control. En los comentarios hay experiencias opuestas: varias personas reportan loops, mientras otras describen tareas largas satisfactorias o loops raros. Los consejos sobre presupuesto de razonamiento o loop recovery son anecdóticos.

El caso no se transfiere al perfil productivo local: ASTRA usa Qwen3.8-Flash-Next IQ2_XS sobre CUDA y dos RTX 3090, no el IQ1_M informado ni la compilación HIP no soportada. La prueba local #7 fue una revisión distinta, ISTA-DASLab Coder IQ1_M: obtuvo 0/8 frente a 1/8 de ASTRA en BCB-Hard-8 y cinco respuestas llegaron al tope de 6.144 tokens. Eso es señal específica de aquel checkpoint y fixture, no reproducción de este relato ni del supuesto loop.

El código local ya incluye límites estrechos para dos patrones: corta tres copias exactas de un bloque de al menos 80 caracteres durante el stream, y replantea llamadas idénticas a herramientas; tests/test_agent_wire.cpp contiene pruebas para ambos casos. Esa cobertura no demuestra un límite ante razonamiento no repetitivo que se prolonga a través de compactaciones, pero la fuente tampoco reproduce tal conducta en un perfil local compatible.

**Resultado: sin prueba local nueva aplicable.** El post mezcla un modelo/quant, un runtime modificado y una sola tarea difícil, con resultados contradictorios en comentarios; no cambia una decisión local verificable. No se descargó, construyó ni usó GPU. Reabrir sólo si un setup soportado reproduce el problema con checkpoint fijado y tarea congelada; capturar opciones efectivas, tokens de razonamiento/generación, compactaciones, stop reason y un criterio de finalización verificable. No extrapolar el IQ1_M a IQ2_XS/IQ3/IQ4.

Fuente: [post y comentarios de r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1x5m9pn/got_qwen38flashnextgsqrcoiq1_m_running_on_8gb/). Evidencia local: [screen IQ1_M Coder #7](#fuente-7-qwen38-flash-next-coder-iq1_m-actualizado), tests/test_agent_wire.cpp y src/core/agent/LlamaAgentBackend.cpp. Recibo: [source-40-review.json](receipts/source-40-review.json).

## Fuente #41: posibles desventajas de Strata

El autor describe loops y problemas de puertos, y compara en cifras aproximadas Swift Q3 Next a 100 tok/s con Qwen 27B Q4 UD a 40–60 tok/s en llama.cpp. Son modelos/cuants y condiciones distintas; los comentarios tampoco aíslan si el problema proviene del quant o de optimizaciones del engine. En el mismo hilo hay experiencias opuestas sobre loops y calidad.

La discusión sí ofrece dos pistas concretas. La ficha oficial de Qwen recomienda para thinking temperatura 1, top_p 0,95, top_k 20, min_p 0, presencia 0 y repetición 1; indica que frameworks compatibles permiten ajustar presence_penalty entre 0 y 2 para reducir repetición, con posible coste de calidad o mezcla de idiomas. El PR de Strata #1274 quedó cerrado después de que el mantenedor indicara que el commit a8091f4 resolvía el problema; el preset de muestreo actualizado quedó opt-in. Un A/B comunitario ligado al PR, en Strata 0.1.41/IQ2_XS y 19 prompts cortos × 3, observó 0/57 loops en ambos brazos y aproximadamente 6% menos decode con el preset. Las tareas llegaban a un máximo de unos 6.000 tokens, así que no responde sobre sesiones largas.

ASTRA local ya fija sampling explícito: temperatura 0,6, top_p 0,95, top_k 20, min_p 0, repetition penalty 1 y presence penalty 0. El screen local Q-20261014-STRATA-IQ2XXS-SAMPLING probó temperatura 0,1/0,6/1,0 con los demás parámetros constantes; los tres brazos dieron 0/13 en TaskFlow y 0/6 en el coding smoke, con la misma repetición de 256 signos !. Eso descarta repetir el A/B de temperatura para la decisión actual, pero no prueba la hipótesis de presence_penalty. La prueba local de puerto cubre el rebind/cancelación del gateway cuando un puerto está ocupado; no reproduce una colisión del listener de Strata.

**Resultado: A/B completado; gate no pasa.** La autorización de recursos vigente reemplazó el bloqueo previo: sólo se detiene si hay inference server/API; la GUI no bloquea. Quedaron tres pares válidos bajo trace v2. Ambos brazos lograron 39/39 finales; el candidato obtuvo 32/39 en primera pasada vs control 33/39, no añadió las ≥2 aprobaciones finales requeridas y sumó 3 fallos de herramienta vs 1 control. Llamadas redundantes: 7 por brazo; el harness no expone un contador directo de repetición/stop. La mediana de duración total de suite por seed fue 324,514 s candidato vs 284,461 s control (+14,08%); es un proxy de suite, no una mediana individual por tarea, que no está disponible. El candidato excede el guard de tiempo en este proxy. La traza verificó 111/111 GEN con `penalty_present=1.0`; control tuvo 102 GEN sin override no-cero; el contexto efectivo fue 1.048.576. El control/4244 intento 01 se excluye por falso positivo Git, sin score; retry válido. Decisión: conservar `presence_penalty=0.0`, no abrir holdout ni tocar el perfil productivo. Todos los servidores propios cerraron rc0, sin listeners/inference remanentes y OOM0. Limitaciones y detalle en `receipts/source41/final-ab-close.json`.

Fuentes: [post de r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1x5cdht/real_downsides_of_strata/), [ficha oficial Qwen](https://huggingface.co/Qwen/Qwen3.8-Flash-Next), [discusión/estado del PR #1274](https://github.com/Niko1221/Strata/pull/1274). Evidencia local: [A/B de temperatura](../Q-20261014-STRATA-IQ2XXS-SAMPLING/RESULTS.md), assets/system_profiles.json, tests/test_system_profiles.cpp. Plan: [PLAN-source-41.md](PLAN-source-41.md). Recibos: [revisión](receipts/source-41-review.json), [preregistro](receipts/source-41-prereg.json).

## Fuente #42: cabeza de salida de dos niveles agrupada por prefijo

El post propone agrupar tokens por orden byte a byte de su escritura y factorizar la cabeza de salida en dos decisiones: escoger un grupo y luego un token. Informa menor KL que otros agrupamientos en cuatro de cinco modelos con pesos congelados, principalmente sobre novelas portuguesas. Para modelos chicos entrenados desde cero, el autor comenta una réplica con novelas inglesas; los swaps de cabezal en LLMs reales siguen usando el corpus portugués. No hay evaluación de coding, agente, tools ni tareas finales.

El repositorio prefix-head publica código, scripts y resultados bajo MIT. Su ruta end-to-end de CPU es un runtime mínimo para Gemma 3 270M; también incluye scripts de extracción/swap con llama.cpp y pruebas KL sobre otras arquitecturas, algunas requieren GPU NVIDIA. El README reporta 132→321 tok/s en AVX-512 y 119→256 en AVX2 para Gemma 3 270M Q8_0 sobre Ryzen 7 7700. El post da cifras de AVX2 distintas, por lo que no mezclo esos modos como una medición confirmada. El repo no demuestra integración de esta cabeza con Strata ni mide éxito de coding o uso de herramientas.

La búsqueda local no encontró prefix-head, el método de agrupación por prefijo ni Gemma 3 270M entre código, perfiles o suites. El modelo productivo que se evalúa es Qwen3.8-Flash-Next IQ2_XS en Strata sobre dos RTX 3090; la velocidad de un modelo Gemma diminuto en CPU no responde si hay un modelo mejor para ese perfil.

**Resultado: sin prueba local aplicable.** No se descargó el repositorio ni pesos, no se compiló y no se usó GPU. Si más adelante se decide evaluar un modelo CPU-first pequeño o investigación sobre cabezas de salida, primero reproducir el resultado upstream con commit, corpus y hardware fijados; después exigir un holdout downstream de coding/agente antes de proponer integración.

Fuentes: [post y comentarios](https://www.reddit.com/r/LocalLLM/comments/1x1yv01/sorting_the_vocabulary_by_spelling_makes_gemma_3/), [repositorio y README de prefix-head](https://github.com/lucasrgt/prefix-head), [archivo DOI](https://doi.org/10.5281/zenodo.23271285). Recibo: [source-42-review.json](receipts/source-42-review.json).


## Fuente #43: GLM-5.3-Flash frente a Qwen Flash-Next mediante Project Maya

El OP probó una sola actualización de features en una app y dice que GLM pensó mejor, pero que no quedó mejor que Flash-Next tras algunos reintentos. Reporta 30 tok/s de decode y 1.200 tok/s de prefill para GLM, frente a 125 y 3.000 para Qwen. No fija quant, hardware, commits, prompt, harness ni métrica de éxito. Las respuestas del hilo discrepan: algunos valoran la planificación de GLM y otros encuentran coding parecido o prefieren Qwen por tiempo total. Este post no establece qué modelo conviene para LlamaCode.

Sí hay una novedad que cambia la auditoría de factibilidad local del 14/09. Project Maya upstream publica Maya-S24 de 94,7 GB, destinada a GPUs de hasta 24 GB, y su README admite NVIDIA desde SM70; la tabla incluye una ejecución reportada con 2×RTX 3090, 128 GB de RAM, 53 tok/s y 885 tok/s de prefill sobre un prompt de 8K. Es una ruta plausible en el host 2×RTX 3090 SM86, no evidencia de que GLM sea mejor que Qwen: la cifra de 97,7% de Maya-S24 mide tareas zero-shot frente al GLM FP8, no coding agente. Maya publica API compatible con OpenAI y tool calls, y el setup compila primero, descarga sólo tras mostrar el tamaño y pedir confirmación. La cuantización pesa 94,7 GB; el pack añade alrededor de 1 GB y la visión 1,14 GB, innecesaria para este screen.

El host tiene 123 GiB de RAM, 24 GB libres en el NVMe de modelos y 131 GB libres en un segundo NVMe de trabajo; la raíz tiene 15 GB libres. El modelo no está instalado. El NVMe de trabajo puede contener los pesos, pero el build y el pack podrían consumir el margen. Por eso el gate exige después del build al menos 115 GB libres antes de descarga y conservar al menos 20 GB una vez armado el pack. El servidor reserva casi toda la RAM disponible y deja alrededor de 6 GB, así que también necesita ambos GPUs libres y cerrar cargas pesadas. No se hizo preflight de inferencia, setup, build, descarga ni benchmark mientras GPU1 está reservada al escritorio.

La búsqueda de duplicados encontró un material previo #13 que menciona GLM en la evaluación de Harness², pero mide la propuesta de ajustar componentes de harness y no compara GLM-5.3 con Qwen; por lo tanto #43 no es duplicado. La auditoría local GLM del 14/09 cubría FP8/NVFP4 sin backend compatible; Project Maya/Maya-S24 es una ruta posterior y distinta.

**Resultado: accionable, con A/B preregistrado y bloqueado por la reserva externa de GPU1 y el gate de espacio posterior a compilación.** Se usará Project Maya upstream fijado por commit, Maya-S24 con archivos/revisión y hashes registrados, sin el drafter DFlash2 y sin visión, frente al perfil productivo ASTRA Qwen3.8-Flash-Next IQ2_XS/Strata 0.1.41. El screen usa BCB-Hard-8 × 3 seeds pareadas, mismos prompts, repos limpios, harness, tools/schema, límite de contexto común de 32K, timeout y reparaciones; registra éxito final, fallos de tools/transporte, tareas, tokens y latencia. Sólo avanza a Hard Mode 28×3 si el candidato obtiene al menos dos éxitos finales adicionales de 24 y no introduce errores de tools/schema. No se modifica ni promueve el perfil productivo con el screen solo.

Fuentes: [post y comentarios](https://www.reddit.com/r/LocalLLM/comments/1x4w4vw/glm_53_flash_vs_qwen_flash_next/), [Project Maya upstream y compatibilidad/hardware](https://github.com/mw00/project-maya), [setup y requisitos](https://github.com/mw00/project-maya/blob/main/docs/SETUP.md), [cuantización y archivos Maya-S24](https://huggingface.co/peasantsmith/GLM-5.3-Flash-Maya-GGUF), [resultados Maya-S24](https://github.com/mw00/project-maya/blob/main/bench/results/MAYA-S24.md), [ficha oficial de Z.ai](https://huggingface.co/zai-org/GLM-5.3-Flash). Evidencia local: [auditoría GLM previa](../../../docs/glm53-flash-local-feasibility-audit-20260914.md), assets/system_profiles.json y ../Q-20261010-STRATA-QUANTS-89TASKS/RESULTS.md. Plan: [PLAN-source-43.md](PLAN-source-43.md). Recibo: [source-43-review.json](receipts/source-43-review.json).


## Fuente #44: GLM-5.3-Flash REAP144 Coder

El autor poda GLM-5.3-Flash de 288 a 144 expertos por capa y publica 48 intentos pareados que pasaron la evaluación propia con Q4/Q3. Su protocolo parte de 30 tareas SWE en tres repositorios Python y dos intentos por tarea; excluye cuatro tareas y cuatro intentos que alcanzaron el límite de 12 horas. El autor mismo describe diferencias pequeñas dentro del ruido. La lista pública identifica tareas, pero los scripts apuntan a rutas e imágenes privadas: el benchmark no es autocontenido.

La tarjeta upstream añade una limitación que determina la aplicabilidad: el checkpoint fue calibrado para sesiones de agente Python y se advierten errores de razonamiento y loops en otros lenguajes incluso con Q8. El autor indicaba que una calibración mixta seguía en validación. Tampoco existe comparación contra Qwen. Por eso los 48/48 no demuestran una mejora para el perfil ASTRA productivo ni para el trabajo C++/QML de este repositorio.

La búsqueda local de REAP144, GLM-5.3-Flash-REAP144 y el checkpoint podado no encontró peso, perfil, fixture ni recibo local. #43 también trata GLM-5.3, pero usa Project Maya/Maya-S24 y pregunta otra decisión; #44 es relacionado, no duplicado. GPU1 sigue reservada al escritorio.

**Resultado: sin prueba aplicable al perfil general actual.** No se descargó, compiló ni usó GPU. Reabrir sólo si se define un flujo especialista Python y se aportan tareas/repositorios representativos con un fixture reproducible. En ese caso, hacer primero un screen pareado de 5–6 tareas frente a ASTRA usando el mismo harness, límites y semillas, en un contenedor descartable sin red ni secretos; no promover el modelo general. Si aparece la revisión multilenguaje anunciada, auditarla como candidato nuevo.

Fuentes: [post y metodología](https://www.reddit.com/r/LocalLLM/comments/1x50ol2/glm53flash_pruned_to_half_the_experts_for_coding/), [repositorio upstream](https://github.com/lapadatbogdan/GLM-5.3-Flash-REAP144-Coder), [tarjeta GGUF y caveats](https://huggingface.co/lapadatbogdan/GLM-5.3-Flash-REAP144-Coder-GGUF), [lista pública de tareas](https://github.com/lapadatbogdan/GLM-5.3-Flash-REAP144-Coder/blob/main/eval/eval_tasks_py.txt). Evidencia local: AGENTS.md, README.md y búsqueda exacta bajo artifacts/docs/assets/profiles/tests/src/qml. Recibo: [source-44-review.json](receipts/source-44-review.json).


## Fuente #45: mod VR de Max Payne 2

El post elogia el mod de Max Payne 2 para VR, en particular los gatillos adaptativos y la integración de opciones de PSVR2. Los comentarios siguen hablando de mods, gráficos, controles y diseño del juego. No hay afirmación ni función de IA aplicable a los modelos o al harness de LlamaCode.

**Resultado: fuera del alcance; sin prueba aplicable.** No se creó prueba, descarga, build ni uso de GPU.

Fuente: [post y comentarios](https://www.reddit.com/r/virtualreality/comments/1x3v1lu/max_payne_2_vr_is_one_of_the_most_elaborate_mods/). Recibo: [source-45-review.json](receipts/source-45-review.json).


## Fuente #46: N+2 lookahead para streaming SSD de Flash-Next

El post reporta +8% en chat y +4,2% en coding con predicción de expertos dos capas adelante, en un Mac Mini M5 de 64 GB con streaming desde SSD. El README actual del repo describe un fork llama.cpp para Apple Silicon/Metal y dos guessers entrenados; allí la comparación contra el guess incorporado informa +12% coding y +16% chat. Son cifras del autor bajo revisiones/configuraciones distintas y dentro de un paquete de optimizaciones; no las mezclo. En un examen fijo, el README dice 18/20 tanto con la receta como con la configuración simple: no muestra mejora de calidad.

La idea es relevante a Flash-Next, pero el runtime publicado se construye con `GGML_METAL=ON`; requiere Apple Silicon y usa RAM unificada + SSD. No es una bandera portable a Strata/CUDA. Además, la auditoría local de Slotstream del 18/09 ya estudió anticipación de expertos desde SSD; la auditoría observó el mismo cuello de botella y concluyó que no había ruta NVIDIA. Las pruebas locales de caché/lazy-loading también encontraron corrupción o menor velocidad con la ruta experimental. El post/repo #46 es otro proyecto y algoritmo de guesser, no duplicado exacto, pero no justifica otra corrida en el hardware actual.

**Resultado: sin prueba local nueva aplicable.** No se clonó, compiló, descargó ni usó GPU. Reabrir sólo si existe un port CUDA/SM86 y se decide usar SSD como backing store. En ese caso, fijar commit/modelo y comparar guesser off/on con lecturas desperdiciadas y salida idéntica; después medir rendimiento a varios contextos y exigir HE0/BCB/tool-use.

Fuentes: [post de Reddit](https://www.reddit.com/r/LocalLLaMA/comments/1x4sit6/based_on_advice_from_localllama_implemented_a_n2/), [repo y README upstream](https://github.com/skeggsguy/Flash-next-ssd). Evidencia local: [auditoría de lookahead Slotstream](../../../docs/qwen38-flash-next-expert-lookahead-slotstream-audit-20260918.md), [auditoría SSD de 12 GB](../../../docs/qwen38-flash-next-12gb-ssd-audit-20260918.md), [auditoría SSD previa](../../../docs/qwen38-flash-next-ssd-offload-post-audit-20260914.md). Recibo: [source-46-review.json](receipts/source-46-review.json).


## Fuente #47: share de Threads BAlJ4iWIw4

No pude abrir el share con la herramienta web. La búsqueda exacta por ID y por ID + `KytyPS5` no devolvió copia atribuible. El inbox trae una nota preliminar que lo describe como contenido de KytyPS5/emulación/controles, pero no la trato como evidencia primaria porque no pude verificarla.

**Resultado: bloqueada por fuente no accesible; sin prueba derivable todavía.** Reabrir con transcripción, captura legible o mirror del mismo share. Si se confirma que sólo es sobre emulación de videojuegos, marcar fuera de alcance. No hubo descarga, build ni GPU.

Fuente recibida: [share de Threads](https://www.threads.com/share/BAlJ4iWIw4/). Recibo: [source-47-review.json](receipts/source-47-review.json).


## Fuente #48: share de Threads BAC2WEIiyE

El share de Threads no abrió en el lector. La búsqueda exacta del identificador junto con “Plexo” no encontró una copia atribuible. La nota preexistente del inbox lo describe como un descargador multiparte, pero no hay evidencia primaria que confirme que corresponda a este enlace.

**Resultado: bloqueada por fuente no accesible; sin prueba derivable todavía.** Reabrir con captura/transcripción legible/mirror del mismo share. Si confirma un gestor de descargas, sólo evaluar integridad por checksum, reanudación y límites si aparece una necesidad concreta en la descarga de modelos. No se clonó, descargó ni usó GPU.

Fuente recibida: [share de Threads](https://www.threads.com/share/BAC2WEIiyE/). Recibo: [source-48-review.json](receipts/source-48-review.json).


## Fuente #49: Baidu Unlimited-OCR para PDFs escaneados

El share de Threads no abrió en la herramienta, así que la atribución a este candidato queda sin verificar. Sí revisé directamente el repo oficial de Baidu y su tarjeta de Hugging Face: Unlimited-OCR es 3B BF16, MIT, y publica inferencia NVIDIA por Transformers/SGLang/vLLM más un flujo PDF por rasterización y `infer_multi`. El candidato es OCR documental; no hay evidencia para sustituir el modelo general de coding.

La oportunidad local es concreta. `DocumentExtractor` envía PDFs a MarkItDown y devuelve error cuando no extrae texto (“¿PDF escaneado? requeriría OCR”). Data Lab marca ese documento fallido y no manda páginas como imágenes. El OCR de escritorio (Windows/Tesseract) no cubre este pipeline. Hay pruebas de extensión y texto, pero no de OCR de PDF. La issue #84 publica dos fallos reproducibles en un entorno específico (una secuencia ST.25 convertida a tabla gigante y un loop numérico que termina por longitud); la issue #27 describe otros problemas, pero indica que parte se corrigió. No se extrapolan esos resultados sin repetirlos en la revisión/runtime fijados.

La revisión actual de `infer.py` conserva un bind `0.0.0.0` y un `mkdtemp` sin limpieza visible. El preregistro prohíbe usar el script upstream tal cual: cualquier servidor será loopback, las páginas serán sintéticas y temporales se gestionarán con limpieza verificada.

**Resultado: screen especializado completado; el holdout sintético P4 pasa 6/6 con el parser preregistrado.** La salida parseada obtuvo CER limpio0 y degradado0,00758; formulario6/6; tabla24/24; dos columnas8/8 en orden; listado 0101–0108 una vez/en orden, páginas B-11→B-12 y marcador final. En el mismo set, Tesseract 5.3.4 igualó texto, formularios y listado, pero obtuvo tabla0/24 y falló el orden de columnas. El valor incremental observado queda limitado a tablas y orden espacial sintéticos. El output raw estructurado falla como texto plano y necesita el parser; P2 raw no se redefine como pase. **Decisión: conservar el checkpoint y venv aislados para sólo un futuro screen de integración opt-in en Data Lab; no cambiar ni promover la app/modelo.** El share BATVtOlrkc sigue sin verificar, y el holdout no prueba documentos reales ni readiness jurídica. No se retiró ningún modelo en este paso; ASTRA/SOL y PeritoSoft siguen protegidos.

Fuentes: [repo oficial y guía de inferencia](https://github.com/baidu/Unlimited-OCR), [script `infer.py`](https://github.com/baidu/Unlimited-OCR/blob/main/infer.py), [tarjeta del modelo](https://huggingface.co/baidu/Unlimited-OCR), [issue #84 (casos ST.25 y loop)](https://github.com/baidu/Unlimited-OCR/issues/84), [issue #27 y actualizaciones](https://github.com/baidu/Unlimited-OCR/issues/27), [issue #78 sobre flujo PDF](https://github.com/baidu/Unlimited-OCR/issues/78). Evidencia local: `src/core/DocumentExtractor.cpp`, `src/core/data/DataLab.cpp`, `tests/test_document_extractor.cpp`. Plan: [PLAN-source-49.md](PLAN-source-49.md). Recibos: [source-49-review.json](receipts/source-49-review.json), [source-49-p4-final-result.json](receipts/source-49-p4-final-result.json), [google-sheet-s49-update.json](receipts/google-sheet-s49-update.json).


## Fuente #50: whatmodel.sh, ranking y estimación de hardware

El post anuncia un score agregado con 19.731 resultados. El README upstream consultado el 20/10 muestra 22.192 resultados, 880 modelos y 574 benchmarks, actualizado el 16/10: la base es viva y cambia. El proyecto describe un modelo latente de un factor ajustado dentro de conjuntos con benchmarks compartidos; avisa que la RAM se estima y que puede faltar memoria para el contexto completo. En el mismo hilo, el autor confirma que los scores son mayormente de precisión completa, que el cálculo de RAM usa un contexto modesto y que la compatibilidad de Strata todavía estaba en revisión. También hay reportes comunitarios de candidatos Qwen/Strata que el filtro no clasificó igual.

El índice puede ayudar a descubrir qué probar. No es un resultado comparable con las suites locales de coding/agente ni confirma un quant, backend, perfil o memoria real. El Qwen3.8-Flash-Next productivo ya tiene resultados locales directos (Hard Mode 28×3 y pruebas de contexto separadas); sus métricas usan otra escala y no se deben mezclar con el score compuesto. #24 es otro índice compuesto, relacionado pero no duplicado.

**Resultado: sin prueba local nueva.** Mantener whatmodel como shortlist/filtro preliminar. Sólo ejecutar una prueba si aparece un candidato exacto y novedoso; luego fijar quant, runtime, contexto, hardware y harness, verificar memoria real y comparar pass rate/tiempo total. No se corrió el script de benchmark ni se usó GPU.

Fuentes: [post y comentarios](https://www.reddit.com/r/LocalLLaMA/comments/1x3wp8c/i_made_an_opensource_ai_leaderboard_that_shows/), [repo y README](https://github.com/jakemanger/whatmodel), [metodología](https://github.com/jakemanger/whatmodel/blob/main/pages/method.md), [protocolo de benchmark](https://github.com/jakemanger/whatmodel/blob/main/BENCHMARKING.md). Evidencia local: [registro y resultados directos](../../../docs/evaluacion-modelos-llamacode.md), [Hard Mode Qwen/Strata](../Q-20261009-STRATA-QWEN38-27B-AB/RESULTS.md). Recibo: [source-50-review.json](receipts/source-50-review.json).


## Fuente #51: Swift 1.5 Qwen3.8-27B frente al ASTRA productivo

**Resultado:** candidato local accionable, con comparación preregistrada; todavía no evaluado por reserva de GPU1 y acceso/modelo pendientes. El artículo Hashnode que enlaza Reddit devuelve 403. El hilo reporta un único problema de predicción con ruido y una mejora de tiempo con Swift, sin evidencia directa de coding. La ficha primaria de UkisAI sí justifica un screen independiente: en su protocolo BF16 de cinco seeds, Swift sube LiveCodeBench v6 de 76,76% a 81,71% y Terminal-Bench 2.1 de 69,21% a 72,13%; el fabricante publica logs crudos. Es una señal de candidato, no evidencia local ni comparativa de quants.

La cuantización oficial Swift GSQ-RCO IQ2_XS es del mismo nivel nominal que ASTRA IQ2_XS y publica un manifiesto de pesos; el paquete con MTP requiere compatibilidad del runtime que debe verificarse. Se preregistró una comparación de perfiles con Strata 0.1.41 y el harness local. Primero HE20 + BCB8; si supera el umbral de screen, Hard Mode 28×3 con los mismos seeds y configuración. Las métricas incluyen calidad primera pasada/final, schema/tools, tokens, reparaciones y tiempo. Para reemplazo general exigimos +3 pp, ganar al menos 2/3 seeds, ≤2× tiempo y TC-92 3/3 sin filtraciones; de lo contrario no se recomienda para tareas con permisos ni datos sensibles.

No hay test de contexto en esta fuente: los consejos de comentarios sobre bajar a 32K/KV no están validados; el pedido de ampliar ventana está cubierto por #57. No hubo descarga, build, inferencia ni uso de GPU. Plan `PLAN-source-51.md`; recibos `receipts/source-51-review.json` y `receipts/source-51-prereg.json`.


## Fuente #52: Qwen Flash-Next IQ3_XXS a 262K en una RTX 5090 Mobile

El post informa 262K configurados en una RTX 5090 Mobile/24GB con Strata, 64GB RAM y 2500–3000 tok/s de prefill. El model card oficial confirma 262.144 tokens nativos para Qwen3.8-Flash-Next (con extensión hasta 1M) y la ficha ISTA publica el quant IQ3_XXS. El reporte comunitario de velocidad no es comparable con el host local ni confirma recuperación correcta por sí solo.

La pregunta local ya quedó cubierta por el screen existente `receipts/iq3xxs-context262k-multifact.json`: tres prompts de 255.005 tokens API, facts posicionados en distintas zonas, 3/3 exactos por corrida (9/9 campos), HTTP 200 y `finish_reason=stop`. El prefill local fue 3365,9–3481,8 tok/s y decode 104,1–112,4 tok/s. Esto valida recuperación sintética para este quant/runtime cerca del contexto nativo; no prueba calidad coding, 1M ni desempeño en una RTX 5090. Se reutiliza el recibo sin repetir GPU.

Los comentarios sugieren `--draft-vocab en` y chunk 8K/16K, pero no aíslan esos factores ni el idioma del workload. El A/B local de chunk 32768 ya mostró menor decode y mayor TTFT en una sola sonda; no se justifica otro sweep ahora. Si aparece un cuello de botella local de prefill con una mezcla de idiomas medida, se puede preregistrar ese ajuste como una pregunta separada. No se cambia contexto ni configuración. Recibo `receipts/source-52-review.json`.


## Fuente #53: ¿Flash-Next Q2 supera Qwen3.8-27B Q4?

El hilo es una pregunta abierta; las respuestas cambian según si hablan de empezar un proyecto, extender código existente, rapidez o robustez agentiva. No fija checkpoints/quant exactos, runtime, prompts, seeds ni un harness común. La ficha primaria de ISTA distingue claramente Q2_0, IQ2_XS e IQ3_XXS y reporta para Q2_0 81,14 en LiveCodeBench v6 frente a 87,43 para el BF16 base, además de mayor velocidad en su protocolo llama.cpp; esa métrica no sustituye una prueba local de agente ni lo compara con 27B Q4.

La prueba local exacta de Q2_0 ya obtuvo 1/8 en BCB-Hard-8 y repitió 1/8 con sampling conservador/thinking apagado. Eso no justifica promoverlo. Existe también un resultado 8/8 para `UD-Q2_K_XL`, pero usa otro formato, runtime y configuración; no se transfiere al Q2_0. No repetí esos casos ni corrí GPU.

**Resultado: sin prueba nueva aplicable ahora.** Si queda una decisión concreta entre artefactos disponibles, el siguiente paso sería un screen apareado con hashes y harness idénticos, reportando calidad final, tools/schema, reparaciones y tiempo hasta aceptación; usar holdout nuevo si los fixtures históricos se solapan. Fuentes: [hilo y comentarios](https://www.reddit.com/r/LocalLLaMA/comments/1wpgyfh/is_qwen_flash_next_at_like_q2_better_than_27b_at/), [ficha ISTA GSQ-RCO](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF), [ficha Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B). Evidencia local: `docs/strata-qwen38-evaluation-20260930.md`, `artifacts/qwen38-q2-vs-sol-20260923.json`. Recibo: [source-53-review.json](receipts/source-53-review.json).


## Fuente #54: OpenJet megakernel para Qwen3.8-27B Q4_K_M

El post actualizado reporta en una RTX 3090 107 tok/s greedy / 78 tok/s en thinking, frente a 63 / 51 de llama.cpp, y 1.530–1.600 frente a 1.050–1.140 tok/s en prefill. El acuerdo de top token/KL se midió a varias longitudes, aunque 30K y 96K usan una sola secuencia; el autor dice que no tiene todavía una medición de pass rate en tareas. La documentación actual restringe el motor megakernel a Qwen3.8-27B Q4_K_M y UD-Q4_K_XL en una sola RTX 30/40/50 compatible. El rendimiento publicado corresponde al Q4_K_M. La API cubre streaming y tool_calls, con limitaciones relevantes: penalties de repetición/presencia ignorados, top_k hasta 32, cambio a KV q8_0 al superar el ajuste fp16 de memoria (~80K en 24GB), sin save/restore de slot y reproceso del historial modificado. El subproyecto megakernel declara AGPL-3.0.

El GGUF Q4_K_M está disponible localmente, pero la fuente sólo sustenta velocidad del runtime. La matriz histórica local tiene un BCB-Hard parcial para Q4_K_M; el screening Linux posterior falló HE0 por extracción y su 0/8 es diagnóstico, no promocionable. En la comparación reciente de perfiles, Qwen3.8-27B AutoRound INT4/vLLM quedó en 66,07/100 frente a 77,98/100 del ASTRA IQ2_XS/Strata; no son el mismo quant ni runtime, así que lo tomo sólo como contexto. El ASTRA actual tiene además un límite de contexto configurado mayor. La cifra de OpenJet no cambia la elección productiva: compara otra ejecución, mide velocidad y no calidad por tarea.

**Resultado: sin prueba nueva aplicable a la decisión vigente.** No instalé ni compilé OpenJet. Si se abre una decisión de usar específicamente Qwen 27B Q4_K_M en una sola 3090 por razones operativas, primero conviene un A/B de servicio sobre el mismo GGUF (commit OpenJet fijado `72ba4a7e587ed0cda1312e3384e415962eaa0db3` contra llama.cpp, mismas solicitudes/categorías), y sólo después una suite de coding/tools. El aviso AGPL-3.0 debe revisarse antes de integrar o distribuir. Fuentes: [post actualizado](https://www.reddit.com/r/LocalLLaMA/comments/1x37q7b/update_qwen_38_27b_140_toks_on_single_rtx_3090/), [documentación runtime](https://github.com/L-Forster/open-jet/blob/master/docs/runtimes/llama-cpp.md), [licencia del megakernel](https://raw.githubusercontent.com/L-Forster/open-jet/master/megakernel/LICENSE). Evidencia local: `docs/benchmark-final-table.md`, `docs/benchmark-profile-matrix.md`, `docs/evaluacion-modelos-llamacode.md` y `assets/system_profiles.json`. Recibo: [source-54-review.json](receipts/source-54-review.json).


## Fuente #55: IQ3_XXS configurado a 700K en una RTX 5090

El enlace corto se resolvió a la publicación de `1x35kdg`; un primer fetch devolvió un destino discordante, por lo que confirmé el redirect con la URL original y una búsqueda exacta. El autor informa 700K configurados con IQ3_XXS/Strata en RTX 5090 32GB + 64GB RAM, pero Qwen Code mostraba cerca de 512K tokens utilizados al terminar. No hubo compaction, aunque tampoco un holdout de retrieval ni medición de calidad a 700K; 1M es explícitamente una estimación. La tarjeta Qwen declara 262.144 nativos y extensión hasta 1M mediante YaRN; la ficha ISTA trata IQ3_XXS como un quant separado.

La prueba local existente de IQ3_XXS cubre 255.005 tokens API y 9/9 hechos a contexto nativo. El test local de hasta 1M fue IQ2_XS y no se transfiere a IQ3_XXS. Por eso preregistré un test nuevo, específico y acotado: tres prompts sintéticos de ~680K efectivos bajo `max_context=700000`, YaRN ×4 desde 262.144, cinco hechos por corrida (15/15 total), distractores/contradicciones/posiciones distribuidas, KV q8_0 y tres réplicas. El resultado medirá capacidad y retrieval sintético de esa combinación; no coding general ni calidad en 1M.

**Resultado: el contexto 700K funciona para recuperación sintética en IQ3_XXS/Strata, sin promoción general.** El proceso confirmó YaRN ×4 desde 262.144, `--max-context 700000` y `--kv int8`. Tres requests seriales usaron 680.006 / 680.009 / 679.974 tokens API y recuperaron los 15 valores exactos; sin embargo, la tercera respuesta los envolvió en una cerca Markdown `json`, por lo que sólo 2/3 respuestas fueron JSON crudo y el gate preregistrado estricto no pasa. MemAvailable mínima 58,52 GiB, OOM 0; el servidor terminó con código 0 y puerto/procesos limpios. Esto demuestra capacidad técnica/retrieval sintético cerca de 680K para esta combinación; no prueba coding/generalidad/producción ni 1M y no justifica aumentar globalmente todos los perfiles. Plan y recibos: [PLAN-source-55.md](PLAN-source-55.md), [source-55-retrieval700k.json](receipts/source-55-retrieval700k.json), [source-55-posthoc-audit.json](receipts/source-55-posthoc-audit.json), [source-55-fixture-prep.json](receipts/source-55-fixture-prep.json), [source-55-model-fingerprints.json](receipts/source-55-model-fingerprints.json). Fuentes: [post de 700K](https://www.reddit.com/r/LocalLLM/comments/1x35kdg/rtx_5090_32gb_64gb_ram_qwen38_flashnext_iq3_xxs/), [model card Qwen](https://huggingface.co/Qwen/Qwen3.8-Flash-Next), [tarjeta ISTA IQ3_XXS](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF).


## Fuente #56: comparación IQ3_XXS, IQ3_S e UD-IQ4_XS

El autor reporta Strata 0.1.40 en RTX 5090/128GB con recetas distintas por quant. La muestra MMLU-Pro empató en 12/14, los tres fallaron el conteo de 130 frases, y la aguja exacta pasó cerca de 125.703 tokens en IQ3_XXS/IQ3_S/UD-IQ4_XS y de 248.346 en IQ3_S/UD-IQ4_XS. Son comprobaciones pequeñas, a una posición de profundidad, no coding/agente; el autor difirió HumanEval y generación sostenida a 240K. Las cifras de velocidad tampoco se trasladan a RTX 3090.

En LlamaCode, IQ3_XXS frente a ASTRA IQ3_S ya fue comparado en HE20/BCB8 y tareas complementarias: IQ3_XXS cerró 24/28 del gate frente a 28/28 y 45/51 frente a 51/51 en la suma descriptiva. No repetir. Para UD-IQ4_XS, la campaña reciente logró HE20 20/20, pero BCB8 tuvo dos timeouts sin score y ADV/TaskFlow quedaron incompletas; tampoco repetir esa huella. La prueba local de contexto UD-IQ4_XS con 7/7 hechos a 117.825 tokens no llega al rango de 248K del post.

**Estado actualizado: S56 cerrado sin score tras cuatro intentos fallidos antes de una respuesta válida.** El holdout preregistrado usa 3 prompts de 247–249K, contexto nativo 262.144, cinco hechos distribuidos por prompt (15/15), `--kv int8`, sin YaRN. Los intentos 01/02 no enviaron solicitudes; el intento 03 sí confirmó API/contexto/flags y envió el prompt de 247.474 tokens, pero el lector SSE del harness falló a los 5 s antes de recibir contenido. No hay respuesta/score; el motor reportó 0 tokens al cerrarse, sin OOM y con swap estable. Preregistré un último intento 04: socket de lectura con límite de 1.200 s y watchdog separado cada 5 s para no perder los guards de memoria. Antes de GPU, se valida con un stream SSE local retrasado 6 s; después se permite un arranque final y hasta tres requests seriales. El intento 04 terminó tras ~545 s sin llegar a READY (runner exit 143); no envió requests ni generó score. Strata quedó en espera de I/O de disco; cerré sólo el grupo de procesos de esta prueba, y la GPU quedó sin procesos de cómputo. No se repetirán arranques. Recibo: [source-56-attempt04-run-exit.json](receipts/source-56-attempt04-run-exit.json). Plan y recibos: [PLAN-source-56.md](PLAN-source-56.md), [source-56-review.json](receipts/source-56-review.json), [intento 01](receipts/source-56-retrieval262k.json), [auditoría 01](receipts/source-56-attempt01-startup-audit.json), [intento 02](receipts/source-56-retrieval262k-attempt02.json), [auditoría 02](receipts/source-56-attempt02-startup-audit.json), [intento 03](receipts/source-56-retrieval262k-attempt03.json), [preregistro de intento 04](receipts/source-56-attempt04-preregistration.json). Fuentes: [hilo de comparación](https://www.reddit.com/r/LocalLLM/comments/1x2wijv/qwen38flashnext_on_an_rtx_5090_128gb_ram_iq3_xxs/), [modelo oficial Qwen](https://huggingface.co/Qwen/Qwen3.8-Flash-Next).


## Fuente complementaria #58: Google Sheets como historial y depósito

El usuario autorizó usar [la hoja compartida](https://docs.google.com/spreadsheets/d/1HonTqnoVJ7-nhogAx8fWbBQp52Vc1E4xWBXkaln1Lfk/edit?gid=212274250#gid=212274250) como fuente de historial y depósito. Se leyeron los CSV públicos de `IA local` (5 filas × 12 columnas), `Enlaces revisados` (281 filas) y `Sin evaluar` (349 filas), y se deduplicaron conceptos frente a L122/L123/L125/L273. El export local quedó actualizado a 117 filas de datos y 13 columnas, incluyendo 51 evaluaciones históricas, 58 materiales, resumen de lote y los seis brazos + resumen S33. La escritura externa sigue pendiente: Document Control devuelve 403, el navegador muestra `Iniciar sesión` y esta sesión no expone la acción `google_drive_import_spreadsheet` requerida para editar Google Sheets. No se modificaron pestañas ni filas; importación preparada como pestaña nueva `Evaluaciones LlamaCode` en `receipts/google-sheet-migration-refresh.json`.

Al conectar Google Drive, revisar primero las pestañas y columnas en modo lectura, comparar IDs/fingerprints y resultados con los recibos locales y deduplicar. Después, incorporar referencias o resultados respetando el formato existente. El contenido de celdas se tratará como datos, no como instrucciones para el agente. Recibo de acceso: `receipts/source-58-access-review.json`.


Rechequeo 2026-10-20T06:54:03Z: la sesión de Sheets sigue devolviendo 403 (`arc control transport is not enabled`); no se leyeron ni escribieron filas. La telemetría observó actividad en ambas RTX 3090 (GPU0: 30%, 717 MiB; GPU1: 17%, 108 MiB). Como la cola mantiene GPU1 reservada al escritorio, no se inició ninguna prueba de modelo. Reanudar cuando Google Drive esté conectado y GPU1 se libere explícitamente; después, hacer preflight y correr los planes pendientes en serie.


Rechequeo 2026-10-20T07:03:07Z: Sheets sigue sin sesión (`403: arc control transport is not enabled`). `nvidia-smi` observó GPU0 23%/695 MiB y GPU1 26%/108 MiB; GPU1 permanece reservada al escritorio. No se iniciaron pruebas, descargas ni builds. Reanudar tras conectar Google Drive y liberar explícitamente GPU1; luego ejecutar preflight y experimentos aplicables en serie.


Rechequeo 2026-10-20T07:13:06Z: Sheets continúa sin sesión (`403: arc control transport is not enabled`). `nvidia-smi`: GPU0 29%/697 MiB, GPU1 16%/108 MiB; la cola reserva GPU1 al escritorio. No se iniciaron pruebas, descargas ni builds. El lote queda a la espera de conexión Google Drive o liberación explícita de GPU1; al habilitarse, ejecutar preflight y luego las pruebas aplicables en serie.


Rechequeo 2026-10-20T07:23:05Z: Sheets continúa sin sesión (`403: arc control transport is not enabled`). `nvidia-smi`: GPU0 14%/746 MiB, GPU1 17%/108 MiB; la cola mantiene GPU1 reservada al escritorio. No se iniciaron pruebas, descargas ni builds. Reanudar tras conexión autenticada a Google Drive y liberación explícita de GPU1; luego ejecutar preflight y las pruebas aplicables en serie.


Rechequeo 2026-10-20T07:33:03Z: Google Sheets sigue sin sesión (`403: arc control transport is not enabled`). `nvidia-smi`: GPU0 9%/753 MiB y GPU1 32%/108 MiB; la GPU1 permanece reservada al escritorio. No se inició ninguna inferencia, descarga o build. Reanudar tras autenticación Google Drive y liberación explícita de GPU1; después ejecutar preflight y pruebas en serie.


Rechequeo 2026-10-20T07:43:05Z: Google Sheets sigue en 403 (`arc control transport is not enabled`). `nvidia-smi`: GPU0 30%/706 MiB, GPU1 52%/108 MiB; GPU1 permanece reservada al escritorio. No se iniciaron pruebas ni descargas/builds. Reanudar tras conexión autenticada a Drive y liberación explícita de GPU1; ejecutar preflight y pruebas aplicables en serie.


Rechequeo 2026-10-20T07:53:02Z: Sheets continúa en 403 (`arc control transport is not enabled`). `nvidia-smi`: GPU0 8%/704 MiB, GPU1 86%/108 MiB; la cola mantiene GPU1 reservada al escritorio. No se iniciaron pruebas, descargas ni builds. Reanudar tras conexión autenticada a Drive y liberación explícita de GPU1, con preflight y pruebas en serie.


Rechequeo 2026-10-20T08:03:01Z: Sheets continúa en 403 (`arc control transport is not enabled`). `nvidia-smi`: GPU0 15%/749 MiB, GPU1 41%/108 MiB; la reserva de escritorio para GPU1 sigue vigente. No se iniciaron pruebas, descargas o builds. Reanudar con Google Drive autenticado y GPU1 explícitamente libre; ejecutar preflight y pruebas en serie.


Rechequeo 2026-10-20T08:13:05Z: Sheets continúa en 403 (`arc control transport is not enabled`). `nvidia-smi`: GPU0 30%/706 MiB, GPU1 22%/108 MiB; WORK_QUEUE conserva la reserva de GPU1 para escritorio, por lo que no inicié pruebas. Reanudar cuando Drive esté autenticado y GPU1 se libere explícitamente; ejecutar preflight y experimentos en serie.


Rechequeo 2026-10-20T08:23:02Z: Google Sheets continúa en 403 (`arc control transport is not enabled`). `nvidia-smi`: GPU0 23%/699 MiB, GPU1 28%/108 MiB; la reserva de GPU1 sigue vigente. No se iniciaron pruebas, descargas ni builds. Reanudar tras conectar Google Drive y liberar GPU1 explícitamente; luego hacer preflight y pruebas secuenciales.

Rechequeo 2026-10-20T08:33:51Z: Sheets sigue devolviendo `403: arc control transport is not enabled` (0 filas leídas/escrituras). `nvidia-smi`: GPU0 12%/741 MiB y GPU1 28%/108 MiB; WORK_QUEUE mantiene GPU1 reservada al escritorio. No se inició inferencia, benchmark, descarga ni build. Reanudar tras conexión autenticada de Drive y liberación explícita de GPU1; luego preflight y pruebas habilitadas en serie.

Rechequeo 2026-10-20T08:43:27Z: Sheets sigue devolviendo `403: arc control transport is not enabled` (0 filas leídas/escrituras). `nvidia-smi`: GPU0 11%/706 MiB y GPU1 16%/108 MiB; WORK_QUEUE mantiene GPU1 reservada al escritorio. No se inició inferencia, benchmark, descarga ni build. Reanudar tras conexión autenticada de Drive y liberación explícita de GPU1; luego preflight y pruebas habilitadas en serie.

Rechequeo 2026-10-20T08:53:28Z: Sheets sigue devolviendo `403: arc control transport is not enabled` (0 filas leídas/escrituras). `nvidia-smi`: GPU0 0%/688 MiB y GPU1 48%/108 MiB; WORK_QUEUE mantiene GPU1 reservada al escritorio. No se inició inferencia, benchmark, descarga ni build. Reanudar tras conexión autenticada de Drive y liberación explícita de GPU1; luego preflight y pruebas habilitadas en serie.

Rechequeo 2026-10-20T09:03:26Z: Sheets sigue devolviendo `403: arc control transport is not enabled` (0 filas leídas/escrituras). `nvidia-smi`: GPU0 30%/742 MiB y GPU1 11%/108 MiB; WORK_QUEUE mantiene GPU1 reservada al escritorio. No se inició inferencia, benchmark, descarga ni build. Reanudar tras conexión autenticada de Drive y liberación explícita de GPU1; luego preflight y pruebas habilitadas en serie.

Rechequeo 2026-10-20T09:13:25Z: Sheets sigue devolviendo `403: arc control transport is not enabled` (0 filas leídas/escrituras). `nvidia-smi`: GPU0 10%/658 MiB y GPU1 17%/108 MiB; WORK_QUEUE mantiene GPU1 reservada al escritorio. No se inició inferencia, benchmark, descarga ni build. Reanudar tras conexión autenticada de Drive y liberación explícita de GPU1; luego preflight y pruebas habilitadas en serie.

Rechequeo 2026-10-20T09:23:25Z: Sheets sigue devolviendo `403: arc control transport is not enabled` (0 filas leídas/escrituras). `nvidia-smi`: GPU0 28%/722 MiB y GPU1 17%/108 MiB; WORK_QUEUE mantiene GPU1 reservada al escritorio. No se inició inferencia, benchmark, descarga ni build. Reanudar tras conexión autenticada de Drive y liberación explícita de GPU1; luego preflight y pruebas habilitadas en serie.

Rechequeo 2026-10-20T09:33:27Z: Sheets sigue devolviendo `403: arc control transport is not enabled` (0 filas leídas/escrituras). `nvidia-smi`: GPU0 19%/669 MiB y GPU1 19%/108 MiB; WORK_QUEUE mantiene GPU1 reservada al escritorio. No se inició inferencia, benchmark, descarga ni build. Reanudar tras conexión autenticada de Drive y liberación explícita de GPU1; luego preflight y pruebas habilitadas en serie.

Rechequeo 2026-10-20T09:43:25Z: Sheets sigue devolviendo `403: arc control transport is not enabled` (0 filas leídas/escrituras). `nvidia-smi`: GPU0 28%/715 MiB y GPU1 17%/108 MiB; WORK_QUEUE mantiene GPU1 reservada al escritorio. No se inició inferencia, benchmark, descarga ni build. Reanudar tras conexión autenticada de Drive y liberación explícita de GPU1; luego preflight y pruebas habilitadas en serie.

Rechequeo 2026-10-20T09:53:26Z: Sheets sigue devolviendo `403: arc control transport is not enabled` (0 filas leídas/escrituras). `nvidia-smi`: GPU0 30%/676 MiB y GPU1 18%/108 MiB; WORK_QUEUE mantiene GPU1 reservada al escritorio. No se inició inferencia, benchmark, descarga ni build. Reanudar tras conexión autenticada de Drive y liberación explícita de GPU1; luego preflight y pruebas habilitadas en serie.

Rechequeo 2026-10-20T10:03:27Z: Sheets sigue devolviendo `403: arc control transport is not enabled` (0 filas leídas/escrituras). `nvidia-smi`: GPU0 9%/716 MiB y GPU1 27%/108 MiB; WORK_QUEUE mantiene GPU1 reservada al escritorio. No se inició inferencia, benchmark, descarga ni build. Reanudar tras conexión autenticada de Drive y liberación explícita de GPU1; luego preflight y pruebas habilitadas en serie.

Rechequeo 2026-10-20T10:13:25Z: Sheets sigue devolviendo `403: arc control transport is not enabled` (0 filas leídas/escrituras). `nvidia-smi`: GPU0 30%/674 MiB y GPU1 17%/108 MiB; WORK_QUEUE mantiene GPU1 reservada al escritorio. No se inició inferencia, benchmark, descarga ni build. Reanudar tras conexión autenticada de Drive y liberación explícita de GPU1; luego preflight y pruebas habilitadas en serie.

Rechequeo 2026-10-20T10:23:45Z: Sheets sigue devolviendo `403: arc control transport is not enabled` (0 filas leídas/escrituras). `nvidia-smi`: GPU0 59%/717 MiB y GPU1 17%/108 MiB; WORK_QUEUE mantiene GPU1 reservada al escritorio. No se inició inferencia, benchmark, descarga ni build. Reanudar tras conexión autenticada de Drive y liberación explícita de GPU1; luego preflight y pruebas habilitadas en serie.

Rechequeo 2026-10-20T10:33:25Z: Sheets sigue devolviendo `403: arc control transport is not enabled` (0 filas leídas/escrituras). `nvidia-smi`: GPU0 9%/715 MiB y GPU1 26%/108 MiB; WORK_QUEUE mantiene GPU1 reservada al escritorio. No se inició inferencia, benchmark, descarga ni build. Reanudar tras conexión autenticada de Drive y liberación explícita de GPU1; luego preflight y pruebas habilitadas en serie.

Rechequeo 2026-10-20T10:43:25Z: Sheets sigue devolviendo `403: arc control transport is not enabled` (0 filas leídas/escrituras). `nvidia-smi`: GPU0 14%/676 MiB y GPU1 20%/108 MiB; WORK_QUEUE mantiene GPU1 reservada al escritorio. No se inició inferencia, benchmark, descarga ni build. Reanudar tras conexión autenticada de Drive y liberación explícita de GPU1; luego preflight y pruebas habilitadas en serie.

Rechequeo 2026-10-20T10:53:26Z: Sheets sigue devolviendo `403: arc control transport is not enabled` (0 filas leídas/escrituras). `nvidia-smi`: GPU0 18%/714 MiB y GPU1 28%/108 MiB; WORK_QUEUE mantiene GPU1 reservada al escritorio. No se inició inferencia, benchmark, descarga ni build. Reanudar tras conexión autenticada de Drive y liberación explícita de GPU1; luego preflight y pruebas habilitadas en serie.

Rechequeo 2026-10-20T11:03:25Z: Sheets sigue devolviendo `403: arc control transport is not enabled` (0 filas leídas/escrituras). `nvidia-smi`: GPU0 0%/665 MiB y GPU1 0%/108 MiB; WORK_QUEUE mantiene GPU1 reservada al escritorio pese a su uso observado en 0%. No se inició inferencia, benchmark, descarga ni build. Reanudar tras conexión autenticada de Drive y liberación explícita de GPU1; luego preflight y pruebas habilitadas en serie.

Rechequeo 2026-10-20T11:13:24Z: Sheets sigue devolviendo `403: arc control transport is not enabled` (0 filas leídas/escrituras). `nvidia-smi`: GPU0 16%/709 MiB y GPU1 18%/108 MiB; WORK_QUEUE mantiene GPU1 reservada al escritorio. No se inició inferencia, benchmark, descarga ni build. Reanudar tras conexión autenticada de Drive y liberación explícita de GPU1; luego preflight y pruebas habilitadas en serie.

Rechequeo 2026-10-20T11:23:24Z: Sheets sigue devolviendo `403: arc control transport is not enabled` (0 filas leídas/escrituras). `nvidia-smi`: GPU0 11%/660 MiB y GPU1 22%/108 MiB; WORK_QUEUE mantiene GPU1 reservada al escritorio. No se inició inferencia, benchmark, descarga ni build. Reanudar tras conexión autenticada de Drive y liberación explícita de GPU1; luego preflight y pruebas habilitadas en serie.

Rechequeo 2026-10-20T11:33:25Z: Sheets sigue devolviendo `403: arc control transport is not enabled` (0 filas leídas/escrituras). `nvidia-smi`: GPU0 6%/703 MiB y GPU1 32%/108 MiB; WORK_QUEUE mantiene GPU1 reservada al escritorio. No se inició inferencia, benchmark, descarga ni build. Reanudar tras conexión autenticada de Drive y liberación explícita de GPU1; luego preflight y pruebas habilitadas en serie.

Rechequeo 2026-10-20T11:43:24Z: Sheets sigue devolviendo `403: arc control transport is not enabled` (0 filas leídas/escrituras). `nvidia-smi`: GPU0 10%/658 MiB y GPU1 39%/108 MiB; WORK_QUEUE mantiene GPU1 reservada al escritorio. No se inició inferencia, benchmark, descarga ni build. Reanudar tras conexión autenticada de Drive y liberación explícita de GPU1; luego preflight y pruebas habilitadas en serie.

Rechequeo 2026-10-20T11:53:54Z: Sheets sigue devolviendo `403: arc control transport is not enabled` (0 filas leídas/escrituras). `nvidia-smi`: GPU0 60%/658 MiB y GPU1 25%/108 MiB; WORK_QUEUE mantiene GPU1 reservada al escritorio. No se inició inferencia, benchmark, descarga ni build. Reanudar tras conexión autenticada de Drive y liberación explícita de GPU1; luego preflight y pruebas habilitadas en serie.


## Síntesis transversal: ampliación de contexto por perfil

La ampliación de contexto es viable por perfil/modelo, no como límite global. En el código de perfiles, el parser reconoce `--ctx-size`, `-c` y `--ctx`; esto confirma que la configuración puede expresarse, no que una instancia concreta haya aplicado el valor.

Evidencia local ya cerrada: ISTA Qwen3.8-Flash-Next IQ3_XXS en Strata 0.1.41 recuperó 9/9 hechos en tres prompts de 255.005 tokens API con contexto nativo 262.144. ASTRA IQ2_XS con YaRN ×4 tiene configuración de 1.048.576 y un screen previo de 996.163 tokens con 10/10 hechos en una corrida; la activación de esa configuración en la instancia actual aún requiere el smoke S57. No transferir resultados entre quants.

S57 pasó el smoke de activación ASTRA 1M (configuración efectiva y generación corta; sin repetir NIAH). S55 completó retrieval IQ3_XXS ~680K con contenido 15/15, pero JSON crudo 2/3: gate estricto no pasa. S56 cerró sin score antes de READY después de cuatro intentos; no se reintenta. No elevar un límite global ni extrapolar entre quants. Los accionables restantes conservan sus precondiciones y se ejecutan en serie.

Rechequeo 2026-10-20T11:57:06Z: el control de Sheets permanece en 403 y la apertura pública directa no es accesible vía web tool; 0 filas leídas/escritas. `nvidia-smi`: GPU0 27%/713 MiB y GPU1 25%/108 MiB; WORK_QUEUE mantiene GPU1 reservada. Sin inferencia, benchmark, descarga ni build.

Rechequeo 2026-10-20T11:57:55Z: el navegador in-app redirige a inicio de sesión Google y no hay cuenta autenticada; el conector de Sheets devuelve 403 y la apertura vía web tool no es accesible. Se leyeron/escribieron 0 filas. `nvidia-smi`: GPU0 60%/708 MiB y GPU1 34%/108 MiB; WORK_QUEUE mantiene GPU1 reservada. No hubo inferencia, benchmark, descarga ni build.


## Auditoría de cobertura del lote y acceso a la fuente #58 (2026-10-20T11:59:55Z)

La auditoría del inbox confirma 58/58 secuencias únicas, del 1 al 58 sin huecos, y 58/58 entradas con objeto de análisis. En el directorio faltan recibos de revisión autónomos para #1–#4 y #7; #7 sí conserva sus recibos de preregistro, ejecución y resultado. El manifiesto `receipts/batch-coverage-reconciliation.json` registra esas brechas con hashes de los registros del inbox y declara explícitamente que no reconstruye ni inventa recibos contemporáneos.

La planilla no es pública por rutas alternativas: `pubhtml`, `gviz` CSV y `export` CSV devuelven HTTP 401; el navegador pide iniciar sesión y el conector de Sheets responde 403. Cero filas leídas/escritas. `nvidia-smi`: GPU0 28%/680 MiB, GPU1 71%/108 MiB; WORK_QUEUE conserva GPU1 reservada. Sin inferencia, benchmark, descarga ni build.


Recibos reconciliados 2026-10-20T12:00:31Z: #1–#4 y #7 no tenían archivo autónomo de revisión. Creé recibos separados `source-01-inbox-reconciliation.json` … `source-04-inbox-reconciliation.json` y `source-07-inbox-reconciliation.json`, cada uno con el análisis copiado del inbox, hash del registro fuente y límite explícito de que no recrea el recibo contemporáneo. El manifiesto `receipts/batch-coverage-reconciliation.json` mantiene esas cinco ausencias originales y enlaza los nuevos recibos de reconciliación.


Rechequeo 2026-10-20T12:01:43Z: el control de Sheets sigue en `403: arc control transport is not enabled`; el inventario actual del navegador solo muestra pestañas del tablero local, sin una sesión visible de Google Sheets. Cero filas leídas/escritas. `nvidia-smi`: GPU0 9%/671 MiB y GPU1 17%/108 MiB; WORK_QUEUE mantiene GPU1 reservada al escritorio. No se inició inferencia, benchmark, descarga ni build. Recibo: `receipts/recheck-20261020T120143Z.json`.


## Fuente #58: hoja de seguimiento de IA local

La exportación CSV quedó accesible en modo lectura. La pestaña «IA local» contiene cinco propuestas. Gufo se limita a AMD Strix Halo/gfx1151 y no justifica instalarlo en este host CUDA; coincide con el historial L122. «Adaptive Thinking (JEV gate)» requiere una API vLLM con `/v1/completions` en batch, top-k logprobs, `logprob_token_ids`, `/tokenize` y un modelo Qwen3 ChatML. La auditoría del código local Strata 0.1.41 encontró solamente las rutas `/v1/chat/completions`, `/v1/messages` y `/v1/responses`; no se encontró la ruta completions ni esas extensiones de logprobs. Por lo tanto, queda bloqueado hasta adoptar deliberadamente vLLM o implementar el contrato requerido; no se instalará ni se gastará GPU en este backend ahora. Coincide con L123. `crit/crit-hub` no aporta un repositorio upstream verificable y su cifra para RTX 5090 sigue siendo una afirmación del autor; coincide con L125. La discusión Strata/Gufo/QFN no propone una comparación controlada nueva y se solapa con los experimentos de contexto ya preregistrados. NVFP4 prefiller sí está ahora en la lista «IA local», pero el README del proyecto exige Blackwell (GB10 sm_121 o RTX 50 sm_120), no Ampere RTX 3090; coincide con L273, así que no se descarga ni se compila en esta máquina.

Relectura del 2026-10-20T14:13:15Z: «IA local» (gid 212274250) devolvió 5 filas de datos/12 columnas; «Enlaces revisados» (gid 353663141) 281 filas de datos/14 columnas; «Sin evaluar» (gid 937051657) 349 filas de datos/19 columnas. El CSV actual confirma duplicados L122, L123, L125 y L273. La hoja no contiene resultados de corridas para esas propuestas. Los hashes y resultados de deduplicación están en `receipts/source-58-sheet-refresh-20261020T141315Z.json`. La lectura pública funciona, pero el acceso de escritura sigue bloqueado en esta sesión: navegador firmado-out, Document Control 403 y sin herramientas MCP de Google Drive. Ninguna fila o pestaña se modificó.


## Estado de migración al Google Sheet · 2026-10-20T15:02:31Z

El CSV de importación actualizado conserva las 51 evaluaciones históricas y las 58 entradas del lote, añade un resumen y seis brazos de S33, y contiene 117 filas de datos con IDs únicos. SHA-256: `6606c4197a44432688f4ddbba43a8267f86897e040d21051fd30bbf5e445e449`. La hoja de destino se pudo leer y deduplicar, pero no se escribió: el canal de edición/importación Google Drive no está disponible en esta sesión (Document Control 403; `google_drive_import_spreadsheet` no expuesto). Cuando se habilite, importar el CSV como pestaña nueva `Evaluaciones LlamaCode` y verificar 117 filas, 13 columnas y las pestañas originales intactas. La mini app no fue modificada.


## Actualización de migración a Google Sheets · 2026-10-20T15:30:00Z

Se verificó en el navegador el registro S58 dentro de la pestaña nueva «Evaluaciones LlamaCode» (gid `1945218181`). El rango de índice es `A1:I118`: 117 registros, 9 columnas, IDs únicos. El indicador mostró «Guardado en Drive». Están incluidos 51 antecedentes, los 58 materiales del lote, el resumen y el agregado más seis brazos del A/B S33.

Se corrigió el encabezado de rutas, se acortaron y ajustaron los encabezados, se creó un filtro sobre `A1:I118` y se inmovilizaron una fila y una columna. Se repararon en las celdas I112:I118 las rutas duplicadas de evidencia de S33. Las pestañas de origen «IA local», «Enlaces revisados» y «Sin evaluar» permanecen intactas.

El export local de detalle conserva los 117 registros en 13 columnas; SHA-256 `0eb125df9403db6581815784d0952cd6d70dec10e4d4b8fbfd926c6b4e468061`. No se pudo importarlo como una segunda pestaña: esta ventana sigue mostrando «Iniciar sesión» y deshabilita Archivo → Importar; Codex Document Control responde `403: arc control transport is not enabled`. El CSV detallado queda referenciado en el índice y en el recibo hasta que haya una sesión autenticada o un conector de escritura.

Recibo de verificación: `receipts/google-sheet-migration-completion.json`. Mini app sin cambios ni ejecución; sin build, benchmark ni uso de GPU.

Verificación local adicional · 2026-10-20T15:35:16Z: el export detallado conserva 117 IDs únicos en 13 columnas; el resumen tiene los mismos 117 IDs únicos en 9 columnas. Se comprobaron 250 referencias a evidencia local (177 rutas únicas), sin rutas faltantes. La pestaña de Sheets conserva el indicador «Guardado en Drive». El detalle de 13 columnas sigue pendiente: la ventana requiere iniciar sesión y deshabilita Archivo → Importar; Document Control responde 403. No se modificó la mini app.

## Refresh de migración a Google Sheets · 2026-10-20T17:57Z

El export de solo lectura del workbook confirmó la pestaña `Evaluaciones LlamaCode` con 117 filas de datos y nueve columnas. El GID que abre el link del usuario corresponde a `IA local` (12 columnas y cinco iniciativas), por lo que la migración se preparó en la tabla de evaluaciones existente y conserva intactas las pestañas de origen.

El delta local ahora incluye 20 IDs nuevos: los 19 registros de pruebas S35/S41 preparados tras el último corte y un registro activo de S43 (Maya-S24, build aprobado, pesos aún en descarga y sin inferencia). Se preparó una actualización de la fila resumen de campaña; tras anexar el delta, la tabla contendrá 137 registros. El mapeo preserva estado/prioridad, fecha, tema/pregunta, fuente, evidencia/decisión, próximo paso/bloqueo y evidencia local dentro del esquema real de nueve columnas. TSV paste-ready: resumen `A2:I2`, delta `A119:I138`; comprobados 9 campos por fila, IDs sin duplicados, sin tabs/saltos de línea embebidos y sin celdas iniciales que puedan interpretarse como fórmulas. Conciliación y hashes: `receipts/google-sheet-schema-reconciliation.json`.

No se ha escrito en el servicio: el navegador continúa en Google Sign-In y Codex Document Control devuelve 403. El usuario debe completar el inicio de sesión en la pestaña abierta para aplicar el cambio; no se manejarán credenciales. La app local no fue modificada ni iniciada. La hoja exportada es un snapshot fechado, así que al habilitar escritura se volverá a leer y deduplicar el rango vivo antes de pegar.

## Reconciliación vigente de migración · 2026-10-20T18:04:53Z

Una exportación fresca del libro volvió a confirmar 117 IDs únicos en `Evaluaciones LlamaCode`; el historial local tiene 137 IDs únicos, sin IDs remotos ausentes, y el delta exacto son 20 filas. El CSV de nueve columnas y el TSV paste-ready sin encabezado coinciden fila por fila. Queda preparada una actualización de resumen y el append `A119:I138`; `IA local` permanece intacta. Evidencia: `receipts/google-sheet-live-reconciliation-current.json`, snapshot SHA-256 `74864cdbaa79961e50d948d0cccde28e497e169cacdae2696d3bd0c826c06f37`.

La edición sigue detenida antes de cualquier escritura: el navegador integrado muestra la pantalla de Google Sign-In y Document Control no encuentra una sesión de documento conectada. El usuario necesita completar el inicio de sesión en la pestaña abierta; no se manipulan credenciales. La app local sigue intacta.

## S43 · avance de descarga Maya-S24 · 2026-10-20T18:12:59Z

El shard 1/3 (43,6 GB) terminó y pasó su verificación SHA-256. El shard 2/3 está descargándose (~7% al último sondeo, a ~26 MB/s); el proceso conserva --no-start --no-vision, así que todavía no hay servidor de inferencia ni uso de GPU. Antes de cargar el modelo se volverán a comprobar los tres hashes, espacio libre ≥20 GB y un preflight fresco de servidor/API/GPU. El guard de recursos aborta bajo 32 GiB de memoria disponible, con crecimiento de swap >1 GiB, incremento del contador OOM o temperatura >85 °C.

Rechequeo de descarga 2026-10-20T18:16:58Z: shard 2/3 Maya-S24 en 24% (~28 MB/s); no se inició inferencia ni se usó GPU. La pestaña de Sheets continúa en Google Sign-In; no hubo escritura externa.

Rechequeo S43 2026-10-20T18:23:56Z: shard 2/3 al 50%, transferencia estable (~28 MB/s), sin servidor ni GPU. Google Sheets sigue en Sign-In; no hubo escritura remota.

Rechequeo S43 2026-10-20T18:27:04Z: shard 2/3 Maya-S24 en 63% (~28 MB/s), sin inference/GPU. Acceso a Google Sheets aún sin autenticar; no hubo cambio remoto.

## Sincronización final de Google Sheets · 2026-10-20

Se completó la migración incremental en la pestaña `Evaluaciones LlamaCode` del workbook existente. Se anexaron 20 registros únicos en `A119:I138`, se actualizó el resumen de campaña y se reconciliaron S33, S41, S43 y S58 con sus resultados finales. La lectura posterior confirmó 137 filas con ID, 137 IDs únicos, los 20 IDs nuevos presentes y sin duplicados. La pestaña `IA local` (gid 212274250) y las pestañas originales no se reescribieron; `IA local!A8:L8` conserva el candidato OCR S49 como especialista opt-in.

Los resultados finales conservan los límites: S33 no se promueve por gate de velocidad/seguridad; S41 mantiene `presence_penalty=0.0`; S43 no promueve Maya-S24 (5/24 vs 5/24 y 2,58× más lenta); S49 se conserva sólo para evaluación opt-in en Data Lab. Qwen Flash-Next de ASTRA/SOL y modelos de PeritoSoft permanecen protegidos. No se modificó código de la aplicación.


## Reanudación iterativa · 2026-10-21T01:48:11.630333+00:00

Se reabrió el lote por instrucción explícita del usuario de continuar hasta completar las pruebas justificadas. La primera reconsulta preregistrada es S36: verificar si existe evidencia primaria pública del Reel antes de diseñar el fixture. No usa GPU ni modifica la app. Prerregistro: [source-36-primary-retrieval-retest-preregistration-20261020.json](receipts/source-36-primary-retrieval-retest-preregistration-20261020.json).


### S36 reintento de evidencia primaria · 2026-10-21T01:49:05.153956+00:00

Reel exacto y variante `/p/` volvieron a fallar por throttling; las búsquedas del shortcode y de la afirmación no recuperaron una copia atribuible. No se creó fixture ni se usó modelo. El bloqueo continúa hasta contar con caption, transcripción, captura legible o mirror atribuible. Recibo: [source-36-primary-retrieval-retest-result-20261020.json](receipts/source-36-primary-retrieval-retest-result-20261020.json).


### S23 control de memoria para reanudación · preregistrado 2026-10-21T01:50:11.102049+00:00

Antes de reintentar el par PLE, se probará sin modelo ni GPU si systemd permite confinar el proceso a un cgroup transitorio con `MemoryMax=72G`. Sólo un PASS habilita preparar el intento 03; no cambia la causa previa de presión ni cuenta como resultado de calidad. [Prerregistro](receipts/source-23-memory-containment-pilot-preregistration-20261020.json).


### Controlador S23 listo para el lock actual · 2026-10-21T01:52:38.690934+00:00

La primera validación había fijado la variable después de importar el módulo y dio falso negativo; la repetición en procesos nuevos pasó: el token de este lock es aceptado, uno incorrecto se rechaza, y `py_compile` pasa. El controlador aislado ahora permite el override por entorno y conserva el token histórico por defecto. Recibo de enmienda y validación: [amendment](receipts/source-23-runner-lock-portability-amendment-01.json), [attempt02](receipts/source-23-runner-lock-portability-result-attempt02.json).


### S23 piloto de control de memoria y watchdog · 2026-10-21T01:53:58.100220+00:00

Los scopes transitorios aplican `MemoryHigh=64G` y `MemoryMax=72G`; un proceso dummy de 8 s quedó observado por el watchdog y terminó normalmente. El guard registra MemAvailable, swap, PSI, oom_kill y memoria cgroup; aborta sólo el scope de prueba. Script validado con `bash -n`. Sin inferencia ni GPU. El límite reduce, pero no elimina, el riesgo sistémico; antes del modelo se requiere preflight fresco. Recibo: [source-23-stock-seed-23002-attempt-03-guard-validation.json](receipts/source-23-stock-seed-23002-attempt-03-guard-validation.json).


### S23 intento 03 abortado y guard ajustado · 2026-10-21T02:02:10.687611+00:00

El intento stock/23002-03 se abortó antes de READY por un pico global de PSI full avg10 de 11,94% a los 10 s, aunque seguían disponibles >108 GiB, el scope usaba 8,1 GiB y oom_kill permanecía en 0. No hubo solicitudes ni score; procesos/puertos quedaron limpios. El pico decayó; el guard revisado conserva `MemoryHigh=64G`/`MemoryMax=72G`, el piso de 48 GiB y aborta por PSI sólo si `some>40%` o `full>25%` durante cuatro muestras consecutivas (20 s); agrega temperatura <85°C. `bash -n` y dry-run acotado pasaron. Intento 04 fue preregistrado antes de modificar el guard. Recibos: [abort 03](receipts/source-23-stock-seed-23002-attempt-03-guard-aborted.json), [guard preregister](receipts/source-23-stock-seed-23002-attempt-04-preregistration.json), [guard validation](receipts/source-23-stock-seed-23002-attempt-04-guard-validation.json).


### S23 wrapper attempt04 corregido · 2026-10-21T02:03:54.947733+00:00

El wrapper ahora recibe unit/arm/seed/attempt por entorno, exige nombres de salida nuevos y rechaza logs ya existentes. El intento de parche anterior no cambió el archivo y está anotado; la validación actual `bash -n` y el dry-run bajo unit único pasaron. No se cargó el modelo. Recibos: [wrapper failure](receipts/source-23-stock-seed-23002-attempt-04-wrapper-failure.json), [amendment](receipts/source-23-stock-seed-23002-attempt-04-wrapper-amendment-02.json), [validation](receipts/source-23-stock-seed-23002-attempt-04-wrapper-validation.json).


### S23 intento 04 detenido por presión sostenida · 2026-10-21T02:05:39.316769+00:00

El brazo stock/23002-04 abortó antes de READY a los 31 s: PSI `some/full` llegó a ~53% mientras el scope cargaba ~37,6 GB. Aunque MemAvailable luego volvió a ~117 GB, el stall sostenido confirma que el mismo método de carga puede presionar el escritorio. No hubo requests, score, swap adicional ni OOM-kill; postflight sin servidor/puertos residuales. No repetir este camino hasta validar otra estrategia de carga de memoria/I/O; continúo con pruebas independientes que no requieran esta carga. Recibo: [source-23-stock-seed-23002-attempt-04-guard-aborted.json](receipts/source-23-stock-seed-23002-attempt-04-guard-aborted.json).

#### Reproducción de respuesta conocida · 2026-10-21T02:11:40Z

El fixture exacto `BigCodeBench/1019` pasó con una implementación de referencia determinista en Python 3.12.3, exit 0 y sin modelo/GPU. La importación global de pytesseract mostró trazas no fatales por módulos opcionales (`numexpr` y `bottleneck`) compilados contra NumPy 1.x mientras el entorno tiene NumPy 2.5.3; aun así, los cinco tests del fixture corrieron y pasaron. Esto descarta una aserción intrínsecamente imposible en ese caso, pero no limpia el entorno ni valida los otros siete casos o la campaña BCB8 completa. No se cambia el estado de timeout/no-score. Recibo: [replay de referencia](../Q-20261021-VF-FINISH-PENDING/receipts/udiq4xs-known-answer-grader-result-20261021.json).

### Diagnóstico de grader UD-IQ4_XS · 2026-10-21T02:09:05Z

Se inspeccionó sin modelo la tarea preservada `BigCodeBench/1019` del BCB8 intento 2. El `venv_probe` no contiene `numpy`, Pillow ni `pytesseract`, por lo que no sirve para certificar el entorno del grader. La expresión esperada de conversión sí funciona para el texto ASCII del fixture; no demuestra el caso de caracteres no ASCII. El EVAL preservado muestra que el candidato devolvió un `MagicMock` en dos casos de fallback; la corrida global sigue inválida por timeout. No se reparó el entorno ni se reintentó el modelo; UD-IQ4_XS permanece parcial y sin promoción. Recibo: [diagnóstico](../Q-20261021-VF-FINISH-PENDING/receipts/udiq4xs-grader-fixture-result-20261021.json).

### Harness²: canario de egress aislado · 2026-10-21T02:09:05Z

El canario CPU-only pasó en un network namespace desechable: sólo expuso `lo`, sin ruta por defecto; un endpoint HTTP local devolvió 200 y una conexión sin payload a TEST-NET terminó `ENETUNREACH`. Esto confirma factibilidad básica de aislamiento y healthcheck local, pero no acceso a un servidor de inferencia de LlamaCode ni evaluación Harness². Siguiente: comprobar si el endpoint local puede colocarse dentro del mismo namespace de forma reproducible y con el mismo control de egress. Recibos: [prerregistro](../Q-20261021-VF-FINISH-PENDING/receipts/harness2-egress-runner-preregistration-20261021.json), [resultado](../Q-20261021-VF-FINISH-PENDING/receipts/harness2-egress-runner-result-20261021.json); script: [canario](../Q-20261021-VF-FINISH-PENDING/work/harness2-egress-canary.py).

#### OpenJet single-3090 speed screen · 2026-10-21

Se compiló el motor OpenJet fijado y se completó el control LlamaCode en GPU0 para el mismo GGUF, contexto 16K, KV Q8 y greedy: cuatro consignas de 256 tokens con tres repeticiones válidas, más prefills de 0/2K/8K. Control: media de decode 25,11 tok/s; para el contexto nominal 8K se procesaron 7.549 tokens a una mediana de 918,75 tok/s. No hay resultado comparativo: el GGUF tiene arquitectura `qwen35`, 64 bloques y embedding 5120; el kernel fijado exige 65 bloques y embedding 5120 y rechaza el modelo antes de ejecutar inferencia. MTP2 tampoco aplica porque el GGUF no contiene capas MTP; el control usó la ruta soportada sin especulación. OpenJet produjo cero muestras; no se recomienda ni afirma una mejora. Reabrir sólo si se identifica un Q4_K_M compatible de 65 bloques o si OpenJet añade soporte a este archivo de 64 bloques. Recibo [resultado](../Q-20261021-VF-FINISH-PENDING/receipts/openjet-single3090-speed-result-20261021.json), [intento bloqueado](../Q-20261021-VF-FINISH-PENDING/receipts/openjet-speed-attempt-04-blocked-dimensions-20261021.json), runner [local](../Q-20261021-VF-FINISH-PENDING/work/openjet_speed_screen.py).

#### Harness²: endpoint LlamaCode dentro del namespace · 2026-10-21

La misma corrida también respondió con `/health`, `/tokenize` y solicitudes de completion desde el namespace aislado, después de habilitar únicamente `lo`; no había ruta por defecto. Esto cierra la comprobación técnica de transporte pendiente: un servidor local de inferencia puede ser consultado dentro del aislamiento sin egress externo. No evalúa calidad Harness² ni la sesión gráfica completa de LlamaCode; esa prueba queda pendiente si cambia la decisión de evaluar el runner real. Recibo [endpoint local](../Q-20261021-VF-FINISH-PENDING/receipts/harness2-same-namespace-inference-endpoint-result-20261021.json).

### Cierre de iteración de pruebas pendientes · 2026-10-21T03:00:05Z

Se ejecutó el follow-up funcional de Harness²: la ruta local OpenAI Responses devolvió mensaje visible y válido tras corregir el criterio del primer request, cuyo límite de 16 tokens sólo produjo razonamiento. En el commit oficial `1cfe254e8d25b15f37048c3730134686abe60335`, la suite local de Harness² pasó 5/5 y el demo determinista completó 2/2 tareas en modos paralelo/secuencial, dentro de bubblewrap sin egress ni acceso a home/modelos. Esto cierra sus pruebas de transporte y mecánica, no una mejora de calidad.

Se reintentó la búsqueda pública exacta del Reel S36 sin recuperar contenido atribuible. S23 sigue pausada porque el controlador `io` no está delegado al cgroup de usuario y el loader anterior produjo PSI sostenida; no se hizo otra carga. UD-IQ4_XS BCB8/ADV/TaskFlow siguen sin EVAL final (BCB8 agotó 1.800 s y 7.200 s; no repetir el mismo fingerprint). OpenJet sigue bloqueado porque el GGUF local tiene 64 bloques y el kernel fijado exige 65. No quedan pruebas de calidad justificadas ejecutables hasta que cambien esas condiciones o se defina el flujo/holdout de Harness². Detalle y pasos de reapertura: [`Q-20261021-VF-FINISH-PENDING/RESULTS.md`](../Q-20261021-VF-FINISH-PENDING/RESULTS.md) y [matriz de bloqueos](../Q-20261021-VF-FINISH-PENDING/receipts/remaining-tests-blockers-result-20261021.json).

### Iteración 4 — revalidación Swift/OpenJet y bloqueos vigentes · 2026-10-21T04:32:00Z

La fila Swift #51 tiene ahora una alternativa potencial sin MTP, con hash oficial fijado, pero no se descargó: su licencia condiciona el uso comercial al umbral consolidado de US$1M y la elegibilidad de Vector Fields no fue confirmada. La opción no-MTP exige volver a ejecutar un control ASTRA no-MTP emparejado y comprobar que ambas cargas sean seguras; no es comparable directamente con el ASTRA productivo MTP4. El usuario tiene pendiente confirmar ingresos consolidados/licencia empresarial. Consulte [prerregistro y licencia actualizados](PLAN-source-51.md) y [recibo de revalidación](../Q-20261021-VF-ITERATION-4/receipts/iteration4-revalidation-20261021T0432Z.json).

La lectura estática del código OpenJet fijado confirmó que `NLA=65` representa 64 bloques base (`NL=64`) más el bloque MTP, no un desajuste cosmético; por ello el GGUF local de 64 bloques no entra en ese kernel. S36 volvió a quedar throttled; S23 sigue sin `io` delegado; UD-IQ4_XS conserva errores reales de candidate output y campañas inválidas por timeout; Harness² calidad requiere workflow/holdout y una carga segura. Se actualizaron y releyeron solamente `Evaluaciones LlamaCode!C149:D149`, `G149:I149`, `C152:D152` y `G152:I152` para OpenJet/Swift. No se ejecutó inferencia ni se cambió ningún modelo/perfil. Esta iteración no completa las pruebas pendientes.

## Auditoría de pruebas pendientes · Q17 · 2026-10-21T07:08:31Z

Q17 volvió a revisar las condiciones de ejecución antes de lanzar otro ensayo. No se encontró inference server/API de evaluación. La GUI ArtCraft permaneció abierta conforme a la instrucción del usuario; no se mató ningún proceso. El intento S23 23002-04 había abortado antes de READY y de enviar solicitudes por presión sostenida del propio loader (PSI de memoria ~48–53% con ~37,6 GB en su scope); sin `io.max` delegado ni un loader distinto verificado, no se repitió. Las GPU libres de un servidor de inferencia no eliminan ese riesgo de presión de memoria.

Corrección de estado: el bloque histórico de S43 aún describía una reserva de GPU como bloqueo. El screen ya se había completado: Maya 5/24 frente a ASTRA 5/24, W/L/T 3/3/18 y mediana de tiempo 2,58× mayor para Maya; no pasó el gate de +2 éxitos y no corresponde ampliar Hard Mode. La hoja de seguimiento ya refleja el estado final.

La evidencia disponible sobre contexto sigue siendo específica por quant y perfil: ASTRA IQ2_XS está configurado con contexto efectivo de 1.048.576 y tuvo un screen NIAH sintético 10/10 en una corrida, más smoke de activación/generación; IQ3_XXS recuperó 9/9 campos cerca de 255K en tres prompts y 15/15 hechos cerca de 680K, pero sólo 2/3 respuestas pasaron JSON crudo. Esto no justifica elevar los límites globales ni repetir los mismos NIAH; mantiene abierta la conclusión por perfil y caso de uso.

No se habilitó una prueba nueva segura en esta iteración. Persisten prerequisitos concretos: S20 proveedor/modelo/versionado, `keyRef`, límite de gasto y frontera de datos; S51 elegibilidad de licencia Swift y un preregistro nuevo sin MTP; S23 loader/estrategia de I/O segura; S36 contenido primario atribuible; UD-IQ4_XS runner/carga aptos sin repetir huella agotada; OpenJet GGUF/kernel compatible; Harness² workflow y holdout de calidad. No se declara completa la campaña. Q17 y la fila 165 de `Evaluaciones LlamaCode` quedaron sincronizadas y verificadas en `receipts/pending-source-audit-result.json` y `Q-20261021-VF-ITERATION-17/receipts/google-sheet-update-result.json`.

## Iteración 18 — S55 JSON Schema a contexto largo · 2026-10-21T11:39:35Z

Se intentó el A/B preregistrado de tres pares para `response_format=json_schema` contra texto plano sobre los fixtures S55. El modelo IQ3_XXS estaba en cuarentena; se usaron sus archivos en esa ubicación, sin mover ni copiar. Size/mtime de ambos shards y hash de tokenizer coincidieron con S55. El scorer CPU pasó 5/5 casos, y el preflight confirmó ausencia de servidores/listeners, 109,52 GiB disponibles, PSI/OOM cero y más de 23 GiB libres por RTX 3090. Se conservó ArtCraft.

La carga inició desde `HDD extra`, pero el proceso propio del loader superó cuatro muestras consecutivas del guard preregistrado (`some.avg10` y `full.avg10` 43,11%, frente a límites 40%/25%) antes de READY. La memoria disponible al abortar era 73,2 GiB, swap usado 1,67 GiB y OOM 0. Se enviaron 0/6 solicitudes y no hubo score. Strata recibió SIGTERM sin SIGKILL; la verificación posterior confirmó que no quedaba servidor/listener, el puerto 8351 estaba libre, la memoria volvió a 109,52 GiB y ArtCraft siguió abierto. No se relajó el guard ni se repitió la misma carga. Q18 queda bloqueada hasta verificar un método de carga distinto que contenga la presión de memoria. La fila 166 de `Evaluaciones LlamaCode` y el resumen C2/E2 se actualizaron con readback. Evidencia: [`Q-20261021-VF-ITERATION-18/RESULTS.md`](../Q-20261021-VF-ITERATION-18/RESULTS.md), [preflight](../Q-20261021-VF-ITERATION-18/receipts/source55-format-ab-preflight-result.json), [cierre](../Q-20261021-VF-ITERATION-18/receipts/700k-json-schema-ab-close-result.json), [Sheets](../Q-20261021-VF-ITERATION-18/receipts/google-sheet-update-result.json).


## Iteración 19 — S55 JSON Schema a 700K con `--mmap-experts` · 2026-10-21T12:31:32Z

Se reanudó S55 con una vía distinta de carga tras el bloqueo por PSI de Q18. El scorer CPU pasó 8/8 casos y el conteo con tokenizer fijado pasó 3/3. Tras tres fallos de harness/runtime/streaming previos a una respuesta utilizable, el intento 4 terminó los seis requests seriales cerca de 680K tokens. Plain y `response_format=json_schema` tuvieron 3/3 salidas válidas, cinco claves exactas y 15/15 hechos exactos por brazo. El candidato JSON pasó el gate de contenido.

La medición fue descriptiva: una ejecución por modo y semilla, tiempos por request de 270–323 s, prefill de 2.140–2.531 tok/s y decode de 30,3–91,9 tok/s. No demuestra superioridad de latencia, y `json_schema` no fue decoding restringido en este runtime. `--mmap-experts` llegó a READY en 15,379 s; postflight PSI/OOM 0, 117.185.839.104 bytes disponibles, sin proceso/listener de inferencia, puerto 8354 libre y ArtCraft conservado. Q19 se cierra como candidato S55 bajo esta configuración; no cambia producción ni límites globales de contexto. La fila 167 y el resumen C2/E2 de `Evaluaciones LlamaCode` quedaron verificados. La campaña sigue incompleta por los prerequisitos de S20/S51, S23, S36, UD-IQ4_XS, OpenJet y Harness². Evidencia: [RESULTS.md de Q19](../Q-20261021-VF-ITERATION-19/RESULTS.md), [recibo final](../Q-20261021-VF-ITERATION-19/receipts/700k-json-schema-mmap-ab-attempt04-result.json), [actualización de Sheets](../Q-20261021-VF-ITERATION-19/receipts/google-sheet-update-result.json).


## Iteración 20 — S23 PLE FP8 con `--mmap-experts` · 2026-10-21T13:10:33Z

Q20 reabrió el A/B S23 bajo un scope propio y límites MemoryHigh/Max 64/72 GiB, con el mismo `--mmap-experts` en stock y FP8. Se completaron los tres pares de seeds 23003/23004/23005, 8 tareas BCB-Hard por brazo: ambos formatos aprobaron 3/24, siempre el mismo caso y con cero pares ganados por FP8. Las medianas de medianas de decode fueron 126,75 tok/s stock y 125,90 tok/s FP8 (−0,7%); no hay diferencia concluyente ni superioridad. No se promovió ni se cambió configuración productiva.

El primer stock 23003 completó transporte, pero el scorer falló en sandbox; el scorer Q20 aislado se probó 14/14 en CPU y las respuestas guardadas se re-calificaron sin solicitudes adicionales: 1/8. Los otros cinco brazos usaron el scorer reparado. Se verificaron fingerprints, límites de cgroup, preflights individuales, 48/48 respuestas, OOM 0 y limpieza del puerto/servidor; no se detuvo la GUI. Los picos de RAM no son comparables porque la primera carga stock fue fría y las demás encontraron caché caliente. Q20 queda cerrado como screen negativo. La campaña sigue incompleta por los prerequisitos externos restantes (S20/S51, S36, UD-IQ4_XS, OpenJet y Harness²). Evidencia: [RESULTS.md de Q20](../Q-20261021-VF-ITERATION-20/RESULTS.md), [resultado machine-readable](../Q-20261021-VF-ITERATION-20/receipts/source23-mmap-fp8-ab-result.json), [fingerprints](../Q-20261021-VF-ITERATION-20/receipts/input-fingerprints.json). La fila 168 y los resúmenes C2/E2 de `Evaluaciones LlamaCode` se actualizaron y leyeron de vuelta; ver [recibo de Sheets](../Q-20261021-VF-ITERATION-20/receipts/google-sheet-update-result.json).


## Iteración 21 — revalidación de fuente primaria y pendientes · 2026-10-21T13:18:00Z

Q21 volvió a abrir la URL primaria S36 y buscó el shortcode exacto: Instagram throttled la apertura y la búsqueda devolvió cero resultados. No apareció caption/transcripción/mirror atribuible, así que no se inventó fixture ni se ejecutó modelo. También se revisó si quedaba otra prueba habilitada: el E2E de concurrencia sólo aplicaría si se decide permitir dos trabajos en paralelo; los A/B híbridos dependen de endpoint, keyRef, gasto y frontera de datos; S51 depende de licencia; UD-IQ4_XS de runner/carga; OpenJet de formato/kernel; Harness² de workflow/holdout. No hay test de calidad justificable ejecutable ahora. Resultado y recibo: [Q21](../Q-20261021-VF-ITERATION-21/RESULTS.md), [S36](../Q-20261021-VF-ITERATION-21/receipts/source36-primary-retrieval-result.json). La fila 169 y los resúmenes C2/E2 de `Evaluaciones LlamaCode` se actualizaron y verificaron; [recibo de Sheets](../Q-20261021-VF-ITERATION-21/receipts/google-sheet-update-result.json). La campaña sigue incompleta.


## Revalidación Q51 — RCO Coder y Swift Flash-Next · 2026-10-23T01:54:06.709404Z

El screen de RCO Coder no se reabre: Hugging Face devuelve el mismo árbol de 13 archivos para la revisión Q27 probada y `main`; ambos shards IQ1_M conservan los mismos SHA-256. La actualización pública ya estaba incluida en el archivo que obtuvo 0/8 frente al control ASTRA 1/8, así que no se descargó ni se repitió.

Se registró una candidata distinta y más comparable con el ASTRA productivo: Swift 1.5 Qwen3.8-Flash-Next GSQ-RCO IQ2_XS (68.152.166.976 bytes; hashes del manifest en Q51). Strata 0.2.2 / engine 0.1.47 lista la familia Swift como soportada. Las métricas KLD de 512 tokens y speed/accuracy del fabricante no cuentan como calidad de coding/agente local. Se preparó un screen BCB-Hard-8 pareado con ASTRA en un runtime aislado común; la licencia comercial sigue pendiente de confirmación, por lo que no se descargó ni se usó GPU.

El usuario dice haber arreglado Windows, pero la sesión de Codex sigue ejecutándose en Ubuntu; no se puede arrancar el runner nativo Windows desde esta sesión. No se ejecutaron builds, servidores, inferencias ni pruebas de modelo en Q51. Evidencia: [plan](../Q-20261023-VF-ITERATION-51/PLAN.md), [recibo de revalidación](../Q-20261023-VF-ITERATION-51/receipts/iteration51-revalidation.json), [Sheet readback](../Q-20261023-VF-ITERATION-51/receipts/google-sheet-update-result.json).


## Iteración 22 — revalidación de cuatro bloqueos · 2026-10-23T01:58:31Z

Se abrieron nuevamente #26/#28/#31/#32 y se cotejaron fuentes primarias. #26 ahora enlaza logs que reportan una ejecución física Qwen2.5-72B/A100 (11/11 protocol trials, 17/17 checks, 8/8 append integrity; pico reportado 57,66 GiB), pero el script de esa misma demostración mantiene la nota “not executed on a GPU by its author (CPU simulation only)” y la etiqueta candidato/no publicado. Aun aceptando la mecánica, la semántica queda sin score general y no es transferible al Qwen3.8 Flash-Next local. #28 continúa anecdótico sin fixture/rúbrica; #31 sigue siendo ROCm/RX7900 con ~570 GB, sin target CUDA/SM86; #32 Instagram sigue inaccesible (`Cache miss`). No se descargó, construyó, ejecutó ni usó GPU; preflight no detectó servidores de inferencia. Las cuatro entradas permanecen bloqueadas con condición precisa. Detalle y fuentes: [Q52](../Q-20261023-VF-ITERATION-52/RESULTS.md), [recibo](../Q-20261023-VF-ITERATION-52/receipts/blocked-sources-revalidation.json).


## Reanudación 2026-10-26 tras cierre Q154

Q154 se cerró con no-go por la acción condicional TC-89; no se continuó con seeds 43/44 conforme al gate preregistrado. No había procesos de PeritoSoft ni inference server que terminar. La candidata Huihui UD-IQ4_XS, su pack y cachés se retiraron tras verificar hashes, enlaces y consumidores; se conservaron ASTRA, SOL y el perfil neutral compartido necesario para las configuraciones históricas. D recuperó 95.178.469.376 B netos. Resultados/Accionables/Inventario/IA local se sincronizaron al Sheet con readback verificado.

No quedó un benchmark local habilitado por la cola: #65 requiere Windows y ~1,1 TB NVMe libre; #66 no enumera ambas 3090 en Vulkan; #67 requiere Blackwell; #69 sigue abierto upstream (Strata #3294) y no hay quant local exacto. #31 continúa bloqueada (ROCm/RX7900, ~570 GB requeridos frente a 498 GB libres en D); #32 no tiene transcripción atribuible; #28 carece de fixture/control externo autorizado; #26 no transfiere a Flash-Next y ya existe cobertura de contexto local. Se registró la revisión en `receipts/queue-progress-update-q154-close-20261026.json`.
