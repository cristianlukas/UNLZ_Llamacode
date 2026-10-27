# Q163 · Conciliación del Sheet y revalidación de gates

- **Fecha:** 2026-10-27T04:33:23Z.
- **Lock:** se reutilizó Q146 `2242863e-c78e-4fa9-9649-c1d1541f3919`.
- **Conciliación:** el inbox local tiene 69 entradas y `actionables.json` 35 registros. La pestaña `Accionables` tiene 43 filas de datos: contiene los 35 IDs locales; las ocho filas adicionales son historial ya cerrado salvo un seguimiento de R36S que espera un release público y no es una prueba de modelos. `Evaluaciones LlamaCode` termina en la fila 360 con Q161.
- **Corrección de hoja:** completé `Accionables!A4:N4` para Q31 desde el registro local exacto; antes sólo tenía tipo, ID y prioridad. La lectura de vuelta coincidió en las 14 celdas. Se conservó Arial 10, alineación superior y ajuste de texto; la fila quedó en 180 px. No se tocaron otros rangos.
- **Revalidación de #65:** Promethevs v0.2 mantiene el requisito Windows y ~1.1 TB libre entre NVMe. Ubuntu tiene 649.820.880.896 B libres sumando los volúmenes NVMe montados; los 313.252.384.768 B del HDD extra no cuentan como NVMe. No descargar ni construir.
- **Revalidación de #69:** Strata #3294 sigue abierto y describe Qwen3.6-35B-A3B como single-GPU; no hay quant exacto local. No hay test dual-GPU que ejecutar.
- **Pruebas:** no inicié inferencia/benchmark. Los otros pendientes requieren Windows nativo, principal/política autenticados, workflow+holdout fijo, transcripción primaria, defecto parser/runtime reproducible o evidencia real de presión crítica. ASTRA 1M y SOL ya completaron; no se induce presión artificial.
- **Estado:** no se cambió ningún score ni la decisión de modelos; ASTRA, SOL y datos de PeritoSoft permanecen intactos.
- **Evidencia:** `receipts/queue-sheet-and-gate-audit.json`.
