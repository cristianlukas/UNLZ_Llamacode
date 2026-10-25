# Q116 · Secuencia mixta de PSI severa en el guard activo

## Pregunta

La política de Q97 se describe como parada cuando `full >= 60%` **o** `some >= 80%` persiste durante 15 muestras. Las auditorías Q113–Q115 cubrieron cada serie por separado, pero no una secuencia donde la condición OR se mantiene verdadera alternando entre ambas señales. ¿El guard activo sostiene una racha por la condición OR o reinicia cada contador al cambiar la métrica?

## Preregistro

- Importar y llamar la función real `pressure_gate_transition` del script Q97, sin modificarlo.
- Repetir controles estables: 15 muestras `full=60%` y 15 muestras `some=80%`; ambas deben detener en la muestra 15 según sus propias fronteras ya auditadas.
- Caso discriminante: 15 muestras alternando `full=60%, some=0%` y `full=0%, some=80%`. La condición OR es verdadera en las 15 muestras; registrar si el guard detiene en la muestra 15 o mantiene contadores separados.
- Caso de recuperación: 14 muestras alternadas, una muestra con ambas métricas por debajo de severo, luego 14 alternadas; ninguna interpretación debe detener antes de acumular 15 muestras de la racha correspondiente.
- No modificar umbrales ni cambiar el código histórico Q97 durante este replay. Si el caso alternado no detiene, registrar la discrepancia semántica y dejar una recomendación explícita; no atribuirla al monitor productivo de LlamaCode ni al cierre de Codex.

## Alcance y recursos

CPU-only, fixtures sintéticos en memoria. No iniciar servidor/modelo, no consultar ni usar GPU, no asignar RAM artificial, no hacer build ni red. ASTRA DEFAULT 1M, SOL, Flash-Next, PeritoSoft, perfiles, RAM y swap permanecen intactos. El objetivo compara la semántica real del helper con la lectura OR compuesta de la frase documentada; no pretende calibrar una nueva política con datos de host.

## Criterio de decisión

Si el helper deja correr 15 muestras donde cada muestra tiene `full>=60%` o `some>=80%`, pero la hoja/cola formula la parada como `full O some` sostenidos 15 muestras, recomendar aclarar o corregir la política antes de usar ese guard en nuevas campañas. La prueba no cambia retrospectivamente resultados previos ni actualiza por sí sola la política de producción.

## Enmienda Q116-A2 · candidato no integrado

Tras observar la semántica per-métrica del helper histórico, preregistro un helper candidato separado. La racha severe-any avanza cuando `full>=60% OR some>=80%` y se resetea sólo cuando ambos caen debajo; los umbrales moderados 20/70 ×30 no cambian. Se probarán cinco escenarios, incluido PSI full=46,52% del control ASTRA moderado. No se edita Q97 ni se integra el candidato en Q97/Q100 o en producto. Fingerprints de helper/runner se agregarán al preregistro antes de ejecutar.
