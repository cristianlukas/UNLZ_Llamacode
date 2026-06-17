# Revision de codehamr para el harness nativo

Fecha: 2026-06-17

Repositorio revisado: https://github.com/codehamr/codehamr

## Resumen ejecutivo

`codehamr` no aporta por cantidad de features: aporta por disciplina de reduccion.
Su harness es deliberadamente chico: loop ReAct simple, una ruta OpenAI-compatible,
cuatro tools (`bash`, `read_file`, `write_file`, `edit_file`) y mucha defensa en
los bordes donde los backends locales fallan.

LlamaCode ya cubre mas superficie: UI nativa, perfiles, MCP, memoria/RAG,
subagents, permisos, tareas y tools mas ricas. Lo valioso para copiar no es
achicar el producto entero, sino endurecer el modo "local-first/simple" del
agente nativo y sumar tests para los errores de protocolo mas frecuentes.

## Ideas que conviene tomar

### P0 - Packer de contexto con invariantes de wire protocol

`codehamr/internal/ctx` empaqueta mensajes newest-first, pero despues repara
formas que rompen backends OpenAI-compatible:

- elimina `tool` messages huerfanos si se podo su `assistant.tool_calls`;
- elimina `assistant.tool_calls` colgantes si falta alguna respuesta `tool`;
- recupera el grupo assistant+tools mas reciente si el recorte dejo la ventana
  vacia;
- conserva siempre el primer mensaje de usuario como ancla de objetivo;
- degrada `system` no inicial a `user`, porque varios backends estrictos solo
  aceptan un system inicial.

En LlamaCode hay compactacion via modelo y `repairDanglingToolCalls()`, pero
esa reparacion solo cubre el ultimo assistant antes de un nuevo user. Conviene
extraer un `sanitizeApiMessagesForWire()` antes de cada request y cubrir estos
casos con tests unitarios.

Impacto esperado: menos 400/500 por conversaciones largas, cancelaciones a mitad
de tool, compaction y tool calls paralelas.

### P0 - Timeout de stream por inactividad, configurable y largo

`codehamr` distingue timeout end-to-end de timeout por frame SSE. Para modelos
locales grandes, el prefill puede tardar muchos minutos sin emitir tokens; por
eso usa un idle timeout largo (`CODEHAMR_IDLE_TIMEOUT`, default 1h) y cancelacion
manual inmediata.

En LlamaCode el request de `QNetworkReply` no tiene un watchdog equivalente por
actividad SSE. Conviene agregar un timer que se reinicie en cada linea SSE y
aborte solo si no llega nada durante N minutos, con override por perfil/env.

Impacto esperado: UI que puede diagnosticar stream muerto sin matar prefills
lentos legitimos.

### P1 - Modo harness minimalista para modelos chicos/locales

`codehamr` gana mucho contexto porque no ofrece router, MCP, subagents ni tools
extra. LlamaCode ya permite deshabilitar tools, pero seria util un preset visible:
`Minimal local agent`.

Propuesta:

- tools: `read_file`, `write_file`, `edit_file`, `run_shell`, opcional `grep`;
- MCP/subagents/memoria/web apagados por defecto;
- system prompt mas corto;
- budgets de tool output mas estrictos;
- temperatura recomendada para coding local no greedy.

Impacto esperado: mejor estabilidad con modelos 7B-30B y contextos reales de
32k-64k, sin quitar el modo completo.

### P1 - Mensajes de error autocorrectivos en tools

`codehamr` escribe errores pensando en que los leera el modelo:

- si los argumentos JSON fueron truncados, le dice que no repita el write entero
  y que use escritura por chunks;
- si `edit_file` falla por whitespace, lo nombra explicitamente;
- si `old_string` aparece mas de una vez, pide mas contexto;
- si una lectura grande fue truncada, advierte que no se puede concluir desde la
  vista parcial.

LlamaCode ya tiene varios mensajes buenos. Faltan dos refinamientos:

- detectar "difiere solo en whitespace" en `edit_file`;
- conservar el `_parse_error` de tool args invalido y devolver una instruccion de
  recuperacion, en vez de sanear a `{}` y perder la causa.

Impacto esperado: menos loops de reintento con el mismo tool call malo.

### P1 - Proceso shell: matar arbol/grupo, no solo el proceso padre

`codehamr` crea process group en Unix y usa `WaitDelay` para que hijos en
background no mantengan vivos los pipes. En Windows tiene implementacion
separada.

LlamaCode usa `QProcess::kill()` para `run_shell`. Eso puede dejar hijos vivos
si el comando lanza subprocesos. Para Windows conviene Job Object por tool shell
o `taskkill /T /PID`; para Unix, process group + killpg.

Impacto esperado: menos procesos colgados tras timeout/cancelacion de comandos
del agente.

### P2 - Tests de regresion del loop

La mayor diferencia de calidad esta en los tests de `codehamr`: multi-tool en un
round, stale events tras cancelacion, assistant vacio, tool-call XML impreso como
texto, output truncation, profile switch y context packing.

Prioridad de tests para LlamaCode:

- `sanitizeApiMessagesForWire` con orphan/dangling/system-no-inicial/user-anchor;
- stream con dos tool calls en paralelo y resultados completos antes del siguiente
  request;
- cancelacion: evento viejo de stream/tool no entra al nuevo turno;
- assistant final vacio: reprompt una vez o cierre honesto con aviso;
- tool call textual filtrado: detectar `<tool_call>` impreso como texto cuando no
  llego structured tool call.

## Lo que no conviene copiar

- No conviene eliminar MCP, subagents, RAG, memoria o UI: son diferenciales de
  LlamaCode y ya estan documentados como parte del producto.
- No conviene cambiar a un solo `config.yaml`: los perfiles compuestos son una
  fortaleza de LlamaCode.
- No conviene copiar codigo Go: las ideas son portables, pero la implementacion
  tiene que vivir en C++/Qt y respetar `AgentToolRunner`/`LlamaAgentBackend`.

## Plan recomendado

1. Crear `sanitizeApiMessagesForWire()` y tests unitarios.
2. Agregar idle watchdog de stream SSE configurable.
3. Endurecer `edit_file` y errores de tool args truncados.
4. Agregar kill de arbol/grupo para `run_shell`.
5. Crear preset `Minimal local agent` en perfiles/harness UI.

