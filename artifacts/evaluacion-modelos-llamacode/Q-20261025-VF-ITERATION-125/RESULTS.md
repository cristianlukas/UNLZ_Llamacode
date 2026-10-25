# Q125 · auditoría del detector frente a ASTRA 1M/SOL · 2026-10-25

## Veredicto

La ejecución exitosa de ASTRA DEFAULT 1M **sí contradice cualquier política que corte por RSS o por porcentaje de RAM ocupada sin mirar headroom y presión efectiva**. No contradice el guard AMD05 probado en Q117: en ambas RTX 3090, ASTRA procesó 1.001.463 tokens, respondió HTTP 200, alcanzó RSS máximo de 51,306 GiB y conservó al menos 58,698 GiB disponibles; PSI global máxima 53,61%, OOM/swap cero y ningún hard-stop. El replay Q118 recorrió 707 muestras de esa misma traza y pasó 12/12.

SOL Q34 también terminó en TP=2 sobre ambas RTX 3090 sin OOM. Su recibo no tiene PSI continua, por lo que confirma terminación segura, pero no calibra umbrales PSI. Los éxitos de ASTRA/Flash-Next/SOL respaldan mantener la RAM, swap, contextos y perfiles actuales; no sirven por sí solos para atribuir o descartar la causa de un cierre de Codex.

## Distinción necesaria entre los dos guards

- **Guard histórico Q97/Q100:** no toma RSS como señal de stop. PSI moderada advierte y la evidencia real de ASTRA/Q98/Q99/Q100 siguió sin abortar con headroom amplio. Sin embargo, Q116 reprodujo un hueco semántico: el hard-stop documentado como `full ≥60% OR some ≥80%` durante 15 muestras no se activa si la señal alterna entre `full` y `some`, porque el helper conserva contadores por métrica. Los controles estables sí detienen en la muestra 15.
- **Candidato AMD05:** exige PSI global severa **y** `MemAvailable <48 GiB` durante 15 muestras; mantiene corte inmediato por `MemAvailable <32 GiB`, nuevo OOM/swap del worker o telemetría inválida. Pasó la suite CPU 21/21, y Q118 pasó el replay real 12/12. A diferencia del helper histórico, no corta ASTRA por RSS alto con headroom.
- **Límite:** la combinación severa + menos de 48 GiB no ocurrió en la corrida real. Su comportamiento de corte está cubierto por fixtures CPU, no por una carga real. AMD05 sigue separado/no integrado; Q121 verifica sus hashes antes de un próximo runner, pero aún no es una corrida nueva.

Por eso no afirmo “el detector está completamente validado”: el no-falso-stop para la traza real de ASTRA está fuertemente respaldado; el hard-stop de AMD05 bajo presión crítica sólo tiene validación sintética, y el guard histórico conserva el hueco de PSI alternante. Q116-A2 demuestra una corrección OR compuesta 5/5 en CPU, aún no integrada. No repetí Q116/Q117/Q118 porque no apareció una señal ni implementación nueva que cambie ese resultado.

## Qué pruebas siguen habilitadas

No hay ahora un test local model-backed nuevo que pase su gate:

- HyperQwen queda bloqueado: Q104 confirmó que Q101 fue HTTP directo a vLLM, no pasó por el dispatcher LlamaCode y no reprodujo un defecto.
- NInfer/C39 y Job Objects necesitan un ejecutor Windows nativo.
- P2.1 necesita un principal autenticado confiable y una policy tenant real.
- S56 (UD-IQ4_XS a ~248K) agotó el último intento preregistrado antes de READY, con Strata en estado D durante lectura de pesos y cero requests; su preregistro prohíbe otro retry. La evidencia local llega a 117.825 tokens; reabrir sólo si cambia materialmente el problema de I/O/runtime y con preregistro nuevo.
- La siguiente evaluación Linux que sí quede habilitada debe pasar por Q121 y fijar los hashes del runner/AMD05 **antes** de iniciar el proceso.

No cambié código, perfiles, guard productivo, contexto, RAM o swap; no corrí build, inferencia, GPU ni estrés artificial.

## Conciliación realizada

- Corregí el texto obsoleto del inbox en #56, #57 y #58. S57 confirma activación efectiva ASTRA IQ2_XS a 1M y sólo una generación corta de 19 tokens; S55 cubre retrieval sintético de ~680K en IQ3_XXS, no calidad general; S56 no produjo score a ~248K. El registro de migración #58 ahora distingue su snapshot histórico Q21 (149 IDs/12 accionables) del workbook que siguió recibiendo filas hasta Q124.
- Completé las once filas Accionables que tenían A:C pero D:N vacías: 5, 6, 8, 9, 10, 11, 12, 13, 14, 15 y 16. Sus estados ahora concuerdan con los recibos: cerrado/no pase, resultado cerrado o bloqueo concreto. Preservé IDs/prioridades y formato WRAP.
- Añadí esta auditoría en `Evaluaciones LlamaCode!A346:J346`. La lectura de vuelta confirma A345/Q124 intacta, A347 vacía, los sentinels Accionables 7/17/18 intactos y WRAP en las celdas actualizadas.
- El primer batch de Sheets se rechazó antes de escribir por incluir una columna K fuera del rango A:J; una lectura de vuelta confirmó que el destino seguía intacto. Corregí el rango, repetí y verifiqué.

## Evidencia

- Q116: `artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-116/RESULTS.md` (gap histórico y candidato OR).
- Q117/Q118: `artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-117/RESULTS.md`; `.../Q-20261025-VF-ITERATION-118/RESULTS.md`.
- Q120/Q121: `artifacts/evaluacion-modelos-llamacode/Q-20261025-VF-ITERATION-120/RESULTS.md`; `.../Q-20261025-VF-ITERATION-121/RESULTS.md`.
- Q125 receipts: `receipts/preregistration.json`, `receipts/inbox-corrections.json`, `receipts/sheet-readback.json`, `receipts/sheet-update-first-attempt-rejected.json`.
- Backups: `receipts/prechange/inbox.json`, `receipts/prechange/actionables.json`, `receipts/prechange/WORK_QUEUE.md`.
