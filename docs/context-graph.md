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
- `hybrid_search` / `repo_slice`: búsqueda BM25 + embeddings opcionales + RRF y
  reranking cuando el server los expone.
- `context_scout`: exploración compacta con presupuesto y recibo.
- `context_fetch`: lectura exacta de un rango, validada contra el hash del archivo.

El índice de chunks vive en `AppLocalData/LlamaCode/context/<repo-hash>.sqlite`.
Puede borrarse sin perder código, sesiones ni memoria; la siguiente consulta lo
reconstruye. Los chunks no se envían a ningún proveedor salvo que el resultado se
inyecte en una petición del modelo configurado.

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

El preflight está desactivado por defecto hasta completar el benchmark A/B. El
editor QML permite activarlo por perfil. Release mantiene el flujo histórico hasta
que las métricas demuestren una mejora sin regresiones.

## Invariantes

1. El código fuente real es la fuente de verdad; el índice es sólo una caché.
2. El retrieval debe respetar el presupuesto o declarar el corte.
3. La búsqueda estructural funciona sin embeddings ni red.
4. Toda expansión debe conservar procedencia y tipo de relación.
5. Las actualizaciones posteriores a `write_file` y `edit_file` invalidan el
   contexto afectado.
6. El índice no concede permisos adicionales ni permite salir del workspace.

## Validación

`tests/test_context_index.cpp` cubre persistencia, chunks, edges, recibos, handles
y rechazo de handles obsoletos. `tests/test_agent_tools.cpp` cubre la integración
de las tools con el worker del agente. La comparación de calidad debe medir recall
de archivos requeridos, tokens, latencia cold/warm, cortes por presupuesto y éxito
de las pruebas de la tarea.
