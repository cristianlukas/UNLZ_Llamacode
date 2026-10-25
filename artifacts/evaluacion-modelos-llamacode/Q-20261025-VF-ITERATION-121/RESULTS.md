# Q-20261025-VF-ITERATION-121 · preflight del guard antes del runner

## Resultado

El wrapper `tools/evaluation_guard_preflight.py` quedó probado para verificar el hash del runner y el guard AMD05, confirmar que el runner importa el módulo exacto, comprobar que el monitor arranca antes del servidor e importar el guard desde la ruta fijada antes de lanzar una evaluación.

- Intento 01: **7/7 PASS** con la cobertura CPU inicial, sin ejecutar runner/modelo.
- Enmienda 01: se agregó el camino feliz de despacho con `subprocess.run` mockeado. La enmienda se preregistró y leyó de vuelta en `Evaluaciones LlamaCode!A342:J342` antes del nuevo pase.
- Intento 02: **8/8 PASS** en 0,015 s. Acepta el par Q117/AMD05; bloquea hash alterado, helper Q97, import ausente y `Popen` antes del monitor; demuestra que la selección inválida no llama al hijo y que la válida despacha sólo el runner fijado con argumentos y `cwd` esperados.
- Smoke CLI `--verify-only`: **PASS**, hashes exactos y módulo preimportado desde la ruta aprobada.
- `git diff --check`: PASS.

## Interpretación y límites

Esta mejora hace verificable el seguimiento que Q120 dejó pendiente para futuras evaluaciones. No integra AMD05 a Q97/Q100 históricos ni a un monitor general de Codex. La prueba no explica los cierres de Codex ni prueba el comportamiento del guard bajo una condición nueva de presión. ASTRA DEFAULT 1M, SOL, Flash-Next, PeritoSoft, RAM, swap, GPU, perfiles y contextos quedaron intactos; no se inició modelo, servidor, GPU, build, red ni asignación artificial de memoria.

Antes del próximo benchmark, preregistrar ambos hashes y lanzar el runner mediante el preflight usando el mismo intérprete Python. El wrapper seguirá rechazando la corrida si cualquiera de los dos archivos cambia. La acción todavía debe comprobarse en la ruta de una nueva evaluación real cuando un candidato quede habilitado.

## Evidencia

- `PLAN.md`
- `receipts/preregistration.json`
- `receipts/amendment-01-preregistration.json`
- `receipts/q121-test-run.json`
- `receipts/sheet-preregistration-readback.json`
- `receipts/amendment-01-sheet-readback.json`
- `receipts/google-sheet-sync-final.json`
- `tools/evaluation_guard_preflight.py`
- `tests/python/test_evaluation_guard_preflight.py`
