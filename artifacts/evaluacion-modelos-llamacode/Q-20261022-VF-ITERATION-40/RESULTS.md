# Q40 · Resultados

Estado: revalidación completada; C39-02 continúa pendiente de acceso Windows nativo.
Lock: `Q-20261022-VF-ITERATION-40`, token `d13b29f0-bd2a-4c3c-88a7-133937f5d95d`.

## Preflight tras el reinicio

- La sesión Codex actual corre en Ubuntu 24.04.5 (`Linux 3090`, kernel `7.0.0-38-generic`). No están disponibles `powershell.exe`, `pwsh`, `cmd.exe`, ni sus rutas bajo `/mnt/c/Windows/...`.
- La búsqueda de procesos conocidos de inferencia no encontró Strata, NInfer, vLLM, Ollama, llama-server, SGLang, LM Studio, TGI, Kobold, Tabby ni Aphrodite. Los listeners observados eran servicios locales de impresión/DNS/OpenRGB y ArtCraft en `127.0.0.1:47413`; no se identificó servidor de inferencia.
- `nvidia-smi` mostró sólo ArtCraft como compute app (PID 5493, 205 MiB); no se terminó. El chequeo no envió trabajo GPU ni lanzó inferencia.
- No se modificaron los artefactos preparados en Q39, el inventario, ni perfiles productivos.

## Decisión y siguiente paso

El mensaje del usuario confirma que reparó Windows, pero el proceso de Codex de esta activación continúa alojado en Ubuntu y no expone un runner Windows. Por tanto, C39-02 no puede ejecutarse en esta sesión: no hay medición nueva de velocidad, calidad, latencia, contexto o estabilidad.

Siguiente paso: abrir/continuar Codex en el host Windows donde está el runtime NInfer v0.16.1 y ejecutar el plan C39-02: comparar con Strata sobre el mismo IQ2_XS y hasta 32K, en serie, reportando prefill, TTFT, decode, E2E, holdout de calidad y estabilidad. Mantener perfiles productivos intactos hasta una comparación válida.

No hay otra inferencia P1–P5 desbloqueada por esta comprobación: Qwen27 y RCO tienen screens concluidos sin adopción; OpenJet conserva el bloqueo 64/65 bloques; Swift conserva su condición de acceso/licencia/runtime; Strata no tiene un claim nuevo; el actionable P2.1 de seguridad sigue siendo recomendación de implementación antes de reabrir Qwen.

## Google Sheet

Q40 fue registrado en `Evaluaciones LlamaCode!A271:J271`. El actionable existente de C39-02 en `Accionables` fila 49 actualizó estado, evidencia de revalidación y timestamps (`D49`, `K49`, `M49:N49`). La lectura de vuelta coincidió y TOP/WRAP se conservó. Recibo: `receipts/google-sheet-sync.json`.
