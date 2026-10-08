# ASTRA IQ3_S retest — 2026-10-08

## Veredicto

La configuración calibrada sí quedó reproducida con la **misma suite ULTRA y
la misma huella histórica**. La primera repetición dio 11/13, así que el 12/13
histórico no garantizaba un resultado estable. Subir sólo el presupuesto de
razonamiento de 4096 a 8192 tampoco lo corrigió: dio 11/13. En cambio, permitir
un tercer turno de reparación después de fallar aceptación cerró **13/13 en dos
corridas independientes**, ambas con el perfil de 8192 y la misma suite.

Se deja productivo el límite general del benchmark en tres reparaciones
acotadas: sólo consume turnos extra si siguen fallando criterios duros de
aceptación; los scores parciales no disparan el camino. El cambio no altera los
pesos ni garantiza 13/13 para toda tarea; la evidencia se limita a esta suite y
perfil.

## Resultados

| Perfil/configuración | Reparaciones | Resultado final | Tiempo | Fingerprint del perfil | Huella de suite |
|---|---:|---:|---:|---|---|
| Histórico calibrado, registro original (4096) | 2 | 12/13 | 177,390 s | `0e3871fab20b8eb2f5dc4cd310d099975604a3192d4e9d6bc2d9aaddc17a2beb` | `sha256:cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef` |
| Repetición exacta calibrada (4096) | 2 | 11/13 | 233,478 s | `0e3871fab20b8eb2f5dc4cd310d099975604a3192d4e9d6bc2d9aaddc17a2beb` | misma |
| Prueba aislada, reasoning 8192, tope 2 | 2 | 11/13 | 201,421 s | `0b766f83c9f065b75b81f3652952ffbac497888791907c5effa5d8150ae488a2` | misma |
| Prueba aislada, reasoning 8192, tope 3 — repetición A | 3 | **13/13** | 287,296 s | `0b766f83c9f065b75b81f3652952ffbac497888791907c5effa5d8150ae488a2` | misma |
| Prueba aislada, reasoning 8192, tope 3 — repetición B | 3 | **13/13** | 333,456 s | `0b766f83c9f065b75b81f3652952ffbac497888791907c5effa5d8150ae488a2` | misma |

Las cuatro corridas nuevas usaron ASTRA Strata 0.1.35, config calibrada
`strata-iq3_s-calibrated-retest-20261006.json`, MTP/spec 4, `spec-min-p 0.70`,
contexto 131072, KV INT8, `agent-maximo`, thinking habilitado, temperatura 0.1,
seed 4242 y la suite `qwen38_taskflow_ultra_ast_vs_sol_20261006`. Las dos
variantes de 8192 sólo difieren en el límite de turnos de reparación. Sus
prompts, backend, modelo, config Strata, semilla, temperatura y suite fueron
idénticos.

La corrida inicial con tope 2 falló pruebas de concurrencia/recurrencia; la
segunda, también con tope 2, falló `ready_tasks`, recurrencia y conteo de
bloqueadas. Las dos corridas con tope 3 repararon esos fallos y superaron los
13 criterios. La variación de fallos entre corridas explica por qué el 12/13
histórico aislado no bastaba para identificar una opción de modelo distinta.

## Recibos

- `astra_historical_profile_ultra.json`: repetición 4096, 11/13.
- `astra_r8192_profile_ultra.json`: reasoning 8192, tope 2, 11/13.
- `astra_r8192_three_repairs_ultra.json`: reasoning 8192, tope 3, 13/13.
- `astra_r8192_three_repairs_ultra_repeat.json`: repetición independiente, 13/13.
- `benchmark-suite.json`: copia de la suite usada.
- `manifest.json`: origen de perfiles, IDs y diferencia aislada de la variante.

Una primera corrida con tres reparaciones usó por error el config Strata por
defecto (`spec-min-p 0.5`); se canceló antes de terminar y no entra en la tabla.
La repetición válida confirmó explícitamente el config calibrado y
`spec-min-p 0.70` en el comando del servidor.

## Comparación alineada con SOL AutoRound INT4 — 2026-10-08

Se midió SOL con la misma TaskFlow ULTRA (`sha256:cca4645b…`), agente
`agent-maximo`, reasoning budget 8192, seed 4242, temperatura 0,1 y el mismo
límite de tres reparaciones. ASTRA conserva la configuración calibrada y sus
recibos de dos corridas independientes. El fingerprint de perfil necesariamente
difiere entre modelos/backend; no se cambió la suite.

| Perfil | Corridas válidas | Calidad | Tiempo | Lectura |
|---|---:|---:|---:|---|
| ASTRA IQ3_S calibrado, reasoning 8192, 3 reparaciones | 2 | **13/13 en ambas** | 287,296 s y 333,456 s; media 310,376 s | Terminó los 13 criterios de la suite en las dos corridas. |
| SOL AutoRound INT4, reasoning 8192, 3 reparaciones | 1 | 7/13 | 138,365 s | Fue 2,24× más rápido en la única corrida válida (42,90 tok/s; primera llamada a 20,967 s), pero dejó sin crear `cli.py`, `main.py` y el test solicitado; fallaron compilación, unittest y self-test. |

**Veredicto acotado:** en esta tarea de coding ULTRA, ASTRA es el candidato más
fiable por calidad de entrega (2/2 completas), mientras que SOL fue más rápido
pero su única corrida válida sólo llegó a 7/13. La muestra de SOL es pequeña;
esto no demuestra superioridad general de inteligencia ni justifica descartar
SOL para otros usos.

Además hubo cuatro intentos de SOL sin una respuesta de herramienta válida. No
son scores de calidad y se excluyen del denominador. En los logs de vLLM 0.27.1,
MTP n=4 terminó en `CUDA error: device-side assert triggered` dentro de
`EngineCore.sample_tokens`, devolvió HTTP 500 y el contenedor salió con 137 sin
marcar OOM. Otro intento empezó la suite mientras el modelo aún cargaba; el
health check seguía recibiendo `Connection closed` y el server quedó listo recién
después de que la suite ya había concluido. Se repitió con
`ASYNC_SCHED=off` (`--no-async-scheduling`), pero MTP siguió cayéndose. Por eso
registramos esto como una limitación de estabilidad del backend MTP de SOL, no
como baja calidad del modelo.

Se intentó una variante aislada sin MTP, pero el nuevo perfil/backend temporal
no quedó visible/resoluble por el launcher y no llegó a iniciar un servidor; no
hay resultado que contar. No se modificó el perfil productivo. Para una prueba
sin MTP válida habría que reparar ese alta temporal antes de volver a medir.

Recibos adicionales:
- `sol/sol_r8192_three_repairs_ultra.json`: la única corrida SOL válida, 7/13.
- `sol/operational-failures.json`: cuatro intentos operativos inválidos,
  configuración, diagnóstico y clasificación; los recibos crudos permanecen en
  el directorio temporal de pruebas del host.
- `sol/vllm-mtp-crash-excerpt.log`: líneas durables de evidencia del CUDA assert,
  EngineCore fatal y respuestas HTTP 500.
