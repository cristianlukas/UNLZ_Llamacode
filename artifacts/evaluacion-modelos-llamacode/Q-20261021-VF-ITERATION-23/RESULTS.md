# Resultados — Q-20261021-VF-ITERATION-23

**Estado:** regrade CPU-only completado; campaña BCB8 sigue incompleta e inválida como suite. No se hizo inferencia ni se modificó ningún modelo o perfil.

## Alcance y validez

Se reejecutaron los acceptance tests congelados del BCB8 `attempt-2` sobre los siete archivos de solución persistidos. Cada tarea corrió en su propio `bubblewrap`: red y namespaces aislados, sistema de archivos de sistema de solo lectura y sólo su carpeta temporal como escritura. El canario de sandbox pasó; los siete casos terminaron sin timeout. El entorno fue Python 3.12.3; las versiones y hashes quedan en el recibo.

En el primer intento de esta iteración el wrapper antepuso el preámbulo de prompt a módulos que ya contenían la firma; los siete procesos dieron `IndentationError` antes de ejecutar candidatos. Se conservó ese resultado como defecto del wrapper, se corrigió con una enmienda preregistrada y no se contó como resultado de modelo.

## Regrade corregido

| Tarea | Resultado grabado en attempt-2 | Regrade aislado |
|---|---:|---:|
| BigCodeBench/928 | Pasa | Pasa |
| BigCodeBench/765 | Falla | Falla |
| BigCodeBench/771 | Falla | Falla |
| BigCodeBench/1019 | Falla | Falla |
| BigCodeBench/906 | Pasa | Pasa |
| BigCodeBench/583 | Falla | Falla |
| BigCodeBench/139 | Pasa | Pasa |
| BigCodeBench/360 | Sin score final | Sin artefacto de solución; no recalificada |

Los flags guardados coinciden en las siete soluciones disponibles: **3/7 pasan y 4/7 fallan**. El artefacto 360 no existe en el workspace de esa corrida. Este recuento es una validación parcial por tarea, no un score de la suite.

El EVAL original sigue marcado `invalid=true`, `failed=true`, `failureKind=timeout`; terminó a 7.226,41 s con `finalScore=0/0`. No debe reportarse como un BCB8 válido ni usarse para comparar/promover modelos.

## Decisión y siguiente condición

Se mantiene UD-IQ4_XS sin promoción. La prueba CPU recupera la validez de los siete resultados individuales y confirma que el timeout global no fue el único problema: cuatro soluciones guardadas fallan y una tarea no tiene solución. Para reabrir el benchmark hace falta un runner agentic reproducible con límite por tarea, ruta de carga viable y ejecución completa del subconjunto de ocho tareas bajo un fingerprint nuevo. No repetir el intento global con la misma huella ni la completion directa 1019.

Qwen Flash-Next ASTRA/SOL y los modelos PeritoSoft permanecieron intactos. Sin GPU, servidor de inferencia, descarga ni build.

## Evidencia

- Prerregistro: [`PLAN.md`](PLAN.md), [`receipts/preregistration.json`](receipts/preregistration.json)
- Enmienda de ensamblado: [`receipts/amendment-01.json`](receipts/amendment-01.json)
- Intento inválido del wrapper: [`receipts/bcb8-saved-candidates-regrade-attempt01-runner-defect.json`](receipts/bcb8-saved-candidates-regrade-attempt01-runner-defect.json)
- Regrade corregido: [`receipts/bcb8-saved-candidates-regrade-attempt02-result.json`](receipts/bcb8-saved-candidates-regrade-attempt02-result.json)
- Runner: [`scripts/regrade_bcb8_saved.py`](scripts/regrade_bcb8_saved.py)

## Reconciliación

Q23 quedó registrado en `Evaluaciones LlamaCode`, fila 176; el filtro se extendió hasta `A1:I176`, el resumen C2/E2 se actualizó y el readback confirmó 175 IDs únicos. El accionable de selección de candidato se sincronizó en `Accionables`, fila 4, con el regrade parcial y el bloqueo restante. Recibo: [`google-sheet-update-result.json`](receipts/google-sheet-update-result.json).

Cierre de iteración: 2026-10-21T13:34:47Z.
