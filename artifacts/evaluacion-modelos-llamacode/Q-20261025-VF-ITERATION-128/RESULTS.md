# Q128 · Replay del guard histórico Q97 en ASTRA DEFAULT 1M

## Resultado

**PASS · 11/11 checks.** El guard Q97 habría permitido continuar la traza real exitosa de ASTRA DEFAULT 1M. El corte no depende del RSS alto aislado: en las 707 muestras, RSS del árbol llegó a **51,3056 GiB**, mientras `MemAvailable` no bajó de **58,6977 GiB**. La PSI global some/full llegó a **53,61%**, generó **216 avisos consultivos** desde la muestra 46 y no alcanzó `full≥60%` ni `some≥80%` durante 15 muestras. No hubo stop por PSI, `MemAvailable<32 GiB`, OOM global ni OOM del worker.

Se comprobó el helper Q97 exacto por SHA-256 y su llamada real a `pressure_gate_transition`; la traza, el resumen Q117, el guard AMD05 y el resultado Q118 también coincidieron con los hashes prerregistrados. Los 707 registros reprodujeron los extremos reportados por Q117. Q118 ya había validado la misma traza con AMD05 (12/12); no se volvió a ejecutar ese replay.

La traza registra **695 páginas de host `pswpout` acumuladas** al final. El swap del cgroup del worker permaneció en cero y no hubo OOM. Ese contador no es un hard-stop del helper Q97.

## Qué demuestra y qué no

Esto es una reproducción CPU/offline **contrafactual**: la corrida en vivo Q117 usó AMD05, no Q97. Muestra que el helper Q97 histórico tampoco habría cortado esta carga exitosa por RSS alto; los avisos se mantuvieron consultivos. El gap documentado en Q97/Q100 al alternar condiciones PSI severas entre `full` y `some` permanece: este rastro nunca superó los umbrales severos.

SOL Q34 finalizó TP=2 con ambas RTX 3090 sin OOM, pero no guardó PSI continua y no se puede reproducir contra un umbral temporal. Q127 midió una solicitud normal de SOL de 24.319 tokens; no fue una repetición de la carga histórica de memoria alta.

No se inició modelo/servidor ni se usó GPU, build, red o memoria artificial. No se cambiaron AMD05, Q97/Q100, modelos, contexto, perfiles, RAM o swap. Esta guarda pertenece a campañas de evaluación; no es un detector general de Codex y el resultado no atribuye los cierres de la app.

## Evidencia

- `receipts/preregistration.json`, `receipts/amendment-01-preregistration.json`
- `receipts/q128-q97-astra1m-replay.json`, `receipts/result-analysis.json`
- `receipts/sheet-prereg-readback.json`, `receipts/sheet-final-readback.json`
- `scripts/replay_q97_astra1m_trace.py`
- Fuente de traza y recibo: Q117 `runs/astra-1m-seed-2026103-attempt05/memory-monitor.jsonl`, `receipts/q117-amd05-result.json`
- Comparador existente: Q118 `receipts/q118-amd05-live-trace-replay.json`
