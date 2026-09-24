# Campaña experimental de reasoning, prefijo e imágenes

Esta campaña agrega mediciones reproducibles para decidir si conviene cambiar
el harness o un perfil. Ninguna variante se promueve sólo por reducir tokens:
debe conservar corrección, seguridad y estabilidad.

## Runners

Los tres runners hablan con cualquier endpoint OpenAI-compatible y dejan un
JSON con las muestras individuales:

```bash
python3 tools/benchmark_reasoning_budget.py \
  --url http://127.0.0.1:8080/v1/chat/completions \
  --model Qwen3.5-9B-Q4_K_M --passes 3 \
  --out artifacts/reasoning-budget-20260923.json

python3 tools/benchmark_image_history.py \
  --url http://127.0.0.1:8080/v1/chat/completions \
  --model Qwen3.5-9B-Q4_K_M --passes 3 \
  --out artifacts/image-history-20260923.json

python3 tools/benchmark_prefix_loop.py \
  --url http://127.0.0.1:8080/v1/chat/completions \
  --model Qwen3.5-9B-Q4_K_M --turns 6 --passes 3 \
  --out artifacts/prefix-loop-20260923.json
```

`benchmark_reasoning_budget.py` barre 0/512/1024/2048/4096/8192 tokens y
puntúa únicamente marcadores versionados. El corpus por defecto es
`reasoning_budget_v2.json`; `reasoning_budget_v1.json` queda conservado para
reproducir la corrida histórica. `benchmark_image_history.py` mide
el costo de conservar 0/1/2 capturas recientes con historiales de 1/2/5/10
imágenes. `benchmark_prefix_loop.py` compara el wire append-only actual
(`rolling-tool`) con un esquema que cambia el orden de las claves del schema;
si el endpoint no informa tokens cacheados, lo declara explícitamente como
`cacheMetricsAvailable=false`.

## Gates

- Reasoning: ningún presupuesto candidato puede bajar el éxito por categoría;
  la latencia sólo se acepta si la mejora de calidad compensa el costo.
- Imágenes: `keepLastImages` sólo cambia si reduce prompt/TTFT sin perder la
  capacidad visual necesaria. El benchmark no convierte un endpoint text-only
  en un falso cero de calidad visual.
- Prefijo: `rolling-tool` sólo puede justificar una implementación específica
  si el servidor informa reutilización real del KV/prefijo y el ahorro se
  repite en al menos cinco pasadas. Sin esa métrica, el resultado es no
  concluyente.

## Resultado real y decisión aplicada

La corrida real se hizo con Qwen3.5-4B Q4_K_M + mmproj BF16, dos RTX 3090,
contexto 16K, KV Q8 y una sola ranura:

- `reasoning_budget=0`: 15/18 en tres pasadas; el único caso fallido por tarea
  era el scorer de seguridad, que penalizaba mencionar “enviar” aunque la
  respuesta recomendara no hacerlo.
- `reasoning_budget=128/256/512`: 0/54; las respuestas visibles agotaron el
  límite de 384 tokens y la latencia subió a aproximadamente 2,4 s.
- Historial de imágenes: 100% de transporte; retener 0/1/2 imágenes no
  produjo una mejora consistente de prompt o latencia. No se cambia el
  comportamiento global de `keepLastImages`.
- Prefix loop, cinco pasadas: `rolling-tool` 207,38 ms contra 206,03 ms para
  la variante inestable; ambos reutilizaron 371,5 de 464,5 tokens. No se
  implementa una política específica nueva de `rolling-tool`.

La conclusión aplicada es mantener reasoning positivo como experimento
explícito, conservar el trimming de imágenes existente sin promover una nueva
política global y no agregar checkpointing `rolling-tool` específico. El corpus
v2 puntúa la acción segura (`revisar`, `guardar`, `borrador`) y permite explicar
por qué no se debe ejecutar la acción externa.

El benchmark existente de compactación y el de orden de Computer Use completan
esta campaña. Sus resultados del 2026-09-23 no promovieron cambios globales:
la compactación puede perder marcadores en modelos pequeños y el sandwich de
Computer Use mejora seguridad en prompts difíciles, pero agrega entre 20,9% y
29,7% de latencia frente a `state-first`.

## Pruebas offline

```bash
python3 -m unittest \
  tests.test_reasoning_budget \
  tests.test_image_history \
  tests.test_prefix_loop \
  tests.test_compaction_quality_matrix \
  tests.test_harness_matrix
```
