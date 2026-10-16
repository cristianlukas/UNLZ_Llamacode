# Revisión de fuentes — Q-20261016-LOCAL-SEARCH-REVIEW

Fecha de consulta: 2026-10-16. Se revisó la rama publicada indicada y se fijaron los commits para esta auditoría; no se clonó ni ejecutó software de terceros.

## Fuentes primarias

- PlumbSearch, `main` en `561a7d90a958cd1dc735c9f1583f10a334785800`: <https://github.com/SueHeir/plumb-search>.
- Guía de Plumb para LLMs locales, misma rama observada: <https://github.com/SueHeir/plumb-search/blob/main/docs/local-llms.md>.
- LLMSearch, `master` en `66f432a506470005b3a50a65adb6d4eaf2175db5`: <https://github.com/OliverGreens/LLMSearch>.
- API de SearXNG, documentación consultada 2026-10-16 (`2026.10.16+8252c0bf6`): <https://docs.searxng.org/dev/search_api.html>.
- Limitador SearXNG, documentación consultada 2026-10-16 (`2026.10.16+8252c0bf6`): <https://docs.searxng.org/admin/searx.limiter.html>.

## Hallazgos contrastados

1. PlumbSearch declara ser un índice distribuido propio, compartir lotes de rastreo P2P y servir `/search?q=…&format=json`, MCP y nodos locales. La API resulta compatible con el formato que consume LlamaCode. El propio README aclara que el índice cubre sitios (nombres, metadatos y términos de homepages) y conjuntos de páginas curados; no indexa todas las páginas. Por eso advierte que publicaciones profundas en blogs/foros son más difíciles de encontrar que con un motor full-text.
2. Plumb publica una evaluación propia, no independiente: corrida 5, build `11bab11` del 2026-10-14, 1.000 búsquedas calificadas 0–3, media 2,06; respuesta conocida #1 en 75% de 464 consultas, top 3 en 84%, mediana 0,50 s. Sirve como evidencia upstream autoinformada, no como resultado LlamaCode ni como comparación contra nuestro buscador.
3. La guía oficial de Plumb afirma que las consultas del nodo propio se resuelven localmente y no salen del equipo; el nodo público sí es remoto. Antes del uso habría que distinguir estrictamente ambas URL. No ejecutamos la aplicación para validar esta propiedad.
4. LLMSearch se presenta como un skill/CLI con extract/crawl/map/research que combina endpoints públicos y locales. Su README indica que búsqueda avanzada usa ocho motores más extracción y reconoce que DuckDuckGo HTML sufre rate limit en la mayoría de hosts. Esto puede mejorar cobertura si opera, pero no ofrece el índice distribuido autónomo del post y el fan-out podría aumentar solicitudes externas. Se revisó README, no código, dependencias, instalador ni el funcionamiento real.
5. SearXNG documenta `/search` y `format=json`; el formato JSON puede estar desactivado por instancia. La documentación del limitador explica que los motores upstream pueden marcar a SearXNG como bot y responder con CAPTCHA o bloqueo, así que una instancia propia no elimina automáticamente el problema de cuota/abuso.

Las cifras del autor de Plumb, las capacidades declaradas por ambos repos y la evidencia local se mantuvieron separadas. No se consultó el nodo público de Plumb, no se hizo scraping ni se instalaron las herramientas.
