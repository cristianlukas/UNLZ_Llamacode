# Control de detener servidor LAN

Fecha: 2026-10-09

## Cambio

- Los inicios habituales `Iniciar servidor + agente` e `Iniciar servidor` comparten el Gateway por LAN cuando está marcada `Compartir en LAN al iniciar`.
- Se quitó la acción duplicada `Iniciar LAN con este perfil`; `Iniciar LAN sin cargar perfil` sigue disponible para levantar sólo el Gateway y permitir que el cliente elija perfil.
- Con el Gateway LAN activo, aparece `Detener servidor LAN`. Desactivar `gatewayLanEnabled` cambia el bind del Gateway a loopback y mantiene el listener local, el motor y el agente locales.
- La opción de autenticación sigue en el mismo panel previo al inicio.

## Verificación

- `./scripts/build-linux.sh Debug`: correcto; produjo `/home/cristian/.cache/llamacode/build_linux/LlamaCode`.
- SHA-256 del binario Debug: `5ccc1a2cd017173ef357344c49cb76d2a5f90c50e83a8a9f84e31f1c83f0581c`.
- `./scripts/tests-linux.sh Release`: 79/79 pruebas pasaron, incluido `controller_startLanGatewayRetriesWhenSettingsAlreadyEnabled`, que comprueba que al desactivar LAN el Gateway continúa activo localmente.
- `git diff --check`: correcto.

## Archivos

- `qml/pages/LaunchPage.qml`
- `tests/test_system_profiles.cpp`
- `README.md`
- `docs/astra-strata.md`

El cambio preexistente en `profiles/launches.json` se dejó intacto.
