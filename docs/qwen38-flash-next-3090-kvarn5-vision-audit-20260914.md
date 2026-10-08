# Qwen3.8 Flash-Next en RTX 3090 — auditoría de KVarN5 y visión

Fecha: 2026-09-14  
Equipo: Ubuntu, 2× RTX 3090, P2P disponible y ~123 GiB de RAM

## Qué propone el post

El autor ejecuta `Qwen3.8-Flash-Next UD-IQ4_XS` con KVarN5, expertos en RAM,
Engram/ngram en disco, visión en GPU y MTP. Reporta aproximadamente 160 tok/s
de prefill y 16 tok/s de decode. También observa que MTP puede empeorar el
decode porque los tokens rechazados aumentan el tráfico hacia la memoria del
host.

La receta es relevante para nuestra arquitectura, pero sus cifras no son
directamente comparables: usa otra build, otro quant, una configuración de
memoria distinta y no aporta BCB o una prueba de tool-use equivalente.

## Validación local

La parte de texto ya está cubierta por las pruebas BeeLlama anteriores:

- KVarN5/KVarN5 carga a 8K, 32K, 64K y 131K.
- Decode local: aproximadamente 36 tok/s en prompts cortos y 27,33 tok/s en
  una solicitud real de ~77,8K tokens.
- JSON, Python, `read_file` y needle largo fueron válidos.
- La cola está desactivada (`--kv-tail-tokens 0`), por lo que no se usa KV
  superior a Q8.
- Las variantes MTP/NGRAM de Flash-Next anteriores no quedaron estables; el
  post confirma que MTP no siempre ayuda cuando los expertos están en RAM.

Se intentó además la combinación del post con `n-cpu-moe 39`, `mmap`, lazy
loading, KVarN5/KVarN5 y el mmproj disponible localmente. El modelo llegó a la
etapa de carga, pero el mmproj fue rechazado:

```text
mismatch between text model (n_embd = 2560) and mmproj (n_embd = 5120)
```

El mmproj local pertenece a otra variante Qwen3.8/27B; no es el visual
compatible con Flash-Next. Sin ese archivo no es posible afirmar que visión en
GPU funcione para este modelo.

## Comparación

| Variante | Resultado | Decisión |
|---|---|---|
| Post: IQ4_XS + KVarN5 + visión GPU | ~160 prefill / 16 decode publicados | Referencia externa, no reproducible todavía |
| BeeLlama KVarN5 local, texto | ~36 decode a 131K; tool-use válido | Mantener experimental texto-only |
| Flash-Next + mmproj Qwen3.8 local | Error de dimensiones 2560/5120 | No usar |
| ASTRA lazy on | TPS bruto alto, salida `////` | Rechazado |
| SOL | 74 narrativo / 102 código; BCB 8/8 | Default |

## Decisión

No se modifica el default, no se agrega visión a BeeLlama y no se descarga un
quant nuevo. Para continuar esta línea haría falta obtener el mmproj específico
de Flash-Next, comprobar que cabe en `/media/cristian/7CFE1E0FFE1DC1F6/models`,
y repetir smoke visual, tool-use, contexto largo y BCB. Hasta entonces,
BeeLlama KVarN5 queda correctamente clasificado como texto-only.
