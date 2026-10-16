# Resultados — Q-20261016-FLASHNEXT-RESUME

**Estado: bloqueada por preflight de swap; 2 de 3 pares A/B completos.** Se
continuó `Q-20261016-FLASHNEXT-FOLLOWUP` con el mismo Qwen3.8 Flash-Next
UD-Q4_K_XL, Strata 0.1.41, dos RTX 3090, split 18/30, corpus, semillas y
configuraciones. Se conservó el par 1 y se completó el par 2, sin cambios de
producto ni promoción del flag `--trim-stage-weights`.

## Server Speed v1: A/B con y sin `--trim-stage-weights`

La prueba fue HTTP directo al servidor Strata, con ocho categorías cold/warm,
una solicitud a la vez, temperatura 0, top-p 1 y seed 424242. El corpus es
`assets/benchmarks/server_speed_v1.json`, SHA-256
`4bad8a5d24ce11096eb9634f7d03f24b83734c3f454031efb28d5fa259c996e9`.
Cada brazo completo tiene 16 muestras. Es un test de rendimiento del servidor,
no una sesión de la aplicación LlamaCode ni una evaluación de calidad.

| Par | Orden | A decode | B decode | Δ decode | Δ prefill | Δ TTFT | Δ total | Hashes distintos |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | A/B | 65,35 tok/s | 63,61 tok/s | −2,7% | −27,5% | +48,5% | +21,4% | 13/16 |
| 2 | B/A | 65,20 tok/s | 70,26 tok/s | +7,8% | +6,9% | −6,2% | −6,7% | 12/16 |

En el par 1, B dio 64,11 tok/s de prefill, TTFT 1.628 ms y latencia total
4.086 ms; en el par 2, B dio 78,33 tok/s, 1.333 ms y 3.623 ms. Los signos se
invierten entre pares, así que la evidencia disponible no muestra una mejora
estable y no justifica promover trim. Tampoco se debe interpretar el cambio de
hash como una puntuación de calidad.

Los cuatro brazos completos terminaron con 16/16 muestras, cero flags de
fallo, hashes de respuesta y configuración íntegros, y puerto 8350 libre. El
intento inicial de pair 1 con Python del sistema falló antes de servir el
modelo y se conserva separado; no cuenta como brazo ni como muestra. La
validación en frío está en
[`receipts/offline-validation.json`](receipts/offline-validation.json).

Pair 3-A quedó detenido en preflight, con cero muestras, antes de cargar
Strata. El recibo del intento midió 0,792 GiB libres; el preflight de cierre,
tras esperar 60 s, midió 0,795 GiB frente al gate de 0,95 GiB. En ese último
preflight había 111,27 GiB de MemAvailable, PSI avg10 0, OOM 0, ninguna app de
cómputo en las GPUs y todos los puertos de prueba libres. No se alteró el swap
ni se interrumpió ningún proceso. Ver
[`receipts/preflight-blocked-current.json`](receipts/preflight-blocked-current.json).

## Otras pruebas del programa

| Área | Estado | Resultado |
|---|---|---|
| Coding/agentes, ADV, TaskFlow y tool-eval Q4 | Reutilizadas | Recibos válidos existentes; no se repitieron. TaskFlow registró 13/13 tras dos reparaciones. |
| Context retrieval Q4 a 262K | No iniciado | Gate de recursos no pasó. No se envió prompt. |
| Visión Q4 | No iniciada | mmproj y encoder ya inspeccionados, pero no se envió imagen. |
| Computer Usage, réplica base ASTRA y Q4 | No iniciado | Sin arranques de modelo ni acciones GUI nuevas; el plan usa Xvfb privado. |
| Ingi-Charla/audio | No aplicable a esta corrida | No había endpoint local ASR/TTS verificado; no se simuló audio con texto. |

La comparación del material publicado usa tres RTX 2080 Ti modificadas de 22 GB,
Strata 0.1.38/0.1.39 y otros quant/configuraciones; sus cifras no son
comparables directamente con esta máquina de dos RTX 3090 y Strata 0.1.41.

## Validaciones realizadas y reanudación

Pasaron `py_compile` del runner resumible y una validación offline de los
recibos: 64/64 muestras de los cuatro brazos completos, unicidad de sampleId,
hash de respuesta/configuración y liberación del puerto. No se modificó C++,
QML ni el producto, por lo que no se ejecutaron builds ni tests del producto.

Reanudar en una tarea nueva cuando un preflight fresco mida SwapFree ≥0,95 GiB,
MemAvailable ≥32 GiB, GPUs sin inferencia ajena y los puertos libres. Conservar
los pares 1 y 2; seguir por pair 3-A/B, luego ejecutar contexto, visión y CU en
serie, cada uno con preflight independiente. No limpiar swap ni detener
procesos ajenos. Plan completo:
[`PLAN.md`](PLAN.md). La corrida original y sus recibos están en
[`Q-20261016-FLASHNEXT-FOLLOWUP`](../Q-20261016-FLASHNEXT-FOLLOWUP/RESULTS.md).
