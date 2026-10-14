# Build receipt

- Intento estándar: `./scripts/build-linux.sh Debug`.
- Resultado: detuvo el espejo NTFS→caché con rsync exit 23 porque no pudo leer archivos de cachés Torch protegidos bajo artifacts de tareas previas. No se cambiaron permisos ni esos archivos.
- Recuperación usada: `rsync -a --exclude='.git/' --exclude='.claude/' --exclude='build*/' --exclude='work/' --exclude='artifacts/' <repo>/ /home/cristian/.cache/llamacode/source/`.
- Configuración CMake Debug completada con `-DBUILD_TESTS=OFF -DLC_USE_QTKEYCHAIN=ON`; `cmake --build /home/cristian/.cache/llamacode/build_linux --parallel 12` terminó con exit 0.
- Binario resultante: `/home/cristian/.cache/llamacode/build_linux/LlamaCode` (115.919.760 bytes; actualizado 2026-10-14 12:03:06 -0300).
- No se ejecutaron tests, inferencia ni GPU. La fuente del perfil `assets/system_profiles.json` y su copia en el espejo nativo tienen SHA-256 `fdf41e0578e39d3289a2bc05d0f3571a7100e280edb057250580f02a7e0b9758`.

## Windows candidate check

- `build/Debug/LlamaCode.exe` todavía tiene timestamp 2026-09-26 y tamaño 27.067.392 bytes.
- CMakeCache señala Visual Studio 17 2022 y Qt `C:\Qt\6.8.3\msvc2022_64`; ambos toolchains existen en la partición montada, pero no hay sesión Windows/CLR utilizable desde este host.
- Intento de consulta de la versión MSBuild bajo Wine: exit 255, `Wine Mono is not installed`. No se instaló Mono ni se modificó el `.exe` Windows.
- Siguiente acción: ejecutar el build prescrito por AGENTS.md (`build.bat Debug NOPAUSE`) en Windows, luego verificar el ejecutable y configurar las rutas Windows del perfil Strata.
