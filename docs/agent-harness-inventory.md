# Inventario de agentes, harnesses y skills

Este inventario separa tres conceptos que no deben mezclarse:

- **Perfil de agente**: capacidades, directivas, permisos y presupuesto del
  agente (`AgentProfile`).
- **Motor de harness**: contrato de ejecución y namespace de sesiones
  (`HarnessEngine`).
- **Adapter/backend**: la conexión concreta que ejecuta el loop (`llamaagent`,
  `opencode` o `raw`).

## Perfiles de agente de sistema

Los perfiles son inmutables y viven en `AgentProfile::systemPresets()`:

| ID | Nombre | Uso | Motor efectivo |
|---|---|---|---|
| `agent-chat` | Chat liviano | Lectura/edición mínima, sin MCP ni thinking | `legacy` |
| `agent-basico` | Básico | Código con tools core | `legacy` |
| `agent-intermedio` | Intermedio | Perfil predeterminado para coding | `legacy` |
| `agent-avanzado` | Avanzado | Código, web, RAG y verificación | `legacy` |
| `agent-maximo` | Máximo | Catálogo completo y directivas completas | `legacy` |
| `agent-intermedio-next` | Intermedio · Harness Next | A/B experimental del perfil Intermedio | `next` |
| `agent-minimal` | Minimal (local-first) | Modelo chico, prompt y loop acotados | `legacy` |
| `agent-rpa` | RPA (escritorio) | UI Automation con guardrails firmes | `legacy` |

También existen perfiles de usuario creados, duplicados o importados. Sus IDs
no son catálogo fijo y pueden heredar de cualquiera de los perfiles anteriores.

## Definiciones persistentes de agente

La entidad de producto `AgentDefinitionStore` mantiene agentes creados por el
usuario en `AppLocalData/LlamaCode/agents/agents.json`. No hay nombres fijos que
enumerar: cada definición tiene `id`, nombre, descripción, perfil técnico,
launch, workspace, instrucciones, skills, MCP, permisos, Tasks y triggers, y
conserva revisiones inmutables. Se pueden duplicar, restaurar y someter a
feedback supervisado. Estas definiciones referencian los perfiles de arriba;
no agregan otro motor de harness.

## Roles de salas multiagente

Los presets de Agent Rooms usan identidades efímeras con grants propios:

| Rol | Presets que lo usan |
|---|---|
| `agent:coordinator` | Coordinación de sala y síntesis |
| `agent:implementer` | `review`, `autoprompt` |
| `agent:reviewer` | `review`, `autoprompt` |
| `agent:verifier` | `autoprompt`, `council`, `research` |
| `agent:perspective-a` | `council` |
| `agent:perspective-b` | `council` |
| `agent:researcher-a` | `research` |
| `agent:researcher-b` | `research` |
| `agent:citation-checker` | `research` |

Estos roles no son perfiles persistentes ni motores de harness: son miembros
de una sala y sus permisos se aplican por grant.

Los presets de sala disponibles son `review`, `autoprompt`, `council` y
`research`. Son recetas de composición de roles, no harnesses independientes.

## Motores de HarnessSpec

El catálogo vigente de `HarnessEngine` tiene dos contratos:

| ID | Versión | Namespace | Estado | Fallback |
|---|---:|---|---|---|
| `legacy` | 1 | `agent_llamaagent` | Compatible, comportamiento histórico | `legacy` |
| `next` | 2 | `agent_harness_next` | Experimental, almacenamiento aislado | `legacy` |

Los adapters/backend son otra capa:

| Adapter | Implementación | Consume `HarnessSpec` |
|---|---|---|
| `llamaagent` | `LlamaAgentBackend` | Sí |
| `opencode` | `OpencodeBackend` + `opencode serve` | No; mantiene su configuración propia |
| `raw` | `RawChatBackend` | No; chat sin tools |

Las lanes de worker (`builtin`, `node`, `python`) son extensiones supervisadas
del harness nativo; no son motores adicionales.
Los identificadores históricos `none`, `aider` y `goose` aparecen en formatos
compatibles, pero no tienen un backend vigente propio; `none` y `opencode` se
normalizan al agente nativo en el flujo principal, mientras `raw` queda como
chat sin tools.

## Skills por harness

El módulo `skills` de `HarnessSpec` controla los slugs portables:

```json
{
  "skills": {
    "include": ["*"],
    "exclude": ["autoprompt-coding"]
  }
}
```

Reglas:

1. Si `skills` no está declarado, todas las skills siguen habilitadas para no
   romper perfiles legacy.
2. `include: ["*"]` habilita todas las skills descubiertas.
3. `include: ["a", "b"]` habilita sólo esos slugs.
4. `exclude` siempre gana y desactiva esos slugs.
5. La skill sólo puede usarse si además el módulo `tools` deja disponibles
   `skill_list` y `skill_load`.
6. La política se hereda y puede cambiar por fase (`plan`, `exec`, `verify` o
   `goalCheck`) igual que los demás módulos.

Skills bundled actuales:

- `autoprompt-coding`
- `citation-verification`
- `critical-paper-reading`
- `experimental-design`
- `literature-review`
- `peer-review`
- `reproducible-data-analysis`

Las skills de browser Teach son secuencias grabadas separadas y no forman parte
de este catálogo portable. `opencode` tampoco consume este módulo: sus skills y
commands siguen la configuración propia de OpenCode.

Fuentes de implementación: `ProfileTypes.cpp`, `HarnessEngine.cpp`,
`AgentRoomStore.cpp`, `HarnessSpec.{h,cpp}`, `PortableSkillStore` y
`LlamaAgentBackend`.
