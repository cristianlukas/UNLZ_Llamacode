# Agent harness TODO

Gaps de paridad vs opencode/pi/aider. Estado:

- [x] **Plan mode** — `m_approvalMode=="plan"`. buildToolSchemas filtra a read-only (read_file/list_dir/grep/glob/web_fetch); processPendingCalls bloquea writes; system prompt de plan; combo en AgentPage ("Plan (solo lectura)").
- [ ] **Subagents** — agentes paralelos aislados (worktree). Tool `task`. GRANDE — pendiente.
- [x] **Imágenes al agente** — detección de visión (`serverHasVision` = server lanzado con `--mmproj`); botón 📎 + chips en AgentPage; `setPendingAttachments` + content multimodal (image_url + docs inline) en LlamaAgentBackend::sendMessage; `sendToAgentWithAttachments`/`pickAgentAttachments` en AppController (filtra imágenes si no hay visión). Chat usa el mismo filtro.
- [x] **Checkpoint/rollback de conversación** — checkpoint por turno (`pushCheckpoint` en sendMessage); `rollbackToMessage(msgIndex)` trunca msgs/ctx + revierte edits posteriores; botón "↩ Rebobinar" en burbujas de usuario.
- [x] **list_dir recursivo** — arg `recursive` (salta dirs ignorados, cap 1000).
- [x] **Permisos por patrón** — reglas "allow|deny|ask [kind:]<glob>" (una por línea) antes de la política global. `setPermissionRules` + eval en processPendingCalls (subject=path o command). Persist `agent/permRules`; editor en el diálogo de tuning del agente.
- [x] **@-mentions** — al tipear `@` aparece popup de archivos del proyecto (`agentProjectFiles`), ↑/↓/Enter/Tab/click para elegir; el archivo se adjunta (chip) y su contenido se inyecta vía el pipeline de adjuntos. Rutas rel resueltas contra cwd en el backend.
- [x] **Web fetch** — tool `web_fetch(url)` → HTML limpiado a texto (timeout 20s, cap 48KB).

## Hechos (7/8)
plan mode, checkpoint/rollback, list_dir recursivo, web_fetch, imágenes+visión, permisos por patrón, @-mentions. Build Debug OK.

## Pendiente (1) — Subagents
El grande. Diseño propuesto:
- Tool `task(description, prompt)`: el agente delega un subtask a un sub-agente.
- v1 (secuencial, sin worktree): el padre está esperando el resultado del tool, así que el sub-agente corre un loop ReAct anidado reusando el worker (sin paralelismo real). Mismo cwd. Devuelve el texto final como resultado del tool.
- v2 (paralelo, aislado): pool de N LlamaAgentBackend headless, cada uno en su git worktree, ejecución concurrente, tool `task` no bloqueante. Necesita workers separados (1 por sub-agente) y merge de worktrees.
- Riesgo: refactor de runCompletion para reusar en contexto de sub-agente + UI de sub-tarjetas. NO meter a las apuradas (puede romper el agente que ya anda).
