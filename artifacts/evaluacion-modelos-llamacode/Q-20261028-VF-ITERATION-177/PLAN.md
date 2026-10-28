# Q177 — Revalidación de gates IA y reconciliación de estado

## Alcance

Continuar VF-20261019-01 revisando si los pendientes de IA todavía están bloqueados. Revalidar dos gates que pueden cambiar de estado: soporte dual de Strata Qwen3.6-35B-A3B y el contrato MCP de autorización. Corregir el registro local y la pestaña `Accionables` si hay evidencia nueva.

## Método

- Solo lectura de fuentes primarias, código, pruebas existentes, inbox/actionables y estado de procesos/puertos.
- No descargar, compilar, iniciar modelos ni usar GPU; no hay una prueba de calidad o velocidad habilitada por los gates actuales.
- Preservar los perfiles ASTRA, SOL, Flash-Next y los modelos PeritoSoft.
- Mantener como pendiente cualquier prueba que requiera una policy real del servidor MCP, una release dual-GPU, un target/oráculo propio o una sesión Windows nativa.

## Prerregistro y límites

Este es un audit de elegibilidad, no un benchmark. No crear un principal tenant, datos, credenciales ni un fixture que no exista. No inferir autorización del servidor MCP a partir de `_meta`.
