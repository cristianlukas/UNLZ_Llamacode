# Operación headless

LlamaCode puede ejecutarse sin QML con `--agent-daemon` (alias `--headless`).
La API local se documenta en [`control-api.md`](control-api.md).

## Smoke test de perfiles de personalidad y estilo

El test completamente offline es:

```powershell
.\tests.bat Debug
```

Para aislarlo durante desarrollo:

```powershell
cmake --build build_tests --config Debug --target test_agent_profiles
ctest --test-dir build_tests -C Debug -R test_agent_profiles --output-on-failure
```

Ese test no requiere GUI, llama-server, modelo, red, GPU ni escritorio visible.
Usa `QTemporaryDir` para que la persistencia no toque los perfiles del usuario.

La prueba HTTP equivalente arranca el daemon con un puerto localhost y un
`LLAMACODE_PROFILES_DIR` temporal, consulta `profileManager` mediante
`/methods?target=profileManager` y ejecuta sus `Q_INVOKABLE` con `/invoke`.
El procedimiento específico está en
[`personality-style-profiles.md`](personality-style-profiles.md).

Los tests que necesiten escritorio, navegador headed, audio físico o interacción
visual no son parte de este smoke test: deben estar separados y marcados como
QA opt-in, nunca ser un requisito del gate headless.
