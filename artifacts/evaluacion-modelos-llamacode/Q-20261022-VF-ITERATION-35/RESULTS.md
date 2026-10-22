# Q35 — diagnóstico y prevención del cierre de Codex

## Hallazgo

El cierre del 2026-10-22 fue causado por `systemd-oomd`: el harness lanzó Strata como hijo de la herramienta de Codex dentro del mismo scope `app-org.chromium.Chromium-833601.scope`. Bajo presión sostenida, systemd-oomd terminó el scope completo. El pico registrado fue 112,9 GiB; PSI del scope 90,01% y del `user@1000.service` 63,31% frente al umbral 50% durante más de 20 s. No hubo OOM del kernel ni Xid de NVIDIA. Strata todavía cargaba pesos/expertos; no se envió un request válido.

## Cambio preventivo

El supervisor y cada inferencia corren en servicios transitorios separados bajo `background.slice`, cada uno con su cgroup, journal y estado persistente. La corrida vigila PSI y se detiene dentro de su unidad antes de que systemd-oomd pueda cerrar el escritorio. El runner rechaza iniciar si no está en el cgroup esperado. No se redujeron pesos, contexto, cuantización, perfil ni memoria lógica, ni se cambió el reparto de GPU.

## Verificación

- Intentos 4–5 cargaron el mismo artefacto y contexto 131K en cgroups aislados. La carga llegó a 3,9 GiB y 5,1 GiB de pico de unidad respectivamente; el escritorio siguió vivo en su cgroup.
- El intento 4 mostró un error de manejo de ausencia de respuesta (`None.values()`). Se corrigió con `score_response()`: si no hubo respuesta, todos los campos de calidad quedan nulos; la fixture no se marca completa. Las regresiones y el guard pasaron 7/7; `py_compile` pasó.
- El intento 5 superó el guard PSI 50% y terminó sólo el worker. Codex siguió vivo, no hubo request ni score y no quedó ningún inference server. El recibo y el progreso permanecieron legibles.

## Estado

La prevención del cierre por este harness quedó verificada. Q35 no tiene aún un resultado de calidad: el barrido restante está bloqueado hasta que cambie la fuente externa de presión del user-manager y un nuevo preflight/startup permanezca bajo el guard. Siguiente paso: revisar la fuente de presión en `user@1000.service`, luego reanudar exactamente desde `131072/2026101`, con la misma configuración. No repetir mientras se reproduzca el guard; no reducir el modelo o el contexto.

Evidencia: `receipts/codex-crash-diagnosis.json`, `receipts/attempt-02-memory-pressure.json`, `receipts/attempt-04-runner-nullscore.json`, `receipts/attempt-05-pressure-guard.json`, `receipts/progress.json`.

## Registro compartido

La fila Q35 se agregó a `Evaluaciones LlamaCode` (`A266:J266`) y la recomendación P0 de aislamiento quedó primera en `Accionables` (`A2:N2`). El readback verificó los valores y el formato WRAP/TOP. El recibo de sincronización está en `receipts/google-sheet-sync.json`.

La recomendación P0 también se añadió al JSON de accionables de la app, como primer elemento; se dejó backup previo y se validó mediante el mismo `read_json()` del servidor, sin iniciar el servicio. El recibo está en `receipts/app-actionable-sync.json`.

## Corrección de diagnóstico y alcance · Q36 · 2026-10-22

La frase anterior «la prevención del cierre por este harness quedó verificada» era demasiado amplia. La lectura posterior del journal mostró que, 16 segundos después del abort controlado Q35-05, systemd registró otro proceso terminado por OOM bajo `app.slice`; el registro no nombra al PID. ChatGPT/Codex siguieron vivos y no hubo request, score ni servidor residual. Por tanto, Q35 por sí sola sólo probó aislamiento/guard para sus intentos, no contención completa frente a OOM.

Q36 corrigió este hueco para el runner Q35: `MemoryMax` dinámico a partir de la RAM disponible, `MemorySwapMax`, `OOMPolicy=kill`, `KillMode=control-group`, `OOMScoreAdjust=900` y verificación de los límites efectivos antes de aceptar un request. Una regresión CPU-only en servicio efímero confirmó que `MemoryMax=128 MiB` mata la unidad completa y no el proceso padre/Codex. La verificación fue una inyección sintética pequeña; el barrido Flash-Next sigue bloqueado por PSI y no se reanudó.

El cambio limita los recursos que puede consumir el proceso de evaluación; no reduce el modelo, el contexto, la cuantización ni el uso de memoria lógica solicitado. Esto contiene el OOM del worker, no demuestra inmunidad a fallos independientes del kernel, systemd-oomd, driver o presión generada fuera del cgroup. Q36 y sus recibos están en `../Q-20261022-VF-ITERATION-36/RESULTS.md`.

## Enmienda de contención · Q37 · 2026-10-22

Q36 probó el OOM de un worker bajo el gestor de usuario, por lo que no cubría un OOMD kill de `user@1000.service`. La revisión Q37 movió supervisor y workers a servicios transitorios del gestor systemd del sistema (`background.slice`, UID/GID 1000), fuera de ese padre. A la vez, el supervisor/worker conservan sus límites cgroup por tarea; sólo se quitó del guard el aborto por PSI intermedio del user-manager. MemAvailable <20 GiB, swap-out >4 MiB y PSI global/cgroup severo sostenido siguen deteniendo la prueba.

El test OOM sintético del gestor del sistema (128 MiB) terminó la unidad y su grupo, mientras controlador, ChatGPT y Codex app-server conservaron los mismos PID. El monitor Q35 leyó exitosamente tanto el cgroup de esa unidad como la presión actual de user@1000. Regresiones: 17/17; `py_compile` y `bash -n` correctos. También se restauró `Monitor.start()/stop()` al detectar que el intento Q35-01 había fallado antes del request porque faltaba `Monitor.stop()`. Se ajustó `ManagedOOMMemoryPressureLimit` sólo en `user@1000.service` de 50% a 70%, persistente; `ManagedOOMMemoryPressure=kill` y OOMD global permanecen activos. La reversión documentada es `sudo systemctl revert user@1000.service`.

No hubo request de modelo en esta etapa de Q37. El acceso GPU del system manager se verificó con una consulta de solo lectura; ambos shards Qwen3.8-Flash-Next IQ2_XS, runtime Strata 0.1.41 y config/fixture 131072/2026101 pasan hashes. El intento 06 quedó preregistrado en `../Q-20261022-VF-ITERATION-37/receipts/q35-resume-attempt-06-preregistration.json`; próximo paso: preflight completo y reanudar ese fixture bajo el gestor systemd del sistema. Evidencia Q37: `../Q-20261022-VF-ITERATION-37/RESULTS.md` y `../Q-20261022-VF-ITERATION-37/receipts/`.

## Diagnóstico del intento 06 y corrección Q37

El intento 06 sí inició la carga de Strata y registró uso transitorio de las GPU, pero `model_loaded=false`, no hubo health check satisfactorio ni request (`request_sent=false`); sus métricas de calidad quedan nulas. Abortó por un delta de 1.458 páginas en el contador **global** `/proc/vmstat:pswpout` (~5,70 MiB). En el mismo recibo, `MemAvailable` mínimo fue 119.390.248.960 bytes (~111,2 GiB), PSI avg10 máximo fue 8,62% global y 17,02% en el cgroup de la unidad, user-manager 0% (por debajo del gate 80%/60%), y los eventos OOM del cgroup de la unidad fueron cero. No era evidencia de presión de swap atribuible al worker. Los máximos se verificaron sobre las ocho muestras; véase `../Q-20261022-VF-ITERATION-37/receipts/q35-attempt-06-evidence-reconciliation.json`.

Q37 sustituyó esa guardia por el delta de `memory.swap.current` del cgroup de la unidad, que atribuye el swap al worker; el `pswpout` global queda registrado como telemetría. Regresión CPU-only: 18/18, incluyendo global `pswpout` >4 MiB sin aborto y swap propio del cgroup >4 MiB con aborto; `py_compile` pasó. No se cambió perfil, contexto, pesos ni parámetros del modelo. El intento 06 sigue siendo inválido de infraestructura y no cuenta como resultado del holdout. Antes de una nueva carga se repetirá el preflight completo; si pasa, se usará un directorio de respaldo inmutable del intento 06 y se preregistrará una reanudación nueva del mismo fixture.


### 131.072 tokens · seed 2026102, attempt 02

Valid request and complete response; 125.224 prompt tokens, 709 output tokens, `finish_reason=stop`, **0/8 exact matches** (`strict_output_valid=false`). Prefill 3.452 tok/s, decode 159,3 tok/s, request 40,76 s; cgroup swap delta 0 and no monitor/OOM abort. The supervisor advanced serially to seed 2026103 without a 8350/TIME_WAIT preflight failure, validating the corrected bindability probe for back-to-back runs. This is a second valid zero-quality result, not evidence for adopting a larger context. Receipt: `../Q-20261022-VF-ITERATION-37/receipts/q35-seed-2026102-attempt-02-completion.json`.


### 131.072 tokens · seed 2026103, attempt 01

HTTP 200, modelo cargado, prompt 125.113/131.072 tokens (pasa 95%), sin error/aborto/OOM y swap del worker 0. La salida consumió el máximo 768 y terminó con `finish_reason=length`; el grade parcial fue 0/8. Se registra como `incomplete`, no como pase de calidad; no repetir. La suite se pausó porque el supervisor no consideraba terminales las respuestas completas negativas. Enmienda registrada para continuar al siguiente contexto sin cambiar condiciones.

### Reanudación tras reparación del volumen · 262.144 tokens, seed 2026101, attempt 01

El preflight del host pasó a las 15:25:20Z tras verificar lock Q37, ausencia de servidores de inferencia, puerto 8350 bindable, 116,9 GiB disponibles, 8 GiB de swap libre, 114,1 GiB libres en el volumen NTFS `rw`, memoria PSI 0%, >23 GiB libres por GPU, OOMD del user-manager aún en 70%, y hashes iguales de los shards, runtime, config y fixture. Las regresiones CPU-only se repitieron: 25/25 y `py_compile` correcto.

El supervisor volvió a arrancar a las 15:25:43Z, reconoció `131072:2026103` como una respuesta terminal incompleta y no la repitió; avanzó directamente a `262144:2026101` en `background.slice`, con límites efectivos preregistrados para el worker. La corrida está en curso; todavía no hay nuevo resultado de modelo. Mantener el criterio: cualquier fallo técnico detiene el barrido; no modificar el modelo, los parámetros ni el fixture. Recibos Q37: `preflight-attempt-09-host.json`, `q35-attempt-09-start-progress.json` y `q35-terminal-incomplete-response-regression-test.json`.

### 262.144 tokens · seed 2026101, attempt 01

HTTP 200 y modelo cargado; el prompt fue 250.383 tokens (≥95% del contexto), se generaron 768 tokens y terminó con `finish_reason=length`. Calidad parcial 0/8, prefill 3.354,9 tok/s, decode 140,7 tok/s, solicitud 80,17 s; swap del cgroup 0, MemAvailable mínimo 75,1 GiB, sin error/aborto de monitor. Se clasifica `incomplete`: no es un pase de calidad ni un fallo técnico; no repetir. El supervisor avanzó serialmente a `262144:2026102`, attempt01. Recibo canónico en `runs/262144/2026101/receipt.json` y resumen Q37 `q35-seed-262144-2026101-incomplete-completion.json`.

### 262.144 tokens · seed 2026102, attempt 01

HTTP 200, modelo cargado, 250.397 tokens de prompt (≥95%), salida 768/768 y `finish_reason=length`. Grade parcial 0/8; prefill 3.296,1 tok/s, decode 143,5 tok/s, 81,40 s; cgroup swap 0, MemAvailable mínimo 75,5 GiB y sin aborto/error. `incomplete`, no repetir. El supervisor avanzó a `262144:2026103` attempt01 en serie. Recibo canónico `runs/262144/2026102/receipt.json`; resumen Q37 `q35-seed-262144-2026102-incomplete-completion.json`.

### 262.144 tokens · seed 2026103, attempt 01

HTTP 200, modelo cargado, 250.416 tokens de prompt (≥95%), salida 768/768 y `finish_reason=length`. Grade parcial 0/8; prefill 3.270,5 tok/s, decode 141,9 tok/s, 82,06 s; cgroup swap 0, sin error/aborto. `incomplete`, no repetir. El supervisor avanzó a `524288:2026101` attempt01 en serie. Tres respuestas a 262K quedan incompletas por el cap de salida, así que aún no permiten comparar calidad entre contextos. Recibo canónico `runs/262144/2026103/receipt.json`; resumen Q37 `q35-seed-262144-2026103-incomplete-completion.json`.

### 524.288 tokens · seed 2026101, attempt 01

HTTP 200, modelo cargado, prompt 500.699 tokens (≥95%), salida 768/768 y `finish_reason=length`. Grade parcial 0/8; prefill 2.875,7 tok/s, decode 122,6 tok/s, 180,54 s; cgroup swap 0, MemAvailable mínimo 71,7 GiB, sin error/aborto. `incomplete`, no repetir. El supervisor avanzó a `524288:2026102` attempt01 en serie. Aún no se puede concluir calidad ni mejora de contexto. Después de terminar la matriz fija, considerar una prueba preregistrada con presupuesto de salida suficiente para emitir la respuesta estructurada. Recibo canónico `runs/524288/2026101/receipt.json`; resumen Q37 `q35-seed-524288-2026101-incomplete-completion.json`.

### 524.288 tokens · seed 2026102, attempt 01

HTTP 200, modelo cargado, prompt 500.692 tokens (≥95%), respuesta completa (`finish_reason=stop`, 426 tokens). Exact match 0/8 y `strict_output_valid=false`; prefill 2.870,5 tok/s, decode 118,6 tok/s, 178,18 s; cgroup swap 0, MemAvailable mínimo 72,0 GiB, sin error/aborto. Se registra como respuesta completa negativa, no repetir. El supervisor avanzó a `524288:2026103` en serie. Esto separa los resultados capados anteriores de la calidad: el cap no explica por sí solo el 0/8. Recibo `runs/524288/2026102/receipt.json`; resumen Q37 `q35-seed-524288-2026102-zero-quality.json`.

### 524.288 tokens · seed 2026103, attempt 01

HTTP 200, modelo cargado, prompt 500.704 tokens (≥95%), respuesta completa (`finish_reason=stop`, 732 tokens). Exact match 0/8 y JSON estricto inválido; prefill 2.870,0 tok/s, decode 125,4 tok/s, 180,46 s; cgroup swap 0, MemAvailable mínimo 72,0 GiB, sin error/aborto. Medición completa negativa, no repetir. El supervisor avanzó a `1048576:2026101`. Dos respuestas completas a 524K dieron 0/8; una salida mayor puede completar los casos capados, pero ya no es una hipótesis suficiente para explicar ni corregir la calidad. Recibo `runs/524288/2026103/receipt.json`; resumen Q37 `q35-seed-524288-2026103-zero-quality.json`.

### 1.048.576 tokens · seed 2026101, attempt 01

HTTP 200, modelo cargado, prompt 1.001.393 tokens (≥95%), respuesta completa (`finish_reason=stop`, 89 tokens), exact match 0/8 y JSON estricto inválido. Prefill 2.310,8 tok/s, decode 89,9 tok/s, 434,67 s; swap del cgroup 0, MemAvailable mínimo 65,1 GiB, sin error/aborto. No repetir. El supervisor avanzó a `1048576:2026102`. A 1M no aparece mejora de calidad; prefill/decode también son menores que a 524K. Recibo `runs/1048576/2026101/receipt.json`; resumen Q37 `q35-seed-1048576-2026101-zero-quality.json`.

### 1.048.576 tokens · seed 2026102, attempt 01

HTTP 200, modelo listo, prompt 1.001.253 tokens, respuesta completa (`stop`, 89 tokens), exact match 0/8 y JSON estricto inválido. Prefill 2.308,6 tok/s, decode 94,4 tok/s, 434,98 s; swap del cgroup 0, MemAvailable mínimo 65,0 GiB, sin error/aborto. No repetir. El supervisor avanza a `1048576:2026103`. Segunda respuesta completa repetida 0/8 a 1M. Recibo `runs/1048576/2026102/receipt.json`; resumen Q37 `q35-seed-1048576-2026102-zero-quality.json`.


## Cierre de la matriz 4 × 3 y corrección de scoring · 2026-10-22

La tercera semilla a 1.048.576 terminó a las 16:03:11Z sin error: HTTP 200, modelo cargado, prompt 1.001.463 tokens, 90 tokens de salida, `finish_reason=stop`, prefill 2.310,6 tok/s, decode 85,5 tok/s, request 434,81 s y sesión de servidor 453,25 s. MemAvailable mínimo 64,98 GiB, swap del worker 0, sin OOM ni aborto de monitor. El servidor propio cerró y liberó el puerto. Recibo: `runs/1048576/2026103/receipt.json`; resumen Q37: `../Q-20261022-VF-ITERATION-37/receipts/q35-seed-1048576-2026103-semantic-completion.json`.

El scoring original devolvía 0/8 porque intenta `json.loads()` sobre la respuesta, pero el prompt enumera ocho pedidos y no exige JSON; el request tampoco fija `response_format`. No se conserva ese 0/8 como calidad semántica. La regrade offline preregistrada examina respuestas numeradas o respuestas explícitas bajo el case ID, excluye valores `REVOKED` y conserva por separado `finish_reason=length`. La misma lista de ocho respuestas esperadas se verificó idéntica entre los cuatro contextos para cada seed. La suite CPU-only del regrader pasó 8/8.

Resultado semántico de las 12 corridas: las siete respuestas completas (`stop`) fueron 8/8; las cinco capadas por `max_tokens=768` dieron cobertura parcial 6/8, 7/8 o 8/8. Distribución: 131K, 2/3 completas (ambas 8/8); 262K, 0/3 completas y coberturas parciales 6/8, 7/8, 8/8; 524K, 2/3 completas (ambas 8/8); 1M, 3/3 completas (todas 8/8). El regrader no transforma una salida `length` en respuesta completa ni cambia los recibos originales.

Medias observadas por contexto (tres seeds):

| Contexto | Prefill tok/s | Decode tok/s | Tiempo request | Tiempo sesión |
|---:|---:|---:|---:|---:|
| 131.072 | 3.440,9 | 154,7 | 40,93 s | 56,82 s |
| 262.144 | 3.307,2 | 142,0 | 81,21 s | 96,88 s |
| 524.288 | 2.872,1 | 122,2 | 179,73 s | 196,94 s |
| 1.048.576 | 2.310,0 | 89,9 | 434,82 s | 454,53 s |

El setup sí procesa aproximadamente un millón de tokens con salida correcta y sin swap/OOM. No se encontró una ventaja de exactitud frente a 131K en las respuestas completas; a 1M el prefill medio fue 32,9% menor y decode 41,9% menor que a 131K, con request medio 10,6× más largo. La matriz demuestra capacidad técnica y un coste sustancial de latencia, no que convenga elevar el contexto productivo por defecto. Recomendación: mantener 131K como default de ASTRA/Flash-Next; habilitar contextos mayores sólo para una tarea que requiera explícitamente más de 131K y acepte ese coste. No cambiar perfil productivo, ASTRA, SOL, PeritoSoft ni pesos.

Evidencia de la auditoría: `../Q-20261022-VF-ITERATION-37/receipts/q35-semantic-regrade-preregistration.json`, `../Q-20261022-VF-ITERATION-37/receipts/q35-semantic-regrade-01.json` y `../Q-20261022-VF-ITERATION-37/scripts/q35_semantic_regrade.py`.
