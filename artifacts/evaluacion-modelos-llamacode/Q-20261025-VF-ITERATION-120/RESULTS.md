# Q120 · reconciliación del detector de presión · 2026-10-25

## Resultado

**No repetí la prueba:** la combinación que propuse probar ya está implementada y cubierta en el candidato AMD05. La revisión de código/recibos confirmó que `q117_pressure_guard_attempt05.py` hace racha compuesta `full>=60% OR some>=80%` **y** exige `MemAvailable <48 GiB` durante 15 muestras. Conserva OOM y el corte inmediato bajo 32 GiB. La suite CPU fijada de ese candidato pasó **21/21**, incluyendo alternancia PSI con headroom bajo que para en la muestra 15, alta PSI con mucho headroom que continúa y ASTRA histórica de RSS alto que no se detiene.

La traza real ASTRA DEFAULT 1M se volvió a reproducir en Q118 contra ese mismo módulo: **12/12**, 707 muestras, RSS máximo 51,306 GiB, MemAvailable mínima 58,698 GiB, PSI global máxima 53,61%, ningún stop/OOM/swap. La ejecución de Q117 que generó esa traza terminó HTTP 200 después de procesar 1.001.463 tokens en ambas RTX 3090. El éxito del usuario con SOL Q34 dual-3090 sin OOM sigue siendo compatible con este resultado; SOL no tiene PSI continua para pasar por una reproducción PSI exacta.

## Distinción que faltaba

- **Guard que ejecutó ASTRA en Q117:** AMD05, candidato y verificado; no detuvo por RSS alto mientras había headroom.
- **Guard histórico Q97/Q100:** mantiene rachas por dimensión y tiene el falso negativo PSI alternado documentado por Q116. No se reescribió ni debe confundirse con AMD05.
- **Producción / cierre de Codex:** AMD05 no está integrado como monitor general de la aplicación. Ninguna de estas pruebas atribuye el cierre de Codex ni prueba todas las causas de OOM del host.

Así que el detector específico de la corrida exitosa de ASTRA funcionó como se esperaba; el hueco conocido es del supervisor histórico Q97/Q100. No hay una nueva prueba CPU justificable para repetir la misma combinación. La acción útil restante es verificar el módulo/call path que use una **próxima corrida nueva** antes de iniciarla; esa verificación no habilita tests actualmente bloqueados por Windows nativo, identidad/policy tenant o un defecto reproducible del runtime.

## Cambios

No se ejecutó código de test en Q120 ni se modificó código, resultados históricos, límites o perfiles. Se corrigió la descripción del actionable para indicar que los fixtures y la reproducción real ya existen, y que lo pendiente es integrar/fijar el guard en la ruta de la próxima evaluación. No se inició modelo, servidor, GPU, build, red ni asignación artificial de RAM.

## Evidencia fijada

- Q97 guard histórico: `../Q-20261024-VF-ITERATION-97/scripts/q97_supervised_bcb.py`, SHA-256 `663a2762ba8e5433b566c1fa2dbbe692cd8d4272619361c477a339da52c6904a`.
- AMD05 candidato: `../Q-20261025-VF-ITERATION-117/scripts/q117_pressure_guard_attempt05.py`, SHA-256 `b4d42302e7d405abd5c59df5aa86bb7de6ef3bb91aef487b49acbebd1d24270e`.
- Runner AMD05: `../Q-20261025-VF-ITERATION-117/scripts/run_context_holdout_attempt05.py`, SHA-256 `24435c412cc791d47687199fb7ab765c7a52aed6b189ac4598eea8dd9d8822b1`.
- Suite AMD05 21/21: `../Q-20261025-VF-ITERATION-117/receipts/q117-amd05-cpu-tests.json`, SHA-256 `11bac5f56b236147926f71a752d4f554c6caa214bddb2c4e3e6471b13d111143`.
- Traza ASTRA: `../Q-20261025-VF-ITERATION-117/runs/astra-1m-seed-2026103-attempt05/memory-monitor.jsonl`, SHA-256 `fb369806324110e6bb20a2a2a681af3cdf9b36583a6e1ccfc02b9e0eba1d6dd1`.
- Replay: `../Q-20261025-VF-ITERATION-118/receipts/q118-amd05-live-trace-replay.json`, SHA-256 `68769dca479da3d40e48873a77fefb3852f449fcc4f700b56de30a414de0e160`.
- Q116 documenta por separado el fallo de la persistencia por métrica: `../Q-20261025-VF-ITERATION-116/RESULTS.md`.
