# Q40 · Revalidación tras reinicio del gate Windows · 2026-10-22

Lock exclusivo: `Q-20261022-VF-ITERATION-40`, token `d13b29f0-bd2a-4c3c-88a7-133937f5d95d`.

## Pregunta

¿El reinicio y la reparación hecha por el usuario cambiaron el host disponible para ejecutar C39-02, el A/B local de Flash-Next IQ2_XS entre NInfer v0.16.1 y Strata?

## Prerregistro y alcance

- Volver a comprobar el sistema operativo y disponibilidad de PowerShell/cmd nativos desde esta sesión Codex.
- Detectar procesos/listeners de inferencia y apps que tengan contexto CUDA. No terminar procesos ajenos.
- Si aparece un runner Windows compatible, validar artefactos y usar el plan C39-02 existente, sin cambiar sus parámetros. Si el host continúa Linux, cerrar como pendiente por la condición concreta y sincronizarlo en la cola y Google Sheet.
- No hacer build, descarga, benchmark, inferencia ni uso de GPU durante esta revalidación. No modificar perfiles, pesos, ni artefactos Q39.

## Condiciones de aceptación del gate

C39-02 sólo se considera ejecutable en esta activación si existe acceso a un runner Windows nativo desde el proceso Codex actual, además del runtime oficial v0.16.1 y los artefactos NInfer v3/ngram ya preparados. La presencia de una GUI o de otro proceso CUDA no cuenta por sí sola como inference server.
