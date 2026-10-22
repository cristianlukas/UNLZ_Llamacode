# Q30 — Resultado del diagnóstico Flash-Next BCB/765

**Estado:** cerrado sin pase; no produjo respuesta final válida antes del timeout.
**Fecha:** 2026-10-22.
**Prerregistro:** [`PLAN.md`](PLAN.md), perfil `q14-udiq4xs-he0`, fingerprint `a56c723fde568b4db160bbb48ccc9e378aa221bdcaffe544ee957e3ba666dd86`.

## Resultado observado

- Se ejecutó una sola tarea `BigCodeBench/765` en una copia aislada de la suite. El único cambio frente al intento previo fue `maxTokens=1200→2400`; Strata 0.1.41, modelo UD-IQ4_XS, contexto 32K, KV int8, MTP4, acceptance y demás parámetros se conservaron.
- La primera solución se escribió a las 06:49:56Z. El grader falló: `copied_files` tuvo longitud 0, frente a 2, 1 y 2 esperados en tres pruebas.
- La vuelta de reparación ejecutó un shell con `python -m py_compile ...`; el entorno respondió `/usr/bin/sh: 1: python: not found`. No se observó una segunda escritura ni una respuesta final válida antes del límite.
- El runner cerró a las 07:07:16Z con `timedOut=true`, `elapsedSec=1800.145`, `score=null`, sin grade y con la etapa BCB todavía pendiente. El 100% del runner indica que cerró la invocación, no que el benchmark haya aprobado.
- No se interpreta la etiqueta interna `EVAL/HE0` como HumanEval: el fixture ejecutado fue BCB/765. No hay score BCB8 ni métricas comparables de throughput.

## Decisión

El aumento aislado de la salida a 2.400 tokens no produjo un caso aceptado dentro de 30 minutos. Cerrar esta ruta y no repetir la misma invocación ni escalar a BCB8 completo con esta evidencia. No adoptar ni promover ningún modelo desde este diagnóstico. Flash-Next ASTRA/SOL y PeritoSoft quedan sin cambios.

Una nueva prueba P1 solo se justificaría tras un cambio material: corregir primero el entorno del harness para exponer `python` o indicar `python3`, y formular un protocolo más corto que todavía use el grader original. En ese caso se preregistra antes de cargar pesos y se compara con ASTRA/SOL bajo la misma suite y límites. El error `python` se registra como problema del harness/entorno, no como una conclusión general sobre el modelo.

## Recursos y limpieza

La corrida estuvo aislada en `llamacode-vf-q30-bcb2-outputcap.scope` (`MemoryHigh=86 GiB`, `MemoryMax=96 GiB`, swap máximo 1 GiB). El recibo final registra `max=0`, `oom=0`, `oom_kill=0`; al cerrar quedaban 115.75 GiB disponibles y 3.04 GiB de swap. La limpieza propia terminó con cero procesos de inferencia o listeners en los puertos 8354/18766.

## Evidencia

- `attempts/flashnext-bcb2-outputcap-01/receipts/benchmark-final.json`
- `attempts/flashnext-bcb2-outputcap-01/receipts/benchmark-invocation.json`
- `attempts/flashnext-bcb2-outputcap-01/receipts/benchmark-poll.jsonl`
- `attempts/flashnext-bcb2-outputcap-01/receipts/owned-process-cleanup.json`
- `attempts/flashnext-bcb2-outputcap-01/receipts/postflight.json`
- `attempts/flashnext-bcb2-outputcap-01/logs/strata-engine.log`
- `attempts/flashnext-bcb2-outputcap-01/work/isolated-runtime/data/LlamaCode/LlamaCode/benchmark-runs/VF_focused_code-output-cap_diagnostic_20261022_033711/EVAL_UD-IQ4_XS_Strata_0_1_41_HE0__ws/.llamacode/agent_events.jsonl`
