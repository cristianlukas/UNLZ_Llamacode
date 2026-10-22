# Q45 — AgentToolRunner E2E de EmbeddingGemma 2

**Cierre:** 2026-10-22 · **Decisión:** no integrar ni activar EG2 por ahora.

## Pregunta y método

Se comparó la ruta real `AgentToolRunner::hybrid_search` sin endpoint auxiliar (control BM25) y con EmbeddingGemma 2 Q8_0 vía llama.cpp b11554, sobre un snapshot aislado del HEAD `51acfeb1299231b6678bc2e9a56ba6f07254165e`. Se reutilizó el holdout Q44 de 21 consultas manuales y qrels fijados antes del experimento. Cada brazo ejecutó las 21 consultas; el candidato se repitió con la caché caliente. Se mantuvieron el límite de 800 chunks, `k=15`, la fusión RRF del código y el gate preregistrado: +0,05 nDCG@5 absoluto, sin caída MRR@5, rankings repetidos idénticos y cero embeddings de documentos en la repetición.

La extracción incluyó 5.635 de 5.639 entradas rastreadas. Se omitieron cuatro symlinks históricos que apuntan a GGUF externos; no se leyeron sus destinos. No se incluyeron cambios ajenos del working tree.

## Resultado válido · attempt-08

| Brazo | nDCG@5 | MRR@5 | Objetivos en top 5 |
|---|---:|---:|---:|
| BM25 sin endpoint | 0,0000 | 0,0000 | 0/21 |
| BM25 + vector RRF, primera pasada | 0,0300 | 0,0238 | 1/21 |
| BM25 + vector RRF, repetición | 0,0300 | 0,0238 | 1/21 |

El único objetivo recuperado fue `tests/test_agent_context_budget.cpp:281-320`: BM25 lo ubicó en rango 7 y el candidato RRF en rango 2. Los otros 20 objetivos no aparecieron en los 15 resultados devueltos. El cambio es +3,00 pp de nDCG@5; queda 2,00 pp por debajo del mínimo preregistrado, por lo que el gate de adopción falla. La auditoría independiente recalculó las métricas y coincide.

La caché envió 800 documentos en la primera pasada y cero documentos en la repetición; sólo reenvió las 21 consultas. Los 55 requests de embeddings respondieron HTTP 200. El endpoint `/rerank` devolvió HTTP 501 en 42 solicitudes porque este server de embeddings no habilita reranking; `hybrid_search` continuó con RRF. Las listas de resultados de la primera y segunda pasada fueron idénticas. Duración QtTest: 36,064 s.

Preflight: RTX 3090 GPU 1, 24.016 MiB libres, cero inference servers y puertos de prueba 8397/8398 libres. Muestra durante el trabajo: 7.950 MiB usados; la lectura postflight volvió a 108 MiB usados/24.016 MiB libres. El controlador terminó con código 0; no quedaron procesos de inferencia ni listeners de Q45. La GUI y el proceso OpenRGB quedaron intactos.

## Intentos de infraestructura

Los intentos `attempt-01` a `attempt-07` no se usan para juzgar calidad:

- `attempt-01`: la variable con la ruta del test no cruzó el scope systemd; no llegó a preflight.
- `attempt-02`: el extractor rechazó symlinks rastreados que apuntan a discos externos; no llegó a GPU. La corrección omite esos enlaces y registra sus destinos sin abrirlos.
- `attempt-03`: orden incorrecto de opciones de `timeout`; preflight pasó y no arrancó llama.cpp.
- `attempt-04` y `attempt-05`: batch físico de 2.048/8.192 insuficiente para lotes de 7.620/16.212 tokens; llama.cpp devolvió HTTP 500 y el candidato cayó a BM25. La primera limpieza con wrapper produjo doble señal y el controlador salió con -11; no quedaron procesos ni VRAM ocupada.
- `attempt-06`: batch 32.768 aceptó el tamaño, pero contexto 8.192 rechazó 16.212 tokens con HTTP 400; métricas no válidas para EG2. Se cambió a cierre directo del servidor; exit 0 y limpieza completa.
- `attempt-07`: contexto/batch 32.768 requirió 26.880,75 MiB de buffers CUDA, superior a los 24.016 MiB libres; el servidor no llegó a health-check y liberó todo.

El último intento usó contexto/batch/ubatch 16.384, suficiente para el máximo observado de 16.212 tokens. Este ajuste sólo pertenece al servidor de evaluación; no es una afirmación sobre la ventana entrenada del modelo ni cambia configuración productiva.

## Decisión y alcance

Q44 mostró una mejora amplia en un holdout aislado de 126 chunks; Q45 no la confirmó en la ruta completa actual de `AgentToolRunner`. Aunque el candidato mejoró una recuperación concreta del rango 7 al 2 y la caché funcionó, no alcanzó el gate de +5 pp y sólo devolvió 1 de 21 objetivos en el top 5. **Mantener BM25/RRF actual y no cambiar defaults ni perfiles.** Si la recuperación de código sigue siendo prioridad, el siguiente trabajo debe medir la cobertura de qrels dentro del presupuesto de 800 chunks y rediseñar la selección de candidatos antes de repetir este fingerprint; no aumentar el contexto del servidor a 32K, que pidió 26,9 GiB sólo para buffers.

Este resultado evalúa recuperación de código, no generación, calidad de agente, Flash-Next, Qwen3.8-27B, RCO, Swift ni Strata. Tampoco autoriza una conclusión de superioridad general por un único holdout.

## Evidencia

- Plan, parámetros y enmiendas: [PLAN.md](PLAN.md)
- Prerregistro/hashes: [receipts/preregistration.json](receipts/preregistration.json)
- Resultado por consulta: [attempt-08/agenttoolrunner-results.json](receipts/attempt-08/agenttoolrunner-results.json)
- Auditoría independiente: [attempt-08/independent-audit.json](receipts/attempt-08/independent-audit.json)
- Proceso, GPU, snapshot y cleanup: [attempt-08/orchestration.json](receipts/attempt-08/orchestration.json)
- Requests anonimizados por forma/longitud/hash: [attempt-08/proxy-requests.jsonl](receipts/attempt-08/proxy-requests.jsonl)
- Log del servidor y del QtTest: `receipts/attempt-08/server.log`, `receipts/attempt-08/agenttoolrunner-test.log`.
- Reconciliación Google Sheets con lectura de vuelta: `receipts/google-sheet-sync.json`; `Accionables!A43:N43` y `Evaluaciones LlamaCode!A275:J275`.
