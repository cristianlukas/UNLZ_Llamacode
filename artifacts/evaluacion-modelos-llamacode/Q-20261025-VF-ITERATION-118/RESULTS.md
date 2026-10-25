# Q118 · replay real del detector y revalidación del lote · 2026-10-25

## Detector de presión de memoria

El replay del rastro real de ASTRA DEFAULT 1M pasó **12/12 checks CPU/offline**. Se verificaron los hashes de la traza, el wrapper realmente ejecutado y el módulo AMD05 exacto; se procesaron sus **707 muestras** por `q117_pressure_guard_attempt05.evaluate` y `evaluate_worker_cgroup` en orden.

- ASTRA terminó HTTP 200 con 1.001.463 tokens de prompt y usó ambas RTX 3090.
- RSS del árbol: máximo **51,306 GiB**; `MemAvailable`: mínimo **58,698 GiB**.
- PSI global some/full avg10: máximo **53,61%**; no alcanzó la severidad global de 80%/60%.
- La PSI severa del cgroup del worker apareció como diagnóstico en 233 muestras; por política no detiene sin la condición global de headroom. No hubo stop del guard, incremento global de OOM, OOM/swap del cgroup ni swap del worker.
- La traza y su recibo coinciden; se mantuvieron sin modificar.

La comparación de código encontró un helper genérico hermano `q117_pressure_guard.py` que conserva la transición PSI anterior sin `MemAvailable <48 GiB`. **Ese no fue el módulo de AMD05**: `run_context_holdout_attempt05.py` importa explícitamente `q117_pressure_guard_attempt05.py`, cuyo corte severo candidato sí exige PSI global severa **y** `MemAvailable <48 GiB` durante 15 muestras. El replay 12/12 confirma la ruta AMD05 correcta sobre la ejecución exitosa de ASTRA; la suite AMD05 registrada ya cubre la frontera/condición conjunta 21/21.

Un control de warning no es un stop: la muestra global moderada puede avisar tras la persistencia configurada. PSI de cgroup aislada también es diagnóstica. Esta prueba respalda que el guard de campaña no debe frenar un proceso por RSS alto si el host conserva headroom. **SOL Q34** finalizó TP=2 en ambas 3090 sin OOM; su registro no guarda PSI continua, por lo que sólo confirma terminación sin OOM y no calibra los umbrales del detector.

**Límite:** AMD05 sigue aislado y candidato; no reemplaza Q97/Q100 en producción ni es un detector general de cierres de Codex/GUI/driver. La ejecución ASTRA no alcanzó la conjunción PSI severa + menos de 48 GiB; su acción de stop sigue validada con fixtures CPU, no observada bajo presión host real. No cambié guard productivo, ASTRA, SOL, perfiles, contexto, RAM ni swap. La causa de los cierres de Codex sigue sin atribución.

El primer intento del replay Q118 se detuvo antes de procesar muestras por leer el nodo de resumen JSON equivocado (`run` en vez de `memory`). No modificó nada ni consumió servidor/GPU/memoria artificial. Se registró la corrección y el hash nuevo antes del reintento; el replay final pasó 12/12.

## ¿Qué prueba sigue habilitada?

No queda un benchmark de modelo local justificado por las fuentes pendientes actuales:

- P0 Windows Job Objects y el gate Flash-Next NInfer necesitan un ejecutor Windows nativo; esta sesión corre en Linux y no dispone de `pwsh`/Windows.
- P2.1 necesita primero un principal confiable y una policy tenant real en el contrato MCP; sin eso cualquier prueba cross-tenant inventaría la identidad y no serviría.
- HyperQwen sigue condicionado a un defecto parser/runtime reproducible que Q104 no encontró; Qwen27, RCO y Swift conservan screens cerrados sin cambio material.
- Los materiales #26/#28/#31/#32 fueron reabiertos contra fuentes actuales pero continúan sin una prueba local válida; #26 sí tiene evidencia mecánica A100 publicada, aunque la procedencia entre demo/log es inconsistente y no es transferible a Qwen3.8 Flash-Next.

Por lo tanto Q118 termina el replay CPU y la revalidación documental; no inicia otra inferencia hasta que una condición externa abra uno de esos gates. El estado de las 58 entradas de la app es terminal (analizada, bloqueada con condición, duplicada, sin prueba aplicable o migrada). Entre las evaluaciones priorizadas por el usuario, Qwen3.8-27B, RCO y Swift ya tienen decisiones documentadas; Qwen Flash-Next NInfer permanece listo para C39-01, que necesita una sesión Windows nativa. No queda una prueba local de modelo habilitada por la evidencia revisada en esta iteración.

## Fuentes bloqueadas revalidadas

Los cuatro estados continúan `Bloqueada` con una condición concreta para reabrir. Para #26, el log del autor registra 30.031 posiciones en Qwen2.5-72B/CUT3 sobre A100, 11/11 trials mecánicos, 17/17 checks y 8/8 hashes de append, pero el script actual dice que esa demo v1.5 no fue ejecutada en GPU y describe el log como histórico. No hay score semántico robusto; CUT3 no amplía la ventana nativa ni se transfiere entre arquitecturas. #28 sigue siendo una comparación subjetiva sin fixture; #31 declara ROCm/RX7900 y ~570 GB; #32 continúa inaccesible.

## Evidencia

- Plan/prerregistro: `PLAN.md`; `receipts/q118-amd05-live-trace-replay-preregistration.json`.
- Replay: `scripts/replay_q117_amd05_real_trace.py`; `receipts/q118-amd05-live-trace-replay.json`.
- Revalidación primaria de las entradas #26/#28/#31/#32: `receipts/q118-source-revalidation.json`.
- Traza AMD05 fuente: `../Q-20261025-VF-ITERATION-117/runs/astra-1m-seed-2026103-attempt05/memory-monitor.jsonl` (SHA-256 `fb369806324110e6bb20a2a2a681af3cdf9b36583a6e1ccfc02b9e0eba1d6dd1`).
- Wrapper/módulo AMD05: `../Q-20261025-VF-ITERATION-117/scripts/run_context_holdout_attempt05.py`; `../Q-20261025-VF-ITERATION-117/scripts/q117_pressure_guard_attempt05.py`.
- Q117 original: `../Q-20261025-VF-ITERATION-117/RESULTS.md`; resultado `../Q-20261025-VF-ITERATION-117/receipts/q117-amd05-result.json`; tests CPU AMD05 21/21 en `../Q-20261025-VF-ITERATION-117/receipts/q117-amd05-cpu-tests.json`.
- Google Sheets actualizado y leído de vuelta: `Evaluaciones LlamaCode!A339:J339` contiene el resultado Q118 y `Accionables!A2:N2` reconcilia P0; ambos rangos usan WRAP. La fila 339 quedó a 160 px. Recibo `receipts/google-sheet-sync-q118-final.json`.
- Datos de app respaldados antes de actualizar y reconciliados: `data/backups/inbox.q118-prechange.20261025T020301Z.json`, `data/backups/actionables.q118-prechange.20261025T020301Z.json`; inbox con 58 materiales y P0 actualizado.
