# Índice y grafo de contexto del agente

LlamaCode mantiene un índice local, descartable y regenerable para que el agente
pueda explorar un repositorio por evidencia antes de editarlo. Está inspirado en
las ideas de Graft y archex, pero forma parte del backend nativo Qt/C++ y no
requiere Node, Python, ONNX ni un servicio externo.

## Capas

- `ProjectBrain`: inventario liviano de rutas, tamaños, fechas y hashes.
- `ContextIndex`: chunks persistentes, frescura, handles y edges de imports.
- `CodeGraphIndexer` + `GraphStore`: grafo estructural y conocimiento persistente
  existente, que no se reemplaza.
- `KnowledgePacket`: une hechos de `MemoryStore` con el vecindario relevante del
  grafo y devuelve un recibo compacto para el prompt o la tool.
- `hybrid_search` / `repo_slice`: búsqueda BM25 + embeddings opcionales + RRF y
  reranking cuando el server los expone.
- `context_scout`: exploración compacta con presupuesto y recibo.
- `context_fetch`: lectura exacta de un rango, validada contra el hash del archivo.

El índice de chunks vive en `AppLocalData/LlamaCode/context/<repo-hash>.sqlite`.
Puede borrarse sin perder código, sesiones ni memoria; la siguiente consulta lo
reconstruye. Los chunks no se envían a ningún proveedor salvo que el resultado se
inyecte en una petición del modelo configurado.

## Grafo con evidencia

Cada edge generado por `CodeGraphIndexer` conserva `SourceRef` con ruta relativa,
rango de líneas y SHA-256 del archivo. Las relaciones creadas por el agente
pueden agregar las mismas referencias mediante la API C++. `graph query` mantiene
la salida Markdown para compatibilidad y acepta `format: "packet"` para devolver
`nodes`, `edges`, `sources` y un `receipt`; cada edge incluye `verified` o
`unreviewed` y sus citas `ruta:Línea-Línea`. Una relación no revisada no debe
presentarse como un hecho confirmado.

`graph doctor` valida el JSONL, detecta edges huérfanos, líneas inválidas y
fuentes cuyo hash ya no coincide. Es una comprobación de salud, no una migración:
el JSONL append-only sigue siendo legible por versiones anteriores. Después de
`write_file` y `edit_file`, el backend actualiza ProjectBrain, ContextIndex y
CodeGraphIndexer también en Release; la selección de icono Debug no participa en
esa ruta.

`KnowledgePacket::build()` combina el recall de memoria con edges cuyo nombre
coincide con la consulta. Sus límites (`maxFacts`, `maxEdges`, `maxChars`) son
parte del módulo `knowledge` de `HarnessSpec`; está apagado por defecto para
conservar el presupuesto histórico. Al activarlo, el system prompt instruye al
modelo a distinguir evidencia verificada de inferencias y a citar las fuentes.

## Contrato de exploración

`context_scout` devuelve rangos, previews, handles y un `context-receipt` con:

- `freshness` y `indexRevision`;
- archivos devueltos y omitidos;
- vecinos del grafo y vecinos cortados;
- `usedTokensEst`, `remainingBudgetEst` y `budgetCut`;
- `recommendedNextAction`.

Un handle `ctx:...` sólo sirve mientras el hash del archivo siga coincidiendo.
Si el archivo cambió, `context_fetch` lo rechaza y pide ejecutar nuevamente el
scout. Así los rangos no se convierten en evidencia silenciosamente obsoleta.

## Modos del harness

El módulo `context` del `HarnessSpec` conserva los defaults históricos y permite:

- `preflight`: prepara contexto antes del primer turno;
- `indexPolicy`: `off`, `lazy` o `eager`; `off` evita la indexación automática y el
  preflight, pero las tools explícitas pueden construir una caché bajo demanda;
- `scoutBudget`: presupuesto inicial del scout;
- `scoutK`: cantidad máxima de rangos;
- `graphExpansion`: incluir vecinos estructurales.

El módulo `knowledge` agrega:

- `enabled`: habilita el paquete durable en el harness;
- `preflight`: lo incluye antes del primer request;
- `citeSources`: exige citas de las fuentes disponibles;
- `maxFacts`, `maxEdges`, `maxChars`: límites explícitos del paquete.

El preflight está desactivado por defecto hasta completar el benchmark A/B. El
editor QML permite activarlo por perfil. Release mantiene el flujo histórico hasta
que las métricas demuestren una mejora sin regresiones.

## Invariantes

1. El código fuente real es la fuente de verdad; el índice es sólo una caché.
2. El retrieval debe respetar el presupuesto o declarar el corte.
3. La búsqueda estructural funciona sin embeddings ni red.
4. Toda expansión debe conservar procedencia y tipo de relación.
5. Las actualizaciones posteriores a `write_file` y `edit_file` invalidan el
   contexto afectado y refrescan el grafo estructural.
6. Las citas sólo son frescas mientras el SHA-256 de su archivo coincida.
7. El índice no concede permisos adicionales ni permite salir del workspace.

## Validación

`tests/test_context_index.cpp` cubre persistencia, chunks, edges, recibos, handles
y rechazo de handles obsoletos. `tests/test_memory_graph.cpp` cubre citas, paquetes
y `doctor`; `tests/test_code_graph.cpp` verifica rangos y hashes producidos por el
indexador. `tests/test_agent_tools.cpp` cubre la exposición de `query packet` y
`doctor` por la tool. La comparación de calidad debe medir recall de archivos
requeridos, tokens, latencia cold/warm, cortes por presupuesto y éxito de las
pruebas de la tarea.
