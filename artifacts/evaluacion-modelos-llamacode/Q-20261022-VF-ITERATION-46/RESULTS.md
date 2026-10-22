# Q46 — Revalidación de acceso al runner Windows nativo

**Fecha:** 2026-10-22 · **Estado:** preflight completado; C39-02 sigue bloqueado por acceso de plataforma.

## Resultado

El usuario informó que reparó Windows. Esta tarea de Codex, sin embargo, continúa ejecutándose en Linux 7.0.0-38-generic sobre Ubuntu 24.04. No se encuentra `powershell.exe`, `pwsh` ni `cmd.exe` en `PATH`, no existe `/mnt/c/Windows/System32/cmd.exe` y no hay montajes `drvfs`/`9p` que expongan un sistema Windows. El checkout en `/media/cristian/7CFE1E0FFE1DC1F6` es un volumen NTFS de datos; no es un runner Windows.

Por esto no se puede ejecutar desde este proceso la comparación nativa C39-02 de NInfer v0.16.1 frente a Strata. No se enviaron solicitudes a modelos ni se descargó, convirtió o ejecutó ningún artefacto. No se usó GPU. El preflight encontró cero procesos de inferencia; los listeners visibles pertenecen a servicios ajenos (impresión, DNS, OpenRGB y ArtCraft) y se dejaron intactos.

Al reconciliar la cola local encontré que `data/actionables.json` terminaba con los dos caracteres literales `\n`, así que `json.loads` rechazaba el archivo y `server.read_json()` devolvía la lista vacía de fallback. Guardé `actionables.json.bak.20261022-q46`, normalicé el archivo y confirmé que vuelve a parsearse con sus 22 accionables. Esto explica una lista de accionables vacía en la mini-app; no demuestra ni explica el cierre de la app de escritorio Codex.

## Decisión / reanudación

C39-01 permanece completa y sus artefactos NInfer v3 siguen preparados. C39-02 permanece pendiente: abrir Codex en Windows nativo con el artefacto/volumen compatibles ya disponibles, y ejecutar allí el plan existente bajo lock y prerregistro separados. No sustituirlo por una corrida Linux de Strata ni cambiar perfiles productivos mientras falte el A/B.

No se afirma que todas las pruebas hayan terminado. Este cierre sólo documenta el acceso de plataforma que impide la siguiente prueba P1.

## Recibo

`receipts/windows-runner-preflight.json`, `receipts/local-actionables-repair.json` y `receipts/google-sheet-sync.json` contienen las comprobaciones exactas y las lecturas de vuelta. No se inició ningún servicio y no quedó trabajo de Q46 en segundo plano.
