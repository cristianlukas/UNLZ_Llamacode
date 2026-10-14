# Plan — Q-20261010-EMBEDDINGGEMMA2-EVAL

## Objetivo y decisión

Determinar si EmbeddingGemma 2 aporta una mejora útil a la recuperación local de código/texto en `semantic_search` y `hybrid_search`, frente al comportamiento vigente de LlamaCode cuando no hay endpoint de embeddings: BM25. Esto es un screening interno de recuperación, no una réplica de MTEB Code ni evidencia sobre calidad del agente en general.

Criterio de interés del usuario: ninguna corrida del perfil debe superar 30 minutos. Parar la prueba del candidato al acercarse a ese límite; no ampliar corpus ni repetir fuera del presupuesto.

## Preflight observado

- En este checkout, `AgentToolRunner` envía strings a `/v1/embeddings`, hace lotes de hasta 64, limita la búsqueda a 800 chunks de 40 líneas y calcula similitud coseno/RRF. No agrega prefijos por separado para query y documentos.
- La configuración local no declara `agent/auxiliaryUrl` ni `agent/auxiliaryEmbeddingModel`; no hay `model_roles.json` local con un modelo de retrieval. El control efectivo disponible es BM25 sin embeddings.
- No se encontró un GGUF de embeddings descargado en los roots revisados. El servidor llama.cpp fue detenido al cerrar la tarea anterior; la lista de procesos no mostró `llama-server` activo al hacer este preflight.
- Espacio libre observado: 106 GiB en `/media/cristian/Disco local`, 163 GiB en el volumen del repo y 8,6 GiB en `/`. El modelo irá en `/media/cristian/Disco local`, no en `/`.
- Hardware previsto: una RTX 3090 libre para el sidecar de screening. `nvidia-smi` mostró GPU 0 ocupada por `artcraft-launcher`, que queda intacta; se reservó sólo CUDA1 (RTX 3090, 24.016 MiB libres observados). No usar ni cambiar perfiles productivos.

## Perfiles candidatos y control

1. **Control:** recuperación BM25 actual de LlamaCode, sin endpoint de embeddings.
2. **EG2 drop-in:** `ggml-org/embeddinggemma-2-GGUF`, archivo `embeddinggemma-2-Q8_0.gguf` (≈310 MB según el model card del publicador), API llama.cpp `/v1/embeddings`, inputs como strings planos tal como los emite hoy LlamaCode.
3. **EG2 con instrucciones:** mismas weights/runtime, query `task: code retrieval | query: {query}` y documento `title: {filename} | text: {code}` como recomienda el model card. Esto mide potencial con un cambio futuro del harness; no representa el comportamiento actual.

Antes de descargar/cargar: resolver revisión completa e inmutable del repo GGUF; consultar tamaños y SHA-256 oficiales del archivo; comprobar disponibilidad de espacio; verificar hash local después de descargar. Registrar commit de llama.cpp y SHA-256 del binario. El soporte de la arquitectura se introdujo en llama.cpp mediante PR #30054, commit merge `4fbc76d`; no asumir compatibilidad hasta verificar el binario concreto.

## Datos y método

- Congelar una copia del corpus del repo para la corrida; generar el mismo chunking de 40 líneas usado por el harness y conservar paths/rangos/hashes.
- Preparar antes de medir un conjunto manual y balanceado de consultas de recuperación de código (español e inglés), con qrels de archivo/rango identificados a partir del corpus. Registrar versión, distribución y hashes de queries, chunks y qrels. Señalar que es una suite interna y que los juicios manuales limitan la generalización.
- Hacer un pase de indexación y una pasada por las mismas queries para cada brazo. Para el candidato medir la etapa fría de embeddings y la búsqueda cálida; secuenciar los brazos sobre el recurso compartido y usar identical chunking/queries.
- Métricas: Recall@1/3/5, MRR@5, nDCG@5; latencia de indexación y por consulta (mediana/p95); RSS y VRAM pico; dimensiones efectivas, request rate, errores y dimensiones de respuesta.
- Comparar BM25; EG2 semántico plano; EG2 semántico con prefijos; y, si el presupuesto lo permite, BM25+EG2/RRF plano y prefijado. Informar todas las condiciones válidas; no elegir una query ni corrida favorable.

## Umbral de screening

EG2 pasa a prueba de integración si alguna condición repetible supera BM25 en al menos 5 puntos porcentuales de nDCG@5, sin bajar MRR@5, y la indexación/consulta cabe en el límite de 30 minutos por corrida. Un resultado favorable sólo justifica una prueba de integración posterior; no promueve perfiles ni cambia defaults. Si sólo gana con prefijos, registrar que requiere una modificación del harness antes de servir como reemplazo drop-in.

## Alcance excluido

No evaluar imagen/audio/video en esta ejecución. Aunque EmbeddingGemma 2 sea multimodal, el código actual de las tools envía strings simples; la capacidad multimodal del modelo no demuestra que LlamaCode pueda ingerir esos datos por esta vía. No cambiar `HarnessSpec`, perfiles ni settings productivos; no agregar dependencias a la app. No correr HE0/HE20/BCB8 ni TaskFlow porque el objetivo es recuperación, no generación de código.

## Evidencia a conservar

`RESULTS.md`, preflight/runtime/model manifests, corpus/query/qrels congelados, outputs por query/ranking, latencias, logs del servidor, hashes de todos los insumos y de cualquier runner, memoria durante la carga, y estado del endpoint al cierre.


## Fuentes fijadas para el screening

- GGUF publicador `ggml-org/embeddinggemma-2-GGUF`, revisión completa `bfcd298762cc34d0357ece5ebdd31791a3a374d8`; archivo text-only `embeddinggemma-2-Q8_0.gguf`; tamaño HTTP 309.855.456 bytes. Metadata HTTP al fijar plan: `X-Xet-Hash` `0ac803e56aa216306210fbb7fe88c19adf40ccd4ebd5ffdcb63be9526501abef`; `X-Linked-ETag` SHA-256 esperado `2188ac1deca4b77dffefd603c2776a9d76d9d74ec01841392982ebb840b09135`.
- Runtime oficial `ggml-org/llama.cpp` release `b11554`, publicado 2026-10-11; asset Ubuntu x64 CUDA 12.8 `llama-b11554-bin-ubuntu-cuda-12.8-x64.tar.gz`; 172.001.544 bytes; GitHub API `digest` SHA-256 `6ad71a462b2953f7ab4ab9a585425ffe0bf0065a198c4f03bd30b9e8d4e77596`. El runtime local previo (`836d571`) antecede el PR y no se reutilizará.
- Descarga de ambos artefactos permitida por este plan; reservar y usar una RTX 3090 solamente si la verificación inmediata de GPU muestra disponibilidad. Directorio aislado de peso/runtime: `/media/cristian/Disco local/LlamaCode-cache/embeddinggemma2-eval/`; no instalar en el repo ni cambiar settings del usuario.


## Suite congelada

Fixture `code-retrieval-screen-v1`: 519 chunks de 40 líneas de 11 archivos seleccionados (código de retrieval/agente, settings QML, tests y dos documentos), 21 consultas de código en español e inglés (10/11) y 21 qrels manuales a spans concretos. Los qrels se fijaron antes de medir. No es búsqueda sobre el repo completo ni benchmark externo. `fixture-manifest.json` registra hashes por archivo y de corpus/queries/qrels. Medir BM25, EG2 vectorial sin prefijos, EG2 vectorial con `task: code retrieval`/title, y RRF con BM25 para ambas variantes. Sin reranker, sin caching entre brazos, mismos 519 chunks.

Hashes del fixture al preregistrar: corpus `7ce992f555a84b3d13d13828f763ad07b68861753362d0643acfcd5172b1ce45`; queries `fee6ccd607bf49bb7a4468bab6b1a53af375a9ddb1907a358f90319a04a370f0`; qrels `c44d60cad3128430d3ae3e375186a6e0577bb948ac878779b0fb8c4b3ffded41`. Umbral de screening ya fijado: +5 pp nDCG@5 vs BM25 sin bajar MRR@5; máximo 30 min para la corrida del perfil.


## Ajuste de preflight por intento inválido

Intento 1 (preservado en `receipts/attempt-01/`): la primera llamada de lote falló HTTP 500 porque llama.cpp redujo el batch físico a 512; una entrada de 538 tokens no cupo. El smoke unitario previo sí había devuelto 768 dimensiones finitas. Se clasifica como **inválido por infraestructura**, sin score EG2. Reintento de la misma fixture con el mismo modelo/runtime/GPU y `--batch-size 2048 --ubatch-size 2048`; no se altera el dataset ni el qrels. El log de carga del servidor y los resultados del reintento quedan en `receipts/attempt-02/`.


## GPU isolation adjustment

A preflight-only server start with `--device CUDA1` created a 256 MiB CUDA context on physical GPU 0 while placing model layers on GPU 1. It was stopped before the retrieval run; the unrelated `artcraft-launcher` on GPU 0 remained running. The scored server uses `CUDA_VISIBLE_DEVICES=1` and logical `--device CUDA0`, so the process can see only physical GPU 1. The preflight log and memory observation are preserved in `receipts/attempt-02/server-device-map-check.log` and `preflight-device-map.json`.
