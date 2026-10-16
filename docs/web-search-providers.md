# Proveedores de búsqueda web

LlamaCode admite DuckDuckGo HTML como default, SearXNG JSON y PlumbSearch mediante
el contrato compatible con SearXNG. No instala ni inicia motores de búsqueda.

## Elegir un proveedor

PlumbSearch de escritorio escucha por defecto en `127.0.0.1:7586`; una instancia
Docker suele publicar `127.0.0.1:8080`. Definir antes de iniciar LlamaCode:

```bash
export LLAMACODE_PLUMBSEARCH_URL=http://127.0.0.1:7586
```

En Docker, publicar el puerto sólo en loopback del host (por ejemplo,
`127.0.0.1:8080:8080`) para que otros equipos de la red no puedan usar el nodo.

Esta variable selecciona PlumbSearch sobre SearXNG y usa
`/search?q=...&format=json`. El endpoint debe ser loopback. PlumbSearch falla
cerrado ante error, redirect o respuesta sin resultados: LlamaCode no reenvía la
consulta a DDG, Bing ni Google.

Para SearXNG se conserva:

```bash
export LLAMACODE_SEARXNG_URL=http://127.0.0.1:8080
```

Sin política estricta, el comportamiento existente sigue activo: si SearXNG falla
o devuelve cero resultados, `web_search` puede usar DuckDuckGo. Para evitar ese
fallback con cualquier endpoint configurado, usar:

```bash
export LLAMACODE_WEB_SEARCH_MODE=local-only
```

`local-only` sólo acepta URL HTTP(S) loopback, no sigue redirects y devuelve el
error local sin buscar en servicios públicos. Se requiere configurar PlumbSearch o
SearXNG; con PlumbSearch la política se activa automáticamente. Los valores
`auto`/`default` mantienen el modo anterior; cualquier valor desconocido falla
cerrado con un mensaje de configuración.

`web_search`, `deep_research` y la Investigación de la aplicación comparten la
selección de endpoint. `web_fetch` sigue siendo otro paso: descarga las páginas
seleccionadas y mantiene sus controles SSRF, límites y extracción. La garantía de
`local-only` cubre el fallback de búsqueda de LlamaCode; no inspecciona ni limita
el tráfico propio del nodo configurado. PlumbSearch indica que su API local
responde desde el índice del nodo; su sincronización/crawling P2P pertenece al
servicio Plumb.

## Comparación local de relevancia

El comparador estático usa 30 consultas técnicas con una URL primaria esperada:

```bash
python3 scripts/compare-local-search.py \
  --plumb-url http://127.0.0.1:7586 \
  --searxng-url http://127.0.0.1:8080 \
  --cases artifacts/evaluacion-modelos-llamacode/Q-20261016-PLUMBSEARCH-INTEGRATION/queries.json \
  --output artifacts/evaluacion-modelos-llamacode/Q-20261016-PLUMBSEARCH-INTEGRATION/receipts/comparison.json
```

Ambas URLs deben ser loopback. Antes de emitir consultas, el script comprueba por
TCP que los dos endpoints estén disponibles; si uno falta, guarda un recibo
`blocked` con `queries_sent: 0`. Durante la comparación envía una solicitud por
consulta/proveedor, alterna el orden, no reintenta y no sigue redirects. No descarga
las páginas de resultados. Compara URLs normalizadas por host/path e informa
hit-rate@3, MRR@5, nDCG@5, recall@5, diversidad de hosts, latencia p50/p95 y
errores. La relevancia binaria y el holdout son exploratorios; una ejecución no
autoriza a promover un default.
