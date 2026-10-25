# Q126 · borde de presión PSI alternada en AMD05 · 2026-10-25

## Resultado

**PASS: 4/4 checks.** El AMD05 fijado por hash acumula la condición compuesta `full >= 60% OR some >= 80%` aunque la señal alterne, pero sólo cuando `MemAvailable < 48 GiB`; corta exactamente tras 15 muestras consecutivas. Con `MemAvailable = 48,00 GiB` no corta, y una muestra normal reinicia la racha.

## Evidencia relevante para el usuario

- ASTRA DEFAULT 1M completó 1.001.463 tokens en las dos RTX 3090 con RSS máximo de 51,306 GiB, MemAvailable mínima de 58,698 GiB, 0 hard-stop/OOM/swap; el replay Q118 pasó 12/12 sobre 707 muestras.
- SOL Q34 dual-3090 terminó sin OOM; no hay PSI continua para calibrar su margen.
- Q126 **no usa RSS como criterio de stop** y no contradice esos éxitos. Demuestra con muestras sintéticas el borde lógico del guard AMD05: las señales PSI alternadas no pierden la racha cuando existe además headroom bajo.
- El guard histórico Q97/Q100 mantiene el hueco Q116 con PSI alternada. Q126 prueba AMD05 como candidato; no lo integra a Q97/Q100, a producción ni al supervisor de Codex.
- No hubo carga artificial de RAM, inferencia, servidor de modelos, CUDA/GPU compute, build ni cambios de perfiles/contexto/RAM/swap.

## Límite y siguiente gate

La combinación severa+`MemAvailable < 48 GiB` no se observó en una corrida real; Q126 es una regresión determinista CPU-only. El siguiente modelo Linux elegible debe pasar por Q121 y fijar/importar AMD05 antes de iniciar el worker. No hay ahora un test model-backed de la prioridad vigente habilitado: NInfer/Job Objects requieren Windows nativo; tenant auth necesita principal/policy reales; otros claims prioritarios están cerrados o requieren cambio material. Esto no atribuye los cierres de Codex a presión de memoria.

## Recibos

- `PLAN.md`
- `receipts/preregistration.json`
- `receipts/cpu-boundary-regression.json`
- `receipts/sheet-preregistration-readback.json`
- `receipts/sheet-final-readback.json`
- `receipts/actionable-update-readback.json`
