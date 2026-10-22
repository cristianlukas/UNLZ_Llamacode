# Q41 · Contención de lanzadores de evaluación Linux · 2026-10-22

Lock exclusivo: `Q-20261022-VF-ITERATION-41`, token `a5758823-c599-48e3-afe5-d34381057eed`.

## Pregunta

¿Puede el proceso de una prueba en Linux aislarse en un cgroup system-manager con límites verificables, sin depender de `user@1000.service`, y sin perder stdout, estado de salida ni cleanup de los launchers actuales?

## Evidencia previa y alcance

Q38 encontró que `tools/kv_cache_ab.py`, `tools/meter_system_profiles.py` y `scripts/run-astra-strata.sh` lanzan hijos directamente. Q35/Q37 demostró que servicios transitorios del system manager en `background.slice` aíslan al worker que contiene el modelo de la GUI de Codex. Este trabajo cubre sólo los entrypoints Linux identificados; no declarará resueltos los launchers PowerShell de Windows.

## Experimentos preregistrados

### C41-01 · canario de launcher con scope system-manager (CPU-only)

- Lanzar un proceso inocuo y acotado mediante `systemd-run --system` en `background.slice`, con UID/GID del usuario actual, `MemoryHigh`, `MemoryMax`, `MemorySwapMax=0`, `TasksMax`, `CPUQuota` y `KillMode=control-group` si el manager acepta la propiedad en un scope.
- El child debe informar su cgroup. Leer de vuelta propiedades efectivas, alcance del cgroup, retorno del wrapper y cleanup. Sin modelo, servidor, build ni carga GPU.
- Si el scope no admite las propiedades necesarias, se detiene el diseño antes de modificar launchers; se documenta la condición y no se usa un wrapper que no garantice sus límites.

### C41-02 · regresión de OOM sintético (sólo si C41-01 pasa)

- En unidad transitoria con límite de 128 MiB, un worker sintético intenta reservar 512 MiB y crea un hijo.
- Pase: el OOM queda dentro de `background.slice`; cgroup y descendientes terminan; el controlador de prueba sigue vivo; la política efectiva corresponde a los límites prerregistrados. No usar GPU ni matar procesos ajenos.

### C41-03 · integración con launchers Linux (sólo si C41-02 pasa)

- Inspeccionar e integrar un helper compartido en los entrypoints Linux listados, manteniendo logs, exit code y stop/cleanup del árbol.
- Añadir regresiones CPU-only para la construcción de argv y el ciclo de vida. No tocar los scripts PowerShell, perfiles, pesos ni runtime productivos desde Ubuntu.

## Criterio de parada

Ante permiso faltante, propiedad systemd no soportada, cgroup fuera de `background.slice`, `OOMPolicy`/cleanup no verificable, pérdida de salida/exit status o cualquier servidor de inferencia activo, detenerse sin modificar lanzadores ni cargar modelos. La prueba no reduce la memoria solicitada por modelos: los límites se usarán sólo para contener workers de evaluación y se harán configurables.

## Enmienda 01 · 2026-10-22T17:13Z

El intento de invocación con `--scope --pipe` fue rechazado por systemd con el mensaje `--pty/--pipe is not compatible in timer or --scope mode`; el comando terminó antes de crear la unidad/proceso. No se reportó stdout/exit porque no hubo child. El canario se reintentará sin `--pipe`: el child escribirá su receipt a archivo; se comprobarán cgroup y propiedades mientras vive, además del exit code del wrapper. Esto conserva la pregunta y los límites preregistrados.

## Enmienda 02 · 2026-10-22T17:14Z

El intento 02 también fue rechazado antes de crear el proceso: `Type=exec` es una propiedad de servicio, no de scope. Un scope tampoco ofrece la política de ciclo de vida `OOMPolicy=kill` requerida por C41. Se cambia C41-01 a la unidad **service** transitoria ya usada en Q37: `systemd-run --system --pipe --wait --collect`, `Type=exec`, `background.slice`, `MemoryMax/MemorySwapMax`, `OOMPolicy=kill` y `KillMode=control-group`. El canario escribirá su receipt a disco y devolverá código 23 deliberadamente; el supervisor debe observar ambos. Se comprobará el cgroup efectivo mientras corre. Si el servicio no preserva la salida/código o el ciclo de vida, se para antes de integrar launchers.

## Enmienda 03 · 2026-10-22T17:18Z

Corrección de diagnóstico tras consultar `man systemd.scope` y `man systemd.resource-control`: los scopes sí aceptan `OOMPolicy=` además de `MemoryMax=` y `MemorySwapMax=`. El rechazo del intento 02 se debió exclusivamente a `Type=exec`, que es una propiedad de servicio; los intentos anteriores tampoco llegaron a evaluar OOMPolicy. Antes de integrar el wrapper service, probar un scope **sin `--pipe` ni `Type=exec`** mediante `Popen`, con `sudo -E`, marcadores de entorno/cwd, stdout/exit code y lectura de propiedades/cgroup mientras corre. Usar scope si conserva esas semánticas; el servicio de C41-01/C41-02 queda como fallback validado.

## Enmienda 04 · 2026-10-22T17:19Z

C41-03 scope probe attempt 01 terminó antes del child: `--wait may not be combined with --scope`. El canario elimina `--wait` y mantiene stdout heredado y la espera natural del proceso de comando; si el cliente vuelve antes que el child o no propaga el código de salida, scope se descarta para integrar `Popen`.

## Enmienda 05 · 2026-10-22T17:19Z

C41-03 scope probe attempt 02 lanzó el child y confirmó stdout, exit 23, entorno, cwd, UID/GID, cgroup y propiedades efectivas; la validación marcó límites como fallidos por buscar claves snake_case cuando el receipt usa camelCase. Se corrigió sólo el matcher del receipt (`memoryHigh`, `memoryMax`, `memorySwapMax`, `oomGroup`) y se repite el mismo canario sin cambiar la pregunta ni los límites.

## C41-04 · OOM sintético dentro del scope system-manager (CPU-only)

Antes de usar scope en un launcher, repetir el OOM 512 MiB/128 MiB del worker de C41-02 dentro del cgroup `.scope` que se obtuvo mediante `Popen`. Capturar límites y cgroup mientras el worker está activo, `memory.events` durante la presión, resultado/journal, estado de los dos procesos y supervivencia del controlador. Si el OOM no queda contenido/registrado o el scope afecta al controlador, descartar esta modalidad y usar únicamente el servicio transitorio de Q37/C41-02.

## Enmienda 06 · 2026-10-22T17:20Z

C41-04 scope OOM attempt 01 fue rechazado antes de iniciar el worker: el scope no admite `OOMScoreAdjust=900`. El servicio C41-02 lo admite, pero este atributo no es necesario para el gate de aislamiento; se elimina sólo de la prueba de scope. `OOMPolicy=kill`, `KillMode=control-group`, `MemoryOOMGroup`, `MemoryMax` y `MemorySwapMax` permanecen en el protocolo.

## Enmienda 07 · 2026-10-22 · recuperación tras reinicio

C41-04 scope OOM attempt 02 sí lanzó el worker y escribió `c41-04-worker.json`, pero el controlador abortó antes de muestrear el OOM: esperaba que `worker.cgroup` tuviera formato `0::/ruta`, mientras el worker guarda sólo `/ruta`; el formato completo está en `child_cgroup`. El scope exacto `llamacode-q41-scope-oom-299361-103c5.scope` ya está inactivo, el journal dice `Deactivated successfully` y los PIDs 299363/299365 no existen. No queda proceso huérfano. El resultado es inconcluso, no pasa el gate: al abortar el controlador no se leyó `memory.events` y systemd no registró OOM.

Antes del siguiente intento se corrige el normalizador de ambas representaciones y se rodea el ciclo de vida con `try/finally` para detener exclusivamente el scope de esta corrida si el controlador falla y confirmar que no queden worker/child vivos. El controlador abrirá `memory.events` mientras el scope existe y conservará ese descriptor para observar el incremento de `oom_kill` aunque el scope desaparezca tras morir todo el grupo. Se preregistra un único C41-04 attempt 03, CPU-only, mismo worker 512/128 MiB y sin tocar modelos/GPU. Sólo pasa si hay incremento OOM verificable, ambos descendientes terminan, el controlador sobrevive y las propiedades/cgroup concuerdan; si el descriptor no permite observar el evento o el OOM no queda contenido, se descarta integrar scopes y se conserva el patrón service ya probado en C41-02.

## Enmienda 08 · 2026-10-22 · atribución de la evidencia OOM

C41-04 scope OOM attempt 03 terminó con `Result=oom-kill`; el journal de la unidad exacta indica que un proceso de ese scope fue matado por OOM. El worker y su hijo están ausentes, ambos compartían el cgroup `/background.slice/llamacode-q41-scope-oom-304731-49e6f.scope`, los límites/`OOMPolicy`/`KillMode` se leyeron correctamente mientras corría y el controlador sobrevivió. `systemd-run` retornó -9. Esto confirma contención por unidad.

El recibo del attempt 03 no indica si la lectura de `memory.events` ocurrió antes o después de desaparecer el scope, así que su delta no se atribuye al cgroup local. El recibo/script separarán contadores muestreados mientras existe el cgroup de la lectura no atribuible posterior. La evidencia aceptable de OOM será un incremento muestreado mientras vive el scope **o** `Result=oom-kill`/journal de esa unidad. Se preregistra attempt 04 para validar el recibo corregido una vez, con los mismos límites/worker y sin inferencia/GPU; si pasa, C41-04 queda aprobado.

## Enmienda 09 · 2026-10-22 · C41-04 aprobado y siguiente gate

C41-04 attempt 04 pasó el recibo corregido. Mientras el scope existía, el controlador muestreó `memory.events`: `oom=1`, `oom_kill=3`, `oom_group_kill=1`; al terminar ya no existía la ruta del scope y no hubo lectura post-exit atribuida. `systemctl show` confirmó `Result=oom-kill`, y el journal de la unidad exacta registró la muerte por OOM. Worker e hijo ausentes; controlador vivo; límites y cgroup verificados. No se asigna significado local al campo de eventos del intento 03, cuyo recibo no distinguía si la lectura ocurrió antes o después de la desaparición.

### C41-05 · alcance de un helper Linux para los launchers de pruebas

Preregistrar un helper compartido para las rutas Linux nativas que ejecutan pruebas/modelos: `background.slice`, scope del system manager, `OOMPolicy=kill`, `KillMode=control-group`, sin `MemoryHigh/Max` ni límite de swap para no recortar memoria solicitada por el modelo, y `oom_score_adj=900` en el proceso ejecutado (heredable por sus hijos) para preferir el árbol de evaluación si hubiera OOM global. Correr una canaria CPU-only de proceso corto y otra de larga duración con stop explícito; verificar cgroup, score del padre/hijo, stdout/exit code, parada del árbol y limpieza del scope. Si permisos/systemd/score/lifecycle no se confirman, no integrar.

Sólo si C41-05 pasa, integrar en el camino Linux nativo de `tools/kv_cache_ab.py`, que comparte el arranque de `tools/long_context_matrix.py` y `tools/context_tps_matrix.py`. Mantener Windows y WSL sin cambios y no tocar el medidor Windows `tools/meter_system_profiles.py`. Documentar que `scripts/run-astra-strata.sh` y PowerShell siguen pendientes; P0 global continúa abierto. Ejecutar pruebas Python pertinentes y un `--dry-run`; no cargar modelos, usar GPU ni alterar perfiles/pesos.

## Enmienda 10 · 2026-10-22 · import del canario C41-05

C41-05 lifecycle canary attempt 01 terminó antes de crear scope: al ejecutar el controlador desde su subcarpeta, `sys.path` no incluía la raíz y falló `from tools.linux_eval_scope`. No se lanzó proceso. El controlador añadirá la raíz del repo a `sys.path` antes del import; se repite el mismo canario sin cambiar la conducta evaluada.

## Enmienda 11 · 2026-10-22 · comparación de salida C41-05

C41-05 lifecycle canary attempt 02 ejecutó las dos fases y la parada explícita. Ambos recibos muestran marcador/cwd correctos, `oom_score_adj=900` heredado por el hijo y cgroups `.scope` bajo `background.slice`; las dos unidades quedaron `inactive/dead` y los cuatro PIDs no existen. El controlador falló después del cleanup al comparar `bytes` con `str`, porque no solicitó `text=True` a `Popen`; no evaluó ni guardó el resultado final de stdout/exit. Se preservan los dos receipts de worker; el attempt 03 sólo añadirá modo texto a las dos capturas y repetirá el mismo canario.

## Enmienda 12 · 2026-10-22 · modo texto del helper C41-05

C41-05 attempt 03 terminó antes de lanzar proceso: el controlador pasó `text=True` al helper para capturar stdout/stderr como strings, pero `popen_in_background_scope` aún no exponía ese parámetro. No hubo scope. Se agrega `text` opcional, transmitido a `subprocess.Popen`, y se repite el mismo canario como attempt 04.


## Enmienda 13 · 2026-10-22 · revalidación del stop en start_server

Después del C41-05 integration probe se mejoró `RunningServer.stop` para cerrar siempre el log y reportar un fallo del stop callback, y se añadió su regresión unitaria. Se preregistra repetir una vez el integration probe CPU-only de `tools.kv_cache_ab.start_server` para confirmar que el helper todavía mata el árbol y deja la unidad inactiva. Sin modelo ni GPU.

## Enmienda 14 · 2026-10-22 · elegibilidad explícita para systemd-oomd

La consulta del host confirma `systemd-oomd.service` activo; los scopes heredan `ManagedOOMMemoryPressure=auto` y `ManagedOOMSwap=auto`, que no los hacen candidatos salvo que un ancestro los marque. Para evitar que una evaluación fuera de la sesión de usuario deje a Codex como único candidato observado por oomd, el helper marcará el scope con `ManagedOOMMemoryPressure=kill` y `ManagedOOMSwap=kill`. Esto no fija topes de memoria/swap ni confirma que oomd haya matado un proceso; sólo incluye el árbol de evaluación entre los candidatos cuando oomd debe actuar. Se preregistra repetir lifecycle y la integración `start_server`, leyendo ambas propiedades de vuelta y manteniendo `MemoryHigh/Max/SwapMax=infinity`. Sin presión sintética global, modelo ni GPU.

## Enmienda 15 · 2026-10-22 · preflight fail-closed de oomd

Como las propiedades `ManagedOOM*=kill` sólo producen protección efectiva si `systemd-oomd` está disponible, el helper comprobará `sudo -n systemctl is-active systemd-oomd.service` antes de crear el scope. Si el servicio no está activo o sudo no es no-interactivo, lanza error antes de iniciar el modelo. Se preregistra repetir lifecycle e integración CPU-only; no habrá modelo/GPU.

## Enmienda 16 · 2026-10-22 · resultado final C41-05

El preflight `systemd-oomd.service` pasó y los canarios lifecycle/integración pasaron con `ManagedOOMMemoryPressure=kill`, `ManagedOOMSwap=kill`, `OOMPolicy=kill`, `KillMode=control-group`, `oom_score_adj=900` heredado y sin topes memory/swap. El helper falla antes del modelo si el servicio no está activo. Las regresiones `test_kv_cache_ab.py` pasaron 11/11 y el parser 3/3; dry-run 8K/16K no lanzó servidor. Se integra sólo el camino Linux nativo de `kv_cache_ab.py` y sus dos callers. No se hizo inferencia/GPU. Q41 queda listo para cierre con P0 global abierto por Strata/PowerShell.
