# Plan Q53 — preflight del runner Windows

Fecha UTC: 2026-10-23.

## Pregunta

¿La sesión actual de Codex ya corre en Windows nativo, de modo que se pueda ejecutar el gate preregistrado C39-02 después del arreglo reportado por el usuario?

## Procedimiento

- Leer SO/kernel y disponibilidad de `pwsh`, `powershell.exe` y `cmd.exe`.
- Comprobar procesos y listeners típicos de inference; observar GPU sólo para detectar procesos de cómputo.
- Gate: ejecutar cualquier prueba Windows únicamente si el propio executor confirma Windows nativo y las herramientas/prerrequisitos del plan C39 están disponibles.
- Si el executor es Linux, cerrar este preflight sin usar Wine para emular Job Objects ni para presentar resultados como Windows nativo.

## Límites

Sólo inspección CPU; no build, benchmark, descarga, servidor o inferencia. No terminar aplicaciones de escritorio. ASTRA, SOL, Qwen Flash-Next, PeritoSoft y los pesos quedan intactos.

## Evidencia observada

El preflight de plataforma se inició en esta sesión antes de guardar este plan; no incluyó test, build, benchmark ni acceso a un servidor de inferencia. Se documentará el detalle en `RESULTS.md` y `receipts/platform-preflight.json`.
