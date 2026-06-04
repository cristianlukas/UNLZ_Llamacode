# Agent harness TODO

Gaps de paridad vs opencode/pi/aider. Estado:

- [x] **Plan mode** — `m_approvalMode=="plan"`. buildToolSchemas filtra a read-only (read_file/list_dir/grep/glob/web_fetch); processPendingCalls bloquea writes; system prompt de plan; combo en AgentPage ("Plan (solo lectura)").
- [x] **Subagents** — tool `task(description, prompt)`. `SubAgentRunner` = loop ReAct headless con worker propio confinado a una git worktree aislada. El modelo puede emitir VARIAS task en un turno → corren EN PARALELO (parallel_tool_calls=true); el padre espera a que terminen todas (m_subsOutstanding), mergea cada worktree a la rama actual y limpia. Tarjeta en vivo por sub. Sin git → corre en el cwd sin aislamiento. Conflictos de merge se reportan (no auto-resuelven).
- [x] **Imágenes al agente** — detección de visión (`serverHasVision` = server lanzado con `--mmproj`); botón 📎 + chips en AgentPage; `setPendingAttachments` + content multimodal (image_url + docs inline) en LlamaAgentBackend::sendMessage; `sendToAgentWithAttachments`/`pickAgentAttachments` en AppController (filtra imágenes si no hay visión). Chat usa el mismo filtro.
- [x] **Checkpoint/rollback de conversación** — checkpoint por turno (`pushCheckpoint` en sendMessage); `rollbackToMessage(msgIndex)` trunca msgs/ctx + revierte edits posteriores; botón "↩ Rebobinar" en burbujas de usuario.
- [x] **list_dir recursivo** — arg `recursive` (salta dirs ignorados, cap 1000).
- [x] **Permisos por patrón** — reglas "allow|deny|ask [kind:]<glob>" (una por línea) antes de la política global. `setPermissionRules` + eval en processPendingCalls (subject=path o command). Persist `agent/permRules`; editor en el diálogo de tuning del agente.
- [x] **@-mentions** — al tipear `@` aparece popup de archivos del proyecto (`agentProjectFiles`), ↑/↓/Enter/Tab/click para elegir; el archivo se adjunta (chip) y su contenido se inyecta vía el pipeline de adjuntos. Rutas rel resueltas contra cwd en el backend.
- [x] **Web fetch** — tool `web_fetch(url)` → HTML limpiado a texto (timeout 20s, cap 48KB).

## TODO completo (8/8) — build Debug OK
plan mode, checkpoint/rollback, list_dir recursivo, web_fetch, imágenes+visión, permisos por patrón, @-mentions, subagents (v2 paralelo + worktrees).

## Caveats subagents — MEJORADOS
- [x] Aislamiento = git REQUERIDO. Si git no está instalado → la UI pide instalarlo (winget Git.Git); la task falla con mensaje (no corre sin aislar). Si git está pero el cwd no es repo → `git init` + snapshot automático. (Antes había fallback de copia FS; reemplazado por pedir git, a pedido del usuario.)
- [x] Conflicto de merge: `git merge --abort` (repo queda intacto) + se PRESERVA la rama `llamacode-sub/<id>` para merge manual. Verificado con repo de prueba (merge limpio + abort/preserve).
- [x] Cap de concurrencia: `kMaxParallelSubs=3`; el resto se encola (m_subQueue) y se lanza al liberarse un slot (pumpSubs). No satura el server.
- parallel_tool_calls =true global (necesario para varias task/turno; el loop serializa los tools normales igual). Comentado en runCompletion.
- Verificación GUI end-to-end (LLM manejando subs) pendiente — requiere server corriendo. El plumbing git/copy/merge/abort está validado.
