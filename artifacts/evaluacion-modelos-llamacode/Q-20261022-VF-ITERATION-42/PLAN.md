# Q42 · Contención del launcher Linux de ASTRA/Strata

## Objetivo

Extender el scope de evaluación ya validado en Q41 al entrypoint
`scripts/run-astra-strata.sh`. Evitar que el cierre o un OOM del servidor Strata
deje procesos hijos huérfanos o compita con Codex/escritorio. No cambiar pesos,
runtime, argumentos de modelo, contexto, sampling, perfiles ni configuración
productiva.

## Prerregistro

1. Antes de iniciar cualquier proceso, comprobar lock propio, `systemd-oomd`,
   ausencia de inference servers/listeners de evaluación y hashes de los archivos
   fuente relevantes. Usar exclusivamente runtime/servidor falsos y CPU.
2. Añadir al launcher Linux un wrapper CLI que use el helper Q41. Debe fallar
   cerrado si no puede crear el scope protegido, preservar argumentos/entorno,
   ubicación `background.slice`, `OOMPolicy=kill`, `KillMode=control-group`,
   `ManagedOOM*=kill` y `oom_score_adj=900`; no fijar límites finitos de memoria
   ni swap.
3. Canario A: un falso servidor escribe un marcador de argv/cwd/env, produce
   stdout y termina con código 23. Verificar propagación exacta del código,
   salidas y cleanup del scope.
4. Canario B: un falso servidor escribe su PID y espera; enviar SIGTERM al
   launcher, verificar que se detengan el scope y el servidor, que el launcher
   cierre y que el controlador siga vivo.
5. Verificar en ambos canarios el cgroup y las propiedades de la unidad exacta;
   verificar `MemoryHigh/MemoryMax/MemorySwapMax=infinity` y ausencia de procesos
   propios sobrevivientes. No generar presión global, no cargar modelos y no
   usar GPU.

## Criterios de pase

- A y B pasan en Ubuntu con el helper Q41 y `systemd-oomd.service` activo.
- El script Linux preserva las opciones y validaciones existentes, falla cerrado
  antes de lanzar el servidor si no hay contención y no fija caps de memoria/swap.
- Windows permanece sin cambios. Un pase no cierra el P0 global: los launchers
  PowerShell/Job Objects aún requieren implementación y validación Windows nativa.

## Criterios de aborto

No iniciar si hay otro lock, inference server, listener de evaluación, oomd
inactivo, `sudo -n` no disponible o si el scope no se puede atribuir a la unidad
exacta. Si falla un canario, corregir sólo el harness y preregistrar el reintento;
no ejecutar Strata real en esta tarea.

## Enmienda 01

El primer intento del probe fue rechazado por `noexec` del volumen NTFS al
invocar directamente el script; falló antes de iniciar el falso servidor o crear
un scope. Repetir sin cambiar el comportamiento del producto invocando el mismo
launcher como `bash scripts/run-astra-strata.sh`. Guardar el recibo de reintento
en un archivo distinto para conservar el rechazo original.

## Enmienda 02

El intento 02 pasó el caso de salida natural (rc 23 y cleanup), pero el caso
SIGTERM agotó 15 s. El postflight confirmó que el scope y el falso proceso ya
habían desaparecido. No atribuirlo como pase. El intento 03 conserva el caso
SIGTERM con sondeo acotado del `ActiveState` del scope exacto y registra si el
controlador termina antes de invocar cleanup de contingencia sobre esa misma
unidad. No se empleará `pkill` ni se tocarán scopes ajenos.

## Enmienda 03

El intento 03 pasó otra vez la salida natural, pero el SIGTERM no devolvió el
launcher y el probe usó `SIGKILL` sólo contra ese controlador temporal antes del
cleanup exacto del scope; el postflight no encontró unidad ni fake server. Para
el intento 04, el handler sólo guardará la señal recibida; el bucle principal
hará `ScopedProcess.stop()` fuera del handler, evitando bloquear dentro del
callback de señal. Conservar el recibo del intento 03 y exigir rc 143 en la
repetición.

## Enmienda 04

Tras pasar exit y SIGTERM en el intento 04, repetir los dos canarios una vez
añadiendo un marcador de entorno inocuo (`Q42_CANARY_ENV=q42-preserved`) al
runtime falso. Verificar que el launcher protegido conserva el entorno heredado,
además de argv/cwd/código. No pasar ni imprimir secretos reales; guardar el
resultado en un recibo nuevo.

## Evidencia

Registrar comandos, timestamps UTC, hashes, PID/cgroup/estado de unidad antes y
después, salida/código del hijo falso, y limpieza final en `receipts/`. El único
proceso lanzado será el runtime falso creado dentro de un directorio temporal.
