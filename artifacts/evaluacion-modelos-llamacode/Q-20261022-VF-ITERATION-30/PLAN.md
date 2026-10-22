# Q30 — Flash-Next · diagnóstico acotado del caso BCB/765

**Estado:** cerrado sin pase; el caso no produjo una respuesta final válida dentro de 1.800 s.
**Prioridad:** P1 (Qwen Flash-Next ASTRA/SOL, prioridad expresa del usuario).
**Lock esperado:** `4c3101a9-2bca-4b9d-9ab9-acc1024075a5`.

## Decisión que informa

¿El caso `BigCodeBench/765`, que quedó sin grader en BCB8, termina y pasa cuando su límite de salida del benchmark sube de 1.200 a 2.400 tokens? El pase previo usó el mismo prompt con `maxTokens=1200`; el perfil tenía `--predict 4096` y `reasoningBudget=8192`. Se cambia sólo el límite del caso; pesos, perfil, suite source, acceptance/tests, contexto, KV, MTP, sampling, hardware y runtime se fijan.

Este diagnóstico de un caso no será puntuación BCB8 ni evidencia suficiente para adoptar el modelo. Si termina, el siguiente paso será preregistrar el BCB8 completo con el límite actualizado y un control ASTRA/SOL emparejado bajo la misma definición. Si vuelve a agotar tiempo o tokens, cerrar BCB8 como inconcluso para esta ruta y no lanzar otra repetición igual.

## Prerregistro

- Candidato: Qwen3.8 Flash-Next Unsloth UD-IQ4_XS; Strata 0.1.41; perfil `q14-udiq4xs-he0`, fingerprint `a56c723fde568b4db160bbb48ccc9e378aa221bdcaffe544ee957e3ba666dd86`; agente `agent-maximo`.
- Suite diagnóstica: una copia del prompt original `BigCodeBench/765`, mismo acceptance/grader y pruebas; `maxTokens=2400` en lugar de 1200. ID aislado `vf-q30-bcb2-token-cap-diagnostic`. El nombre evita que LlamaCode la cuente como BCB8 y marque cobertura completa.
- Se conserva `--predict 4096`, `reasoningBudget=8192`, `T=0.60`, `top-p=.95`, `top-k=20`, `min-p=0`, `repeat=1`, `presence=0`, reasoning medium, contexto 32K, KV int8, MTP4, GPU0 y resident budget 12 GiB.
- Una sola tarea, una pasada, timeout de etapa 1.800 s; sin reintento automático ni descarga/build. Ejecución en serie, scope propio `MemoryHigh=86 GiB`, `MemoryMax=96 GiB`, `MemorySwapMax=1 GiB`, `OOMPolicy=kill`.
- Antes de modelo: lock/docs/hash, runner/suite/hash/fingerprint, ausencia de inference server y listeners 18766/8354, `MemAvailable≥80 GiB`, `SwapFree≥1 GiB`, scope correcto, binarios/pesos locales existentes. Durante ejecución: abortar el proceso propio si `MemAvailable<24 GiB`, `SwapFree<1 GiB` o RSS del árbol de LlamaCode llega a 60 GiB. No matar GUI ni procesos ajenos.
- Éxito del diagnóstico: caso válido según el grader original, con respuesta final, sin transporte/infraestructura fallida y dentro de 1.800 s. Registrar tiempo total y tokens disponibles; no atribuir TPS ni mejora general.

## Base observable

El recibo BCB8 del 2026-10-22 dice 8/8 prompts invocados, reparación 2/3, timeout de 1.800 s y grader pendiente; el prompt 2 agotó el reasoning budget y terminó por repetición sin respuesta final. No es un 0/8 ni un score. La suite fuente fija `BigCodeBench/765` en 1.200 tokens. La variante sólo prueba si ese tope explicaba el cierre del caso.

## No cambiar

No modificar perfiles productivos, ASTRA/SOL, Qwen Flash-Next guardados ni PeritoSoft. No usar los resultados de un caso para afirmar superioridad de calidad/velocidad. No descargar Swift ni ejecutar otra suite durante este pase.

## Resultado y decisión

El runner lanzó el caso tras READY, con el cambio preregistrado de `maxTokens=2400`. El agente escribió una primera solución a los 12:45 min; el grader falló y observó `copied_files` de longitud 0 frente a esperados 2, 1 y 2 en tres tests. La vuelta de reparación llegó a una llamada `python -m py_compile ...`; el shell devolvió `python: not found` (el entorno dispone de `python3`). No quedó una respuesta final corregida ni un grade válido antes del timeout.

El benchmark terminó a las 07:07:16Z: `timedOut=true`, `elapsedSec=1800.145`, `score=null`, cobertura BCB pendiente. Los 2.400 tokens por sí solos no resolvieron el caso bajo este perfil/entorno. No iniciar BCB8 completo ni repetir este diagnóstico idéntico. Si se propone una nueva prueba P1, primero debe corregir el acceso a Python del harness y presentar una hipótesis materialmente distinta; entonces preregistrar el caso con el grader original y un control ASTRA/SOL compatible. Esto no es un resultado de velocidad ni una comparación de calidad general.

El scope propio cerró sus procesos; postflight confirmó cero inference servers/listeners, `MemAvailable=115.75 GiB`, `SwapFree=3.04 GiB`, sin OOM (`max=0`, `oom=0`, `oom_kill=0`). ASTRA, SOL, Flash-Next productivo y PeritoSoft permanecen intactos.
