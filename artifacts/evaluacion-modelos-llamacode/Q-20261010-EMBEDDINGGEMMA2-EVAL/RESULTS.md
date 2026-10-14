# Q-20261010-EMBEDDINGGEMMA2-EVAL — resultados

**Estado:** screening válido, resultado prometedor pero provisional. **No se cambió ningún perfil, setting productivo ni HarnessSpec.**

## Qué se evaluó

El control local efectivo era BM25 sin embeddings: el checkout no tenía un endpoint/modelo auxiliar configurado y no se encontró un GGUF local de embeddings. Se comparó esa recuperación con EmbeddingGemma 2 Q8_0 en el endpoint OpenAI compatible de llama.cpp.

El candidato es `ggml-org/embeddinggemma-2-GGUF`, revisión `bfcd298762cc34d0357ece5ebdd31791a3a374d8`, archivo text-only `embeddinggemma-2-Q8_0.gguf`, 309.855.456 bytes, SHA-256 `2188ac1deca4b77dffefd603c2776a9d76d9d74ec01841392982ebb840b09135`. Runtime: llama.cpp `0.6.0-dev`, build `11554`, commit `966baae76`; servidor SHA-256 `fe8a7d6073d3e3a276193fcaec162cbf280d2572ad2016c9100fd924be19c6ed`. La arquitectura se incorporó en el [PR oficial #30054](https://github.com/ggml-org/llama.cpp/pull/30054), merge commit `4fbc76d`.

El servidor corrió en `127.0.0.1:8397`, `--embeddings`, `--pooling mean`, contexto 8192, batch físico 2048, concurrencia 1, 16 threads, sólo GPU física 1. Se ocultó GPU física 0 con `CUDA_VISIBLE_DEVICES=1` y se seleccionó el dispositivo lógico `CUDA0`; el proceso no tuvo acceso a la GPU 0. Pico observado: 708 MiB del proceso en GPU 1, 826 MiB total en la GPU y 2.238 MiB RSS. El servidor se apagó al terminar.

El fixture congelado contiene 519 chunks de 40 líneas, tomados de 11 archivos de código, tests, ajustes QML y documentación; 21 consultas (10 en español, 11 en inglés) y 21 juicios de relevancia a spans concretos. Es un fixture interno, no el repo completo ni una réplica de MTEB. Sus hashes están en `fixture-manifest.json`.

Se midieron cuatro condiciones del candidato: embeddings directos con strings planos (como los envía hoy LlamaCode), RRF BM25+vector sin prefijos, embeddings con el prefijo oficial de code retrieval y título de archivo, y RRF con esos prefijos. No hubo reranker. Google documenta la instrucción `task: code retrieval | query: ...` y documentos como `title: {filename} | text: {code}`; también recomienda re-normalizar si se truncan las dimensiones. Se usaron los 768 valores de salida, sin truncamiento. [Model card oficial](https://huggingface.co/google/embeddinggemma-2).

## Calidad de recuperación

Cada consulta tiene un span relevante etiquetado. Recall es la fracción de consultas cuyo span apareció en el top-k; MRR@5 y nDCG@5 usan ese span único.

| Condición | Recall@1 | Recall@3 | Recall@5 | MRR@5 | nDCG@5 | Δ nDCG@5 vs BM25 |
|---|---:|---:|---:|---:|---:|---:|
| Control BM25 | 33,33% (7/21) | 42,86% (9/21) | 61,90% (13/21) | 0,4079 | 0,4588 | — |
| EG2, strings planos | 42,86% (9/21) | 76,19% (16/21) | 80,95% (17/21) | 0,6071 | 0,6594 | +20,06 pp |
| BM25 + EG2 RRF, strings planos | 47,62% (10/21) | 61,90% (13/21) | 80,95% (17/21) | 0,5849 | 0,6400 | +18,12 pp |
| EG2, prefijo code retrieval | 47,62% (10/21) | 71,43% (15/21) | 80,95% (17/21) | 0,6111 | 0,6612 | +20,24 pp |
| BM25 + EG2 RRF, con prefijo | 38,10% (8/21) | 76,19% (16/21) | 85,71% (18/21) | 0,5532 | 0,6291 | +17,02 pp |

Las cuatro condiciones superaron el umbral preregistrado de +5 pp nDCG@5 sin bajar MRR@5. En este fixture, el RRF plano subió nDCG@5 en 18,12 puntos y MRR@5 de 0,4079 a 0,5849 frente a BM25. Eso hace de EmbeddingGemma 2 una candidata prometedora para recuperación de código; no basta para integrarla por defecto.

La muestra por idioma también fue favorable, aunque muy pequeña. En español (n=10), BM25 tuvo nDCG@5 0,293; EG2 plano 0,626 y RRF plano 0,531. En inglés (n=11), BM25 obtuvo 0,609; EG2 plano 0,690 y RRF plano 0,739. Son resultados de las mismas consultas usadas para el screening, no una validación independiente.

## Tiempo y recursos

- Corrida válida completa: 20,13 s; 60/60 solicitudes HTTP devolvieron 200 y 768 dimensiones finitas.
- Indexación de 519 documentos: 10,07 s sin prefijos y 8,79 s con prefijos.
- Latencia por consulta (21 solicitudes individuales): mediana 5,30 ms y p95 6,94 ms sin prefijos; mediana 5,41 ms y p95 6,94 ms con prefijos.
- Pico observado: 708 MiB de VRAM del proceso en GPU física 1 y 2.238 MiB RSS. La GPU física 0 quedó oculta durante la corrida puntuada.
- El límite de interés del usuario es 30 min por corrida; esta corrida completa quedó muy por debajo.

## Intento inválido y corrección de huella

El intento 1 quedó preservado en `receipts/attempt-01/`. El servidor devolvió HTTP 500 porque la configuración efectiva había reducido el batch físico a 512 y una entrada de 538 tokens no cabía. Se clasifica como **inválido por infraestructura**, sin score de EmbeddingGemma. El retry conservó modelo, runtime, GPU y fixture; fijó batch/ubatch a 2048 y completó las 60 llamadas.

Una verificación de aislamiento detuvo un arranque de preflight que, aunque apuntaba a GPU 1, había creado un contexto de 256 MiB en GPU 0. Ese proceso se apagó antes de puntuar. La corrida válida ocultó GPU 0 con `CUDA_VISIBLE_DEVICES=1`. Los logs y la secuencia están en `receipts/attempt-02/`.

El primer JSON de resumen arrastró `--device CUDA1` en el texto de huella, aunque el comando puntuado usó `CUDA_VISIBLE_DEVICES=1 --device CUDA0`. Se conserva la huella generada originalmente (`76be2412…`) y se registra la huella corregida (`550580ecaaf965cbc4aee3d7fc577a99ba3294f907b596dd48a395016ad579a0`) en `fingerprint-correction.json`; weights y mediciones no cambiaron.

## Decisión y límites

Dejar EmbeddingGemma 2 como **candidata provisional para un sidecar de búsqueda de código**. El modo plano ya es compatible con las solicitudes string-only actuales de `AgentToolRunner`; en la muestra medida, tanto búsqueda vectorial como RRF mejoraron sobre BM25. Los prefijos requieren que LlamaCode distinga queries de documentos y los agregue al llamar a embeddings, por lo que no son comportamiento actual del harness.

La corrida fue un screening único, determinista, sobre 21 consultas seleccionadas manualmente. Hace falta un holdout más grande y no solapado, luego una prueba E2E con `AgentToolRunner` que cubra caché, RRF, fallback y latencia con el índice del repo completo. No se probó reranking, truncamiento MRL a 128/256/512 dimensiones, ni multimodalidad. Aunque el model card describe espacio compartido para texto, código, imagen, audio y video, LlamaCode hoy manda strings al endpoint de embeddings. El soporte multimodal de llama.cpp usa contenido tipado anidado; el autor de [issue #30082](https://github.com/ggml-org/llama.cpp/issues/30082) corrigió su reporte y confirmó que el payload válido pone `content` dentro de cada elemento de `input`. Nada de eso se evaluó en esta corrida.

El 78,68 de MTEB Code de Google corresponde al modelo full-precision y a la suite oficial; no se debe trasladar a este GGUF Q8 ni al harness local. [Resultados del model card](https://huggingface.co/google/embeddinggemma-2#benchmark-results).

## Artefactos

- `PLAN.md`, `fixture-manifest.json`, `corpus.jsonl`, `queries.jsonl`, `qrels.jsonl`.
- `receipts/attempt-01/`: fallo de configuración y rankings BM25 parciales.
- `receipts/attempt-02/`: resumen, rankings por consulta, vectores f32, 60 recibos HTTP, logs, configuración efectiva y corrección de fingerprint.
- Peso y runtime preservados fuera del repo en `/media/cristian/Disco local/LlamaCode-cache/embeddinggemma2-eval/`; descargas verificadas y hashes en `download-manifest.json`.
