# Arreglos LlamaCode

Estado levantado con `Qwen-Profile` (`4854da5e-95fb-42ea-b4e1-1852b6d036f9`) vía Control API.

## Errores encontrados y arreglados uno por uno
1. `sendToAgentWithAttachments` aceptaba imágenes aunque `serverHasVision=false` si la llamada entraba por Control API o si el usuario elegía una imagen desde el filtro `Todos`.
   - Arreglo: filtro centralizado en `AppController::sendToAgentWithAttachments`; las imágenes se omiten y se registra el evento en `agentLog`.
   - Verificación: build OK; la ruta con visión sigue aceptando imagen + texto y respondió `VISION_OK`.

2. El botón `Rebobinar` dependía de `!App.agentRunning`.
   - Problema: el backend queda running aunque no haya turno activo, entonces rollback quedaba oculto después de terminar un turno.
   - Arreglo: visibilidad basada en `!root.hasTypingMessage && !root.waitingApproval`.
   - Verificación: rollback por API creó `roll.txt`, luego `rollbackAgentToMessage(0)` lo eliminó.

3. Las reglas de permisos por patrón clasificaban tools MCP como `mcp`.
   - Problema: reglas como `deny write:...` no aplicaban a MCP filesystem aunque fueran escrituras.
   - Arreglo: MCP `write_file`, `edit_file`, `move_file`, `create_directory` ahora son `write`; shell MCP es `shell`; el resto queda `read`.
   - Verificación: `deny write:blocked.txt` bloqueó `write_file blocked.txt`.

4. El glob de permisos era frágil para separadores y patrones recursivos.
   - Problema: podía no matchear rutas esperadas o producir expresiones ambiguas.
   - Arreglo: parser manual con avances explícitos y soporte de `/` y `\`.
   - Verificación: logs muestran `glob='blocked.txt' rx=[^blocked\.txt$] kindOk=1 rxOk=1`.

5. Una denegación de permisos sólo llegaba al contexto del modelo.
   - Problema: el usuario no veía una tarjeta de tool fallida en el chat.
   - Arreglo: `PermDeny` agrega una tarjeta `toolcall` visible con `ok=false` y también el resultado interno para el modelo.
   - Verificación: prueba final mostró tarjeta `write_file`, `kind=write`, `ok=false`, y `blocked.txt` no se creó.

6. El Control API había quedado sin respuesta durante una prueba larga de permisos.
   - Problema observado: corrida previa con polling largo agotó timeout.
   - Arreglo efectivo: después de corregir permisos/glob/tarjeta visible, repetí la prueba acotada y no se reprodujo.
   - Verificación: Control API respondió, el turno terminó y el archivo bloqueado no apareció.

## Funciona
- Build Debug compila (`build/Debug/LlamaCode.exe`).
- `Qwen-Profile` resuelve un perfil válido con `--mmproj`.
- Al iniciar server con ese perfil, `serverHasVision=true`.
- `startAgent` usa `llamaagent`.
- `@-mentions` por API devuelve archivos del proyecto (`src/main.txt`, `README.md`).
- `sendToAgentWithAttachments` acepta imagen + documento con server vision y el modelo respondió `VISION_OK`.
- `list_dir` con `recursive=true` devolvió rutas anidadas (`src/main.txt`).
- `Plan mode` expone sólo tools de lectura: usó `list_dir`, no creó `plan_mode.txt`, respondió `PLAN_OK`.
- `web_fetch` descargó `https://example.com` y el agente respondió `WEB_FETCH_OK`.
- `Subagents` funcionó con git worktree: creó `sub_done.txt`, mergeó `llamacode-sub/...` a la rama temporal y respondió `SUBAGENT_OK`.
- `Checkpoint/rollback` funcionó: el agente creó `roll.txt`; `rollbackAgentToMessage(0)` lo eliminó y truncó la conversación.
- `Permisos por patrón` funcionó en logs con `deny write:blocked.txt`: `write_file blocked.txt` fue bloqueado y el archivo no se creó.

## Fallas / mejoras
- [x] `sendToAgentWithAttachments` no filtraba imágenes cuando `serverHasVision=false` si la llamada llegaba por API o si el usuario elegía imágenes desde el filtro `Todos`.
  - Arreglo: filtra imágenes en `AppController::sendToAgentWithAttachments` y registra la omisión en el log del agente.
- [x] El botón `Rebobinar` se ocultaba con `!App.agentRunning`; el backend queda running aun cuando está idle.
  - Arreglo: visibilidad basada en `!root.hasTypingMessage && !root.waitingApproval`.
- [x] Las reglas de permisos por patrón no evaluaban bien tools MCP tipo filesystem porque `toolKind()` las marcaba como `mcp`.
  - Arreglo: MCP `write_file`/`edit_file`/`move_file`/`create_directory` se clasifican como `write`; shell MCP como `shell`; resto como `read`.
- [x] Glob de permisos endurecido.
  - Arreglo: parser con avances explícitos (`continue`) y soporte de `/`/`\`.
- [x] Denegaciones de permisos no dejaban tarjeta visible de tool.
  - Arreglo: `PermDeny` agrega `toolcall` fallido además del `tool` result interno.
- [x] La prueba de `deny write:blocked.txt` dejó el Control API sin respuesta en una corrida previa.
  - Resultado posterior: no se reprodujo con el build corregido; la denegación quedó registrada en `agent.log` y `blocked.txt` no se creó.
