# Q46 — Revalidación de acceso al runner Windows nativo

## Pregunta

¿El arreglo que el usuario hizo en Windows dejó disponible para esta sesión de Codex un runner Windows nativo capaz de ejecutar el A/B C39-02 de NInfer v0.16.1 frente a Strata con Qwen3.8 Flash-Next?

## Prerregistro

- Lock: `d8fa1b61-3530-48fd-bf08-8bd736efb0ea`.
- Alcance: preflight de plataforma y disponibilidad, sólo lectura. Revisar kernel/plataforma, presencia de `powershell.exe`, `pwsh` o `cmd.exe`, montaje Windows conocido y procesos/listeners de inferencia. No inspeccionar directorios amplios ni leer modelos.
- No ejecutar build, conversión, descarga, benchmark, inferencia ni comandos Windows. No tocar GUI, servidores ajenos, archivos/modelos, perfiles, inventario productivo o datos de PeritoSoft. Sin uso de GPU.
- Si hay runner Windows accesible, detener este preflight y encolar el benchmark C39-02 bajo un lock nuevo con su prerregistro propio. Si no, registrar el bloqueo y condición externa exacta, sin simular ni sustituir la prueba por Linux.
- Verificar el estado final de procesos/listeners sólo para confirmar que este preflight no inició servicios.
