# Q38 · Reanudación iterativa de VF-20261019-01

Fecha de inicio: 2026-10-22T16:18:23Z
Lock: `Q-20261022-VF-ITERATION-38`

## Objetivo

Continuar el orden priorizado del usuario y cerrar sólo pruebas cuyo resultado
pueda cambiar una decisión. Antes de reabrir inferencia, completar el accionable
P0 de aislamiento: Q35/Q37 validaron un runner, pero no todos los lanzadores.
Revalidar también si el preview NInfer Flash-Next puede ejecutarse en este
entorno después de la reparación hecha por el usuario en Windows.

## Prerregistro

1. Hacer una auditoría estática de los puntos de entrada mantenidos del
   repositorio que puedan lanzar workers de inferencia/evaluación. Buscar
   lanzadores en `scripts/`, `tools/`, código de proceso/benchmark de la app y
   los scripts activos de evaluación; excluir copias vendorizadas, snapshots de
   runtime y datos de resultados. Para cada punto encontrado registrar el
   proceso hijo, la frontera de cgroup/Job Object, límites duros de memoria y
   swap, política OOM, monitor/cleanup y persistencia de recibos. No generalizar
   desde Q35.
2. Inspeccionar sólo las rutas locales de Windows/Linux ya montadas para NInfer
   y Flash-Next (binarios, release/runtime y peso exacto). No descargar,
   compilar, emular Windows, ni iniciar modelo. Resultado habilitante sólo si
   hay un runtime Windows invocable desde este host o soporte Linux explícito y
   están presentes artefactos compatibles.
3. Revisar fuentes primarias de los cuatro materiales marcados bloqueados que
   puedan haber cambiado (#26, #28, #31, #32). Si no hay contenido atribuible o
   condición nueva, registrar el bloqueo concreto y no derivar una prueba.
4. No usar GPU, no iniciar inference server, no modificar modelos, perfiles,
   datos productivos ni código de aplicación en esta iteración. Si una prueba
   futura pasa sus gates, deberá tener preregistro propio, preflight fresco y
   ejecución serial.

## Addendum de plataforma · 2026-10-22T16:26Z

La revisión de fuentes encontró un cambio material posterior al gate inicial:
Don-Chad publicó NInfer v0.16.1 con binarios Windows x64. El release incluye
Flash-Next como preview, pero dice que Flash-Next no formó parte de su benchmark
de inferencia y que el paquete publicado es sólo Windows. El README mantiene el
límite de que Flash-Next sólo se construyó y ejecutó en Windows. En el host de
esta sesión seguimos en Ubuntu 24.04, sin `powershell.exe`, `pwsh` ni `cmd.exe`.

Hay shards locales del GGUF Flash-Next IQ2_XS, pero no se halló un contenedor
NInfer v3 `.ninfer` ni una runtime Windows v0.16.1 en las raíces de evaluación
consultadas. La guía del fork requiere el contenedor convertido y un volumen
n-gram adicional. Por tanto se reabre como prueba **pendiente por acceso de
ejecución a Windows y preparación/conversión de artefactos compatibles**; no se
declara bloqueado por soporte de producto ni se extrapolan las cifras publicadas.
No descargar, convertir, compilar ni ejecutar desde esta sesión.

La auditoría estática también confirma que el aislamiento probado de Q35/Q37 no
se extiende a todos los runners: los scripts genéricos actuales inician servidores
con `Start-Process`/`subprocess.Popen` directo, mientras que `HarnessSandbox`
proporciona protecciones sólo cuando la app lanza workers mediante ese módulo.
P0 permanece abierto hasta centralizar y verificar límites/cierre de procesos en
los entrypoints de evaluación para Linux y Windows.

## Criterios de cierre

- El inventario de lanzadores incluye ruta/fuente y evidencia verificable para
  cada clasificación; el estado de aislamiento se distingue como verificado,
  ausente o no determinable.
- El gate NInfer queda habilitado sólo con runtime/artefactos locales compatibles
  o soporte de plataforma documentado y ejecutable.
- Cada material revalidado termina como accionable, sin prueba aplicable,
  duplicado o bloqueado por condición concreta.
- Actualizar `WORK_QUEUE.md`, recibos locales y Sheets al concluir la auditoría.
