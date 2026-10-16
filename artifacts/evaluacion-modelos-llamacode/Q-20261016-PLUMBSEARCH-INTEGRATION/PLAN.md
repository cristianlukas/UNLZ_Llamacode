# Preregistro — integración y comparación de búsqueda local

Fecha: 2026-10-16. Task `Q-20261016-PLUMBSEARCH-INTEGRATION`.

## Alcance

- Agregar PlumbSearch opcional a `web_search`, `deep_research` e Investigación mediante su API JSON compatible con SearXNG.
- Agregar `LLAMACODE_WEB_SEARCH_MODE=local-only`: sólo endpoint loopback, sin fallback a buscadores públicos y sin seguir redirecciones. Configurar `LLAMACODE_PLUMBSEARCH_URL` selecciona PlumbSearch y aplica esa política automáticamente.
- Mantener intacto el comportamiento por defecto cuando no se configura PlumbSearch ni `local-only`.
- Añadir regresiones para selección del proveedor, URL/API y ausencia de salida a proveedores públicos en caso vacío o endpoint no local.

## Comparación de relevancia

Comparar PlumbSearch y SearXNG usando exactamente las mismas 30 consultas de `queries.json`, en serie, una solicitud por consulta/proveedor, `/search?format=json`. No descargar páginas ni consultar nodos públicos. Ambos endpoints deben estar configurados y disponibles por loopback antes de enviar la primera consulta; si falta alguno, se registrará `blocked` con cero consultas.

La relevancia es binaria por URL oficial esperada, normalizada por host y path (se ignoran query y fragment), con corte top-5. Métricas: hit-rate@3, MRR@5, nDCG@5, recall@5, hosts únicos promedio@5 y latencias p50/p95. Es un primer holdout técnico; una pasada no demuestra estabilidad ni reemplaza consultas de agente reales.

## Límites

- No instalar, clonar ni iniciar nodos/crawlers; usar sólo instancias loopback ya disponibles.
- No usar endpoints públicos ni consultas de usuario. El nodo Plumb local puede mantener su propio tráfico de indexación/intercambio de páginas; el modo de LlamaCode sólo garantiza que una consulta fallida no se reenvíe a DDG/Bing/Google.
- Sin GPU, modelo, perfiles, HarnessSpec ni fetch de resultados.
