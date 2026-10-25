# Q128 · Replay del guard Q97 sobre la traza ASTRA DEFAULT 1M

## Pregunta

¿El guard histórico exacto de Q97 habría parado la traza real exitosa de ASTRA DEFAULT 1M por el uso alto de memoria?

## Prerregistro

Registrado en `receipts/preregistration.json` a `2026-10-25T05:21:34Z`. Se fijaron por SHA-256 el guard Q97, la traza ASTRA de 707 muestras, el resumen métrico Q117, el guard AMD05 y el recibo del replay Q118. La enmienda01 quitó de las entradas el recibo individual de respuestas que el replay no lee; no cambió pregunta ni método.

Hipótesis: Q97 no aborta esta traza porque RSS no es umbral de corte, MemAvailable no cruza 32 GiB, PSI global no llega a full 60% ni some 80% durante 15 muestras, y OOM permanece sin incremento. Puede haber avisos consultivos.

## Método

Replay CPU/offline de las muestras originales, en orden, con `q97_supervised_bcb.pressure_gate_transition()` y sus contadores persistentes. Validar huellas, 707 filas y extremos contra el recibo Q117. Usar Q118 AMD05 sólo como comparación de evidencia ya existente; no volver a correrlo.

## Límites

SOL Q34 confirma que la ejecución dual-3090 terminó sin OOM, pero no guardó PSI continua; no es posible reproducir temporalmente su detector. Esta prueba no ejerce presión real severa + bajo headroom, no identifica la causa de cierres de Codex y no modifica ningún guard, modelo o perfil.

## Resultado

Q128 pasó **11/11 checks**. El replay contrafactual del helper histórico Q97 sobre las 707 muestras exitosas de ASTRA DEFAULT 1M habría continuado: RSS máximo 51,3056 GiB, MemAvailable mínima 58,6977 GiB, PSI global máxima 53,61%, 216 avisos consultivos y cero hard-stops de PSI/memoria/OOM. El worker no registró OOM ni swap de cgroup. La traza tuvo 695 páginas de host `pswpout` acumuladas; Q97 no usa ese contador como stop y no hubo OOM.

La corrida ASTRA original fue en vivo con AMD05; Q128 sólo reinyectó sus métricas al Q97 fijado por hash. Q118 ya había pasado 12/12 al reproducir la misma traza con AMD05. El hueco conocido Q97/Q100 al alternar PSI severa sigue independiente: este rastro no alcanzó sus umbrales severos. SOL Q34 terminó sin OOM pero carece de PSI continua; Q127 fue un smoke normal de 24.319 tokens, no una repetición de SOL de memoria alta. No cambian umbrales, producción ni perfiles; Codex crash sigue sin causa atribuida.
