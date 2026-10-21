# Q22 — Reconciliación de S23 y auditoría de condiciones externas

**Estado:** reconciliación completada; VF-20261019-01 sigue incompleto por precondiciones externas.
**Cierre:** 2026-10-21T13:23:41Z
**Lock:** `a1b696f1-7986-4f55-883f-3b63d1c267e6`

## Resultado

La ficha S23 de `data/actionables.json` y la pestaña `Accionables` aún mostraban el corte de un par (1/3) y la pausa por presión de memoria, aunque Q20 ya había completado los tres pares. Se actualizó a **Resuelto** con el resultado final: stock 3/24, FP8 3/24, mismo único caso por semilla, 0/3 pares ganados por FP8 y decode mediano 125,90 vs 126,75 tok/s (−0,7%). Se mantiene PLE stock y no se promueve FP8. No se alteraron pesos, rutas ni perfiles; Qwen Flash-Next ASTRA/SOL, PeritoSoft y los perfiles productivos permanecen intactos.

El Google Sheet `Evaluaciones LlamaCode` no contenía Q21 al hacer la búsqueda exacta; la fila 169 estaba ocupada por `VF-20261021-PASTED-TRIAGE`. No se sobrescribieron filas. Se añadieron Q21 en la fila 174 y esta reconciliación Q22 en la fila 175, se actualizó el resumen y se extendió el filtro. Lectura posterior: **174 IDs únicos**, filas Q21/Q22 completas y fila 13 de `Accionables` refleja el nuevo estado S23.

## Auditoría de lo que puede correr ahora

Q21, terminado pocos minutos antes, reintentó la fuente primaria S36 y revalidó los restantes. El scan de procesos por `comm` y sockets locales de Q22 encontró **0 procesos de inference server y 0 listeners** en los puertos revisados. No se inició un benchmark porque no cambió ningún prerrequisito externo:

- S20/S21/S24: faltan proveedor, modelo/versión, keyRef autorizado, tope de gasto y límite de datos.
- S36: falta caption, transcripción, captura legible o mirror atribuible; Instagram sigue throttled y la búsqueda exacta no encontró evidencia primaria.
- S51: faltan elegibilidad/licencia y ruta de runtime/formato no-MTP compatible verificada.
- UD-IQ4_XS: falta runner/grader corregido y un nuevo plan de carga seguro con fingerprint nuevo.
- OpenJet: el único Qwen3.8-27B Q4_K_M local tiene 64 bloques; el kernel disponible requiere 65.
- Harness²: faltan workflow concreto de LlamaCode y holdout sintético independiente de calidad.
- Otras fuentes conservan sus requisitos de hardware, almacenamiento o runtime consignados en inbox/recibos.

Las 58 entradas tienen estado y disposición en `data/inbox.json`; los cierres previos separan pruebas completadas, sin prueba aplicable, duplicadas y bloqueadas. Reabrir sólo cuando cambie una condición listada.

## Evidencia y siguiente acción

- `receipts/actionables-reconciliation.json`
- `receipts/inference-server-audit.json`
- `receipts/google-sheet-update-result.json`

No se ejecutó ninguna prueba de modelo nueva en Q22; por tanto, no hay score ni afirmación nueva de calidad. La próxima prueba se elige después de que cambie una precondición externa concreta, con prerregistro y lock propio.
