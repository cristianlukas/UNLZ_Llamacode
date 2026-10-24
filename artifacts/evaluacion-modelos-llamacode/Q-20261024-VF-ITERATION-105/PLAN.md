# Q105 — Diagnóstico CPU de las respuestas cruzadas en Q100

**Estado:** preregistrada; aún no iniciado el análisis de artefactos.

## Pregunta y decisión

En Q100, el brazo `parallel:2` aprobó 1/3 semillas en mapping exacto frente a 3/3 serial. ¿Los resultados persistidos prueban un cruce real de identidad entre subagentes/respuestas, o el scorer/harness atribuyó mal las respuestas? El resultado determina si hay un defecto concreto de integración que merezca corrección y una nueva prueba, o si se mantiene “no adoptar parallel:2” sin más inferencia.

## Protocolo preregistrado

1. Inspeccionar únicamente los resultados, logs y manifiestos ya persistidos de Q100 seeds 5051–5053 y el scorer/runner versionado en esa iteración.
2. Construir una tabla por seed/modo con task id, worker/subagent id, request/correlation id, tool-ledger id, respuesta final, marcador esperado/observado, decisión del scorer y timestamps, sólo cuando cada campo exista en evidencia. No inferir campos ausentes.
3. Ejecutar fixtures CPU sintéticos sobre copias de los objetos persistidos para verificar que el scorer asocia una respuesta a la tarea por identidad estable, no por orden de llegada. Casos preregistrados: respuestas en orden, respuestas reordenadas con ids estables, ids repetidos, respuesta ausente y etiquetas cruzadas. No llamar a servidores ni abrir workspaces de producción.
4. Clasificar como **defecto reproducible** sólo si artefactos identificados por ids y una regresión sintética demuestran una asociación incorrecta en código de scheduler/scorer de LlamaCode. Si sólo hay marcadores/resultados sin ids suficientes, dejar **inconcluso**; no iniciar modelos/GPU.

## Límites y guardas

CPU-only, sin build, sin red, sin servidor de inferencia, sin modelos/GPU, sin editar perfiles productivos ni checkout/runtime de usuario. Sólo se escribirán recibos de Q105. Se conserva el gate HyperQwen Q101. Esta prueba no puede habilitar HyperQwen ni `parallel:2` por sí sola.

## Criterio de cierre

Informe con evidencia concreta por semilla; decisión explícita entre defecto reproducible, harness/scorer inválido o inconcluso; fixtures con conteo y salida reproducibles; estado del siguiente paso. Sheets preregistrada antes del primer análisis/fixture.


## Incidencias del harness, sin cambio del protocolo

- Attempt01 no abrió datos: profundidad de raíz incorrecta; corregida de `parents[5]` a `parents[4]`.
- Attempt02 leyó el artefacto raw para un campo que sólo existe en el re-score; reconciliación corregida mediante clave `(seed, policy)`.
- Ambas fallas se preservan en `receipts/q105-forensic-attempt01.json` y `q105-forensic-attempt02.json`; la tercera corrida completó 34/34 checks.
