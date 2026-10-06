# Strata IQ3_S / Swift 1.5 vs SOL: LC-H1

Evaluación comparativa del 2026-10-03 con el harness agentivo de LlamaCode. Los
recibos estructurados, hashes de entradas/modelos, configuración y run paths
están en [`artifacts/strata-swift-vs-sol-lch1-20261003`](../artifacts/strata-swift-vs-sol-lch1-20261003/).

## Protocolo

SOL, Swift 1.5 y ASTRA IQ3_S corrieron las mismas definiciones guardadas de
HE20, BCB8 e Intelligence Adversarial v1 con `agent-maximo`, seed 4242,
temperatura 0.1, thinking activado, `reasoningEffort=medium`, el mismo
`HarnessSpec` (`sha256:cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`),
un pase y hasta dos reparaciones automáticas por suite. Cada perfil usó el
ControlApi de LlamaCode y un directorio de perfiles de prueba aislado. SOL corrió
primero en vLLM y se detuvo antes de cargar Strata en ambas GPU.

Swift usó Strata 0.1.35, IQ3_XXS, contexto 131072, KV int8 con 32768 tokens
residentes, MTP4, expert cache automática, prefill automático y layer split
automático en las dos RTX 3090. Fue una corrida de texto (`vision=no`). ASTRA
usó el perfil Strata IQ3_S instalado, con su configuración de visión y las
mismas GPU. El adaptador de memoria de LlamaCode mantuvo los argumentos exactos
de Strata y no añadió la escalera `--fit` de llama.cpp. SOL fue Qwen3.8-27B
AutoRound INT4 en vLLM 0.27.1, TP2, MTP4 y KV fp8. Los detalles y hashes están
en el manifiesto.

La compuerta de LlamaCode exige HE0 antes de HE20 en perfiles nuevos. Swift pasó
HE0 1/1 tras una reparación en 17.1 s; ASTRA pasó 1/1 tras una reparación en
19.1 s. Esos prerrequisitos están registrados y excluidos de la comparación.
Cada suite principal corrió una vez por candidato: no mide variación entre
semillas.

La ficha de [Swift 1.5 en Hugging Face](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF)
atribuye al modelo 63.4% menos tokens de thinking y 1.8× de velocidad frente al
modelo base en sus propias evaluaciones xhigh. Esa es una medición de los
autores, no un pronóstico directo del tiempo total de un agente con herramientas.

## Resultados

| Suite | SOL: primera → final | Swift: primera → final | ASTRA IQ3_S: primera → final | Tiempo SOL / Swift / ASTRA | Llamadas SOL / Swift / ASTRA |
|---|---:|---:|---:|---:|---:|
| HumanEval/20 | 19/20 → 20/20 | 19/20 → 20/20 | 18/20 → 20/20 | 272.4 / 656.6 / 709.5 s | 42 / 40 / 40 |
| BigCodeBench-Hard/8 | 3/8 → 7/8 | 3/8 → 8/8 | 2/8 → 8/8 | 726.9 / 477.4 / 570.5 s | 40 / 38 / 45 |
| Intelligence Adversarial v1/10 | 7/10 → 10/10 | 7/10 → 10/10 | 7/10 → 10/10 | 534.9 / 1061.8 / 560.8 s | 52 / 73 / 32 |

En la suma directa de 38 tareas, SOL y Swift empataron con 29/38 en la primera
pasada; ASTRA obtuvo 27/38. Tras las reparaciones, Swift y ASTRA finalizaron
38/38 y SOL 37/38. ASTRA tardó 1840.8 s, 20% más que SOL y 16% menos que Swift.
Usó 117 llamadas de herramienta (115 correctas, 2 fallidas), frente a 134 de
SOL (131 correctas, 3 fallidas) y 151 de Swift (147 correctas, 4 fallidas).
BCB8 tuvo una llamada fallida en ASTRA, pero la suite terminó con 8/8 y no
expiró por timeout. Las cifras totales no ponderan dificultad ni categoría.

ASTRA y Swift empataron en resultado final en las tres suites. SOL fue más rápido
en HE20; Swift fue más rápido en BCB8. ASTRA fue casi tan rápido como SOL en
Adversarial (560.8 frente a 534.9 s) y bastante más rápido que Swift (1061.8 s).
La primera pasada de ASTRA fue dos tareas inferior a SOL y Swift, por lo que su
38/38 dependió de las reparaciones. ASTRA ejecutó menos llamadas totales que
ambos candidatos.

## Decisión sobre modelo y harness

No promoví Swift ni cambié sampling o concurrencia. La comparación controlada
muestra que ASTRA IQ3_S iguala a Swift con 38/38, una tarea por encima de SOL,
y tarda 20% más que SOL en el total. Su ventaja frente a Swift se concentra en
Adversarial; HE20 sigue siendo costoso. Los tres candidatos necesitaron
reparaciones para alcanzar sus puntuaciones finales. Una sola pasada por modelo
no basta para promover un candidato por una diferencia de una tarea. La
recomendación es conservar ASTRA IQ3_S como candidato actual y no elevar su
concurrencia: Strata atiende una secuencia a la vez en FIFO, y LlamaCode ya
respeta un slot.

Tampoco cambié la reserva de VRAM. Swift corrió sin visión y no incluyó la
reserva de 700 MiB de IQ3_S con encoder visual. La máquina sólo tiene dos RTX
3090 CUDA visibles, por lo que no se probó una GPU adicional para conducir la
pantalla.

La auditoría previa de Computer Use para IQ3_S sigue siendo la evidencia
relevante: el benchmark de decisiones de interfaz empató con SOL en 72/72 y
63/63 decisiones seguras, pero no ejecutaba acciones reales en escritorio. No
corrí comparación visual de Swift. Tampoco se midió Ingi-Charla (ASR/TTS/diálogo);
no se deben inferir resultados de esos subsistemas con estas suites.

## Correcciones de integración ASTRA

La revisión encontró que LlamaCode reconocía visión mediante `--mmproj`, pero
ASTRA obtiene el encoder de su archivo JSON de Strata. Se corrigió la detección
para leer la configuración y aceptar visión sólo si están `--vision`, el
binario del encoder y el archivo mmproj. Se añadieron regresiones para assets
presentes, flag ausente y mmproj faltante.

El benchmark adaptativo también intentaba reiniciar ASTRA con `--fit` y
`--fit-target`, opciones de llama.cpp que Strata rechaza. Se desactivó esa
escalera para el backend ASTRA: conserva la configuración exacta y registra la
política `exact-profile`. La nueva corrida verificó esta ruta. El gate Linux
pasó 77/77 tests.


## Repetición Flash-Next LC-H1 — 5 oct. 2026

Se repitieron en serie ASTRA IQ3_S base, ASTRA IQ3_S calibrado y Swift IQ3_XXS con el mismo `agent-maximo`, seed 4242, temp 0,1, reasoning medium, thinking activado, HarnessSpec y suites HE20/BCB8/Adversarial. Cada perfil pasó antes HE0 1/1 tras reparación. No hubo servidores simultáneos; al terminar se cerró el entorno de prueba y se restauraron la configuración y los perfiles temporales.

| Perfil | Corrida original: primera pasada → final | Repetición 5 oct.: primera pasada → final | Tiempo total original / repetición |
|---|---:|---:|---:|
| ASTRA IQ3_S base | 27/38 → 38/38 | 29/38 → 38/38 | 1840,8 / 2331,5 s |
| ASTRA IQ3_S calibrado (`pcie-frac .00`, `spec-min-p .70`) | 29/38 → 38/38 | 31/38 → 38/38 | 1857,0 / 1880,8 s |
| Swift 1.5 IQ3_XXS | 29/38 → 38/38 | 29/38 → 38/38 | 2195,8 / 2023,5 s |

Los tiempos de la repetición son HE20 + BCB8 + Adversarial, sin HE0. Los dos primeros perfiles ASTRA usan los mismos pesos IQ3_S; sólo cambia la configuración, y la variante calibrada cambia dos flags a la vez. La calibrada superó a la base en primera pasada en ambas corridas; frente a Swift, empató en la original (29/38) y quedó arriba en la repetición (31/38 vs. 29/38); su media observada de tiempo fue 1868,9 s frente a 2086,1 s para la base y 2109,7 s para Swift. La media tiene sólo dos corridas por perfil y la base mostró una variación temporal grande, así que no es una promesa de latencia. La repetición deja la calibrada como **recomendación provisional para el agente Flash-Next**; SOL Qwen3.8-27B sigue siendo la opción más rápida en LC-H1 histórico (37/38, 1534,2 s).

La primera ejecución BCB8 de ASTRA calibrado y Swift alcanzó el guard de 64.000 caracteres antes de usar herramientas; se repitió la suite y ambas finalizaron 8/8. Esos intentos de 24,8 y 22,7 s son fallos de infraestructura/harness, no scores. No se cambió el harness: el reintento automático recuperó el resultado y el fenómeno apareció sólo una vez por perfil.

**Decisión de conservación:** elegir ASTRA IQ3_S calibrado como perfil Flash-Next principal; conservar Swift IQ3_XXS si se valora el checkpoint compacto o la alternativa con mayor decode (aprox. 104–110 tok/s en estas corridas). El ASTRA base puede quedar como rollback de configuración, pero comparte el mismo checkpoint y borrarlo no recuperaría espacio de pesos. No recomiendo borrar ningún checkpoint por esta comparación: los tres completaron 38/38 y el peso Swift es una variante de cuantización distinta. La prueba no evalúa Computer Use real, Ingi-Charla, voz, visión comparativa ni perfiles Flash-Next que usan otros runtimes/cuants.

Recibos: [`results.json`](../artifacts/flashnext-repeat-20261005/results.json), [`manifest.json`](../artifacts/flashnext-repeat-20261005/manifest.json). Se conservan también los resultados completos del test daemon en `artifacts/flashnext-repeat-20261005/app-results-*.json`.

## Ablación de `pcie-frac` y `spec-min-p` — 5 oct. 2026

Para averiguar qué parte de la receta ASTRA calibrada `.00/.70` explica el resultado, corrí dos perfiles aislados contra la base `.25/.50`, cambiando un flag a la vez. Se mantuvieron ASTRA IQ3_S, Strata 0.1.35, LlamaCode Debug, `agent-maximo`, HarnessSpec, seed, sampling y suites. Resultados completos, fingerprints y configs: [informe y recibos de ablación](../artifacts/flashnext-ablation-20261005/report.md), [`results.json`](../artifacts/flashnext-ablation-20261005/results.json) y [`manifest.json`](../artifacts/flashnext-ablation-20261005/manifest.json).

| Variante | HE20 | BCB8 | ADV | Primera pasada principal | Tiempo válido |
|---|---:|---:|---:|---:|---:|
| Base repetida `.25/.50` | 19→20/20 | 3→8/8 | 7→10/10 | 29/38 | 2331,462 s |
| Sólo `pcie-frac=.00` | 19→20/20 | 2→8/8 tras retry | 6→10/10 | 27/38 | 1827,902 s |
| Sólo `spec-min-p=.70` | 19→20/20 | bloqueado dos veces antes de tools | 6→10/10 | 25/30 en suites válidas | 1280,413 s parcial |
| Calibrada `.00/.70` | 19→20/20 | 4→8/8 tras retry | 8→10/10 | 31/38 | 1880,833 s |

La ablación no prueba una mejora de calidad por cambiar un flag solo. `.00/.50` fue más rápido en una ejecución, pero bajó 2 puntos de primera pasada frente a base y su `n=1` no vence la variación histórica. `.25/.70` no mejoró HE20/ADV y BCB quedó bloqueado por el guard de salida antes de herramientas; ese estado se excluye como score. Por tanto, mantengo la receta combinada `.00/.70` como recomendación Flash-Next provisional según las dos repeticiones completas (31/38 y 29/38 vs. base 29/38 y 27/38; todas 38/38 final), sin atribuir causalidad a un flag ni cambiar el perfil productivo. Swift queda alternativa; ASTRA base, rollback. No hay evidencia para borrar pesos. La incidencia de guard BCB queda anotada para evaluarla por separado, sin relajar el harness en esta comparación. Ingi-Charla y Computer Use E2E no fueron probados.
