# Qwen3.8-Flash-Next en LlamaCode

Modelo MoE de 125B (arquitectura Qwen4) con 262k de contexto. Lo particular no es
el tamano sino que una parte grande del modelo son tensores **Ngram / PLE**: una
lookup table de acceso aleatorio, no compute.

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

Mainline todavia no mergeo la arquitectura: hace falta el PR
[ggml-org/llama.cpp#27742](https://github.com/ggml-org/llama.cpp/pull/27742).

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

## Offload de Ngram a SSD: lo que realmente hay que saber

Tres cosas contraintuitivas, confirmadas en la practica por el reporte de
`returnity` en el PR 27742 (medido en un M5 Max de 128 GB):

1. **`--mmap` ya es el default.** No hay que pasarlo. Lo que ROMPE el offload es
   pasar `--no-mmap` o `--mlock`. Un perfil que active mlock "para ir mas rapido"
   silenciosamente convierte 29 GB de lookup table en residentes.
2. **El layout del quant puede sabotearlo.** En el GGUF de unsloth los tensores
   PLE/Ngram estan interleaved con el backbone adentro de los shards. Si un shard
   mezcla ambos, mmap lo trae entero y no se ahorra nada. Solo funciona si los
   Ngram viven en shards propios; si no, hay que repackear el GGUF.
   Verificado en Metal; en CUDA puede no aplicar, hay que medirlo.
3. **Regla de bolsillo:** el backbone es ~**75%** del tamano en disco del quant.
   El 25% restante son los Ngram, que pueden irse al SSD. Q4_K_XL: 111 GB en
   disco -> ~83 GB de backbone + ~28 GB de Ngram.

Numeros reportados: 123 GB -> 97 GB de memoria residente, con el **mismo** t/s
(36 tok/s sin MTP). O sea: el offload sale gratis en velocidad.

Por eso `benchmark_qwen38_flash_next.ps1` mide **working set y VRAM**, no solo
t/s: sin la foto de memoria el benchmark no prueba que el offload esta pasando.
Los brazos son `gpu` (baseline), `ram` (`-ot ngram=CPU --no-mmap`, residencia
forzada) y `ssd` (`-ot ngram=CPU`, mmap por default). El script tambien corre un
preflight que reporta que shards mezclan Ngram con backbone.

## Implicancia para el calculo de tier

`EffectiveProfileBuilder` asume `tamano de archivo ~= memoria necesaria`. Con
esta arquitectura eso sobreestima en ~25%: un tier que hoy rechaza Q4_K_XL por
"no entra" en realidad lo corre si manda los Ngram al SSD. El calculo deberia
usar **peso residente** (backbone), no el tamano del GGUF.

## Licencia

No es Apache/MIT. Permisiva para uso local, interno, fine-tuning y derivados,
pero MaaS comercial o un asistente de codigo/oficina standalone requieren una
licencia aparte de Qwen. Relevante si LlamaCode alguna vez lo bundlea o lo
ofrece como servicio; para uso local no cambia nada.
