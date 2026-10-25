# Q122 · regresiones Linux para tandas de herramientas · 2026-10-25

## Pregunta

¿Las modificaciones actuales de `LlamaAgentBackend` para replanificar tandas mixtas de herramientas después del primer resultado pasan el gate Linux Release completo, manteniendo el fan-out de tandas que sólo contienen `task`?

## Alcance

- Validar el estado de trabajo existente; no editar ni reemplazar los cambios C++ del usuario.
- Ejecutar `scripts/tests-linux.sh Release`, que compila y corre el gate Linux completo sobre la copia nativa configurada por el script.
- Confirmar los tests de replanificación de herramientas y conservar la salida completa del gate.
- Mantener las variables de endpoint Q77/Q102 sin definir para que el canario Qwen opt-in se saltee; no permitir tráfico de inferencia accidental.

## Preflight

- OS: Linux Ubuntu 24.04, kernel `7.0.0-38-generic`, host `3090`.
- Memoria disponible: 111 GiB; espacio de la caché de build: 59 GiB; Qt 6.8.3, CMake y Ninja presentes.
- No se encontró proceso de inferencia; `LLAMACODE_Q77_SERVER_URL` y `LLAMACODE_Q102_SERVER_URL` no están definidos.
- Prerequisitos del script validados antes del build: usa Release, copia el checkout NTFS a `~/.cache/llamacode/source`, conserva allí el build `build_tests_linux` y acepta `LC_JOBS=4`.

## Prerregistro

- Comando exacto: `env -u LLAMACODE_Q77_SERVER_URL -u LLAMACODE_Q102_SERVER_URL LC_JOBS=4 ./scripts/tests-linux.sh Release`.
- Archivos bajo prueba y SHA-256 previos: `src/core/agent/LlamaAgentBackend.cpp` `d2ef9a49387a05d8352647dd8cfc14c053623cfbe24274fd756aa35784bb4071`; `.h` `29b0764343787de378c2ff774deb9177924008e97cf636688b53697f31ca4eab`; `tests/test_agent_wire.cpp` `cab4163c10275c2a3b1aeb6b183a531ee8eace1e61fe18a732e1765579043c44`; script `scripts/tests-linux.sh` `a342faa577999198c708698fce15774db676a938f93e7517f8e342a7af57ccc4`.
- Criterio: build Release y CTest terminan con exit 0; regresiones sintéticas de orden/replanificación pasan; el canario de Qwen permanece opt-in/skipped sin endpoint.
- Recursos: CPU y disco de caché únicamente. Sin modelo, inference server, GPU, descarga, red externa ni asignación artificial de memoria. Interfaz gráfica y perfiles productivos permanecen sin cambios.

## Límite

Un gate verde valida estas modificaciones de orden de herramientas; no implementa ni valida un principal autenticado o una policy por tenant. P2.1 seguirá bloqueado para pruebas con efectos multi-tenant hasta que exista ese contrato confiable.
