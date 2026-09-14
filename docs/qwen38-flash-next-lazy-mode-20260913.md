# Qwen3.8-Flash-Next: `lazy-mode` y `on-direct` en Ubuntu — 2026-09-13

## Objetivo

Se revisó la recomendación de usar `--lazy-mode on` para dejar la tabla PLE/ngram
en disco y reducir el coste de memoria de Qwen3.8-Flash-Next. La prueba se hizo
contra el artefacto local `UD-Q4_K_XL`, usando KV `q8_0` tanto para K como para V,
sin superar el límite Q8 del proyecto.

La comparación se aisló del resto de LlamaCode: cada caso arrancó un
`llama-server` nuevo, esperó `/health` y ejecutó la misma petición corta de
Python a 32K de contexto.

## Resultados locales

| Variante | Runtime | Prefill | Decode | Smoke | Lectura |
|---|---|---:|---:|---|---|
| Control Q8, `lazy off` | CUDA Flash-Next actual, caché MoE 188 | **27,13 tok/s** | **14,87 tok/s** | Código Python válido | Referencia reproducible |
| Candidata Q8, `lazy on` | CUDA Flash-Next actual, caché MoE 188 | **26,42 tok/s** | 37,56 tok/s reportados | **Salida corrupta: `////`** | Rechazada; el TPS bruto no es utilizable |
| `lazy on-direct` | llama.cpp PR #28136, `--n-cpu-moe 48`, PLE en CPU, sin caché `CUDA_Host` | 8,19 tok/s | **7,54 tok/s** | Código Python válido | Correcta pero 49% más lenta que el control |

El resultado de `lazy on` no se promociona: aunque el campo de decode fue mayor,
la salida del mismo smoke dejó de ser código válido. La prueba no demuestra una
mejora de calidad ni de agente.

## Compatibilidad del `on-direct`

La rama oficial compilada desde el PR de lecturas directas reconoce
`--lazy-mode on-direct`, pero rechaza el buffer experimental
`CUDA_Host` utilizado por nuestra build Flash-Next con caché MoE 188. La prueba
alternativa con `--n-cpu-moe 48` es funcional, pero ya no es la misma arquitectura
de ejecución que produjo los 36,04 tok/s históricos de ASTRA; mueve los expertos
a CPU y por eso no es candidata a reemplazar el runtime actual.

El PR upstream describe `on-direct` como lecturas `pread()` de las filas PLE,
evitando los page faults de `mmap`. Su beneficio publicado es principalmente de
prefill frío en otros equipos; no implica automáticamente una mejora de decode ni
integra la caché `CUDA_Host` de nuestra rama experimental.

## Comparación con ASTRA existente

Los resultados históricos de ASTRA siguen siendo:

- 36,83 tok/s de decode en la prueba Server Speed a 196K con caché MoE 188.
- aproximadamente 16–22 tok/s en la matriz de contexto con el runtime Linux
  anterior y KV F16.
- HE0/BCB no válidos: ASTRA produjo salida no utilizable en el harness, por lo
  que no es un agente principal aunque cargue y tenga contexto largo.

La nueva prueba Q8 no corrige esa limitación de calidad. Tampoco permite afirmar
que `lazy on-direct` sea mejor: la única ejecución comparable que conservó una
salida válida fue claramente más lenta.

## Decisión para LlamaCode

No se modifica el perfil por defecto ni el dropdown:

1. No se agrega `--lazy-mode on`; en esta build su salida fue corrupta.
2. No se agrega `--lazy-mode on-direct`; el runtime oficial no conserva la caché
   MoE 188 y la variante CPU quedó por debajo del rendimiento actual.
3. Se mantienen la caché MoE 188, `--load-mode mmap`, `--split-mode layer` y KV
   Q8 como la ruta experimental reproducible de ASTRA.
4. La rama compilada queda sólo como artefacto de investigación para repetir la
   prueba si upstream integra `on-direct` con la caché de expertos usada por
   LlamaCode.

Para promoverlo en el futuro deberían cumplirse simultáneamente: compatibilidad
con `CUDA_Host`/caché 188, smoke correcto, HE0 válido, BCB reproducible y una
mejora de prefill o decode frente al runtime actual en 32K, 131K y 196K.

## Artefactos

- [Control Q8 lazy off](../artifacts/qwen-next-linux-lazy-off-tps-20260913-result.json)
- [Q8 lazy on](../artifacts/qwen-next-linux-lazy-on-tps-20260913-result.json)
- [Q8 lazy on-direct](../artifacts/qwen-next-linux-lazy-direct-tps-20260913-result.json)
- [Configuración A/B](../artifacts/qwen-next-linux-lazy-ab-20260913.json)

Referencias upstream: [opciones oficiales de carga y lazy-mode en llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/tools/cli/README.md)
y [PR de lecturas directas para la tabla PLE](https://github.com/ggml-org/llama.cpp/pull/28136).

## Revisión del tutorial de offload PLE por `mmap` — 2026-09-14

El tutorial recomienda no usar `--no-mmap` ni `--mlock` y añadir:

```text
--load-mode mmap
--override-tensor per_layer_token_embd.weight=CPU
```

La ruta Linux de ASTRA ya utiliza `--load-mode mmap` y mueve
`per_layer_token_embd.weight` a CPU, además de mantener la colocación de
expertos `CUDA_Host` y la caché MoE 188. Por lo tanto, esta recomendación ya
está incorporada; no requiere modificar el perfil.

El tutorial se ejecutó en Apple Silicon con un quant reempaquetado y tabla PLE
separada. No se puede trasladar su ahorro de memoria de forma automática a
nuestro GGUF ni a CUDA. En nuestras pruebas equivalentes:

| Configuración | Resultado |
|---|---|
| ASTRA con `mmap`, override CPU y caché 188 | Carga y conserva el contexto largo, pero la calidad agéntica no quedó validada |
| `lazy on` | TPS bruto alto, salida corrupta `////` |
| `lazy on-direct` | Salida válida, ~7,54 tok/s; más lento que el control |
| SOL | BCB 8/8, tool-use OK, 74 narrativo / 102 código |

Conclusión: el tutorial confirma la configuración de memoria que ya usamos,
pero no ofrece una mejora adicional para LlamaCode. No se modifica ASTRA, no se
activa `lazy-mode` y SOL sigue siendo el default.
