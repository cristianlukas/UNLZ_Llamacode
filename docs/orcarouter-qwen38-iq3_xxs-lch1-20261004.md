# Evaluación de OrcaRouter Qwen3.8 Flash Next Uncensored · IQ3_XXS

Fecha: 2026-10-04. Estado: **bloqueada para comparación completa LC-H1**.

## Artefactos y configuración

- Revisión Hugging Face: `e43d00f4e2b8b40b89f75e9adeb1045ac34c8acc`.
- Shard 1 SHA-256: `aaf57046943c6638480e8984835ce5ec29c486180ff71169d3c22c6929851b7b`.
- Shard 2 SHA-256: `a19cf9bbe87bce45f312ef11401c88b675f3784c927d02fa2272822229e6a224`.
- Directorio GGUF: `/media/cristian/7CFE1E0FFE1DC1F6/models/Orca-Qwen38-uncensored-IQ3_XXS`.
- Strata 0.1.38, pack IQ3_XXS: `/home/cristian/.cache/strata-dualgpu-eval-20261003/packs/orca-iq3_xxs`.
- Servidor texto-only, contexto 32K, KV int8, prefill 512, MTP/spec 4, mínimo de especulación 0.5 y caché de expertos auto. Smoke OpenAI HTTP respondió `42` a `19 + 23`.
- Perfil de harness temporal derivado del perfil ASTRA Strata; `agent-maximo`, thinking habilitado, `reasoningEffort=medium`, presupuesto 4096, temperatura 0.1 del harness, seed 4242, una pasada y dos reparaciones automáticas. Fingerprint de configuración: `1fcadee0b054242ff21099de581b27a93f1f629a705518b2151f269a963133e3`.

## Resultados

| Suite | Resultado | Interpretación |
|---|---:|---|
| HumanEval 1 (smoke/gate) | 1/1, aceptado tras 1 reparación, 76.1 s, 46.0 tok/s promedio | Válido como HE0 para este fingerprint. |
| HumanEval 20 | 8/20 artefactos aceptados; timeout duro a 1801.1 s | Inválido como pase HE20. El resultado oficial queda con `failed=true`, `timedOut=true`; no habilita BCB8. |
| BigCodeBench-Hard 8 | No ejecutada | Bloqueada por el gate LC-H1 tras HE20 incompleto. |
| Intelligence Adversarial v1 (10 tareas) | 0/10; fallo de infraestructura a 86.0 s | El agente agotó el límite preventivo de 64K caracteres antes de usar herramientas, incluso tras una reparación. Los graders que sí arrancaron además informaron imports ausentes en los workspaces. No es un score de calidad válido. |

El entorno de herramientas tampoco tiene el comando `python` (`run_shell` devuelve `exit=127`); `python3` sí existe. Esto agregó intentos de reparación en HumanEval. No se modificó el entorno ni la implementación de LlamaCode para mantener la configuración del harness estable.

## Archivos de resultados

- `/tmp/orca-eval/results/he0.json`
- `/tmp/orca-eval/results/he20.json`
- `/tmp/orca-eval/results/adv.json`
- Directorios de ejecución LlamaCode bajo `/home/cristian/.qttest/share/LlamaCode/LlamaCode/benchmark-runs/`, incluidos `HumanEval_20_tems__20261004_041036` y `Intelligence_Adversarial_v1_-_10_tareas_20261004_044204`.

Se detuvo el servidor al acabar. La RTX 3090 quedó sin procesos de cómputo del modelo. El perfil temporal y los ajustes ASTRA del daemon `.qttest` se retiraron/restauraron. No se modificó código de producción. Próxima acción: corregir el entorno del harness (`python`/`python3` y aislamiento de imports) y el límite de salida previa a herramientas; repetir HE20 con el mismo fingerprint, después BCB8 si HE20 pasa, y volver a correr ADV.

## Suplemento: Strata v0.1.39 y prefill helper (2026-10-04)

Se reusaron los dos shards completos verificados y el pack IQ3_XXS existente.
Strata v0.1.39 se compiló para CUDA 12.0/sm_86 con ggml `3cf03257`. El método
fue el harness administrado LlamaCode con `agent-maximo`, thinking activado,
reasoning medium/4096, temperatura 0.1, seed 4242 y hasta dos reparaciones.
Contexto 32K, KV int8, prefill 512, MTP/spec 4, `spec-min-p 0.5`, caché de
expertos auto y split automático por capas en las dos RTX 3090. El HarnessSpec
se mantuvo en `cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`.

| Variante | HE0 | HE20 | Lectura |
|---|---|---|---|
| Base, `STRATA_PREFILL_HELP=0` | 0/1 → **1/1**, 2 reparaciones, 46.088 s | 19/20 tareas aceptadas al corte de 1801.2 s; **score inválido** | No pasó el gate; BCB8 quedó bloqueado |
| Prefill helper, `STRATA_PREFILL_HELP=1` | 0/1 → **1/1**, 2 reparaciones, 44.083 s | 19/20 tareas aceptadas al corte de 1801.03 s; **score inválido** | No rescató HE20; dentro del margen de la base |

La única variable entre esas dos configuraciones fue `STRATA_PREFILL_HELP`; la
documentación de v0.1.39 limita su efecto al camino de prefill en layer split.
En esta batería no mejoró la duración ni permitió completar HE20, así que no hay
un score HE20 válido para juzgar calidad y BCB8/Adversarial no se ejecutaron.
El cambio no es transferible como arreglo probado. A diferencia del UD-Q4,
Orca no falló por un presupuesto residente de RAM insuficiente: su carga ya usa
split dual-GPU y alrededor de 49.8 GiB de expertos mapeados, mientras la
variación evaluada atacó el camino de prefill.

**Decisión:** conservar el checkpoint IQ3_XXS, pero mantener su evaluación
inconclusa. El timeout no prueba que el modelo sea malo ni que sea irrecuperable;
para retomarlo se necesita investigar el costo no generativo y la configuración
de ejecución del harness, no adjudicarle un score de calidad ni borrarlo.

Los recibos v0.1.39 están en
`/home/cristian/.codex/visualizations/2026/10/02/01a0fdac-e702-72e3-94fd-585859906215/lch1-data-q139/results/`
(`orca-v139-{baseline,prefill-help}-{he0,he20}.json`). Configs aisladas:
`/home/cristian/.cache/strata-0.1.39-q001/eval-q139/orca-v139-{base,prefill-help}.json`;
logs correspondientes en el directorio `logs/` del mismo árbol de evaluación.
