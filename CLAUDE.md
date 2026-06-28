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

## Build
- **Política actual (desde 2026-06-18): build Release + tests, sin Debug.**
  Compilar solo Release (no Debug) y correr `tests.bat` + el gate de ctest antes
  de commitear. La sección "Testing policy (OBLIGATORIA)" de arriba está vigente.
- App: `build.bat [Debug|Release|Both]` (tiene `pause`; correr con `< nul` para no colgar).
- Tests: `tests.bat [Debug|Release]` (sin `pause`).
- La lógica core vive en la lib estática `llamacode_core`; el app y los tests linkean contra ella.
