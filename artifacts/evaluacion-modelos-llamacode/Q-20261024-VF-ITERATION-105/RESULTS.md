# Q105 — Diagnóstico CPU de respuestas cruzadas en Q100

**Estado:** cerrado; chequeo forense 34/34 PASS y regresiones Qt 7 PASS, 0 fallidas, 1 opt-in omitida. No se usó servidor/modelo/red/GPU.

## Resultado

- Q100, semillas 5051–5053: modo serial terminó con mapping exacto 3/3; `parallel:2`, 1/3. Las semillas paralelas 5051 y 5053 devolvieron en el texto final las etiquetas ALPHA/BETA invertidas. El resultado operativo se mantiene: no adoptar dos subagentes paralelos; el throughput bruto paralelo también fue 5,11% menor y el throughput de tareas E2E correctas 68,37% menor.
- En las seis corridas, las dos respuestas guardadas como tarjetas de subagente contienen cada una uno de los marcadores correctos; en las dos semillas fallidas están ordenadas ALPHA, BETA. El texto final del padre es el que invierte las etiquetas. Eso localiza la discrepancia después de los contenidos individuales de las tarjetas, pero no identifica con certeza el componente que la causa.
- Ni `live-probe-result.json`, ni el re-score, ni `live-probe.log` conservan IDs de task-call/request que enlacen cada tarjeta con su llamada. El C++ del probe proyecta los resultados a `ok`, `output` y `toolTrace`; la evidencia no permite demostrar un cruce del scheduler. Lectura más precisa: síntesis final incorrecta; atribución modelo vs. asociación upstream inconclusa.
- No hubo cambio en producción. ASTRA DEFAULT 1M conserva la regla de fan-out serial por defecto; el test CPU volvió a verificarla. SOL se mantiene intacto. HyperQwen sigue bloqueado por el gate Q101.

## Detector de presión de memoria

La revisión Q102/Q103 confirma que el guard está diseñado para reaccionar a presión del sistema, no al RSS alto aislado. El ASTRA DEFAULT 1M real completó 10/10 con RSS 51,14 GiB y 55,728 GiB de MemAvailable; SOL Q34 TP=2 completó sin OOM. El smoke Q103 mantuvo RSS 56,013 GiB por 12 s con 53,386 GiB disponibles, PSI avg10 pico 0,36%, cero avisos/paradas/OOM y recuperación inmediata. En Q100 la PSI full moderada llegó a 46,52% y sólo avisó: MemAvailable mínima 69,386 GiB, seis corridas completadas y OOM=0. El hard-stop calibrado queda para MemAvailable <32 GiB, OOM nuevo o PSI memoria severa sostenida; no hay fundamento en estas pruebas para subir un límite por usar mucha RAM ni para endurecerlo por el porcentaje ocupado. Q103 fue RSS sintético, no inferencia; el ASTRA histórico sí fue carga real.

## Pruebas ejecutadas

1. Reconciliación CPU de los seis resultados raw/re-scored, outputs de task cards, labels finales y código collector/scorer: **34/34 checks PASS**.
2. Binario enfocado `test_q100_subagent_probe`, con endpoint opt-in desactivado y `CUDA_VISIBLE_DEVICES=`: **7 PASS, 0 FAIL, 1 SKIP**. Pasó `productionOneMillionContextStaysSerial` y las cuatro regresiones de mapping/final answer; se omitió la prueba live por diseño.
3. Inventario estructural de seis líneas Q100 del log: confirma que no se persistieron ids de correlación; no copió texto de prompts ni respuestas al recibo.

## Próximo paso

No repetir GPU por el mismo resultado. Si se decide reabrir la hipótesis de parallel2, primero preregistrar una instrumentación diagnóstica que persista IDs estables entre llamada task, tarjeta/resultado y respuesta final; después un test nuevo podrá separar el error de síntesis del scheduler. Esto no abre el gate de HyperQwen.

Evidencia en `receipts/q105-final-result.json`, `q105-forensic-check.json`, `q105-q100-log-inventory.json`, `q105-cpu-regressions.json` y Q100 attempt05.
