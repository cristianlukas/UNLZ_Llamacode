# ASTRA DEFAULT en YaRN 1M

**Estado: completa.** ASTRA DEFAULT ISTA IQ2_XS quedó configurado con YaRN 1M en Linux y Windows. Se actualizó el ejecutable Windows Debug, se preparó Strata y Python en D:, y se seleccionó el perfil en las preferencias Windows.

## Cambio

- Perfil de sistema: `sys-astra-iq2xs-default`; alias ASTRA y estado `best=false` conservados.
- Strata: `--max-context 1048576 --rope-scaling yarn --rope-scale 4 --yarn-orig-ctx 262144`.
- Perfil de la app: backend `ctx=1048576`; nombre visible actualizado a `1M YaRN ×4`.
- Modelo ISTA IQ2_XS, rutas y hashes de pesos, Strata 0.1.41, MTP4, spec-min-p 0.70, KV int8/resident 32768, GPUs 0/1, split, sampling y límites de seguridad no cambiaron.
- La selección ASTRA DEFAULT preexistente sigue siendo la activa en Linux. Una instancia Strata que ya esté cargada conserva su configuración hasta que se reinicie el servidor.
- La preferencia de Windows apunta a `sys-astra-iq2xs-default`; `Astra\StrataRoot` y `Astra\ConfigFile\sys-astra-iq2xs-default` apuntan al runtime/configuración en D:.
- El runtime Windows usa los pesos IQ2_XS ya existentes en D: y el MTP del paquete IQ3_XXS ya existente. No se descargaron pesos.

## Evidencia disponible

Se reutilizó el screening documentado, sin volver a ocupar las GPU:

- Contexto de 1.048.576: prompt real de 996.163 tokens; prefill 2.232,9 tok/s, decode 85,6 tok/s, solicitud 447,24 s.
- RAM RSS pico 51,14 GiB y VRAM pico GPU0/GPU1 23.822/22.454 MiB.
- NIAH sintético: 10/10 hechos exactos en una corrida a 1M.
- Es un screening de una corrida por punto y un fixture sintético; no confirma calidad general ni estabilidad estadística a contexto largo.
- Hard Mode histórico mantiene 77,98/100, 154,19 tok/s media y 11:05 total. TC-92 (fuga entre tenants) y TC-74 fallaron 3/3; `best=false` se conserva. No asignar al perfil datos sensibles ni tareas que exijan aislamiento multi-tenant.

Fuentes: [barrido de contexto](../Q-20261014-ISTA-CONTEXT-SWEEP/RESULTS.md), [Needle in a Haystack](../Q-20261014-ISTA-NEEDLE-HAYSTACK/RESULTS.md) y [Hard Mode](../Q-20261009-STRATA-QWEN38-27B-AB/RESULTS.md).

## Verificación, build y configuración Windows

- Se validó el JSON del catálogo y de la configuración activa, la presencia única de cada flag, el límite 1.048.576 y que los argumentos no relacionados de Strata no cambiaran.
- Los cambios del perfil del catálogo se limitaron a `backend.ctx`, nombre visible y comentario de evidencia. El perfil continúa con `best=false`.
- `git diff --check`: correcto.
- `./scripts/build-linux.sh Debug` no pudo espejar artefactos protegidos en NTFS (`rsync` exit 23; permiso denegado en cachés Torch anteriores). No se alteraron esos archivos ni sus permisos.
- Se espejó el código a la caché nativa excluyendo `artifacts/`; CMake Debug y el enlace terminaron correctamente. Ejecutable Linux: `/home/cristian/.cache/llamacode/build_linux/LlamaCode`.
- Para Windows se compiló `build/LlamaCode.sln` con MSBuild 2022, configuración `Debug|x64`, dentro de un prefijo Wine aislado. Se inicializó el entorno x64 de Visual Studio y se pasaron explícitamente las rutas de include y librerías del SDK 10.0.26100.0. MSBuild terminó con exit 0.
- Ejecutable actualizado: [`build/Debug/LlamaCode.exe`](../../../build/Debug/LlamaCode.exe), 27.582.464 bytes, SHA-256 `dbca39f84fb6de8d6b944d4aba1576571dba13d58051539d6aceedf6c0f1bddc`, fecha 2026-10-14 12:58 local. `windeployqt` terminó con exit 0; también se desplegó `Qt.labs.settings`. Recibos: [`windows-build-attempt-11.log`](receipts/windows-build-attempt-11.log), [`windows-deploy-with-vcvars.log`](receipts/windows-deploy-with-vcvars.log), [`windows-runtime.json`](receipts/windows-runtime.json).
- Strata 0.1.41, su engine Windows, Python 3.12.10, dependencias y bibliotecas CUDA 13 se instalaron en `D:\LlamaCodeRuntime\Strata`; wheels y descargas tienen hashes en `D:\LlamaCodeDownloads\windows-runtime-20261014`. Se reutilizaron ambos shards IQ2_XS, el pack, el tokenizador y el directorio MTP ya instalados en D:. Todas las rutas de entrada y la carpeta de runtime fueron comprobadas desde Linux.
- Se guardó una copia verificable de `NTUSER.DAT` y sus archivos de transacción en `D:\LlamaCodeDownloads\windows-runtime-20261014\windows-user-hive-backup`. Tras validar una hive temporal con hivex, se actualizó la preferencia Windows de forma atómica y se volvió a leer para comprobar los tres valores.
- No se ejecutaron tests automatizados, el GUI en Windows, inferencia ni GPU. `windeployqt` informó que no encontró `dxcompiler.dll`/`dxil.dll`; Wine tampoco pudo importar NumPy (`ucrtbase.dll.crealf` no está implementada en Wine). El build y la configuración quedan instalados, pero no se declara verificado un arranque ni una inferencia Windows. `astra-iq2xs.log` se crea cuando Strata arranca por primera vez.

Hashes efectivos y checks: [verificación](receipts/verification.json), [estado anterior y posterior](receipts/before-state.json) y [configuración exacta](receipts/after-state.json). Backups: [`receipts/backup/`](receipts/backup/).

## Rollback

1. En `/home/cristian/.config/LlamaCode/astra-iq2xs-strata.json`, volver `--max-context` a `131072` y eliminar `--rope-scaling`, `--rope-scale` y `--yarn-orig-ctx`.
2. En `assets/system_profiles.json`, restaurar para `sys-astra-iq2xs-default` los campos `backend.ctx`, `displayName` y `comment` desde `receipts/backup/sys-astra-iq2xs-default.before.json`. No reemplazar el catálogo completo.
3. Ejecutar `./scripts/build-linux.sh Debug` para la app Linux (o repetir el espejo excluyendo `artifacts/` según `receipts/build.md`). En Windows, restaurar el backup verificado de `NTUSER.DAT` sólo si no hubo otros cambios de preferencias desde que se creó; si ya los hubo, revertir selectivamente `LastLaunchId` y la subclave nueva `Astra`.
4. Reiniciar ASTRA para que Strata cargue el rollback.

El valor previo de `LastLaunchId` era `f1a7c4d0-5e92-41b3-c8f6-0a4d9e2b3758`; está respaldado junto con el hive original en la partición D:. Los pesos, sus rutas y los demás perfiles no requieren cambios para volver a 131K.
