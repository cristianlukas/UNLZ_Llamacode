# Q63 — recheck del driver y condiciones de licencia Swift

**Fecha UTC:** 2026-10-23T16:44:40Z
**Estado:** Q56 continúa bloqueada antes del servidor/request por desalineación NVIDIA. El host arrancó 2026-10-22T22:26:57Z; el módulo cargado es 610.57.04, mientras `modinfo` y NVML son 615.71.09; `nvidia-smi` devuelve exit 18 y permanece `/var/run/reboot-required`. No se detectó inference server ni listener. No se inició servidor, request, benchmark ni GPU. El lock se tomó por creación exclusiva y se liberará al terminar la sincronización.

## Trabajo útil completado

Se revisaron las licencias oficiales de los dos candidatos Swift. La Swift Open License v1.0 fija el umbral en ingresos brutos de **US$1.000.000 o más**, medidos en el ejercicio fiscal más reciente y agregados entre entidades bajo control común; el uso comercial por encima del umbral no está cubierto y requiere licencia Swift Enterprise separada. La licencia Qwen Community 1.0 añade una condición para las entidades que operan negocios de MAAS o AI Work Assistant: licencia Qwen separada antes de uso comercial; exceptúa el uso interno si no se ofrecen el modelo, sus outputs o capacidades a terceros. La elegibilidad de la entidad y el alcance de despliegue no están confirmados; este resumen no es dictamen legal.

Se actualizaron los accionables locales `vf-swift15-qwen38-20261019` y `vf-swift15-flashnext-iq2xs-ab-20261023` con estas condiciones, manteniendo bloqueadas las descargas y la adopción. No se cambió ningún modelo, perfil productivo, PeritoSoft ni archivo de pesos.

## Reanudación

1. Reiniciar Ubuntu después de la actualización; no descargar ni descargar manualmente módulos NVIDIA en caliente.
2. Revalidar `nvidia-smi`, módulo cargado y cero inference servers; sólo entonces continuar Q56 con el preflight fresco ya preregistrado.
3. Para el test Swift, confirmar elegibilidad comercial y clasificación de uso según ambas licencias; luego validar acceso/hash/runtime y usar el plan pareado existente.

**Recibos:** `receipts/driver-recheck.json`, `receipts/swift-license-conditions.json`.

## Sincronización del registro

A las 2026-10-23T16:44Z, se actualizaron y leyeron de vuelta `Accionables!A10:N10` (Swift 1.5 Qwen3.8-27B) y `Accionables!A53:N53` (Swift 1.5 Flash-Next IQ2_XS). Las celdas editadas conservan `WRAP` y alineación `TOP`; sólo cambiaron valores de texto y fechas. Receipt `receipts/google-sheet-sync-q63-swift-license.json`.
