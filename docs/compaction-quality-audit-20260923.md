# Auditoría de compactación y contexto cuantizado — 2026-09-23

## Pregunta

Se evaluó si la tesis externa —una ventana operativa más corta con
compactación puede superar a conservar un contexto largo en modelos
cuantizados— justifica cambiar LlamaCode, Ingi Charla, Computer Use o los
perfiles de modelo.

La métrica principal no fue el número de tokens ahorrados. Se midió si la
sesión conserva restricciones durables después de cinco resets y si la primera
acción posterior sigue siendo correcta. También se registraron tokens de prompt,
tokens cacheados, prefill, decode y tiempo de pared.

## Método reproducible

`tools/compaction_quality_matrix.py` envía el mismo workload a un
`llama-server` OpenAI-compatible en dos variantes:

- `raw`: conserva todo el historial y la caché de prefijo;
- `compaction`: después de cada ronda reemplaza el tramo intermedio por el
  mismo contrato JSON que usa `LlamaAgentBackend::startCompaction`.

Cada ronda agrega una restricción durable y salida ruidosa de una tool. Después
del reset se solicita una única acción (`ACTION-n`) y al final se comprueba la
retención de cinco marcadores, además de `ACTION-FINAL`.

Modelo/runtimes de esta corrida:

- Qwen3.5-4B Q4_K_M, KV K/V `q8_0`, contexto 16K, CUDA, `reasoning off`,
  `temp 0` para acciones y `temp 0.2` para compactación.
- Qwen3.5-9B Q4_K_M, misma receta y contexto.

No se mezclaron estos resultados con BCB/HE20: esta es una prueba de memoria de
trabajo y recuperación, no una promoción de modelo.

## Resultados

| Modelo | Pasadas | Acción posterior | Retención final raw | Retención final compactada | Lectura |
|---|---:|---:|---:|---:|---|
| Qwen3.5-4B Q4 | 3 pares | 100% / 100% | 3/3 | 2/3 | una compactación produjo un resumen sin marcadores; no promover |
| Qwen3.5-9B Q4 | 2 pares | 100% / 100% | 2/2 | 2/2 | conserva la información, pero paga el costo de cinco resúmenes |

En Qwen3.5-4B, la variante compactada mantuvo la acción local en las 15/15
rondas, pero retuvo todas las restricciones sólo en 2/3 corridas. En la corrida
fallida se perdió la estructura útil del primer resumen y el resultado final no
recuperó ningún marcador.

En Qwen3.5-9B, las dos corridas compactadas conservaron los cinco marcadores,
pero el control raw terminó con aproximadamente 3.071 tokens de prompt y la
variante compactada con 329–448 tokens en la consulta final. El ahorro de
contexto no fue gratis: la compactación agregó cinco prefills completos y la
consulta final compactada tuvo una mediana de pared de aproximadamente 1,32 s
frente a 0,67 s del control en esta máquina. El beneficio de memoria no
superó el costo temporal en este workload corto.

Artefactos completos:

- `artifacts/compaction-quality-20260923-qwen35-4b-r3.json`
- `artifacts/compaction-quality-20260923-qwen35-9b-r2.json`

## Decisión por subsistema

### Harness

La política actual queda sin cambios: compactación alrededor de 90% del
presupuesto efectivo, `tailRatio=0.60`, resumen JSON, transcript inmutable y
anti-loop por estancamiento. Se agrega sólo telemetría separada:
`compactions`, `compactionFallbacks` y `compactionMs`, persistida en
`contextStats` y expuesta junto a `efficiencySummary`. Antes,
`prunedMessages` mezclaba poda determinista con compactaciones y no permitía
contar resets limpiamente.

No se baja el umbral a 128K ni se fuerza compactación temprana: los resultados
no muestran una mejora universal y el modelo pequeño exhibió pérdida de memoria
durable.

### Computer Use

No se cambia. La ruta de Tasks evita compactar durante la ejecución autónoma y
recorta capturas viejas; esa decisión protege el estado operativo de ventanas,
controles y acciones. Una compactación puede conservar una narrativa coherente
y aun así perder el identificador exacto del control que debe usarse.

### Ingi Charla

No se cambia el perfil. Charla mantiene una ventana deliberadamente limitada y
prioriza latencia; el warmup/prefix-cache y el diálogo por turnos son más
relevantes que acumular un transcript largo. Compactar durante una conversación
de voz debería requerir una medición acústica y de latencia separada.

### Modelos y perfiles

No se promueve ningún modelo ni se cambia sampling/contexto. La evidencia
previa del proyecto ya separa contexto operativo diario (64K–131K), techos
validados (196K–262K) y calidad agentiva; esta prueba no reemplaza la escalera
HE0 → HE20 → BCB. Se conserva KV `q8_0`/FP8 y prefix-cache estable.

## Próximo criterio de promoción

Una futura variante de compactación sólo podrá promoverse si, con al menos cinco
pasadas por modelo/perfil y la suite agentiva congelada:

1. retiene restricciones y artefactos críticos en el primer paso posterior;
2. no baja éxito funcional ni calidad HE20/BCB;
3. registra la cantidad de compactaciones y fallbacks por sesión;
4. compensa el prefill perdido, o demuestra un ahorro de tiempo/memoria en una
   sesión que realmente alcanzaría el límite de contexto.

La conclusión actual es conservadora: **la compactación es un mecanismo de
seguridad para evitar overflow, no una mejora de calidad por sí misma**.
