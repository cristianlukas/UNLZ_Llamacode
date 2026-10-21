# Q20 — S23 PLE FP8 con expertos file-backed

**Estado:** screen completo; PLE FP8 no pasa el gate de calidad y no se promueve. La campaña VF-20261019-01 continúa incompleta.  
**Lock:** `Q-20261021-VF-ITERATION-20` · `50d8dfb3-511a-48b2-a253-2cd6197cee17`  
**Fecha:** 2026-10-21 (UTC)

## Decisión

Se completaron tres pares matched-seed de IQ3_S stock frente a PLE FP8 E4M3 con `--mmap-experts` idéntico, 8 tareas BCB-Hard bilingües por brazo, y un solo servidor a la vez. Stock e FP8 aprobaron 3/24 tareas cada uno; en las tres semillas aprobaron exactamente el mismo caso (`BigCodeBench/870`). FP8 no ganó ningún par y la mejora requerida de dos tareas no apareció. Decode mediano por corrida fue 125,9 tok/s en FP8 y 126,75 tok/s stock (−0,7% throughput), dentro del margen del 5%; esa cercanía no cambia la decisión de calidad.

**Conclusión:** no hay evidencia local de que sustituir la PLE stock por la sidecar FP8 mejore el coding evaluado. Mantener el perfil/modelo actual. No copiar, mover ni borrar artefactos; no cambiar configuración productiva. El gate positivo tampoco puede declararse porque el fixture no mide safety/tool-use independientemente; aunque ese gate no fuese requisito, calidad quedó empatada. La carga con `--mmap-experts` sí pudo completar los seis brazos de manera segura bajo los límites fijados.

## Resultados por par

| Seed / orden | Stock | FP8 | Decode mediano stock / FP8 | Wall de requests stock / FP8 |
|---|---:|---:|---:|---:|
| 23003 · stock→FP8 | 1/8 | 1/8 | 121,35 / 123,75 tok/s | 100,31 / 39,96 s |
| 23004 · FP8→stock | 1/8 | 1/8 | 130,25 / 128,10 tok/s | 39,64 / 41,28 s |
| 23005 · stock→FP8 | 1/8 | 1/8 | 126,75 / 125,90 tok/s | 44,96 / 41,70 s |
| **Total** | **3/24** | **3/24** | **126,75 / 125,90 tok/s** (mediana de las medianas por seed) | **184,91 / 122,94 s** |

Los seis brazos tuvieron transporte 8/8 y ejecución 0 de infraestructura; todas las respuestas se calificaron con los ocho tests ocultos del mismo fixture. En el primer stock (23003), el scorer falló por dos problemas de sandbox/extracción; las respuestas crudas quedaron guardadas y se re-calificaron en CPU con la copia corregida del scorer, sin nuevas solicitudes. El regrade final da 1/8. Los regrades preliminares se conservan, pero no se usan como resultado final. Los otros cinco brazos ya usaron el scorer Q20 corregido.

Las sumas de wall por request no incluyen el tiempo de carga del servidor y son sensibles a longitudes de respuestas. El stock 23003 fue la primera carga fría y tardó 186,06 s desde preflight a cierre, mientras que los otros cinco brazos estuvieron cerca de 60–65 s; por orden y caché de archivos esos tiempos totales no son una comparación de velocidad atribuible al formato PLE. La mediana de wall por respuesta fue 4.205,94 ms stock y 4.563,46 ms FP8, pero las salidas tienen longitudes distintas. No se afirma superioridad de velocidad.

Prefill mediano por corrida: 306,30 tok/s stock frente a 302,70 tok/s FP8 (mediana de medianas; −1,2%). No es una diferencia concluyente. El PLE FP8 mide 51.200.246.112 bytes. El pico de `memory.current` observado fue 55,48 GiB en la primera carga stock fría y 7,52–9,04 GiB en las otras cinco; como el primer brazo calentó la caché de archivos, esto no es una comparación válida de huella RAM entre PLEs.

## Seguridad y recursos

- Los seis servidores llegaron a READY y completaron 48/48 solicitudes; `--mmap-experts` permaneció idéntico en ambos brazos.
- Cada ejecución usó un transient systemd scope propio con `MemoryHigh=64 GiB`, `MemoryMax=72 GiB` y watchdog cada cinco segundos. Ningún scope fue detenido por guard; OOM=0. PSI máxima observada fue baja, memoria disponible mínima 103,24 GiB y temperatura GPU máxima 67 °C.
- Después de cada brazo: servidor/listener propio cerrado y puerto 8355 libre. Verificación final: no quedó servidor de inferencia. ArtCraft se mantuvo intacto; ningún proceso ajeno fue terminado.
- Las huellas SHA-256 de los dos shards, sidecar FP8 y engine coinciden con las referencias previas. Pack, MTP, tokenizer, fixture y scorer se inventariaron en `receipts/input-fingerprints.json`.
- Qwen Flash-Next ASTRA/SOL, PeritoSoft y perfiles productivos no se modificaron.

## Problemas de harness encontrados y reparación

El primer stock seed 23003 produjo ocho respuestas HTTP válidas, pero el scorer antiguo lanzó un Python oculto por `bwrap`; su puntuación inicial se descarta. El primer regrade de prueba resolvió el intérprete pero expuso que Python aislado no veía `pandas`; la versión intermedia se conserva sólo para auditoría. Q20 montó en sólo lectura el runtime Python de datos y su site-packages, y corrigió extracción de fences incompletos en respuestas truncadas. El scorer/regresor terminó con 14/14 tests CPU, `py_compile` correcto y 5/5 dry-runs para los outputs aún no usados. El regrade final desde respuestas almacenadas fue 1/8, idéntico al score stock directo de las otras semillas.

## Artefactos

- Diseño y enmienda del scorer: [PLAN.md](PLAN.md)
- Fingerprints: [input-fingerprints.json](receipts/input-fingerprints.json)
- Validación CPU y probe cgroup: [cpu-validation-result.json](receipts/cpu-validation-result.json)
- Regrade final stock/23003: [stock-seed-23003-regrade-v2.json](receipts/stock-seed-23003-regrade-v2.json)
- Resultados por brazo: `work/source23/results/{stock,fp8}-seed-{23003,23004,23005}.json`; stock/23003 usa `stock-seed-23003-regraded-v2.json` para la puntuación corregida.
- Ejecución y watchdog por brazo: `receipts/{preflight,execution}-*-seed-*.json` y `work/source23/guard-*-seed-*.jsonl`.
- Resumen machine-readable: `receipts/source23-mmap-fp8-ab-result.json`
- Recibo de sincronización del Google Sheet: [google-sheet-update-result.json](receipts/google-sheet-update-result.json)

El cierre de S23 no termina la campaña. Siguen bloqueados S20/S51 por condiciones del usuario, S36 por contenido primario, UD-IQ4_XS por runner/carga, OpenJet por GGUF/kernel compatible y Harness² por workflow/holdout de calidad.
