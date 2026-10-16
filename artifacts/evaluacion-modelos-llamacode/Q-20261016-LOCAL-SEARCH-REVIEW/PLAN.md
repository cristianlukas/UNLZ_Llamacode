# Plan — Q-20261016-LOCAL-SEARCH-REVIEW

Fecha: 2026-10-16.

## Objetivo

Evaluar si las ideas del post de r/LocalLLM sobre búsqueda web local/P2P, SearXNG, APIs de búsqueda y navegación con browser aportan algo a LlamaCode. Revisar su utilidad para coding/agentes, Computer Usage, Ingi-Charla, visión, contexto y rendimiento, sin presuponer cambios de modelo o perfil.

## Alcance y controles

- Controles existentes: `web_search` con SearXNG explícito o DuckDuckGo, `web_fetch` direct/Playwright MCP/Camofox y la búsqueda del flujo de investigación/compras que declara SearXNG o distribución DDG/Bing/Google HTML.
- Candidatos conceptuales: índice web local/P2P del post (PlumbSearch), scripts/skills LLMSearch, y browser real/MCP. Se fijarán versiones/commits antes de atribuir capacidades a esos proyectos. No se descargarán ni ejecutarán servicios de terceros.
- No hay candidato de modelo ni A/B de perfil declarado: este trabajo evalúa herramientas/arquitectura, no ranking de modelos. No cambiar HarnessSpec, perfiles productivos ni defaults.

## Pruebas previstas

1. Revisar el documento canónico, el código de búsqueda/fetch y los tests para mapear proveedores, límites, seguridad, ranking/extracción, cancelación y comportamiento ante fallos.
2. Revisar fuentes primarias actuales (repositorios y documentación de los proyectos citados). Distinguir claims comunitarios de capacidades verificadas.
3. Ejecutar las pruebas existentes directamente relacionadas con despacho web, perfiles/herramientas y seguridad del fetch. Si el harness admite fixtures locales, usar una respuesta SearXNG loopback aislada, sin cambios de configuración del usuario.
4. Ejecutar un smoke de red de una sola consulta/fetch sólo si la ruta existente y el preflight permiten hacerlo sin credenciales ni riesgo de rate-limit; no hacer reintentos automáticos ni scraping repetido.
5. Evaluar por dominio: agents/web tools, Computer Usage/browser, Ingi-Charla/audio, visión, contexto y coste/latencia/robustez. Medir pruebas de agente sólo si hay un endpoint ya disponible y aislable; no iniciar GPU/inferencia ajena.

## Criterios y límites

- Separar funciones del harness, calidad de resultados, cobertura/frescura del índice, privacidad, rate limits, latencia y mantenimiento.
- Una prueba textual de web_search no demuestra acción de Computer Usage, visión ni calidad de voz.
- Promoción requiere mejora repetible y evidencia independiente; si no hay holdout/endpoint, cerrar como auditoría documental o screening y enumerar la evidencia faltante.
- Guardar fuentes, hashes/commits, comandos, resultados crudos y limitaciones bajo este directorio; actualizar `docs/evaluacion-modelos-llamacode.md` al cierre.
