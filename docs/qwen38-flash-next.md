# Qwen3.8-Flash-Next en LlamaCode

Modelo MoE de 125B (arquitectura Qwen4) con 262k de contexto. Lo particular no es
el tamano sino que una parte grande del modelo son tensores **Ngram / PLE**: una
lookup table de acceso aleatorio, no compute.

## Perfil implementado para la campaña 2026-09

El catálogo ahora expone el candidato manual
`sys-48-qwen38-flash-next-q2kxl-8k` para 2x RTX 3090 + RAM abundante. La base
es deliberadamente conservadora: `split-mode layer`, `--n-cpu-moe 40`, KV
`q8_0`, contexto 8k, sin MTP, visión ni overrides de Ngram. La variante
`cache188` mide la caché de expertos por separado y la de 131k sólo se habilita
después de pasar HE0.

Esto corrige una premisa importante de recetas anteriores: 48 GB de VRAM no
alcanzan para hacer residente un Flash-Next Q4 completo. Los GGUF multi-shard
deben dimensionarse con el total de sus shards y con la RAM necesaria para el
MoE/Ngram; `--n-gpu-layers 999` no implica que toda la red quede en VRAM. Q2/IQ2
puede reducir el archivo, pero no se promueve automáticamente: primero hay que
medir calidad, estabilidad y uso real de memoria contra SOL.

### Matriz Q2 medida en 2x RTX 3090

La matriz ejecutada el 2026-09-23 usa el GGUF `UD-Q2_K_XL`, `qwen4exp
c6a9e5c9`, KV `q8_0`, batch/ubatch 512 y un único slot. Para 16k y 32k se
usó `--n-cpu-moe 4`; para 64k, 128k y 256k se usó `--n-cpu-moe 40`. La
velocidad de decode se midió con el mismo prompt fijo de 157 tokens y una
salida de 117 tokens efectivos, por lo que sirve para comparar las
configuraciones, no para simular el prefill de un prompt que ya ocupa todo el
contexto.

| contexto reservado | n-cpu-moe | VRAM usada GPU0/GPU1 | prefill del prompt corto | decode |
|---:|---:|---:|---:|---:|
| 16k | 4 | 23.0 / 23.6 GiB | 314.60 tok/s | 56.19 tok/s |
| 32k | 4 | 23.2 / 23.8 GiB | 352.97 tok/s | 57.15 tok/s |
| 64k | 40 | 4.3 / 10.7 GiB | 105.89 tok/s | 32.19 tok/s |
| 128k | 40 | 5.0 / 11.7 GiB | 106.81 tok/s | 31.77 tok/s |
| 256k | 40 | 6.9 / 13.6 GiB | 102.74 tok/s | 30.96 tok/s |

El perfil `n-cpu-moe 4` no pudo reservar 64k: faltaron aproximadamente 542
MiB en la GPU1. Por eso los perfiles largos devuelven expertos a RAM. El
recibo reproducible está en
`artifacts/qwen38-q2-context-matrix-20260923.json`.

También se probó el punto intermedio `n-cpu-moe 8`: sin ajuste deja sólo 287
MiB libres en la GPU1. Con `--split-mode layer --tensor-split 1.2,1` se
balancea en aproximadamente 21.5/21.9 GiB por GPU y logra 53.35 tok/s, con
2.7/2.2 GiB libres. A 64k no consigue reservar los buffers de cómputo.
Con `--tensor-split 1.22,1` también sostiene 128k: aproximadamente 22.5/23.4
GiB usados y 53.68 tok/s; es el menor `n-cpu-moe` probado que llega a ese
contexto. `n-cpu-moe 4` y `6` fallan al reservar los buffers de 128k.
`n-cpu-moe 12` produjo acceso ilegal CUDA durante el warmup, incluso con batch
256/ubatch 128, así que no se habilita. El detalle está en
`artifacts/qwen38-q2-ncpu-moe-sweep-20260923.json`.

### Búsqueda de 256k

Para 256k, el reparto óptimo cambia porque el KV consume más memoria. La
combinación mínima estable encontrada fue `--n-cpu-moe 12 --tensor-split 1.4,1`:

| n-cpu-moe | tensor-split | estado | decode | VRAM libre G0/G1 |
|---:|---:|---|---:|---:|
| 40 | 1,1 | estable conservador | 30.96 tok/s | 17.2 / 10.5 GiB |
| 32 | 1.22,1 | estable | 34.76 tok/s | 17.1 / 3.4 GiB |
| 28 | 1.5,1 | estable | 36.86 tok/s | 14.7 / 2.1 GiB |
| 24 | 1.8,1 | estable | 38.58 tok/s | 8.7 / 4.4 GiB |
| 20 | 1.8,1 | estable | 40.69 tok/s | 5.1 / 4.4 GiB |
| 16 | 1.8,1 | estable | 43.89 tok/s | 1.4 / 4.4 GiB |
| 12 | 1.4,1 | estable balanceado | **47.14 tok/s** | **1.1 / 1.1 GiB** |

`n-cpu-moe 10` no reserva los buffers de 256k. `n-cpu-moe 12` con
`tensor-split 1.5,1` llega a responder, pero deja sólo 111 MiB libres en GPU0
y no es seguro. Por eso el perfil recomendado es 12/1.4,1; el 40/1,1 queda
como fallback conservador.

Esta receta queda publicada en el catálogo con el alias operativo **ASTRA**;
el ID técnico permanece
`sys-bench-48-qwen38-flash-next-q2kxl-long-256k-balanced-moe12` para conservar
la trazabilidad de benchmarks y scripts.

**Estado actual (2026-09-24):** los tres shards físicos de esta receta fueron
movidos a la Papelera de D después de la comparación agentiva contra SOL. El
perfil y sus resultados se conservan sólo como referencia histórica y no debe
usarse ni descargarse automáticamente sin restaurar los pesos.

### Validación LC-H1 exacta y recuperación a 256K

El 2026-09-23 se ejecutó la receta exacta de ASTRA con `n-cpu-moe 12`,
`tensor-split 1.4,1`, contexto `262144`, KV `q8_0`, batch/ubatch `512/512`,
un slot y el mismo harness agentivo LC-H1:

| Etapa | Resultado | Tool calls | Velocidad media | Estado |
|---|---:|---:|---:|---|
| HE0 | **1/1** | 1/1 exitoso | 39,16 TG | Válido |
| HE20 | **20/20** | 44/44 exitosos | 32,16 TG | Válido |
| BCB | **8/8** | 41/42 exitosos | 32,15 TG | Válido; un tool call falló y la reparación alcanzó el score completo |

La campaña totalizó 87 tool calls, 86 exitosos, y no tuvo timeouts ni fallos de
infraestructura. Esta evidencia ya es comparable dentro de LC-H1 con otros
perfiles agentivos, pero no constituye todavía un A/B directo contra SOL con
los mismos prompts y la misma ventana de ejecución.

La prueba de recuperación de contexto nominal 256K también pasó **4/4**:

| Needle/passkey | Exacta | Latencia | Prefill | Decode |
|---:|---:|---:|---:|---:|
| 25% | Sí | 379,1 s | 425,78 tok/s | 16,54 tok/s |
| 50% | Sí | 369,9 s | 437,41 tok/s | 16,90 tok/s |
| 75% | Sí | 378,4 s | 427,39 tok/s | 17,02 tok/s |
| 95% | Sí | 377,4 s | 427,72 tok/s | 17,03 tok/s |

El probe usó un prompt efectivo de aproximadamente 161K tokens dentro de una
ventana reservada de 256K; por eso esta prueba certifica recuperación profunda
en la receta de 256K, pero no debe describirse como cuatro prompts de 262144
tokens exactos. El recibo reproducible está en
`artifacts/astra-lc-h1-256k-retrieval-20260923.json` y la configuración en
`artifacts/astra-lc-h1-256k-retrieval-config-20260923.json`.

La campaña reproducible es
`tools/run_qwen38_flash_next_campaign.ps1`. Ejecuta por contexto una base
`layer`, una variante `cache188` y, opcionalmente, una corrida diagnóstica
`row`; guarda logs, snapshots de `nvidia-smi`, probes deterministas y un
manifiesto JSON. La promoción exige HE0, HE20 y BCB con el mismo runtime,
sampling y harness que SOL.

Ejemplo Windows:

```powershell
pwsh -NoProfile -File .\tools\run_qwen38_flash_next_campaign.ps1 `
  -Server C:\llama\llama-server.exe `
  -Model D:\models\Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf `
  -Contexts 8192,32768 -Passes 3
```

En Ubuntu se puede usar el wrapper equivalente:

```bash
./tools/run_qwen38_flash_next_campaign.sh \
  -Server /opt/llama/bin/llama-server \
  -Model /models/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf \
  -Contexts 8192,32768 -Passes 3
```

El scanner de GGUF también agrega ahora el tamaño y la metadata de todos los
shards, incluyendo shards de metadata sin tensores. `ngramElements` queda como
dato diagnóstico: no se interpreta como ahorro de VRAM en CUDA/Flash-Next.

## Por que rompe los supuestos del proyecto

1. **`size_total` deja de predecir la VRAM necesaria.** El peso residente y el
   peso total divergen: unsloth reporta que el 1-bit corre en 75 GB de RAM *sin
   VRAM*. El calculo de tier de `EffectiveProfileBuilder` asume archivo ~= VRAM.
2. **RAM vs VRAM importa mucho menos que en un MoE normal.** Los Ngram se pueden
   dejar en RAM o incluso en SSD con mmap y la perdida de t/s es chica.
3. **No se cuantizan agresivamente.** Minimo 4-bit, porque el acceso aleatorio se
   degrada mal. Por eso el 1-bit pesa 75 GB en vez de los ~30 GB que uno
   esperaria de 125B a 1 bpw.

## Engine

El soporte de la arquitectura ya fue mergeado en mainline mediante el PR
[ggml-org/llama.cpp#27742](https://github.com/ggml-org/llama.cpp/pull/27742).
La build local que se uso en los ensayos historicos sigue siendo una build
anterior del arbol experimental (`ef6876693`), por lo que no representa
automaticamente todo lo que hoy ofrece mainline.

El catalogo tiene la entry `qwen38-next` (`src/core/EngineCatalog.cpp`), que
compila desde ese pull request. Para eso hubo que agregar soporte de **PR refs**:
`git clone --branch pull/27742/head` no funciona (un PR no es una rama), asi que
el script de build detecta la forma `pull/<N>/head` y hace
`git fetch origin pull/<N>/head:pr-<N>` + checkout.

- `EngineCatalog::parsePullRequestRef()` / `localBranchForRef()`
- Tests: `pullRequestRefIsParsedAsBranch`, `qwen38NextEntryBuildsFromPullRequest`
  en `tests/test_engine_catalog.cpp`.

El arbol del PR vive en `tools/llama.cpp-qwen38-next/` (slug distinto del
llama.cpp oficial, para no pisarse).

### Runtime CUDA de Ubuntu

Ubuntu registra además una build experimental de la rama de replicación
`flashnext-2x3090`, compilada con CUDA 12.0, NCCL y `compute_86` para las dos RTX
3090. El perfil compartido conserva sus argumentos Windows, pero declara una
lista `platformArgs.linux` con expertos `CUDA_Host`, `--numa distribute`, KV f16
y `--moe-expert-cache 188`; LlamaCode sólo aplica esa lista al ejecutarse en
Linux. Esto permite probar la optimización sin romper la build Windows.

En este equipo y con el GGUF UD-Q4_K_XL real (103.68 GB), una A/B a 16K de
contexto y 256 tokens pasó de 16.45 tok/s sin caché a 36.04 tok/s con la caché
MoE. Es una prueba de rendimiento local; la rama sigue siendo experimental.
El cabezal MTP compartido Q8_0 ya está descargado y validado, pero la rama
experimental falla con acceso ilegal CUDA al combinar `draft-mtp` y
expert-cache; MTP sin cache fue estable, aunque más lento que cache188, por lo
que no se activa en el perfil usable.

En una comparación controlada con el mismo prompt, `--batch-size 512`
alcanzó 45.22 tok/s frente a 43.09 tok/s con 4096. El perfil Ubuntu conserva
512/512. P2 funciona, pero NVLink aparece inactivo en `nvidia-smi` y la
topología es PHB, así que NCCL no puede aprovechar NVLink en este equipo.

N-gram `M=7` fue estable, pero dio 36.97 tok/s en el mismo prompt, por debajo
de cache188 sin speculative. `--split-mode tensor --tensor-split 1,1` tampoco
es una alternativa para este modelo: la build informa que tensor split no está
implementado para la arquitectura `qwen4exp`.

## Eleccion de quant

KLD publicado por unsloth (top-1% = cuanto coincide con BF16):

| quant | GB | mean KLD | top-1 % |
|---|---|---|---|
| UD-Q4_K_XL | 111.3 | 0.0447 | 93.5 |
| UD-IQ4_XS | 93.7 | 0.0792 | 91.1 |
| UD-Q3_K_XL | 90 | 0.0997 | 90.4 |
| UD-IQ3_XXS | 82 | 0.1565 | 87.6 |
| UD-Q2_K_XL | 78.9 | 0.2133 | 85.2 |
| UD-IQ1_M | 74.5 | 0.3022 | 82.4 |
| UD-IQ1_S | 72.5 | 0.3751 | 80.2 |

Los requisitos se cuentan como **RAM + VRAM sumadas**. En la maquina de
desarrollo (2x RTX 3090 = 48 GB VRAM + 127 GB RAM = 175 GB) entra UD-Q4_K_XL con
aire para KV cache; el salto de IQ4_XS a Q4_K_XL casi duplica la fidelidad por
17.6 GB, y es el mejor de la tabla.

## Sampling

Son dos perfiles distintos, no uno con variantes:

| | thinking | instruct |
|---|---|---|
| temperature | 1.0 | 0.7 |
| top_p | 0.95 | 0.80 |
| top_k | 20 | 20 |
| min_p | 0.0 | 0.0 |
| presence_penalty | 0.0 | 1.5 |

`reasoning_effort` (`xhigh` por defecto, `medium`, `low`, `none`) va por
`--chat-template-kwargs`. En PowerShell hay que escapar las comillas:

```
--chat-template-kwargs "{\"reasoning_effort\":\"medium\"}"
```

## Benchmark

`tools/benchmark_qwen38_flash_next.ps1` barre las tres colocaciones de los Ngram
(VRAM / RAM / SSD+mmap) contra los dos perfiles de sampling, y reporta t/s y
accuracy. El regex de tensores Ngram se **deriva del GGUF**, no se adivina.

```
powershell -File tools\benchmark_qwen38_flash_next.ps1 -Passes 2 -Output run.json
```

## Estado real: el engine produce salida corrupta

Lo mas importante que salio de correrlo: **el PR 27742 genera texto corrupto de
forma no reproducible**. Se le caen digitos y caracteres:

```
"2^100 mod 125"   ->  el modelo razona sobre "2^18 mod "
"coprime"         ->  "copr"
"doesn't"         ->  "doesn"
"Count: 121 122 123 ..."  ->  "1211 1211 1212" en vez de "130 131 132"
```

Con `temperature 0` y `seed` fijo la salida deberia ser identica siempre. No lo
es: cambia entre instancias del server y entre modos de prefill.

### Lo que SI se pudo aislar

| condicion | resultado |
|---|---|
| 10 peticiones identicas, mismo estado | 10/10 identicas (estable DENTRO de un estado) |
| `cache_prompt=false` (prefill fresco) | corrupto, consistente |
| `cache_prompt=true` (prefijo cacheado) | correcto, consistente |
| `--ubatch-size 1` | arregla algunos prompts, no todos |

O sea: la generacion desde un prefijo ya cacheado esta bien; el **prefill** es
donde se rompe. Encaja con el commit del propio PR ("hold the qwen4exp indexer
cache in a new llama_memory_hybrid_idx"): hay un cache nuevo especifico de esta
arquitectura.

### Caracterizado: se caen tokens de UN caracter

Probe con 5 continuaciones inequivocas x 3 repeticiones x 4 tamanos de ubatch
(`tools/` no lo incluye; fue un harness descartable). Resultado:

| tarea | prompt | ubatch1 | ubatch32 | ubatch128 | default |
|---|---|---|---|---|---|
| letters | `A B C D E F G H I` | 3/3 | 3/3 | 3/3 | 3/3 |
| evens | `2 4 6 8 10 12 14 16` | 0/3 | 3/3 | 3/3 | 3/3 |
| count | `121 122 ... 129` | 3/3 | 0/3 | 1/3 | 1/3 |
| numbers | `55 56 ... 63` | 0/3 | 0/3 | 0/3 | 0/3 |
| days | `Monday Tuesday ...` | 0/3 | 0/3 | 0/3 | 0/3 |

**`letters` es el unico que sale perfecto siempre.** Y las fallas tienen forma:

```
"55 56 57 ... 63"   -> " 6 6 6 6 6 6"      (el 2do digito de cada numero, ausente)
"2 4 6 ... 16"      -> " 1820222426283"    (los numeros correctos, SIN espacios)
```

El tokenizer NO es el culpable: `/tokenize` + `/detokenize` da round-trip
perfecto en 8/8 casos, incluidos `"Count: 121 122 123"` y `"2^100 mod 125"`.

Lo que si muestra el tokenizer es la clave: `"55 56 57"` son **8 tokens** -- los
digitos van de a uno. `"J K L M"` son 4. O sea que el modelo genera digito por
digito, y lo que se pierde son **tokens de un solo caracter** (digitos sueltos y
espacios). Las letras zafan porque cada "letra + espacio" es un token unico.

Es corrupcion en el forward pass a nivel de token individual, no en el
tokenizer ni en el sampler. `--ubatch-size` cambia CUALES prompts fallan, lo que
apunta al batching del prefill, pero ningun valor los arregla a todos.

### Correccion de una conclusion anterior

En una primera pasada se atribuyo la corrupcion a `-ot` de los Ngram y a
`--cpu-moe`. **Eso estaba mal.** Esas mediciones eran de UNA sola peticion por
config, y justo esa peticion cae en la loteria del prefill. Repitiendo con
warmup y varias peticiones, ambas configs alternan entre salida buena y mala:

| | req 1 | req 2 | req 3 |
|---|---|---|---|
| sin `-ot` | correcto | corrupto | corrupto |
| con `-ot` | corrupto | correcto | correcto |

No hay causalidad a nivel de flag. Por eso NO se agrego ningun health check que
culpe a `-ot` o a `--cpu-moe`: seria codificar una conclusion que los datos no
sostienen.

## El offload de Ngram no sirve (por otro motivo)

Independientemente de la corrupcion, el `-ot` de los Ngram **no ahorra memoria**
en CUDA. Medido en el sweep completo:

| config | VRAM |
|---|---|
| `--n-cpu-moe 40` sin `-ot` | 24168 MiB |
| `--n-cpu-moe 40` con `-ot` de Ngram | 24136 MiB |

32 MiB de diferencia sobre 26.85 GB de tensores, y ~0.06 t/s mas lento. El
reporte original que motivo la idea era de **Metal**; en CUDA el override no
hace lo que promete. La variable util para dimensionar es `--n-cpu-moe`.

## Implicancia para el calculo de tier

`EffectiveProfileBuilder` asume `tamano de archivo ~= memoria necesaria`. Para
esta arquitectura eso sigue siendo falso, pero **no** por la razon que se
esperaba: como el offload de Ngram no funciona en CUDA, los 26.85 GB de lookup
tables SI tienen que estar en memoria. Lo que si cambia el calculo es el MoE:
con `--n-cpu-moe 36` el modelo de 103.68 GB corre con 30.1 GB de VRAM.

O sea que la variable de dimensionamiento util es `--n-cpu-moe`, no el offload de
Ngram. `GGUFScanner::ngramElements` sigue siendo el dato correcto para saber
cuanto del peso es lookup, pero hoy no se traduce en memoria ahorrada.

## Licencia

No es Apache/MIT. Permisiva para uso local, interno, fine-tuning y derivados,
pero MaaS comercial o un asistente de codigo/oficina standalone requieren una
licencia aparte de Qwen. Relevante si LlamaCode alguna vez lo bundlea o lo
ofrece como servicio; para uso local no cambia nada.

## Medido en la maquina de desarrollo (2x RTX 3090 + 127 GB RAM)

Composicion real del UD-Q4_K_XL, leida de los 4 shards:

| | |
|---|---|
| Total | 103.68 GB |
| Ngram/PLE | 26.85 GB (**25.9%**) |
| Backbone residente | 76.82 GB |

La regla del 75% se confirma con el modelo en la mano. Layout: el **shard 1 no
tiene tensores** (solo metadata) y **todos** los Ngram estan en el shard 2, que
ademas mezcla backbone (46.4 GB totales, 26.9 de Ngram). Por eso
`readComposition` de un solo shard no sirve para este modelo y hay
`readCompositionAllShards`.

### Cosas que rompen, encontradas al correrlo

1. **KV cache cuantizado: ARREGLADO upstream (2026-08-27).** Hasta el commit
   `035e22731` abortaba en `qwen4exp.cpp:544` (`GGML_ASSERT(inp->self_k_rot ==
   nullptr)`). El commit `0ac4b1802` ("support a quantized KV cache in the QSA
   attention path") lo resolvio: verificado contra `ef6876693`, q8_0 y q4_0
   levantan y responden bien.
   LlamaCode llego a tener un workaround que descartaba el KV quant para esta
   arquitectura; **se revirtio**, porque una vez arreglado el engine ese dropeo
   pasaba a recortar contexto en silencio. Moraleja para forks en desarrollo
   activo: un workaround contra un bug transitorio caduca, y hay que re-testear
   antes de dejarlo.

2. **`-ot` desactiva `--fit`.** El loader avisa `tensor_buft_overrides already
   set by user, abort` y entonces mete todas las capas a GPU -> OOM. `--tensor-split`
   lo desactiva igual. Con `-ot` hay que dimensionar a mano.
3. **`--n-gpu-layers 999` solo no alcanza.** El backbone son 77 GB contra 48 GB
   de VRAM. Hace falta `--n-cpu-moe N`.
4. **`--mmap` / `--no-mmap` / `--mlock` estan DEPRECADOS** en este build, en favor
   de `-lm/--load-mode {auto|none|mmap|mlock|mmap+mlock}` (auto = mmap). Ademas el
   loader sugiere `--load-mode none` cuando hay `-ot ...=CPU`, o sea que hay un
   trade-off real entre RAM y page faults, no una opcion obviamente mejor.

### VRAM por configuracion (deterministico)

| `--n-cpu-moe` | VRAM total | resultado |
|---|---|---|
| 26 | — | **OOM**: pide 36 GB en una sola placa |
| 32 | — | carga |
| 36 | — | carga |
| 40 | 22.8 GB | carga |
| 48 (`--cpu-moe`) | 10.2 GB | carga |

Con 48 capas de expertos en CPU sobran ~38 GB de VRAM: hay lugar de sobra para
subir expertos, el limite lo pone el reparto desigual entre las dos placas.

**Los t/s medidos hasta ahora NO son confiables**: se tomaron con otra sesion
compilando en paralelo (7 procesos de MSVC), y dieron entre 2.4 y 8.2 t/s para la
misma clase de configuracion. Para numeros publicables hay que correr
`benchmark_qwen38_flash_next.ps1` con la maquina quieta.

## Benchmark medido (maquina libre, 2x RTX 3090 + 127 GB)

`tools/benchmark_qwen38_flash_next.ps1 -Passes 1 -Mode thinking -IncludeNgramOffload`

| `--n-cpu-moe` | ngram `-ot` | t/s | VRAM | working set | accuracy |
|---|---|---|---|---|---|
| 36 | no | **9.96** | 30168 MiB | 25.4 GB | 0% |
| 40 | no | 9.41 | 24168 MiB | 19.6 GB | 0% |
| 40 | si | 9.35 | 24136 MiB | 19.6 GB | 0% |
| 32 / 34 | — | OOM (pide ~28 GB en una placa de 24) | | | |

**La accuracy de 0% NO mide calidad del modelo**: casi todas las tareas agotan el
presupuesto de 4096 tokens sin emitir su linea `FINAL`, porque el razonamiento se
va corrompiendo (ver la seccion de arriba). Mientras el prefill este roto, la
accuracy de este harness no dice nada sobre el modelo.

Lo que si es solido de esta tabla: **throughput (~9.4-10 t/s) y VRAM**, que no
dependen de que el texto sea correcto.

## Re-test contra `ef6876693` (2026-08-27)

El PR aun no estaba mergeado en ese momento, pero sumo 27 commits en un dia.
Recompilado y
re-medido con el mismo probe:

| ubatch | build `035e22731` | build `ef6876693` |
|---|---|---|
| 1 | 40% | 40% |
| 32 | 40% | 53% |
| 128 | 47% | 60% |
| default | 47% | 60% |

Mejoro, y `count` paso de 1/3 a 3/3. Siguen fallando 0/3 `numbers`
("55 56 ... 63" -> " 6 6 6 6") y `days` en todas las configuraciones.

### Descartado como causa (verificado, no supuesto)

Se comparo `qwen4exp.cpp` contra la implementacion de referencia
(`transformers/models/qwen4_exp/modeling_qwen4_exp.py`):

- el mixing del hash n-gram (XOR de `token * multiplicador` por posicion) es
  identico;
- el corte de ventana por EOS es identico, incluida la sutileza de que el EOS
  del propio token no corta su contexto;
- las constantes horneadas en el GGUF (`layer_multipliers`, `head_vocab_sizes`,
  `head_offsets`) se reprodujeron en Python desde el config de referencia
  (splitmix64 + primos + offsets acumulados) y **coinciden exactamente**.

O sea que ni el convert ni la matematica del hash son el problema. Lo que queda
es la obtencion de predecesores desde las celdas KV o el grafo de computo -- que
es justo donde estan iterando los autores (`llama: give the qwen4exp full memory
context its indexer cache`, `keep the indexer cache in step across server
slots`, `fix the PLE history seq_rm(-1) iterator invalidation`).

Siguiente paso si hace falta localizarlo: instrumentar `llm_graph_input_ple::
set_input` para volcar los indices calculados y diffearlos contra el calculo en
Python sobre los mismos token ids.

## Intento de campaña en la máquina real (2026-08-28)

Se verifico la máquina inicialmente libre y se inicio el smoke con el binario
local `llama-server` de `ef6876693` (compilado el 2026-08-27), el GGUF
`UD-Q4_K_XL` de cuatro shards y `--n-cpu-moe 36`, Flash Attention, mmap, KV
`f16/f16`, contexto 4096 y batch/ubatch 2048. El binario carga la arquitectura
`qwen4exp`, reconoce `--override-tensor`, `--n-cpu-moe`, `--n-cpu-ffn`,
`--split-mode` y los tipos KV cuantizados, pero **no reconoce
`--tensor-read-lazy`**. La prueba de lazy queda pendiente de una build nueva de
mainline.

La inspeccion de los cuatro GGUF encontro 3 tensores de la familia Ngram/PLE
por el regex del harness; el shard 2 contiene 12 tensores PLE/Ngram entre 891
tensores totales, asi que el layout es intercalado con el backbone. Esto
confirma que `-ot ...=CPU` no puede convertir este GGUF en un offload limpio a
SSD ni promete ahorrar toda la tabla de 26.85 GB.

El modelo llego a cargar y consumo aproximadamente 26.9 GB de VRAM combinada,
pero el smoke HTTP no produjo una respuesta valida (el cliente informo un error
de envio mientras el log del servidor mostraba el prefill en progreso). No se
registran t/s ni accuracy de este intento. Antes de continuar con 32k/64k, el
servidor de la aplicacion LlamaCode paso a estar activo; se detuvieron nuevas
cargas para no interferir con la sesion del usuario. La campaña comparativa
(`n-cpu-moe`, colocacion PLE, lazy y KV) se completo luego en una ventana libre;
los resultados quedan en la seccion siguiente.

## Campaña reproducible completada (2026-08-28)

Cuando la máquina quedo libre se ejecuto
`tools/run_qwen38_flash_next_campaign.ps1`, con el GGUF `UD-Q4_K_XL`,
`--split-mode layer --fit off --n-gpu-layers 999`, mmap, 8 threads, batch y
ubatch 2048. Cada caso hizo health y un smoke de 32 tokens por
`/completion`; por lo tanto, los casos 32k y 64k validan carga, reserva de
contexto y una inferencia corta, **no** recuperación de un prompt de 32k/64k.
Los JSON y logs crudos quedaron en
`build_tests_aux/qwen38-campaign-20260828/`.

| caso | resultado | carga s | request s | prefill tok/s | decode tok/s | VRAM MiB |
|---|---:|---:|---:|---:|---:|---:|
| 16k, `n-cpu-moe=40`, KV q8/q8 | OK | 24.59 | 12.52 | 2.46 | 3.88 | 22690 |
| 16k, `n-cpu-moe=40`, PLE `-ot` a CPU | OK | 27.58 | 7.99 | 5.92 | 4.41 | 22902 |
| 32k, `n-cpu-moe=40`, KV f16/f16 | OK | 27.86 | 9.69 | 5.02 | 4.14 | 23894 |
| 64k, `n-cpu-moe=40`, KV f16/f16 | OK | 57.98 | 32.78 | 0.78 | 1.66 | 25813 |

El smoke produjo salida y métricas en los cuatro casos OK. El salto de 32k a
64k multiplico por 2.1 el tiempo de carga y redujo el decode a 40% del valor de
32k. El PLE `-ot` no mostro ahorro frente a las mediciones historicas sin
override (aprox. 24.1 GB); ademas, el shard 2 mezcla PLE con backbone, por lo
que no es un offload a SSD limpio.

Fallos registrados, sin ocultarlos en el promedio:

- `n-cpu-moe=36` y el patrón de bandas de expertos terminaron con exit 1 antes
  de `/health`.
- `n-cpu-moe=48` llego a cargar pero el request HTTP fallo; no se contabiliza
  como throughput.
- KV `q4_0/q4_0` termino con exit 1 antes de `/health`; KV `q8_0/q8_0` sí
  cargo, pero fue más lento que f16 en las condiciones comparables disponibles.
- El baseline 16k f16 tuvo un fallo transitorio de arranque en el arnés; el
  mismo binario había respondido en una ejecución manual previa. Por eso no se
  usa ese caso como dato determinista adicional.

La build instalada reporta `0.3.0-dev`, commit `ef6876693`. No contiene
`--tensor-read-lazy`: tanto `--help` como la invocación directa devuelven
`error: invalid argument: --tensor-read-lazy`. Esa medición queda pendiente de
una build de mainline que incluya el flag. El binario sí reconoce
`--override-tensor`, `--n-cpu-moe`, `--n-cpu-ffn`, `--split-mode`, `--fit`,
`--load-mode` y KV cuantizado.
