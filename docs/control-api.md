# Control API (headless)

API HTTP que **espeja todo `AppController`** para manejar LlamaCode sin GUI: tests
automatizados, scripting, CI. Reflexión automática vía meta-object de Qt — expone los
mismos `Q_INVOKABLE` y `Q_PROPERTY` que usa el QML, sin código por función.

Implementación: `src/core/ControlApi.{h,cpp}`, instanciado en `src/main.cpp`.

## Habilitar / puerto
- Escucha en **`http://127.0.0.1:<port>`** — solo localhost.
- Puerto: env **`LLAMACODE_CONTROL_PORT`** (default **8765**). `0` = desactivado.
- Se levanta al iniciar la app (con o sin GUI visible).

```powershell
$env:LLAMACODE_CONTROL_PORT = "8765"   # o dejar default
.\build\Debug\LlamaCode.exe
```

## Endpoints

| Método | Ruta | Body | Devuelve |
|--------|------|------|----------|
| GET  | `/health` | — | `{"ok":true}` |
| GET  | `/methods` | — | `{methods:[...], properties:[...]}` (introspección) |
| GET  | `/prop?name=X` | — | `{name, value}` |
| POST | `/setprop` | `{name, value}` | `{ok:true}` |
| POST | `/invoke` | `{method, args:[...]}` | `{ok:true, result?}` |

- `Content-Type: application/json`. CORS abierto (`Access-Control-Allow-Origin: *`).
- `args` se convierten al tipo del parámetro del método (QString/bool/int/double/QVariantMap…).
- El match de método es por **nombre + aridad** (cantidad de args).
- Las acciones de la GUI que son **setters de propiedad** (no `Q_INVOKABLE`) se cambian con
  `/setprop`, no con `/invoke` (ej. `agentApprovalMode`, `agentThinkingEnabled`).
- `/invoke` corre en el hilo de `AppController` (mismo hilo) → seguro y síncrono. Las
  operaciones de por sí asíncronas (arrancar server, stream del agente) siguen siendo
  asíncronas: hay que **pollear propiedades** para ver el resultado.

## Métodos y propiedades útiles (agente/servidor)

Invocables (`/invoke`):
- `startServer(launchId)` / `stopServer()` — arrancar/parar llama-server.
- `startAgent(launchId)` / `stopAgent()` — arrancar/parar el backend de agente.
- `sendToAgent(text)` — mandar mensaje al agente.
- `approveAgentTool(id, always)` / `rejectAgentTool(id)` — aprobación de tools.
- `revertAgentEdit(path)` — revertir un write del agente.
- `readAgentMemory(projectDir)` → string / `writeAgentMemory(projectDir, text)`.

Propiedades (`/prop?name=` y `/setprop`):
- `serverRunning`, `serverReady` (read) — estado del server.
- `agentRunning`, `agentMessages`, `agentSessions`, `agentPendingTool` (read).
- `agentContextUsed`, `agentContextLimit` (read).
- `agentApprovalMode` (read/write: `auto|ask|manual|super`).
- `agentThinkingEnabled` (read/write: bool).

Listá todo en vivo con `GET /methods`.

## Ejemplo: test end-to-end del agente (PowerShell)

```powershell
$base = "http://127.0.0.1:8765"
function Inv($m,$a){ Invoke-RestMethod "$base/invoke" -Method Post -ContentType application/json -Body (@{method=$m;args=$a}|ConvertTo-Json -Compress) }
function SetP($n,$v){ Invoke-RestMethod "$base/setprop" -Method Post -ContentType application/json -Body (@{name=$n;value=$v}|ConvertTo-Json -Compress) }
function Prop($n){ (Invoke-RestMethod "$base/prop?name=$n").value }

# 1) arrancar server y esperar ready
Inv "startServer" @("<launchId>")
while (-not (Prop "serverReady")) { Start-Sleep 1 }

# 2) configurar agente y arrancar
SetP "agentApprovalMode" "super"      # acceso total + sin prompts
SetP "agentThinkingEnabled" $false
Inv "startAgent" @("<launchId>")

# 3) mandar mensaje y pollear respuesta
Inv "sendToAgent" @("Leé README.md y resumilo")
do { Start-Sleep 2; $msgs = Prop "agentMessages" } while ($msgs[-1].typing)
$msgs[-1].content

# 4) si pide aprobación (modo ask/manual):
$pend = Prop "agentPendingTool"
if ($pend.id) { Inv "approveAgentTool" @($pend.id, $false) }
```

## Lecciones operativas (agente)

- `changeAgentProject(directory)` define el **directorio de trabajo** del agente (dónde lee/escribe/busca archivos).
- Las tools/MCP **no tienen que vivir en ese directorio**. Se pueden configurar en scope `global` y el agente las reutiliza aunque cambie el proyecto.
- Para editar archivos con el backend nativo `custom`, el agente necesita:
  1) `serverReady = true`
  2) un `launchId` cuyo harness sea `custom`
  3) tools disponibles (built-in y/o MCP según config).

### `custom` vs `opencode`

- `startAgent(launchId)` usa el adapter del harness del perfil:
  - `custom`: backend nativo interno (sin proceso externo de agente).
  - `opencode`: backend externo (`opencode serve`).
- Si querés forzar backend nativo, usá un `launchId` con harness `custom`.

## Fix aplicado: múltiples tool calls en `custom`

### Síntoma

En corridas con múltiples tool calls, el segundo/tercer ciclo podía fallar con:
- `500 Failed to parse tool call arguments as JSON`
- errores visibles en agente como `Conexión rechazada` o `Internal Server Error`.

### Causa

Se enviaba `parse_tool_calls=true` al endpoint `/v1/chat/completions`. Si el modelo emitía argumentos parciales/mal cerrados en streaming, el parseo server-side abortaba con `500`.

### Solución implementada

En `src/core/agent/CustomBackend.cpp` se cambió:
- `parse_tool_calls: true` → `parse_tool_calls: false`

Con eso, el parseo queda del lado cliente (`CustomBackend`), que ya reensambla deltas por `index` y maneja validación/reintentos sin tumbar la request.

### Verificación

Probado con secuencias de múltiples tool calls (`list_dir` + `write_file`) en una misma conversación del agente `custom`, sin `500` de parseo del server.

## Troubleshooting rápido

- Si `agentLog` muestra `mcp 0 tool(s) descubiertas`:
  - revisá `listMcpServers("global", "")` y/o `listMcpServers("project", "<dir>")`
  - verificá que el comando MCP exista en PATH (en Windows, preferir `cmd /c ...` cuando aplique).
- Si `serverReady` pasa a `false` durante un turno:
  - revisar `%LOCALAPPDATA%\LlamaCode\LlamaCode\logs\server.log`
  - relanzar `startServer(...)` y recién después `startAgent(...)`.
- Si el agente acumula contexto roto por intentos previos:
  - crear sesión nueva (`newOpencodeSessionInProject(...)`) antes de reenviar prompt.

## Notas
- Solo localhost; no exponer el puerto. Pensado para dev/test, no producción.
- Para diagnosticar fallas: el server llama.cpp loguea en
  `%LOCALAPPDATA%\LlamaCode\LlamaCode\logs\server.log` y el agente en `agent.log`.
- Parsing HTTP mínimo (headers + `Content-Length`); una request por conexión.
