# Plan de implementación — Multi-backend de agentes (Harness)

Arquitectura objetivo: LlamaCode (Qt/QML) habla con un **runtime de agente** intercambiable
vía una interfaz común `IAgentBackend`. El runtime usa el `llama-server` local
(OpenAI-compatible) y herramientas vía MCP.

```
App Qt/QML
   ↓  IAgentBackend (start/stop/sendMessage/sesiones/tools)
Backend: opencode | goose | raw | ...
   ↓  OpenAI-compatible API
llama.cpp server
   ↓  tools / MCP
filesystem, shell, git, ripgrep, tests, browser, etc.
```

Principio rector: **la app no se casa con un harness**. El valor real (control de
contexto, tool-calling estable, diffs, aprobación, memoria por proyecto, perfiles por
modelo, fallback de JSON roto) es **harness-agnóstico**.

---

## Leyenda de estado
- ✅ HECHO
- 🚧 EN PROGRESO
- ⬜ PENDIENTE

---

## Etapa 0 — Contrato / interfaz  ✅ HECHO
**Meta:** definir la interfaz y los tipos antes de mover lógica.

- ✅ `src/core/agent/AgentTypes.h` — `AgentContext`, `AgentMessage`, `AgentSession`, `ToolCall`.
- ✅ `src/core/agent/IAgentBackend.h` — QObject abstracto:
  - ciclo de vida: `start(ctx)`, `stop()`
  - conversación: `sendMessage(text)`
  - sesiones: `newSession`, `newSessionInProject`, `switchSession`, `renameSession`,
    `deleteSession`, `forkSession`, `refreshSessions`
  - tools: `approveTool(id, always)`, `rejectTool(id)`
  - getters: `currentSessionId/Title/ProjectDir`, `messages()`, `sessions()`
  - señales: `runningChanged`, `messagesChanged`, `sessionsChanged`, `logAppended`,
    `toolApprovalNeeded`, `errorOccurred`
- ✅ Registrado en CMake. Compila.

---

## Etapa 1 — Extraer OpencodeBackend  ✅ HECHO
**Meta:** mover toda la lógica opencode de `AppController` a un backend. Comportamiento idéntico.

- ✅ `src/core/agent/OpencodeBackend.{h,cpp}` autocontenido: dueño de su `QProcess`
  (`opencode serve`) + `QNetworkAccessManager` + stream SSE.
  - sesiones (crear/listar/mensajes/rename/delete/fork)
  - eventos SSE (deltas, idle, session.updated, errores)
  - reconexión del stream (server opencode se apaga sin suscriptores)
  - kill del árbol de procesos al detener (libera puerto 4096)
  - auto-approve de permisos (provisional — lo reemplaza Etapa 4)
- ✅ `AppController` convertido en **fachada**: `ensureAgentBackend(adapter)` crea el
  backend y conecta señales → mirrors/señales QML existentes.
- ✅ `startAgent/stopAgent/sendToAgent` + `*OpencodeSession*` + `changeAgentProject` +
  `currentAgentProjectDir` delegan al backend.
- ✅ QML sin cambios (mismas propiedades/señales).
- ⬜ **Limpieza pendiente:** borrar el código opencode viejo e inerte de `AppController`
  (hoy queda con guard `if (m_agentBackend) return;`). No urgente.
- ⬜ **Falta test en vivo:** iniciar/chatear/sesiones/restart/nuevo-proyecto.

---

## Etapa 2 — RawChatBackend (modo Chat)  🚧 EN PROGRESO
**Meta:** chat directo contra `llama-server` `/v1/chat/completions` (sin harness de agente).
`raw` es exclusivo de **Chat**; no debe ser seleccionable en perfiles de **Agente**.

- ✅ `RawChatBackend` implementa `IAgentBackend` con streaming SSE de OpenAI (`stream:true`).
- ✅ Definición de producto: `raw` fuera del pipeline de Agente (solo Chat).
- ✅ Sesiones locales en memoria (crear/cambiar/renombrar/borrar/fork).
- ⬜ Persistencia local de sesiones (SQLite o store de chat existente).
- ✅ Integración en Chat para usar `RawChatBackend` como runtime único de chat directo.
- ⬜ Selector en UI: "Modo: Chat / Agente" (Agente solo con harness tool-calling).
- **Entregable:** chat directo funcional + interfaz probada con 2 backends reales.

---

## Etapa 3 — GooseBackend  ⬜ PENDIENTE
**Meta:** segundo agente real (runtime Rust, MCP, local-first).

- ⬜ Spike (0.5 día): validar endpoints de `goosed` con curl ANTES de codear UI.
- ⬜ Lanzar `goosed`/`goose` server en cwd del proyecto, env → `llama-server`.
- ⬜ Mapear API Goose: crear sesión, enviar mensaje, stream de eventos, tool approval.
- ⬜ Config Goose: `~/.config/goose/config.yaml` (YAML). Generalizar el config dialog
  o crear `GooseConfigDialog`.
- ⬜ Detección/instalación: descarga binario Rust (no npm).
- ⬜ Una línea en `ensureAgentBackend` + tarjeta en selector de harness.
- **Riesgo alto:** API `goosed` poco documentada → reverse-engineering del event stream.
- **Entregable:** Goose seleccionable (chat + tools + sesiones). opencode intacto.

---

## Etapa 4 — Aprobación de herramientas visible  ⬜ PENDIENTE
**Meta:** human-in-the-loop real (hoy opencode auto-aprueba TODO — peligroso).

- ⬜ Señal `toolApprovalNeeded(ToolCall)` → UI: card con comando/diff/archivo +
  botones Aprobar / Rechazar / Siempre.
- ⬜ Backend espera respuesta en vez de auto-`always`.
- ⬜ Setting global + por proyecto: "auto-aprobar lectura / pedir en escritura+shell".
- **Entregable:** ninguna escritura/exec sin OK (configurable). Diferenciador clave.

---

## Etapa 5 — Diffs visibles + control de cambios  ⬜ PENDIENTE
**Meta:** ver qué tocó el agente.

- ⬜ Interceptar tool calls de edición → render diff (antes/después) en el chat.
- ⬜ Botón revertir por-archivo (git stash/checkout o snapshot propio).
- **Entregable:** panel de diffs por mensaje. Integra con Etapa 4.

---

## Etapa 6 — Memoria + contexto por proyecto  ⬜ PENDIENTE
**Meta:** lo que mueve la aguja en LLM local.

- ⬜ Memoria por proyecto: `AGENTS.md` / `.llamacode/memory.md` editable.
- ⬜ Control de contexto visible: tokens usados/límite, archivos en contexto,
  pin/exclusión.
- ⬜ Compactación configurable (ya hay flags en perfiles opencode).
- **Entregable:** barra de contexto + editor de memoria por proyecto.

---

## Etapa 7 — Robustez con modelo local  ⬜ PENDIENTE
**Meta:** que no explote cuando Qwen rompe JSON/tool calls.

- ⬜ Fallback: tool-call malformado → reintento con prompt corrector / degradar a texto.
- ⬜ Validación de args (schema) antes de ejecutar.
- ⬜ Detección de loops (mismo tool call repetido) → cortar.
- ⬜ Indicador de salud: tool-call success rate por sesión.
- **Entregable:** sesiones no se cuelgan por JSON roto + logs de fallos.

---

## Etapa 8 — Perfiles de agente por modelo + UX final  ⬜ PENDIENTE
**Meta:** ajuste fino local-first.

- ⬜ Perfil de agente ligado a perfil de modelo: system prompt, temp para tool-calling,
  handler `--jinja` por modelo (Qwen2.5 / Hermes / Llama3 / Mistral Nemo).
- ⬜ Config global vs por proyecto de agente (scope ya existe en config dialog).
- ⬜ Pulido: selector de backend por proyecto, estados, errores claros.
- **Entregable:** v1 multi-backend completa.

---

## Dependencias
```
0 ✅ → 1 ✅ → 2 (valida interfaz)
              ↓
              3 (Goose)  ── paralelo ──  4 → 5 (approval + diffs)
                                          ↓
                                        6 → 7 → 8
```
Etapas 4–8 son **harness-agnósticas** (sirven a cualquier backend).

## Estimación
~16–20 días totales. MVP útil en Etapa 4 (opencode + Goose + aprobación visible).

---

## Ranking de harnesses (para referencia)
1. **Goose** — mejor integración general app Qt / local-first (runtime Rust, MCP, server API).
2. **OpenHands SDK** — coding agent pesado; backend Python/Docker (packaging duro).
3. **Pydantic AI** — harness propio limpio y controlado (FastAPI + Python).
4. **Aider** — benchmark de edición, no motor embebible.
5. **LangGraph** — workflows persistentes complejos, no MVP.
6. **OpenCode / Pi / SmallCode** — ya probados; opencode quedó como default.

Backends planeados detrás de `IAgentBackend`:
- `OpencodeBackend` ✅ (default)
- `RawChatBackend` ⬜ (chat directo)
- `GooseBackend` ⬜ (agente local)
- `CustomBackend` ⬜ (Pydantic AI / ReAct propio — opcional, largo plazo)

---

## Notas de estado actual del repo
- pi / smallcode: ocultos del selector (UI comentada), lógica aún en `AppController`
  (pi por print-mode, smallcode por stdin). Migrar a backends o eliminar.
- Editor de config opencode (`OpencodeConfigDialog.qml`) + MCP + skills/commands ya
  implementados (backend en `AppController`: `readOpencodeConfig/writeOpencodeConfig`,
  `listMcpServers/setMcpServer/...`, `listOpencodeCommands/...`). Específico de opencode;
  generalizar al sumar Goose.
- Build: `build.bat` o `cmake --build build --config Debug --target LlamaCode`.
  QML embebido (qt_add_qml_module) → requiere recompilar para ver cambios de UI.
