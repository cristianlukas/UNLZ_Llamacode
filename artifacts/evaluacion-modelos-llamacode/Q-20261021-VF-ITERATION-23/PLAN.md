# Q-20261021-VF-ITERATION-23 — Regrade CPU-only de resultados BCB8 persistidos

## Pregunta
¿Los indicadores por tarea guardados en `BCB8-attempt-2/EVAL.json` corresponden a los mismos candidatos y acceptance tests congelados, y se pueden validar de forma reproducible fuera del harness original?

## Prerregistro
- Fuente: `artifacts/evaluacion-modelos-llamacode/Q-20261019-STRATA-UDIQ4XS-REMAINING/receipts/runs/BCB8-attempt-2/{EVAL.json,metadata.json}`.
- Workspace de candidatos apuntado por `EVAL.json`; sólo leer siete `solution_BigCodeBench_<id>.py` existentes: 928, 765, 771, 1019, 906, 583, 139. El archivo de 360 no existe y se reportará faltante, no se reconstruirá.
- Para cada tarea existente: ejecutar exactamente el código candidato almacenado junto a `acceptance.preamble` y `acceptance.tests` de metadata, en directorio privado independiente con `bubblewrap`, egress deshabilitado, paths del host no montados y filesystem de sistema read-only. Un único intento, límite duro 120 s por tarea.
- No cargar modelos ni llamar al servidor; no descargar dependencias, no compilar; no cambiar la suite, el prompt, el candidato, el grader original, modelos ni perfiles.
- Registrar versión de Python y dependencias presentes; stdout/stderr, exit code/timeout, SHA-256 del candidato y de `EVAL.json`/metadata. Comparar los resultados individuales recalculados con los flags `acceptance` guardados.

## Criterio de interpretación
Un match sólo valida ese caso aislado y el artifact persistido. No convierte en válido el BCB8 global: `EVAL.json` está marcado `invalid=true`, `failed=true`, `failureKind=timeout`, con `finalScore=0/0` y una tarea sin solución. No permite promoción, ranking ni afirmación de superioridad. Divergencia o error de entorno se etiqueta por separado, sin reparar candidato ni reintentar.

## Seguridad e invariantes
No ejecutar archivos fuera del workspace temporal por las pruebas; cada tarea recibe sólo su propia copia del código y test. Qwen Flash-Next ASTRA/SOL y modelos PeritoSoft permanecen intactos.

## Enmienda 01 — composición del módulo para el regrade

Attempt 01 terminó los siete casos en 0,05 s cada uno con `IndentationError`: el wrapper concatenó el preámbulo de firma con una solución ya completa. No se ejecutó código candidato. Esa salida queda archivada en `receipts/bcb8-saved-candidates-regrade-attempt01-runner-defect.json`. El único cambio del attempt 02 es omitir `acceptance.preamble` y concatenar el módulo candidato guardado con el `acceptance.tests` congelado. El alcance, orden, sandbox, límite de 120 s, candidatos y ausencia de retries/model requests siguen iguales.
