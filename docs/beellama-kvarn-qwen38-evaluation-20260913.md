# BeeLlama KVarN sobre Qwen3.8-27B — evaluación local

Fecha: 2026-09-13  
Equipo: Ubuntu, 2× RTX 3090, P2P disponible, 123 GiB RAM  
Modelo: `Qwen3.8-27B-UD-Q4_K_XL.gguf`  
Backend probado: BeeLlama preview v0.4.7, CUDA 12.4, SM86, `--split-mode layer`, `--tensor-split 1,1`.

## Qué aporta

KVarN es una representación de la caché KV, no una cuantización adicional de los pesos. BeeLlama expone tipos K/V independientes (`kvarn2` a `kvarn8`) y una cola de precisión opcional. La documentación del proyecto describe KVarN5/KVarN4 como un equilibrio de memoria y KVarN6/KVarN5 como una variante más conservadora:

- [Repositorio BeeLlama](https://github.com/Anbeeld/beellama.cpp)
- [Argumentos de KVarN](https://github.com/Anbeeld/beellama.cpp/blob/main/docs/beellama-args.md)
- [Matriz de características y presets](https://github.com/Anbeeld/beellama.cpp/blob/main/docs/beellama-features.md)
- [Preview v0.4.7 y binarios CUDA](https://github.com/Anbeeld/beellama.cpp/releases)

Para respetar la política de LlamaCode, la corrida promovida usa `kvarn5/kvarn5` y `--kv-tail-tokens 0`: no hay cola F16/BF16 ni un tipo de KV superior a Q8.

## Resultados de rendimiento

Control y candidato usaron el mismo GGUF, batch, GPUs y muestreo. Los números son del endpoint local, no del benchmark externo.

| Contexto asignado | KV Q8 prefill | KVarN5/KVarN5 prefill | Cambio | KV Q8 decode | KVarN5/KVarN5 decode |
|---:|---:|---:|---:|---:|---:|
| 8K | 297,0 tok/s | 543,8 tok/s | +83,1% | 36,17 tok/s | 36,81 tok/s |
| 32K | 296,1 tok/s | 521,8 tok/s | +76,2% | 36,25 tok/s | 36,17 tok/s |
| 64K | 291,4 tok/s | 515,3 tok/s | +76,8% | 36,34 tok/s | 35,58 tok/s |
| 131K | 297,1 tok/s | 511,9 tok/s | +72,3% | 36,58 tok/s | 35,99 tok/s |

KVarN6/KVarN5 también cargó correctamente en los cuatro tamaños: 35,97 / 36,08 / 36,01 / 35,80 tok/s de decode y 513,7 / 514,5 / 486,1 / 504,3 tok/s de prefill.

Hay una salvedad importante: en una prueba con una solicitud real de ~77.860 tokens, el prefill completo fue ~999,6 tok/s con Q8 y ~684,0 tok/s con KVarN5. En esa misma solicitud el decode fue 25,66 tok/s con Q8 y 27,33 tok/s con KVarN5. Por eso KVarN no se presenta como una mejora universal de prefill; su beneficio más claro aquí es el decode y la memoria al trabajar con contexto ya poblado.

## Calidad y estabilidad

| Prueba | KV Q8 | KVarN5/KVarN5 |
|---|---:|---:|
| Smoke de servidor en 8K/32K/64K/131K | 4/4 | 4/4 |
| JSON exacto sin markdown | OK | OK |
| Código Python con `--reasoning off` | salida válida | salida válida e idéntica |
| Tool call `read_file(path)` | validado en el control | `finish_reason=tool_calls`, argumentos JSON válidos |
| Needle a ~77,8K tokens | `KVARNSURVIVES` | `KVARNSURVIVES` |

Con `--reasoning on` y sólo 512/1024 tokens de salida, Qwen3.8 puede consumir todo el presupuesto pensando antes de emitir código. Esto ocurrió en ambos casos y no se clasificó como corrupción de KVarN. El perfil de LlamaCode queda con `--reasoning off` para que el benchmark sea reproducible; el harness puede seleccionar el nivel de razonamiento según la tarea.

## Comparación contra la tabla actual

| Perfil | Decode local | Contexto | Calidad/estabilidad | Decisión |
|---|---:|---:|---|---|
| SOL | 74 narrativo / 102 código | 262K validado | BCB 8/8, tool-use OK | Sigue siendo principal |
| BeeLlama KVarN5 | ~36 tok/s | 131K probado | Smoke, JSON, código, tool-call y needle OK; BCB completo pendiente | Agregado como experimental texto-only |
| QWEN38-Q8 | 22,1–41,3 tok/s según contexto | 262K validado | BCB pendiente | Sigue siendo la opción de fidelidad/contexto extremo |
| ASTRA | 16–41 tok/s | 196K | BCB no válido | No reemplazado |

KVarN no supera a SOL en decode ni en calidad BCB validada, así que no se cambia el principal. Sí aporta un perfil local reproducible para sesiones largas y quedó agregado como:

`[experimental] Qwen3.8 UD-Q4 · BeeLlama KVarN5 · 131k`

La variante KVarN6/KVarN5 queda como benchmark, no como perfil prioritario. La visión no se promovió: el modelo base tiene mmproj, pero esta campaña sólo validó texto y tool-use; no hay evidencia suficiente para afirmar que el camino KVarN + mmproj sea estable en nuestra máquina.

## Artefactos

- `artifacts/beellama-q8-8k-20260913.json`
- `artifacts/beellama-q8-long-20260913.json`
- `artifacts/beellama-kvarn5-8k-20260913.json`
- `artifacts/beellama-kvarn5-long-20260913.json`
- `artifacts/beellama-kvarn6-kvarn5-20260913.json`
- `artifacts/beellama-quality-q8-20260913.json`
- `artifacts/beellama-quality-kvarn5-20260913.json`
- `artifacts/beellama-quality-code-ab-20260913.json`
- `artifacts/beellama-tool-kvarn5-20260913.json`

El binario usado queda fuera del repositorio en `/home/cristian/.cache/llamacode/beellama-bin-v047-20260913/`; no se reemplazó el runtime de producción ni se modificó Windows.
