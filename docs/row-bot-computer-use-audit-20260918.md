# Auditoría Row-Bot v4.9.1 — Computer Use — 2026-09-18

## Resultado

Row-Bot v4.9.1 es una referencia útil de producto y seguridad para el modo de
control de PC, pero no es un perfil de modelo ni un motor de inferencia. No
aporta una mejora de PP, TG, BCB, HE, visión del modelo o contexto, así que no
se modifica la tabla de modelos ni el default SOL.

La referencia oficial describe cuatro ideas relevantes: Buddy como overlay
desacoplable que conserva el hilo seleccionado; separación estricta entre
Browser Automation y Computer Use nativo; Computer Use opt-in con una sola
sesión interactiva; y targets/snapshots efímeros con aprobaciones, cancelación
y receipts. La versión más reciente revisada es v4.9.1, que además ajusta el
readiness por diagnóstico y deja la prueba con Calculator como verificación
opcional. Ver [releases de Row-Bot](https://github.com/siddsachar/row-bot/releases) y
la [documentación oficial de Computer Use](https://row-bot.ai/docs/computer-use/).

## Comparación con LlamaCode

| Capacidad | LlamaCode antes de esta auditoría | Resultado |
| --- | --- | --- |
| Browser separado de escritorio | `browserBackground` y escritorio foreground son superficies distintas | Ya cubierto |
| UI semántica antes que coordenadas | UI Automation → OCR → plantilla → coordenada normalizada | Ya cubierto |
| Snapshots efímeros | `snapshot_id`, fingerprint y stale guard | Ya cubierto |
| Evidencia | receipts con estrategia, hashes, sesión, correlación y redacción | Ya cubierto |
| Teach/reparación | Teach v3 con precondición, postcondición y reparación acotada | Ya cubierto |
| Exclusión entre corridas | mutex dentro del proceso y lease de acciones por worker | Faltaba proteger instancias separadas |
| Overlay Buddy | LlamaCode tiene ventana principal y bandeja, pero no un Buddy desacoplable equivalente | Mejora futura de UX, no necesaria para la seguridad |
| Readiness/diagnóstico | Entrenamiento requerido para tareas desktop y políticas locales; no hay aún una prueba E2E de readiness equivalente a Cua Driver | Brecha acotada |
| Take over/reanudación | Lease, cancelación y stale guard; falta una interacción manual Windows validada de punta a punta | Brecha E2E |

## Mejora implementada

Se agregó `DesktopComputerUse::ProcessSessionGuard`, un `QLockFile` en
`AppLocalDataLocation/desktop-computer-use.lock`:

- sólo se adquiere al ejecutar la primera acción mutante de escritorio;
- cubre también la convivencia entre la instancia GUI y un daemon/Task separado;
- se mantiene durante la sesión del agente, no sólo durante un click;
- se libera en `shutdown()`, al cambiar de sesión y al destruir el worker;
- una instancia competidora recibe un rechazo explícito en vez de intercalar
  teclas, mouse o foco;
- si el proceso muere, el lock puede recuperarse mediante la detección de PID
  obsoleto de `QLockFile`.

Esto complementa, sin reemplazar, el stale guard de snapshots y el mutex local.
No se habilitó un overlay permanente ni se cambió el comportamiento de las
automatizaciones existentes.

## Validación

- Build Linux nativo Release con Qt 6.8.3/GCC: compilación y link de los cuatro
  targets completados.
- `test_automation`: **38/38 PASS en 14 ms**.
- `test_desktop_backend`: **5/5 PASS**.
- `test_visual_matcher`: **8/8 PASS en 294 ms**.
- `test_automation_store`: **8/8 PASS**.
- CTest focalizado: **4/4 targets PASS**, 100% sin fallos, 0,37 s total.
- Nueva regresión: dos guards no pueden adquirir simultáneamente la sesión;
  después de liberar el primero, el segundo adquiere correctamente.
- La regresión ejecutada valida exclusión dentro del proceso. La cobertura real
  entre dos procesos GUI/daemon y la recuperación después de un proceso muerto
  queda pendiente de una prueba Windows separada; no la cuento como PASS sólo
  porque `QLockFile` exista.
- Los probes que mueven mouse, teclado o foco no se ejecutaron en Linux para no
  alterar el escritorio durante el gate. La prueba E2E restante debe usar una
  aplicación neutra, una ventana real y una matriz de foco/stop/reanudación.

## Decisión sobre perfiles

No se agrega ningún modelo ni perfil nuevo. Row-Bot mejora la referencia de UX
y seguridad del control de PC; la mejora concreta aplicada a LlamaCode es la
exclusión entre procesos. Un Buddy desacoplable podría evaluarse más adelante
como feature de interfaz, con pruebas multimonitor, foco, tray, stop y
restauración. También conviene agregar un gate de readiness explícito y un
probe Windows cross-process antes de afirmar equivalencia operacional completa,
pero no debe confundirse con una mejora de calidad o velocidad de los modelos.
