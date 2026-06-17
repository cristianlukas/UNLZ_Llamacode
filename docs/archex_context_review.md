# Revision de archex para contexto de codigo local

Fecha: 2026-06-17

Repositorio revisado: https://github.com/Mathews-Tom/archex

## Resumen ejecutivo

`archex` no es un agente de codigo completo: es una capa local de seleccion y
empaquetado de contexto para que otro agente razone con mejores archivos,
simbolos y vecinos del grafo. Esa separacion encaja muy bien con LlamaCode,
porque nuestro agente nativo ya tiene loop ReAct, tools, MCP, memoria, UI,
permisos, subagents y perfiles. Lo valioso no es reemplazar el agente por
archex, sino endurecer `hybrid_search` hasta convertirlo en un "context scout"
deterministico, auditable y persistente.

LlamaCode ya implementa la idea central en `AgentToolRunner::hybrid_search`:
ranking lexical, embeddings via `llama-server`, fusion RRF, rerank opcional,
`token_budget` y expansion simple por imports/includes. Para el estado actual,
eso es suficiente como MVP integrado y evita meter una dependencia Python/ONNX
pesada en el producto base.

## Ideas que conviene tomar

### P0 - Recibo de contexto

archex devuelve el bundle junto con un recibo: freshness del indice, revision,
candidatos omitidos, si el contexto esta completo o incompleto, edges cortados y
proxima accion recomendada.

En LlamaCode `hybrid_search` hoy devuelve texto util, pero el modelo no recibe
una explicacion estructurada de lo que falta. Conviene extender el resultado con
un bloque final estable:

- `freshness`: `live-scan` por ahora; futuro `clean|stale|dirty`.
- `returned`: archivo, linea, score/fuente (`bm25`, `vector`, `rerank`).
- `skipped`: por presupuesto, limite de chunks, archivo grande/binario/ignorado.
- `graph_omitted`: vecinos detectados que no entraron por presupuesto.
- `recommended_next_action`: `read_file`, `hybrid_search` con mas budget, o
  `fetch_related` cuando el grafo quedo cortado.

Impacto esperado: menos falsas certezas del agente cuando el bundle quedo
truncado o cuando una dependencia importante solo aparece como vecino.

### P0 - Presupuesto de tokens como contrato de tool

`token_budget` ya existe, pero el schema y el prompt deberian empujarlo como
camino principal para exploracion. En modelos locales, pedir `k` fijo es peor:
un chunk largo puede comerse el contexto o un chunk chico puede dejar capacidad
sin usar.

Propuesta:

- en el schema de `hybrid_search`, documentar `token_budget` como parametro
  preferido y sugerir defaults por tarea;
- devolver `used_tokens_est`, `remaining_budget_est` y `budget_cut=true|false`;
- si `budget_cut=true`, listar el primer candidato no incluido.

Impacto esperado: mejor uso de ventanas 16k-64k sin depender de que el modelo
calcule contexto a ojo.

### P1 - Indice persistente repo-local

archex guarda estado en `.archex/` y separa `init`, `index`, `status/doctor` y
`query`. LlamaCode hoy hace live scan hasta 800 chunks y cachea embeddings por
hash de texto, pero no mantiene un indice estructural persistente del proyecto.

Para LlamaCode conviene una version incremental y nativa:

- carpeta `.llamacode/context/` o `AppLocalData/context/<repo-hash>/`;
- SQLite con archivos, mtimes, hashes, chunks, imports/includes y scores
  lexicales precomputables;
- invalidacion por mtime/hash;
- `context_status` o extension de `hybrid_search` que avise si el indice esta
  ausente, limpio o stale.

Impacto esperado: busquedas mas rapidas y reproducibles en repos medianos/grandes,
sin perder el modo live-scan como fallback.

### P1 - Expansion de grafo con edges tipados

La expansion actual parsea imports/includes por regex y lista vecinos por basename.
Es barata y funciona, pero produce pocos datos de confianza. archex aporta la idea
de edges con procedencia y confianza.

Propuesta pragmatica:

- mantener regex como fallback;
- guardar edges `imports`, `includes`, `qml-import`, `cmake-source`,
  `test-target`;
- incluir `source_file`, `target_file`, `reason` y `confidence`;
- priorizar vecinos test/source: si el hit cae en `src/foo.cpp`, subir
  `tests/test_foo.cpp`; si cae en un test, subir el modulo probado.

Impacto esperado: mejores bundles para tareas de cambio de comportamiento y tests.

### P1 - Scout/fetch en dos pasos

archex separa `scout` (mapa compacto con handles) de `fetch` (contenido exacto).
LlamaCode puede simular esto sin cambiar toda la UI:

- `hybrid_search(mode:"scout")`: devuelve arbol compacto, handles y recibo.
- `hybrid_search(mode:"bundle")`: comportamiento actual.
- `read_file` ya cubre el fetch por archivo/rango; a futuro sumar handles de
  chunk para evitar que el modelo copie paths y offsets manualmente.

Impacto esperado: el agente explora barato primero y solo lee detalle cuando hay
evidencia suficiente.

### P2 - Benchmark de recuperacion de contexto

archex publica un harness comparativo con recall, eficiencia de tokens y latencia.
LlamaCode ya tiene benchmarking de modelos/agente, pero no uno enfocado en
recuperacion de archivos requeridos.

Propuesta:

- fixture con 10-20 tareas de repo local: query, archivos requeridos, archivos
  distractores;
- medir `required_file_recall`, `missed_required_file_rate`,
  `returned_tokens_est`, latencia y `budget_cut`;
- comparar `grep`, `search_docs`, `semantic_search`, `hybrid_search`.

Impacto esperado: evitar que `hybrid_search` parezca bueno solo por demos chicas.

## Lo que no conviene copiar

- No conviene depender de archex como proceso externo obligatorio: mete runtime
  Python, ONNX/FastEmbed/tree-sitter y packaging adicional en una app C++/Qt que
  busca ser autocontenida.
- No conviene agregar telemetria ni metricas opt-in complejas ahora. Si se mide,
  que sea local, borrable y orientado a debug/benchmark.
- No conviene reemplazar memoria/RAG de LlamaCode por archex. archex resuelve
  contexto de codigo; `MemoryStore`/`GraphStore` cubren conocimiento durable del
  proyecto y conversaciones.
- No conviene prometer "determinismo total" mientras dependamos de embeddings y
  rerank del `llama-server` activo. Podemos prometer determinismo BM25/live-index
  y reportar cuando vector/rerank entraron en la mezcla.

## Plan recomendado

1. Agregar recibo estructurado al output de `hybrid_search` y testear casos de
   truncado por budget/chunks. **Pendiente**.
2. Mejorar schema/prompt de `hybrid_search` para priorizar `token_budget`.
   **Pendiente**.
3. Persistir indice repo-local minimo: archivos, hashes, chunks e imports.
   **Pendiente**.
4. Expandir dep-graph con edges tipados y heuristica source/test. **Pendiente**.
5. Sumar benchmark de recuperacion de contexto contra fixtures. **Pendiente**.
