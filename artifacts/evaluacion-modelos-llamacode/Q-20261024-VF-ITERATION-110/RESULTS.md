# Q110 · Detector de presión y elegibilidad del host

**Estado:** Completa · 9/9 checks focales y 6/6 checks de cadencia PSI.  
**Lock:** `Q-20261024-VF-ITERATION-110`, token `549f3a3b-673a-4d3a-9046-1122a67c04a2`.  
**Cierre:** 2026-10-25 00:10:15 UTC.

## Conclusión sobre ASTRA 1M, SOL y memoria

La evidencia confirma la observación del usuario: **usar mucha RAM/RSS no es por sí solo un motivo para abortar**. El guard toma decisiones por `MemAvailable`, PSI de memoria sostenida y un incremento del contador OOM, no por RSS ni por porcentaje de memoria ocupada.

- ASTRA DEFAULT/Flash-Next a 1.048.576 tokens completó con ~51,14 GiB de RSS y 55,728 GiB de `MemAvailable`; el guard no detuvo esa corrida. Q35 completó además 3/3 semillas con 64,98–65,06 GiB mínimos disponibles y cero OOM.
- SOL Q34 TP=2 completó en ambas RTX 3090 sin OOM. No tiene serie PSI por segundo y no se usa para calibrar PSI.
- Q97 ejecutó ASTRA con PSI global moderada pico de 34,72%; hubo avisos, recuperación y 8/8 respuestas completadas, sin OOM ni crash. Q100 completó seis corridas con PSI full pico 46,52% y sin aborto. Son señales de stalls/reclaim, no predictores de crash.
- Q102/103 aportan controles CPU de 48,013 y 56,013 GiB de RSS, con 61,693 y 53,386 GiB mínimos disponibles, sin stop/OOM. Q110 no repitió cargas artificiales ni la inferencia 1M.
- Las antiguas reglas Q91/Q93 sí abortaban demasiado pronto con PSI full ~51–52%, aunque quedaran 92–101 GiB disponibles y OOM=0. Esa fue la calibración incorrecta. La política de hard stop vigente mantiene `MemAvailable <32 GiB`, aumento OOM, o PSI global severa sostenida (`full ≥60%` o `some ≥80%`) por 15 muestras de 1 s; PSI moderada sólo informa.

## Q110 · regresión del core

El executor sigue en Ubuntu Linux. El preflight de 2026-10-25T00:06:03Z registró módulo, NVML y `nvidia-smi` en 615.71.09; 106,31 GiB disponibles; PSI some/full avg10=0%; OOM=0. No encontró procesos ni puertos de inferencia. `nvidia-smi` listó ArtCraft (207 MiB), que quedó intacto; no es un servidor de inferencia según el scan de procesos/listeners.

La regresión focal CPU de Q110 pasó **9/9**: ASTRA high-RSS continúa, SOL queda sustentado sin inventar PSI, PSI moderada avisa pero no aborta, fronteras del piso/OOM/PSI severa se mantienen, recuperación reinicia el streak, telemetría faltante falla cerrado, y sólo se señala el PID candidato. No hubo inferencia, servidor, GPU, reserva de VRAM, asignación artificial de RAM ni señales a procesos ajenos.

No se ejecutó el runner original de Q108: su última prueba exige el token Q108 y otra aserción lee un accionable externo. Reutilizarlo bajo Q110 habría violado su ownership. Se creó antes de la prueba un runner focal Q110 sobre el core Q108 sin modificar. La primera descripción en Sheets todavía decía “15 checks”; se corrigió tras leer el runner. El resultado correcto es 9/9, no 15/15.

## Enmienda A1 · cadencia de avisos

La revisión encontró una diferencia no relacionada con los hard stops: el core Q108 devuelve `warning=True` en la primera muestra que cruza PSI moderada, mientras la política calibrada Q97 requiere **30 muestras consecutivas** de un segundo. Esto podría generar avisos prematuros/repetidos si se integrara directamente; no causa un hard stop ni explica los cierres de Codex.

El wrapper candidato Q110, separado y no integrado, conserva el core y reproduce la persistencia de Q97. Su auditoría CPU pasó **6/6**: muestra 1–29 sin aviso, aviso en la 30, reset tras recuperación, stop severo intacto en la muestra 15, control ASTRA alto-RSS sin PSI continúa, y PSI ausente continúa fallando cerrado. No se modificó el core Q108 ni el runtime de producción.

## Estado de las pruebas del lote

No hay un benchmark de modelo nuevo habilitado en este executor. C39-02 y la validación de Job Objects/entrypoints dependen de una sesión Windows nativa; aquí no están `powershell.exe`, `pwsh`, `powershell`, `cmd.exe` ni `cmd`. Los demás accionables del lote esperan cambios concretos de runtime/artefacto, backend/fixture de autorización, o fuente primaria. No se reemplazaron esas pruebas por comparaciones incompatibles. Las 58 entradas del lote mantienen resultado y los bloqueos conservan sus condiciones de reapertura.

El guard Q108/109/Q110 sigue siendo candidato para los lanzadores de evaluación: **no** está integrado como monitor general de Codex, GUI, driver o kernel, y **no** limita la memoria/contexto de ASTRA o SOL. No reducir RAM/contexto ni cambiar perfiles. Q68 resolvió el gate del reinicio/driver pendiente: el estado post-reinicio muestra el binario de Codex actual, módulo/NVML alineados y `nvidia-smi` funcional; la causa raíz del cierre reportado sigue sin demostración concluyente.

## Google Sheets

- `Evaluaciones LlamaCode!A330:J330`: Q110 cerrado, 9/9 y lectura exacta; las diez celdas conservan WRAP.
- `Evaluaciones LlamaCode!A331:J331`: enmienda A1 cerrada, 6/6 y lectura exacta; las diez celdas conservan WRAP.
- `Accionables!A2:N2`: se retiró la recomendación obsoleta de reiniciar/alinear el driver; quedó P0 parcial por Windows nativo. Las 14 celdas leídas de vuelta conservan WRAP.
- Durante el primer batch-update se borraron momentáneamente A2:C2 al enviar celdas vacías para columnas no modificadas. Se restauraron a sus valores previos, se verificó toda A2:N2 con identidad, evidencia y formato, sin pérdida final.

## Artefactos

- `PLAN.md`, `receipts/preregistration.json`, `receipts/preregistration-amendment-01.json`
- `runner/q110_detector_recheck.py`, `runner/q110_warning_policy.py`, `runner/test_q110_warning_policy.py`, `runner/q110_host_preflight.py`
- `receipts/q110-regression-result.json`, `receipts/q110-warning-cadence-audit.json`, `receipts/q110-host-preflight.json`, `receipts/q110-sheet-sync.json`, `receipts/q110-final-summary.json`
