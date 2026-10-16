# Resultados — Q-20261016-LOCAL-SEARCH-REVIEW

Fecha: 2026-10-16. Estado: **auditoría y prueba funcional completadas; sin adopción ni cambio de perfiles**.

## Pregunta y alcance

Evalué si las ideas del post de r/LocalLLM —un índice web local/P2P (PlumbSearch), reducir búsquedas repetidas a DDG, usar una instancia SearXNG y separar browser/MCP— mejoran los modelos, perfiles o harness de LlamaCode. La petición cubre coding/agentes, Computer Usage, Ingi-Charla, visión, contexto y rendimiento.

## Resultado por superficie

- **Coding/agentes e investigación web:** un índice local puede mejorar privacidad de consulta, autonomía y control de rate limits. PlumbSearch es candidato técnico porque su API JSON coincide con SearXNG y el cliente existente. No hay evidencia independiente de que sus resultados resuelvan mejor nuestras consultas de repos/docs/bugs; el autor reconoce menor recuperación de páginas profundas. El benchmark publicado es upstream/autoinformado, no holdout LlamaCode.
- **Hallazgo de privacidad en el camino actual:** `web_search` usa `LLAMACODE_SEARXNG_URL` cuando está configurada, pero si el servidor falla o entrega cero resultados el código vuelve a DuckDuckGo HTML. Por tanto, una configuración SearXNG local no equivale hoy a un modo local estricto: la consulta podría salir a un proveedor externo. Recomiendo un futuro modo explícito fail-closed/local-only antes de prometer privacidad. No alteré código productivo en esta evaluación.
- **web_fetch/seguridad:** el camino actual limita SSRF hacia loopback/redes privadas/metadata cloud, revalida redirects, limita el cuerpo, extrae contenido legible y puede escalar a Playwright MCP/Camofox. El contenido remoto sigue siendo entrada no confiable; un índice local no reemplaza estas guardas ni resuelve por sí solo prompt injection.
- **Browser/Computer Usage:** browser/MCP sirve para leer o interactuar con una página que el agente tiene que abrir; no sustituye un índice de búsqueda ni mejora por sí mismo el control general de la PC. La búsqueda del post no justifica tocar el backend universal de CU.
- **Ingi-Charla/audio y visión:** no hay transferencia directa. No se ejecutó modelo, imagen, ASR, TTS ni GUI; una API de búsqueda textual no acredita esas modalidades.
- **Contexto y rendimiento:** un índice podría reducir consultas repetidas y cambiar tokens de snippets, pero no medimos calidad, latencia, tokens ni estabilidad en LlamaCode. No hay base para alterar contextos, sampling, cuantización o ranking productivo.
- **LLMSearch:** no integrar como default. Su README describe un agregador de endpoints mayormente públicos, hasta ocho motores en modo avanzado y rate limiting de DDG; el broad fan-out necesita auditoría de código, privacidad, carga y licencias antes de habilitarlo.

## Pruebas ejecutadas

- Añadí la regresión `AgentToolsTests::webSearch_usesConfiguredSearxngJsonApi` en `tests/test_agent_tools.cpp`: levanta un QTcpServer loopback que devuelve un fixture JSON compatible con SearXNG, configura `LLAMACODE_SEARXNG_URL` sólo durante el caso, despacha `web_search` y verifica título/URL/snippet y que hubo exactamente una solicitud `/search` con `q` y `format=json`.
- Corrí el gate completo final `./scripts/tests-linux.sh Release`: salida 0; **90/90 CTest pasaron**. `test_agent_tools`: 50 pasaron, 0 fallaron, 1 omitido (comprobación de nombres de lanzamiento sólo Windows); el nuevo caso pasó.
- El log crudo queda en `receipts/LastTest.log`; resumen, comando, hashes y conteos en `receipts/test-summary.json`.

Esta regresión prueba el contrato HTTP/JSON contra un fixture local. **No** prueba el ranking/calidad real de SearXNG o PlumbSearch, un nodo Plumb desplegado, la privacidad de red de un tercero, el fallback de fallo/cero resultados ni calidad de agente. No hice consulta a proveedores de búsqueda, GPU, inferencia ni descargas.

## Decisión

Mantener el camino actual y los perfiles. No cambiar HarnessSpec, perfiles, sampling, `web_fetch` ni navegador a partir de testimonios del hilo. Registrar PlumbSearch como candidato optativo para un piloto local: el contrato SearXNG es compatible; su cobertura, frescura, seguridad, costo operativo y relevancia en nuestras consultas están **no evaluados**. Tratar LLMSearch como opción documental, no como componente de producción.

## Próxima evidencia útil

Si se prioriza un piloto: usar un nodo Plumb local fijado por commit y el SearXNG actual, con un holdout etiquetado de 30–50 consultas de código, documentación, issues y consultas abiertas. Medir nDCG@5/MRR@5/Recall@5, dominio/frescura, duplicados, latencia p50/p95, errores y fan-out; guardar resultados crudos. Incluir consultas sensibles sintéticas y una prueba de fallo del servidor para comprobar modo fail-closed. Hacer tres repeticiones sólo donde se mida variabilidad temporal. No repetir el fixture loopback para reclamar una mejora de relevancia.

## Reproducibilidad y artefactos

- Pre-registro: [PLAN.md](PLAN.md).
- Revisión de fuentes y commits: [receipts/source-review.md](receipts/source-review.md).
- Test summary y CTest raw log: [receipts/test-summary.json](receipts/test-summary.json), [receipts/LastTest.log](receipts/LastTest.log).
- Fingerprint funcional: test `AgentToolsTests::webSearch_usesConfiguredSearxngJsonApi`; SHA-256 del archivo de test en `receipts/test-summary.json`. No existe fingerprint de modelo/perfil/HarnessSpec ni seed porque no hubo inferencia.
