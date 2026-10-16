# Resultados — Q-20261016-PLUMBSEARCH-INTEGRATION

Fecha: 2026-10-16. Estado: **integración validada; comparación real de relevancia bloqueada por falta de endpoints locales**.

## Cambios aplicados

- `LLAMACODE_PLUMBSEARCH_URL` agrega PlumbSearch por su API JSON `/search?format=json`; si también existe `LLAMACODE_SEARXNG_URL`, PlumbSearch tiene precedencia.
- Configurar PlumbSearch activa automáticamente el modo local: exige endpoint loopback, evita el proxy del sistema y falla cerrado ante error, cero resultados o redirects. No recurre a DuckDuckGo, Bing ni Google.
- `LLAMACODE_WEB_SEARCH_MODE=local-only` aplica la misma restricción a un SearXNG loopback. `auto`/`default` mantienen el comportamiento anterior; un valor desconocido devuelve un error de configuración.
- La búsqueda usada por `web_search`, `deep_research` y la pantalla Investigación comparte la selección del endpoint. Investigación también desactiva proxy/redirects en modo local.
- README, guía de configuración, descripción de tool y matriz de evaluación actualizados. El proveedor por defecto y los perfiles no cambian; tampoco se cambia `web_fetch`, Browser/MCP o HarnessSpec.

La política protege contra que **LlamaCode reenvíe la consulta** a un buscador público cuando el proveedor local falla. No inspecciona el tráfico propio del nodo. PlumbSearch describe su API local y sus puertos en la [guía para apps locales](https://github.com/SueHeir/plumb-search/blob/main/docs/local-llms.md); su nodo Docker puede unirse a la red y sincronizar/crawlear según sus [documentos Docker](https://github.com/SueHeir/plumb-search/blob/main/docs/docker.md). Para esta tarea no instalé ni inicié ese servicio.

## Validación

- `./scripts/build-linux.sh Debug`: exit 0. Binario: `/home/cristian/.cache/llamacode/build_linux/LlamaCode`, SHA-256 `38d2b916c7c2b08061a2a59eb9b0b120247b19768aed454f4a6992e53ed48959`.
- `./scripts/tests-linux.sh Release`: exit 0, **90/90 CTest pasaron**. `test_agent_tools`: **54 pasaron, 0 fallaron, 1 omitido** (validación exclusiva de Windows). Log crudo y hashes: [receipts](receipts/).
- Las regresiones cubren compatibilidad JSON, precedencia PlumbSearch sobre SearXNG, respuesta vacía sin fallback público, rechazo de endpoint remoto y bloqueo de redirects.
- El comparador corrió un self-test con dos APIs fixture de loopback: 30 casos × 2 stubs (60 solicitudes), MRR@5 sintético de 1,0 y 0,0. Esto valida el cálculo, **no** compara la calidad de los productos.
- `git diff --check`: sin errores.

## Comparativa de proveedores

Preparé un holdout fijo de 30 consultas técnicas y un script que mide hit-rate@3, MRR@5, nDCG@5, recall@5, diversidad de hosts, latencia p50/p95 y errores: [consultas](queries.json), [comparador](../../../scripts/compare-local-search.py), [preregistro](PLAN.md).

El preflight de `127.0.0.1:7586` (PlumbSearch) y `127.0.0.1:8080` (SearXNG) obtuvo `Connection refused` en ambos puertos. El comparador guardó `status=blocked` y **0 consultas enviadas** en [comparison.json](receipts/comparison.json). Por lo tanto, no hay puntajes de relevancia, frescura o latencia reales para comparar; no son cero y no prueban inferioridad. No contacté nodos públicos ni instalé/arranqué crawlers.

Para completar la comparación cuando ambos servicios loopback estén disponibles:

```bash
python3 scripts/compare-local-search.py \
  --plumb-url http://127.0.0.1:7586 \
  --searxng-url http://127.0.0.1:8080 \
  --cases artifacts/evaluacion-modelos-llamacode/Q-20261016-PLUMBSEARCH-INTEGRATION/queries.json \
  --output artifacts/evaluacion-modelos-llamacode/Q-20261016-PLUMBSEARCH-INTEGRATION/receipts/comparison.json
```

## Reproducibilidad

- [Plan](PLAN.md)
- [Holdout](queries.json)
- [Guía de uso](../../../docs/web-search-providers.md)
- [Resumen de pruebas y SHA-256](receipts/test-summary.json)
- [Log completo de CTest](receipts/LastTest.log)
- [Self-test del comparador (fixtures)](receipts/comparator-selftest.json)
- [Preflight y resultado de comparación](receipts/comparison.json)
