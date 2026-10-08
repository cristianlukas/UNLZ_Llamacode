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
