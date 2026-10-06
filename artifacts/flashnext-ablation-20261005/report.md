# Ablación de ASTRA Flash-Next: `pcie-frac` y `spec-min-p`

Fecha: 5 oct. 2026 · Tarea `Q-20261005-FLASHNEXT-ISOLATE`.

## Protocolo

LlamaCode Debug actual, Strata 0.1.35, ASTRA Qwen3.8-Flash-Next IQ3_S, una configuración activa por vez en dos RTX 3090. LlamaCode test daemon aislado; `agent-maximo`, seed 4242, temperatura 0,1, thinking ON, reasoning medium, HarnessSpec `cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`. Se mantuvieron pesos, engine, harness y suites; las variantes de ablación cambian un único flag respecto de base `.25/.50`. Las ejecuciones son `n=1` por variante y sirven para orientar, no para inferencia estadística.

## Resultados

| ASTRA IQ3_S | Flags | HE20 primera→final | BCB8 primera→final | ADV primera→final | Primera pasada principal | Tiempo suites principales |
|---|---|---:|---:|---:|---:|---:|
| Base, repetición | `.25 / .50` | 19/20→20/20 | 3/8→8/8 | 7/10→10/10 | 29/38 | 2331,462 s |
| Sólo PCIe reducido | `.00 / .50` | 19/20→20/20 | 2/8→8/8 tras retry; primer intento fue guardia pre-tool | 6/10→10/10 | 27/38 | 1827,902 s |
| Sólo mínimo de draft elevado | `.25 / .70` | 19/20→20/20 | dos intentos bloqueados antes de tool por guardia de salida | 6/10→10/10 | 25/30 en suites válidas; BCB no comparable | 1280,413 s en HE20+ADV; incompleto |
| Calibrada combinada, repetición | `.00 / .70` | 19/20→20/20 | 4/8→8/8 tras retry | 8/10→10/10 | 31/38 | 1880,833 s |

HE0 pasó 1/1 en 19,068 s para `.00/.50` y 1/1 en 19,070 s para `.25/.70`. Se excluye HE0 de las sumas principales. Los dos BCB de `.25/.70` no son scores de calidad: LlamaCode guardó `failureKind=infrastructure`, `elapsedSec≈25 s`, mensaje **“El agente produjo demasiado texto antes de usar herramientas.”** y cero reparaciones. En `.00/.50`, el intento inicial tuvo la misma guardia; el reintento directo sí ejecutó 8 casos y pasó 8/8 tras reparar.

## Veredicto

No se demuestra que un flag aislado mejore calidad. Bajar `pcie-frac` a `.00` produjo en una sola ronda un total principal 2/38 puntos menor que la base repetida y fue 21,6% más rápido; la velocidad es prometedora, pero no compensa por sí sola la caída de primera pasada ni la variabilidad observada. Subir sólo `spec-min-p` a `.70` no mejoró HE20 ni ADV, y BCB quedó bloqueado por la guardia; no hay caso para desplegar ese cambio aislado.

La receta combinada `.00/.70` sigue siendo el perfil Flash-Next recomendado provisionalmente porque sus dos corridas completas repitieron 38/38 final y mejoraron la primera pasada frente a base (29/38 y 31/38 vs. 27/38 y 29/38). Sin embargo, no atribuyo esa mejora a uno de los flags y no prometo una reducción de latencia: las dos corridas base variaron mucho y esta ablación tiene sólo una observación por flag.

**Acción:** no cambié producción, harness ni pesos. Mantener ASTRA IQ3_S calibrado `.00/.70` como perfil principal Flash-Next, Swift IQ3_XXS como alternativa y ASTRA base como rollback de configuración. No borrar checkpoints por estos resultados: comparten los pesos ASTRA y la comparación no prueba inferioridad de Swift. La guardia BCB merece un estudio separado del harness, pero no se relajó aquí para evitar cambiar una variable adicional.

No se evaluaron Ingi-Charla ni Computer Use E2E. Recibos completos de las dos variantes, configs y manifiesto en este directorio; repetición base/calibrada en `../flashnext-repeat-20261005/`.

## Estado de restauración y cierre

La comparación se ejecutó con QSettings aislado. Al cierre, `/home/cristian/.qttest/config/LlamaCode/LlamaCode.conf` coincide byte a byte con `artifacts/flashnext-repeat-20261005/LlamaCode.conf.before`, y el árbol de perfiles aislados coincide byte a byte con su respaldo. La configuración canónica del usuario en `~/.config/LlamaCode/LlamaCode.conf` no fue el target de la prueba y no se sobrescribió. La comprobación final encontró procesos de usuario Qwen3.5-9B en los puertos 8033/8081 y Gemma en 8083; se dejaron intactos y no se hicieron más cargas ni benchmarks.
