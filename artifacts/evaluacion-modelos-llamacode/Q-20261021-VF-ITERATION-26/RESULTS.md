# Q-20261021-VF-ITERATION-26 — Resultado de la evaluación prioritaria

**Estado al 2026-10-22T04:58:43Z:** P1 Flash-Next tiene HE20-06 válido 20/20 y BCB8 inconcluso por timeout sin score. P1.1 completó el screen inicial y los 3/3 pares Mini v2 preregistrados. Los resultados incluyen un screen inicial favorable a OFF, un par asimétrico en 4243 y dos pares limpios que empatan aceptación y favorecen ON en E2E. El criterio preregistrado impide un claim general; mantener MTP-off en producción y seguir a P2 sólo tras revisar sus condiciones de reapertura.

## P1 — Qwen3.8 Flash-Next UD-IQ4_XS

Se ejecutó HE20-05 con fingerprint `a56c723fde568b4db160bbb48ccc9e378aa221bdcaffe544ee957e3ba666dd86`, Strata 0.1.41 y la configuración preregistrada. El runner llegó a 10/20 prompts y la guarda abortó durante el prompt 11/20 a las 2026-10-22 00:46:53 UTC: MemAvailable 70,85 GiB, SwapFree 0,56 GiB, árbol LlamaCode 23,03 GiB RSS y árbol del servidor 73,69 GiB. La guarda de preregistro exige al menos 1 GiB libre de swap.

No se generó EVAL final, grade ni score. El `benchmark-final.json` conserva un `benchmark_running` obsoleto; para el cierre prevalecen el error explícito de guardia, `owned-process-cleanup.json` y el postflight de `safety-abort-result.json`. Strata terminó con exit 0 y la copia aislada de LlamaCode fue detenida con SIGTERM (-15). El postflight no encontró servidores de inferencia, runners ni listeners de prueba.

**Recomendación:** no concluir que Flash-Next falló en calidad ni adoptarlo a partir de telemetría interna. Mantener sin cambios ASTRA/SOL y los modelos de PeritoSoft. No repetir la misma configuración ni bajar el límite de seguridad. Reabrir HE20 sólo con un prerregistro nuevo que trate la trayectoria de memoria/swap y un preflight fresco.

## Prioridades siguientes

| Prioridad | Estado y evidencia | Recomendación / condición para reabrir |
|---|---|---|
| P1.1 — MTP Q4/llama.cpp | Screen inicial OFF 7/7 sin repair/400,437 s vs ON 7/7 final tras 2 repairs/850,805 s. Réplica 4243: OFF 6/7 tras 3 repairs/1161,152 s; ON 7/7/364,398 s. Pares 4244 y 4245: ambos brazos 7/7 sin repairs; ON 366,399/194,237 s vs OFF 390,406/391,432 s. | Seguimiento 3/3 completo. Mantener MTP-off: el screen inicial y el seed 4243 muestran diferencias de reparación/aceptación, por lo que el protocolo preregistrado impide reclamar superioridad pese a que ON fue más rápido en las dos parejas limpias. `avgTps` agregado; sin TPS prefill/decode. Reabrir solo con claim, suite o runtime materialmente nuevo. |
| P2 — Qwen3.8-27B Q4_K_M | Ya se hicieron los intentos 09–11 del canario Codex con el adaptador de compatibilidad; el 11 fue el intento final y no emitió tool call ni archivo. El diagnóstico directo Responses API terminó HTTP 200 pero devolvió sólo `reasoning`, cero `function_call`. No hay score matched de coding. | No repetir este modelo/runtime/protocolo. Reabrir únicamente con un cambio material de modelo, runtime, template/parser o protocolo y un prerregistro nuevo; sólo después del canario de tools hacer A/B matched con ASTRA/SOL. |
| P2.1 — OpenJet | Screen local previo produjo control, pero ningún resultado del candidato: el kernel fijado requiere 65 bloques y el GGUF Qwen3.8-27B disponible tiene 64; el archivo tampoco tiene capas MTP. | No volver a ejecutar la combinación incompatible. Reabrir con soporte para 64 bloques o un artefacto local compatible de 65 bloques, y un objetivo de comparación decidido. |
| P3 — RCO Coder IQ1_M | Screen local BCB-Hard-8 ya completado en la revisión `bba88856f8c3c0c9e40e45f82d05e228b814ac43`: 0/8 del candidato frente a 1/8 del control ASTRA IQ2_XS; transporte 8/8 en ambos. El umbral de avance preregistrado era ≥3/8; el candidato usó el máximo de 6.144 tokens en 5/8 respuestas. | No descargar ni repetir esta revisión. La ficha del autor declara SWE-bench 79,2 frente a 82,8 BF16 y LiveCodeBench v6 87,43 frente a 87,43; son métricas externas y no cambian el screen local. Reabrir sólo ante nueva revisión/quant, harness o backend materialmente distinto. Los shards de esta revisión ya fueron removidos; quedan hashes y recibos. |
| P4 — Swift 1.5 Qwen3.8-27B | Bloqueada: falta determinar elegibilidad comercial y Strata 0.1.41 no tiene una conversión verificada para el formato del MTP head publicado. | No descargar ni inferir hasta documentar elegibilidad/licencia y una ruta runtime compatible. Un brazo sin MTP sería otro experimento, con control ASTRA emparejado. |
| P5 — Strata y otros claims | Los A/B locales pertinentes ya están registrados. Entre ellos, PLE FP8 dio 3/24 frente a 3/24 para stock y ganó 0/3 pares; no se justifica promoción. Otros cambios de tuning no superaron sus gates o no son comparables con este host. | No repetir resultados negativos con la misma configuración. Añadir una prueba sólo ante claim nuevo verificable, artefacto compatible y métrica que pueda cambiar una decisión. |

## Cierre de iteración

El estado anterior de cierre se actualiza con los recibos HE20-06 y MTP Mini v2 que siguen abajo. Se conservan las condiciones de reanudación; no se cambió código ni configuración productiva, y no se eliminó ningún modelo en esta iteración.

Recibos Q26: [prerregistro](attempts/he20-05/receipts/preregistration.json), [guardia](attempts/he20-05/receipts/memory-guard-trip.json), [limpieza](attempts/he20-05/receipts/owned-process-cleanup.json), [cierre autoritativo](attempts/he20-05/receipts/safety-abort-result.json). RCO: [resultado local de la fuente 7](../Q-20261020-VF-20261019-01/receipts/source-07-screen-result.json), [resultado del candidato](../Q-20261020-VF-20261019-01/results/source-07-candidate-bcb.json), [remoción de shards](../Q-20261020-VF-20261019-01/receipts/storage-cleanup/source07-iq1m-weight-removal.json). Qwen3.8-27B: [cierre de los canarios previos](../Q-20261021-VF-RESUME-ITERATION/RESULTS.md).


## Sincronización de Google Sheets

Se reconciliaron las tarjetas P1/P2/P3/P4 de `Accionables`, el resumen/cierre de Q26, Qwen3.8-27B y RCO en `Evaluaciones LlamaCode`, y el inventario vivo en `Inventario de modelos`. El readback confirmó los estados y fundamentos escritos. Se añadieron fichas para Qwen3.8-27B, RCO IQ1_M y Swift 1.5; las rutas Windows, TPS no comparables y usos no verificados se dejaron como N/D en vez de inferirlos. Recibo: [google-sheets-priority-reconciliation-20261022.json](receipts/google-sheets-priority-reconciliation-20261022.json).

## Reanudación HE20-06 · 2026-10-22T01:10:23Z

Se preregistró una nueva variante P1 con contención del proceso propio porque HE20-05 se había abortado al consumir swap global. Se mantiene el mismo Qwen Flash-Next UD-IQ4_XS, fingerprint `a56c723fde568b4db160bbb48ccc9e378aa221bdcaffe544ee957e3ba666dd86`, Strata 0.1.41, contexto 32.768, KV INT8, MTP4 y HE20. Cambian sólo `resident_budget_gib` 20→12 y límites de cgroup 86/96 GiB + 1 GiB swap. No se aflojan guardias ni se inicia BCB. El wrapper debe validar lock/documentos/cgroup; el runner exige preflight y vuelve a escanear procesos antes de arrancar el modelo. Recibos: `attempts/he20-06/receipts/preregistration.json`, `runtime-copy.json`.


## Avance HE20-06 · 2026-10-22T01:47:01Z

El screen sigue activo en el prompt 10/20; todavía no hay EVAL final, grader ni score agregado. Los marcadores parciales de `benchmark_acceptance_probe`, incluso los que reportan `hardFailed`, no son veredicto del HE20 y no se usarán para recomendar adopción. A 01:46:14Z la guardia registró MemAvailable 98,38 GiB, SwapFree 3,48 GiB, cgroup memory.current 39.032.942.592 bytes, peak 39.859.298.304 bytes, sin eventos `high/max/oom/oom_kill`; GPU0 23.851/24.576 MiB y 100% de uso. La GUI permanece fuera del criterio de bloqueo.

La ficha P1 en `data/actionables.json` y las pestañas `Accionables`, `Evaluaciones LlamaCode` e `Inventario de modelos` quedaron sincronizadas a 10/20. Readback verificado; recibo `attempts/he20-06/receipts/google-sheet-progress-04.json`. La recomendación no cambia hasta que cierre el gate final.


### Avance HE20-06 · 2026-10-22T02:01:37Z

El runner avanzó a prompt 12/20. No hay EVAL final, grader ni score agregado; los probes parciales siguen sin valor de gate. La guardia de 02:00:44Z registró MemAvailable 97,86 GiB, SwapFree 3,49 GiB y cgroup sin eventos high/max/OOM; continúa el límite de memoria del scope. Se sincronizaron el accionable local y las tres ubicaciones del Sheet; readback confirmado en `google-sheet-progress-05.json`. La recomendación sigue en espera del resultado final.


### Avance HE20-06 · 2026-10-22T02:14:45Z

El screen está en prompt 14/20, sin EVAL, grader ni score agregado. Guardia: MemAvailable 97,97 GiB, SwapFree 3,51 GiB; cgroup sin eventos high/max/OOM. La ficha local y las tres ubicaciones del Sheet fueron actualizadas; readback en `attempts/he20-06/receipts/google-sheet-progress-06.json`. No se interpreta calidad ni rendimiento antes del gate final.


### Avance HE20-06 · 2026-10-22T02:15:50Z

El runner avanzó a prompt 15/20. Sigue sin EVAL, grader ni score agregado; los datos parciales no pasan el gate. Última guardia 02:14:45Z: MemAvailable 97,97 GiB, SwapFree 3,51 GiB y cgroup sin eventos high/max/OOM. La ficha local y Sheets están sincronizados y leídos de vuelta; recibo `attempts/he20-06/receipts/google-sheet-progress-07.json`.


## Cierre BCB8 · 2026-10-22T02:58:48Z

HE20-06 queda válido a la huella `a56c723f…`: 20/20 finales tras dos reparaciones (14/20 en el primer intento). No constituye una comparación de velocidad: el baseline histórico tiene otro fingerprint.

El único pase BCB-Hard-8 sí invocó la suite congelada `05c28394-11d0-41fe-a55f-b3cb69db9c15`, con los ocho IDs y SHA preregistrados. Alcanzó 8/8 prompts, pero seguía en la reparación 2/3 al llegar al límite preregistrado de 1.800 s. El prompt 2 agotó el presupuesto de razonamiento y terminó por repetición sin respuesta final; el grader quedó pendiente. Resultado: **inconcluso por timeout, sin score ni grade**, no 0/8 y no evidencia de inferioridad.

La última guarda, 02:57:07Z, seguía dentro de los límites: MemAvailable 66,50 GiB, swap libre 1,77 GiB, RSS de la app 34,68 GiB y árbol servidor 64,15 GiB. El scope propio quedó `inactive/dead` con `Result=success`; se registró la parada de Strata y LlamaCode aislados y el postflight no detectó procesos de inferencia ni procesos de cómputo GPU. No se tocó ningún servidor ajeno.

**Recomendación:** no adoptar ni promocionar Flash-Next por HE20 solo; no repetir BCB8 con la misma configuración/timeout. Antes de volver a invocarlo, revisar el ciclo de reparación del prompt 2 y determinar si existe una variante materialmente distinta y acotada que pueda cerrar el grader. La cola continúa en orden: diagnóstico de harness P1.1 para MTP Q4/llama.cpp; los canarios Qwen3.8-27B, OpenJet, RCO, Swift y Strata conservan sus condiciones previas. ASTRA, SOL, PeritoSoft y producción quedan sin cambios.

Recibo autoritativo: [`attempts/bcb-01/receipts/bcb-final-result.json`](attempts/bcb-01/receipts/bcb-final-result.json). El JSON `benchmark-final.json` mantiene el `benchmark_running=true` obsoleto del último snapshot del cliente; para el cierre prevalecen el timeout del runner, este recibo, `owned-process-cleanup.json` y el estado final de systemd.


### MTP-off preflight setup failure · 2026-10-22T03:13:27Z

El primer arranque aislado verificó el daemon en `18119`, suite/fingerprint MTP-off `e9c5c527e30744049cff955f0489c36cd08a8777b9bf87422f0f768c3d42cf23`, memoria y scope; salió antes de cargar el modelo porque faltaba la copia local de `run_taskflow.py`. No hubo `llama-server`, evento `benchmark_start`, proceso de cómputo GPU ni score. El scope se limpió correctamente. Se copió el runner histórico sin cambios, se fijó su SHA-256 `1cf43f5cafbfd83ff6357bd3dbd1d6986b68ee1499f7008f8ea2bf8f67df484c`, y `py_compile` + hash gate pasan. Este fallo de preparación no consume el único pase preregistrado del brazo. Evidencia: `attempts/mtp-taskflow-v2-01/receipts/preflight-failure-01/setup-failure-summary.json` y `systemd-scope-probe.json`.


### MTP-off interrumpido por guardia no preregistrada · 2026-10-22T03:18:32Z

La carga pasó el gate exacto del perfil `q4-mtp-off-taskflow-20261013` / fingerprint `e9c5c527…`, y sí inició el modelo y la suite, pero el wrapper abortó cuando RSS del árbol alcanzó 60 GiB. Ese límite no figuraba en el prerregistro. En ese momento MemAvailable era 115.73 GiB, SwapFree 2.71 GiB y el cgroup estaba en 76.11 / 96 GiB, sin eventos max/OOM; no hay resultado final ni score. No es una conclusión sobre MTP-off. El proceso servidor apareció en el snapshot inmediato de postflight, pero desapareció al terminar el scope; el chequeo posterior confirma unidad inactiva, sin PID/puertos 18112/18119 ni compute app. Se eliminó la regla RSS no preregistrada y se alineó la guarda a MemAvailable <20 GiB sostenido 15 muestras, swap <1 GiB y eventos max/OOM del cgroup. Un pase válido de control sigue disponible. Evidencia archivada en `attempts/mtp-taskflow-v2-01/receipts/abort-unregistered-rss-guard-01/`.


### TaskFlow Mini v2 · MTP-off control · 2026-10-22T03:28:26Z

Pase válido completado con fingerprint `e9c5c527e30744049cff955f0489c36cd08a8777b9bf87422f0f768c3d42cf23`. Aprobó 7/7 criterios: 4/4 archivos, `py_compile` (exit 0), 8/8 tests unitarios (exit 0) y self-test `SELF_TEST_OK` (exit 0). Primer intento 7/7, cero reparaciones y cuatro llamadas de herramienta. Tiempo total 400.437 s; primera llamada 157,224 s y primera escritura 157,456 s. La suite no devuelve TPS. Resultado favorable al control en este fixture, no comparable numéricamente con TaskFlow ULTRA ni con Server Speed. El postflight de la scope confirmó cero servidores/puertos/GPU residuales, MemAvailable 116.19 GiB, SwapFree 2.81 GiB y cero eventos de cgroup/OOM. Próximo brazo: MTP-on, sólo tras gates frescos y readback de Sheets. Recibo `attempts/mtp-taskflow-v2-01/receipts/mtp-off-final-result.json`.


### TaskFlow Mini v2 · MTP-on candidato · 2026-10-22T03:43:39Z

El brazo candidato completó 7/7 criterios con el fingerprint esperado `b39dcfa4f912aee2ae973d28f25ac04f81e5ba1c0dbaaa2e0a7e5641e38d3d27`: 4/4 archivos, compilación, 8/8 pruebas unitarias y `SELF_TEST_OK`. Su primer intento pasó 6/7; completó el criterio faltante tras dos reparaciones. Registró 14 llamadas de herramienta, 850,805 s de tiempo total, 163,273 s a primera herramienta y 163,316 s a primera escritura. La suite reporta `avgTps=27,557`, pero no prefill/decode TPS.

Comparado dentro del único par Mini v2, el control MTP-off terminó 7/7 en primera pasada, 0 reparaciones, 4 llamadas y 400,437 s; primera herramienta/escritura 157,224/157,456 s. El candidato alcanzó el mismo score final pero necesitó dos reparaciones y 2,125× el tiempo total. La diferencia de `avgTps` (+31,5% reportado) no es un claim de velocidad: no hay TPS desglosados y el candidato usó más reparaciones/llamadas y generó más tiempo no-generativo. La diferencia E2E es la métrica operativa disponible; sigue siendo un solo par, por lo que no es evidencia estadística estable.

**Recomendación:** mantener MTP apagado para esta ruta; no migrar producción ni anunciar una ventaja de calidad/velocidad. Para resolver variabilidad quedó preregistrado un follow-up de tres pares con llama.cpp seeds 4243, 4244 y 4245, compartidas por off/on dentro de cada par y en orden balanceado. Si los perfiles no conservan únicamente la diferencia del sidecar y el seed pareado, el brazo se detendrá antes de cargar pesos. La suite permanece fija; no se compara con TaskFlow ULTRA ni con Server Speed. Prerregistro: `attempts/mtp-taskflow-v2-repeats-01/receipts/preregistration.json`.

Postflight limpio: cero servidores/listeners/compute apps residuales, cero eventos max/OOM, MemAvailable 116,33 GiB y SwapFree 2,88 GiB. Recibo autoritativo [MTP-on y comparación](attempts/mtp-taskflow-v2-01/receipts/mtp-on-final-result.json); EVAL SHA-256 `a9fe22a17410bdb720ea4c0962a184c60d266272a77d42bdbebfa25c7626feee`.


### Réplica TaskFlow Mini v2 · par seed 4243 · 2026-10-22

El par OFF→ON completó la misma suite Mini v2, prompt, acceptance y seed de harness (4242), con el seed de servidor 4243 compartido. OFF, fingerprint `08d42ba0a29c2b34ecc94e7741747b7df0f4b7f6195ded88c87f39151ac6593b`, quedó en 6/7 tras 3 reparaciones, 23 llamadas, 1.161,152 s; primera herramienta/escritura 170,916/170,964 s. Falló un test unitario de normalización de espacios. ON, fingerprint `4c7b0956a6ccbc2c74b33df60637820b8051aaa760574dfbfa97b6db61c63bdd`, aprobó 7/7 al primer intento, sin reparaciones, 4 llamadas y 364,398 s; primera herramienta/escritura 152,789/152,833 s. El tiempo ON/OFF fue 0.314×. No hay prefill/decode TPS; `avgTps` es agregado y auxiliar. Ambos brazos tuvieron cleanup limpio y no registraron eventos cgroup max/OOM.

La réplica favorece MTP-on en este par, en contraste con el screen inicial donde OFF pasó 7/7 en 400,437 s y ON requirió dos reparaciones y 850,805 s. Por esa variabilidad entre pares, **no cambiar producción ni concluir superioridad**. El seed 4244 completó la secuencia ON→OFF; queda 4245 OFF→ON. El resultado del brazo OFF está en `attempts/mtp-taskflow-v2-repeat-4243/receipts/repeat-4243-off-result.json`; comparación pareada en `attempts/mtp-taskflow-v2-repeat-4243/receipts/pair-4243-comparison.json`.


### Réplica TaskFlow Mini v2 · par seed 4244 · 2026-10-22

La pareja ON→OFF usó la misma suite, prompt SHA `b5d0bc…`, suite SHA `7e0ff7…`, harness seed 4242 y llama.cpp seed 4244 en ambos perfiles. ON (fingerprint `bf00ea76a84b42702436b1a85f1e1bed502ea4c268be8fef2fc1c74a786bf484`) aprobó 7/7 al primer intento, sin reparaciones, 4 tool calls, 366,399 s; primera herramienta/escritura 151,496/151,538 s. OFF (fingerprint `422f9547e122f9a3590af88709c7ce1514a1e590a2db797ff059494119644670`) también aprobó 7/7 sin reparaciones y 4 tool calls, 390,406 s; primera herramienta/escritura 152,455/152,498 s. En este par ON usó 24,007 s menos (6,15 %); los tiempos a primera herramienta/escritura fueron similares. `avgTps` fue 30,435 ON y 21,042 OFF, pero es agregado; prefill/decode TPS no están disponibles.

El par 4244 favorece modestamente ON en tiempo total, con aceptación idéntica. La secuencia completa aún es mixta frente al screen inicial; **mantener MTP-off en producción y completar 4245**, sin declarar una mejora general a partir de dos pares exploratorios. Ambos postflight quedaron limpios, con MemAvailable 115,49/115,60 GiB, SwapFree 3,07/3,17 GiB y eventos cgroup high/max/OOM en cero. Recibo: `attempts/mtp-taskflow-v2-repeat-4244/receipts/pair-4244-comparison.json`.


### Réplica TaskFlow Mini v2 · par seed 4245 · 2026-10-22

La pareja OFF→ON completó la suite, prompt y harness seed 4242 con llama.cpp seed 4245 compartida. OFF, fingerprint `02c68df52706c23d4348d42465811718f6844ffa1095c727b5d38f7fb34d3a65`, aprobó 7/7 al primer intento, 0 reparaciones, 4 tool calls y 391,432 s; primera herramienta/escritura 151,995/152,039 s. ON, fingerprint `2ef35633f64da85dbee0ce4e39667f01cb78947ae05d413e6a09ed799b70b8b7`, también aprobó 7/7 al primer intento, 0 reparaciones, 4 tool calls y 194,237 s; primera herramienta/escritura 193,415/193,480 s. El E2E de ON fue 197,195 s menor (50,38 %) en este par, aunque su primera herramienta/escritura llegó unos 41,4 s después. `avgTps` 21,148/32,351 es agregado; no hay prefill/decode TPS.

Los tres pares repetidos quedan terminados. Los dos pares limpios (4244/4245) empatan aceptación y favorecen ON en E2E; el screen inicial favoreció OFF y 4243 tuvo diferencia asimétrica (OFF finalizó 6/7 tras 3 reparaciones; ON 7/7 sin reparaciones). La política preregistrada impide afirmar superioridad con una aceptación fallida o reparaciones desbalanceadas. **Recomendación: mantener MTP-off en producción; no migrar ni hacer claim.** No se cambia ningún perfil productivo. Ambos postflight fueron limpios: no quedaron procesos de inferencia, listeners ni compute apps; eventos cgroup max/OOM=0; MemAvailable 115,91/115,47 GiB. Recibo: `attempts/mtp-taskflow-v2-repeat-4245/receipts/pair-4245-comparison.json`.
