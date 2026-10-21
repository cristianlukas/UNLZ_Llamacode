# Q-20261021-VF-RESUME-ITERATION — cierre de esta iteración

**Estado: bloqueada por condiciones externas; no quedan pruebas de esta iteración que puedan cambiar una decisión sin cambiar materialmente el modelo, runtime o protocolo.** La cola general VF-20261019-01 conserva 58/58 fuentes con disposición; este seguimiento añadió dos diagnósticos locales de compatibilidad de herramientas.

## Pruebas ejecutadas

| Prueba | Resultado | Límite de la conclusión |
|---|---|---|
| Canario Codex CLI de edición/lectura, intento final 11 | El request llegó al servidor local, el modelo generó 33 tokens y Codex salió con código 0, pero no emitió una llamada de herramienta ni creó archivo. Se requerían `canary.txt` = `TOOL_LOOP_OK` y ningún otro archivo; el workspace quedó vacío. llama.cpp omitió los tool types `namespace` y `web_search`; no hubo egress. Postflight sin proceso ni listener residual. | No pasa el gate de integración de herramientas Codex para Qwen3.8-27B Q4_K_M + llama.cpp b11554 + adaptador actual. No es un score de calidad general ni comparación pareada con ASTRA/SOL. No repetir esta combinación sin un cambio material. [Prerregistro](receipts/harness2-qwen38-q4-codex-tool-canary-attempt-11-preregistration-20261021.json), [resultado](receipts/harness2-qwen38-q4-codex-tool-canary-attempt-11-result-20261021.json), [log del servidor](work/harness2-qwen38-q4-codex-tool-canary/attempt-11/codex-home/llama-server.log). |
| Diagnóstico directo Responses API con una herramienta `function` | HTTP 200 y `status=completed`, pero el único item de salida fue `reasoning`; cero `function_call`. 336 tokens de entrada, 5 de salida; no se ejecutó la herramienta ni se escribió archivo. Namespace con sólo loopback; TEST-NET `ENETUNREACH`; postflight sin procesos y puerto libre. | La ausencia no se explica sólo por los tipos `namespace`/`web_search`: tampoco emitió la función con una solicitud mínima. No se hizo una comparación de calidad. Este diagnóstico es de una sola solicitud y no se repite sin cambio material. [Prerregistro](receipts/harness2-qwen38-direct-function-tool-diagnostic-preregistration-20261021.json), [resultado](receipts/harness2-qwen38-direct-function-tool-diagnostic-result-20261021.json), [log resumido](logs/harness2-qwen38-direct-function-tool-diagnostic-runner.log). |

La secuencia de setup y reintentos 01–10 permanece íntegra en sus recibos. El intento 11 corrigió el esfuerzo no soportado `minimal` a `low`; el log anterior confirma que el template de Qwen rechazaba `minimal` antes de generar tokens. `py_compile` del runner final pasó; no se tocó C++/QML, configuración productiva, modelos ni packs. El preflight detectó ArtCraft en GPU0 y se dejó abierto; no había inference server. Las dos corridas quedaron con aislamiento de salida y limpieza verificada. Qwen Flash-Next ASTRA/SOL y modelos PeritoSoft se conservaron intactos.

## Pruebas aún pendientes

No están terminadas todas las evaluaciones del lote. Las que quedan requieren las condiciones externas documentadas; esta iteración no las habilitó:

| Área | Condición para reabrir |
|---|---|
| S36 Instagram | Caption/transcripción, captura legible o copia atribuible del reel. |
| S23 PLE FP8 | Delegación `io` por tarea o estrategia de carga distinta, validada sin modelo y sin presión sostenida de memoria. |
| UD-IQ4_XS BCB8/ADV/TaskFlow | Runner y grader corregidos, dependencias fijadas, fallback `MagicMock` resuelto y fingerprint nuevo preregistrado. |
| OpenJet | Soporte para el GGUF local de 64 bloques o disponibilidad local de un modelo compatible de 65 bloques; además, decisión de evaluar Qwen 27B single-GPU. |
| Harness² calidad | Workflow concreto de LlamaCode y holdout sintético fijo. Transporte y mecánica del harness ya pasan; no sustituyen calidad. |
| Qwen3.8 Q4_K_M en herramienta local | Cambio material de modelo/runtime/protocolo que pueda explicar y corregir la falta de `function_call`; no repetir el mismo canario ni promover a partir de este resultado. |

La matriz anterior y los recibos de los bloqueos previos están en [Q-20261021-VF-FINISH-PENDING](../Q-20261021-VF-FINISH-PENDING/RESULTS.md) y [remaining-tests-blockers-result](../Q-20261021-VF-FINISH-PENDING/receipts/remaining-tests-blockers-result-20261021.json). La condición de reapertura del nuevo test queda en [remaining-tests-resume-iteration-result](receipts/remaining-tests-resume-iteration-result-20261021.json).
