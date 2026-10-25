# Q112 · Verificar si existe un contrato local para probar autorización tenant

## Pregunta

¿El código actual de LlamaCode lleva un principal autenticado hasta la llamada MCP y aplica autorización por recurso/tenant antes del efecto, de modo que un fixture de dos tenants pruebe comportamiento real?

## Alcance y preregistro

- Iteración `Q-20261025-VF-ITERATION-112`, lock exclusivo verificado.
- Auditoría CPU/read-only de la interfaz `AgentSession`, el request `tools/call`, el dispatch MCP y los tests cercanos.
- Antes de la inspección final, se fijan hashes de los siete archivos en `receipts/preregistration.json`.
- Criterio: sólo ejecutar/crear un fixture de dos tenants si existe una identidad confiable y una policy real en esta ruta. Si falta cualquiera, cerrar como bloqueado por contrato ausente; no inventar `tenantId`, no usar args/prompt como principal, no reportar un test cross-tenant ficticio.
- No cambiar código, no compilar, no ejecutar suite, no iniciar servidor/modelo, no usar GPU/red ni hacer side effects.

## Estado

La exploración inicial apunta al bloqueo ya descrito en Q78. La comprobación preregistrada actualizará hashes y verificará si el contrato cambió desde entonces.

## Cierre

Q112-A1 terminó el 2026-10-25 como bloqueo verificable: 6/6 checks estáticos PASS y el contrato confiable de principal/policy no existe en la ruta examinada. No se ejecutó test de comportamiento ni side effect; por eso P2.1 conserva un prerequisito concreto. Sheets quedó reconciliado; recibos en `receipts/`.
