# Auditoría de `oh-my-openagent` para LlamaCode — 2026-09-18

## Resultado ejecutivo

`oh-my-openagent` es un sistema de orquestación para OpenCode/Codex/Claude,
no un modelo, un backend de inferencia ni un quant. Por eso no puede reemplazar
SOL, QWEN35-A3B, TERRA ni ningún otro perfil de la tabla de modelos.

La revisión no encontró una receta que mejore PP, TG, VRAM, contexto, visión,
HE o BCB de nuestros perfiles. LlamaCode ya tiene implementadas las partes que
sí son directamente comparables: subagentes paralelos, worktrees aislados,
límite adaptativo por contexto y VRAM, routing por rol, planificación,
memoria, goals, skills portables, MCP y persistencia de corridas.

No se descargó ni instaló `oh-my-openagent`, no se añadió telemetría externa,
no se modificó `assets/system_profiles.json` y SOL permanece como default. Sí se
incorporó una mejora local, acotada y compatible: una guardia SHA-256 optativa
para rechazar ediciones obsoletas cuando una segunda sesión cambió el archivo.
No es una copia completa de Hashline por línea; evita cambiar el contrato actual
de `edit_file`/`write_file` y permite migración gradual.

Fuente primaria revisada: [repositorio oficial](https://github.com/code-yeongyu/oh-my-openagent),
su [README de desarrollo](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/dev/README.md),
la [guía de instalación](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/dev/docs/guide/installation.md)
y el [roadmap](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/dev/ROADMAP.md).
La revisión local del upstream se fijó en el commit `9ba073a8b1cd503c8e806945b4e2e83961b64428`.

## Comparación con LlamaCode

| Capacidad | `oh-my-openagent` | LlamaCode actual | Decisión |
|---|---|---|---|
| Subagentes paralelos | Team Mode, líder + hasta 8 miembros, con categorías por tarea | `SubAgentRunner`, worktrees, cola, límite adaptativo por slots/contexto/VRAM y hard-cap 5 | No importar el plugin; la implementación local está más integrada con el hardware |
| Routing por rol | Categorías `visual-engineering`, `deep`, `quick`, `ultrabrain` | `DifficultyRouter`, roles de modelo y `HarnessSpec` por fase | Sin cambio de perfiles |
| Planificación y continuación | ultrawork, loops y continuación | `HybridPlanning`, loops de tarea, `GOAL_MET`, replanning y recuperación | Sin cambio |
| Memoria | Memory core, reflexión y persistencia del workflow | `MemoryStore`, `GraphStore`, `ProjectBrain`, `KnowledgePacket` y event log | Sin cambio |
| Skills/MCP | Skills y MCP embebidos en la edición elegida | skills portables, selección por perfil/fase y routing MCP adaptativo | Sin cambio |
| Aislamiento y seguridad | reglas, workspaces y comentarios de cambios | políticas read-only, bloqueo de destructivas, approvals, sandbox y worktrees | Mantener control local |
| Edición contra cambios concurrentes | Hashline opt-in: tags `LINE#ID` y validación de líneas | `read_file` devuelve SHA-256 completo; `edit_file`/`write_file` aceptan `expected_sha256` y rechazan conflictos | Mejora local incorporada; Hashline por línea queda opcional/futuro |
| Comprensión estructural | LSP y AST-Grep como herramientas auxiliares | No hay adaptador LSP/AST-Grep equivalente detectado | Candidato futuro, no activar como dependencia obligatoria |
| UI de equipo | vista DAG/tmux y herramientas `team_*` según edición | Agent Rooms y progreso nativo, sin una vista Team Mode equivalente | Mejora de UI opcional |
| Telemetría | el upstream la habilita por defecto y permite opt-out | historial/event log local controlado por LlamaCode | No importar el default externo |

La diferencia de “hasta 8 agentes” tampoco es una mejora automática: en este
equipo el límite seguro depende de los dos RTX 3090, del contexto por worker y
de la memoria libre. LlamaCode ya reduce el máximo cuando el contexto o la VRAM
no permiten mantener sesiones independientes.

## Pruebas y verificaciones realizadas

Se contrastó la documentación upstream con el código local y con los tests ya
existentes. No se repitieron corridas de modelos que no podían aportar evidencia
nueva.

### Cobertura local ya existente

- `SubAgentRunner` ejecuta loops headless con worker propio, worktree y política
  de lectura/solo-shell; bloquea herramientas destructivas cuando corresponde.
- `test_agent_wire.cpp` cubre el límite adaptativo: 1, 2, 3, 4 y el hard-cap 5
  según slots, contexto y VRAM, incluyendo el caso de 262K con workers de 64K.
- `test_agent_tools.cpp` cubre prompts y herramientas del sistema de subagentes.
- `test_appcontroller.cpp` cubre loops de goals y cierre `GOAL_MET`.
- `test_harness_modules.cpp`, `test_harness_spec.cpp` y
  `test_portable_skills.cpp` cubren módulos, herencia/selección de skills y
  portabilidad.
- `test_managed_agent_runs.cpp` y `test_auxiliary_job_scheduler.cpp` cubren
  corridas administradas y scheduling auxiliar.

### Inventario negativo reproducible

La búsqueda inicial en `src`, `qml`, `tests`, `docs` y `assets` no encontró una
implementación equivalente para Hashline por línea, servidores LSP, AST-Grep ni
herramientas `team_create`/`team_*`. Esto confirma una diferencia funcional,
pero no demuestra que convenga importar el plugin completo.

### Mejora implementada: guardia de edición por SHA-256

La herramienta `read_file` ahora devuelve una cabecera y un campo estructurado
`sha256` con la huella del archivo completo. El agente puede pasar esa huella
como `expected_sha256` en `edit_file` o `write_file`; si el archivo cambió,
la operación se rechaza antes de escribir y se devuelve la huella esperada y la
actual para que el agente relea y reintente. La huella se calcula por streaming,
por lo que sigue siendo exacta aunque la vista de contenido esté limitada a
varios MiB.

La opción es retrocompatible: si no se envía `expected_sha256`, el camino previo
sigue funcionando. Esto cubre el problema práctico que Hashline intenta resolver:
ediciones obsoletas por concurrencia, sin afirmar que ya tengamos tags
individuales por línea, navegación LSP o reescritura AST.

Prueba A/B reproducible sobre `test_agent_tools`:

| Caso | Resultado |
|---|---|
| Lectura devuelve hash y archivo externo cambia antes de editar | Rechazo seguro; contenido externo preservado |
| Relectura y edición con hash fresco | Aplicación correcta |
| Edición histórica sin hash | Compatibilidad mantenida |
| Tests dirigidos de guardia (`hashGuard_*` + ciclo histórico) | 5/5 PASS |

La compilación Release terminó correctamente en
`/home/cristian/.cache/llamacode/build_linux/LlamaCode`. El gate global
`./scripts/tests-linux.sh Release` recompiló todos los targets, pero quedó sin
resultado final porque `ctest` no terminó dentro de 180 s en este entorno; el
test dirigido de esta modificación sí completó sin fallos. Esto no se convirtió
en un resultado BCB ni en una afirmación de calidad del modelo.

No se ejecutó una instalación de Bun/Node, un daemon externo, tmux ni un
servidor LSP sólo para producir una cifra artificial: cambiarían el entorno,
la latencia y el contrato de herramientas, y no medirían un perfil de modelo.

## Impacto sobre los perfiles

| Perfil | Cambio por esta auditoría |
|---|---|
| **SOL** | Sigue siendo default; no hay cambio de modelo, flags, BCB, visión ni contexto |
| **QWEN35-A3B** | Sigue siendo el secundario multimodal/concurrente; no hay evidencia de mejora |
| **GALACTA, TERRA, METEOR y auxiliares** | Sin cambios; el proyecto externo no aporta una receta de inferencia |
| **ASTRA/NINFER/QWEN38-Q8 y experimentales** | Sin promoción; las diferencias de orquestación no arreglan sus fallos de runtime/calidad |

Un Team Mode o un hashline más robusto podría cambiar la tasa de reparaciones,
el tiempo de tarea o los fallos de edición. Eso debe medirse como una campaña
del harness, no como una nueva fila de BCB de un modelo.

## Mejoras que sí vale la pena evaluar después

Quedan anotadas para no repetir esta auditoría:

1. **Hashline por línea opt-in:** extender la guardia de archivo a tags
   `LINE#ID`, sólo si una campaña demuestra menos reparaciones que la huella
   completa y conserva el flujo actual.
2. **LSP read-only:** exponer diagnósticos, símbolos y referencias como tools
   locales, sin convertir el servidor en una autoridad de escritura.
3. **AST-Grep opt-in:** búsquedas/reemplazos estructurales con diff y approval,
   comparados contra `grep`/`edit_file` en tareas reales.
4. **Team view:** mostrar Agent Rooms, cola, worktrees y consumo de VRAM sin
   cambiar el límite adaptativo seguro.

El criterio de promoción será la misma suite Harness Context A/B y luego HE0,
HE20 y BCB con un perfil fijo: tasa de primer intento, reparaciones, tool-call
quality, archivos correctos, TTFT/TG y consumo de VRAM. Una mejora de UX no se
convertirá en mejora de calidad del modelo sin esa separación.

## Decisión final

- No se instala `oh-my-openagent` dentro de LlamaCode.
- No se agrega ningún perfil nuevo ni se elimina/supersede uno existente.
- SOL sigue siendo el perfil principal.
- La guardia SHA-256 queda activa como capacidad del contrato de edición; no
  cambia perfiles, permisos ni defaults de inferencia.
- LSP, AST-Grep, Team view y el Team Mode externo quedan registrados como
  trabajo futuro separado de los benchmarks de modelos.
- Esta auditoría evita repetir la revisión del plugin, la comparación de
  subagentes/skills/memoria y el inventario negativo de hashline/LSP/AST-Grep.
