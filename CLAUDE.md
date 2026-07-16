# LlamaCode — guía para Claude

## Testing policy (OBLIGATORIA)

Toda feature nueva o cambio de comportamiento DEBE llegar con su test (unit +
integration cuando aplique). Sin test = incompleto.

Reglas:
- Agregar/actualizar el test en `tests/` y registrarlo en `CMakeLists.txt` con
  `add_lc_test(<area> tests/test_<area>.cpp)` (helper ya definido, sección
  `if (BUILD_TESTS)`).
- Antes de commitear: correr `tests.bat` (configura `BUILD_TESTS=ON`, compila en
  `build_tests/`, corre `ctest`). Build + todos los tests verdes = gate (hoy 27;
  ver `add_lc_test` en `CMakeLists.txt`). No commitear en rojo. Atajo: `/gate`.
- Un executable por subsistema (QtTest = 1 `QTEST_MAIN` por binario).

### Convenciones de tests
- Aislamiento de disco: `QStandardPaths::setTestModeEnabled(true)` redirige
  AppData/AppLocalData a una ubicación de test (registries, catalog, chat_raw,
  cache de DocumentExtractor). Perfiles: env var `LLAMACODE_PROFILES_DIR`
  (setear en `initTestCase` ANTES de construir el primer `ProfileManager`: la
  raíz se cachea en un `static`).
- DB de catálogo persiste entre corridas: borrarla en `initTestCase` si el test
  necesita estado limpio.
- ControlApi / backends de red: server y client en el mismo hilo → NO usar
  `waitForReadyRead`; bombear el event loop (`QCoreApplication::processEvents`).
- AgentToolRunner: `executeTool` emite `toolExecuted`; capturar con `QSignalSpy`.
  `run_shell` es async (esperar el spy).
- Los test exes se linkean contra la lib `llamacode_core` (mismos objetos que el
  app) y se fuerzan a subsistema consola para que QtTest imprima a stdout.

### Mapa módulo → archivo de test
| Subsistema | Test |
|---|---|
| GGUFScanner, EffectiveProfileBuilder | `tests/test_gguf_profiles.cpp` |
| ProfileTypes, ProfileManager | `tests/test_profiles.cpp` |
| AgentProfile (perfiles de agente: capacidades+directivas, presets, gating system prompt) | `tests/test_agent_profiles.cpp` |
| LlamaBinary, ModelRoot, BinaryRegistry, ModelRootRegistry | `tests/test_registries.cpp` |
| CatalogModel, ModelCatalog | `tests/test_catalog.cpp` |
| CapabilityDetector | `tests/test_capability.cpp` |
| DocumentExtractor | `tests/test_document_extractor.cpp` |
| MemoryStore, GraphStore | `tests/test_memory_graph.cpp` |
| AutoTuner / tuner | `tests/test_tuner.cpp` |
| EvalSuite | `tests/test_eval.cpp` |
| ControlApi | `tests/test_control_api.cpp` |
| AgentToolRunner (tools nativas) | `tests/test_agent_tools.cpp` |
| LlamaAgentBackend (system prompt: discipline/test-net/contexto) | `tests/test_agent_wire.cpp` |
| HotspotAnalyzer (archivos riesgosos: churn+autores+sin test) | `tests/test_hotspots.cpp` |
| MasterCli | `tests/test_master_cli.cpp` |
| RawChatBackend (sesiones/persistencia) | `tests/test_backends_net.cpp` |
| LogTriage (barrido de errores) | `tests/test_logtriage.cpp` |
| DownloadHistoryStore (historial de descargas) | `tests/test_download_history.cpp` |

### Pendiente de cobertura
Stub HTTP ya disponible: `SseStubServer` en `tests/test_backends_net.cpp` cubre
el stream SSE de `/v1/chat/completions` para RawChatBackend (acumulación de deltas
+ error HTTP). El ciclo del bucle de Loops (sin swap) se cubre en
`tests/test_appcontroller.cpp` con `FakeAgentBackend` + `setTestAgentBackend` +
`runTaskBodyForTest` (body→goal-check→repeat→GOAL_MET / corte por maxIter). El
ensamblado de tool_calls en streaming se cubre en `tests/test_agent_wire.cpp`
(`LlamaAgentBackend::mergeToolCallDelta`, pura). Falta: `/props` (chat-template),
`/v1/embeddings`, y el swap de modelo verify-phase end-to-end (el swap recrea el
backend vía `ensureAgentBackend`, así que no es stubbeable sin un harness cloud
completo; queda como QA manual). Reusar `SseStubServer`.

### QA manual pendiente (sin test automatizado)
Necesitan una sesión de escritorio interactiva con ventanas vivas (no
reproducible en headless/CI), así que sólo se cubre el path de error en
`tests/test_agent_tools.cpp`. La lógica real es **QA manual**:
- **UI Automation** (`DesktopAutomationBackend::controls` / `clickElement`, tools
  `desktop_controls` / `desktop_click_element`): abrir Notepad → `desktop_windows`
  para el id de ventana → `desktop_controls` lista los controles → tomar el
  `controlId` de un botón (ej. menú "Archivo"/"Guardar") → `desktop_click_element`
  lo invoca. Verificar que el clic semántico (patrón Invoke) acciona el control.
- **desktop_observe → visión**: con un perfil con `--mmproj`, confirmar que la
  captura se inyecta como `image_url` y el modelo la describe (el agente VE lo que
  observa). Sin mmproj no se inyecta (gateado por `setVisionAvailable`).
- **Browser teach persistente**: grabar un skill con login (`--user-data-dir` en
  `browser_skills/profiles/<slug>`), cerrar, reproducir → la sesión sigue logueada
  (no re-pide credenciales).

## Build
- **Política actual (desde 2026-06-18): build Release + tests, sin Debug.**
  Compilar solo Release (no Debug) y correr `tests.bat` + el gate de ctest antes
  de commitear. La sección "Testing policy (OBLIGATORIA)" de arriba está vigente.
- App: `build.bat [Debug|Release|Both]` (tiene `pause`; correr con `< nul` para no colgar).
- Tests: `tests.bat [Debug|Release]` (sin `pause`).
- La lógica core vive en la lib estática `llamacode_core`; el app y los tests linkean contra ella.

### Encolamiento inteligente de builds (sesiones paralelas)
Varias IAs/CI pueden correr `build.bat` / `build_auto.bat` / `tests.bat` a la vez.
`build_coord.ps1` serializa por **lane** (`build` y `tests` tienen locks separados,
corren en paralelo entre sí) con un lock atómico (`.buildlock/`, gitignored):
- Si NO hay build en curso → tomás el lock (OWNER), bumpeás versión y compilás.
- Si ya hay uno en curso con la **misma fuente** (fingerprint = hash de
  `src/ qml/ tests/ CMakeLists.txt` con los triples semver neutralizados, para
  que el auto-bump no cuente) → esperás y **adoptás su resultado** (REUSE, no
  recompilás). Si ese build compartido falló, reintentás propio.
- Si es **otra fuente** → esperás tu turno (QUEUE).
- Locks muertos (guardian PID caído) o vencidos (`StaleSec`) se roban solos.
- El "owner" real es un proceso *guardian* oculto (su vida == el lock); `release`
  lo mata. Así el PID sí prueba vida (el powershell que hace `acquire` muere ya).
- Test: `powershell -File tests\test_build_coord.ps1` (fuera de ctest; infra PS/bat).
### Sesiones paralelas: worktree por tarea (preferido)
Si vas a hacer **más de una mejora a la vez**, no compartas el working tree:
```
powershell -File worktree.ps1 -Action new    -Name <tarea>   # ../LlamaCode-<tarea>, rama session/<tarea>
powershell -File worktree.ps1 -Action list
powershell -File worktree.ps1 -Action remove -Name <tarea> [-Force]
```
Cada worktree tiene su propio `build/`, `build_tests/` y `.buildlock/` (gitignored
root-anchored) → compilan en paralelo sin pisarse, y `git add` nunca mezcla hunks
de otra tarea. Comparte el object store: crearlo son segundos. Costo: el primer
build del worktree es full. `remove` sin `-Force` frena si hay cambios sin commitear.

**Por qué importa:** `build_coord.ps1` serializa *quién compila*, NO *qué fuente hay
en disco*. Con un tree compartido, la otra sesión edita `src/` mientras vos compilás
→ "error de compilación que no es mío", hunks ajenos en `CMakeLists.txt`, gate verde
que no corrió sobre tu fuente. Ningún lock lo arregla: la edición pasa fuera del lock.

### Hooks de convivencia (`tools/session_guard.ps1`)
`worktree.ps1` y `build_coord.ps1` son opt-in — hay que *acordarse*. Los hooks los
corre el harness solo, así que son el único punto donde esto se aplica sin
disciplina. Enganchados en `.claude/settings.json` (checkeado al repo):
- **SessionStart** → si el tree ya tiene trabajo sin commitear, lo lista y sugiere
  el worktree. Informativo.
- **PreToolUse(Edit|Write)** → claim por archivo en `.buildlock/claims/`. Si otra
  sesión viva (claim < 90 min) tocó ese archivo, **avisa** — no bloquea: un claim
  stale no debe trabar trabajo legítimo, y un choque de edición se arregla con un
  merge.
- **PreToolUse(Bash|PowerShell)** → **BLOQUEA** git de alcance global
  (`checkout/restore .`, `reset --hard`, `clean -fd`, `stash`, `add -A`/`.`) si hay
  trabajo sin commitear. Es el único caso irreversible. La forma **por path**
  (`git checkout -- src/foo.cpp`, `git add <path>`) pasa siempre: es la salida
  recomendada, no puede caer en el guard.

Test: `powershell -File tests\test_session_guard.ps1` (fuera de ctest, infra PS).

**Regla: los scripts de infra PS son ASCII puro** (`build_coord.ps1`,
`worktree.ps1`, `tools/session_guard.ps1`). Windows PowerShell 5.1 lee un `.ps1`
sin BOM como ANSI; un carácter UTF-8 dentro de un **string** se decodifica mal y
puede terminarlo (el em-dash `—` = `E2 80 94` → en CP1252 el `0x94` es `”`, que PS
toma como comilla de cierre → ParserError y el hook muere entero). En comentarios
sólo se ve feo; en strings rompe. El test 0 de `test_session_guard.ps1` lo fija.

- **Tree compartido en movimiento** (defensa, no cura — la cura es el worktree):
  `acquire` re-fingerprintea tras `-MutationCheckMs` (1200ms, 0 = off) y avisa si
  la fuente está cambiando *antes* de gastar minutos de MSBuild; `release`
  revalida el fingerprint y, si cambió durante el build, publica **DIRTY** en vez
  de OK (exit 12) → nadie adopta por REUSE un artefacto de otra fuente, y los
  `.bat` gritan que el binario/gate no es confiable.
