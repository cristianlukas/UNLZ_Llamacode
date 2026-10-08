# llamAmpere + Qwen3.8 ATX-IQ4_XS-M — auditoría local

Fecha de auditoría: 2026-09-14 · revisión de upstream: 2026-09-15  
Decisión: **no promover como default ni reemplazar SOL**. El backend dual queda
documentado como candidato experimental, sin entrada activa en el menú.

## Qué se evaluó

El post propone el fork [JakeATX/llamAmpere](https://github.com/JakeATX/llamAmpere)
con kernels específicos para SM86, TurboQuant para KV y MTP con un mapa de
vocabulario de 65.536 tokens. El candidato descargado fue
[Qwen3.8-27B-ATX-IQ4_XS-M-GGUF](https://huggingface.co/jakeatx/Qwen3.8-27B-ATX-IQ4_XS-M-GGUF):
un GGUF de 15.588.551.712 bytes, con pesos por debajo de Q8 y sin `mmproj`/artefacto
de visión.

El fork publica cifras externas de hasta ~99 tok/s en una RTX 3090, pero son cifras
del propio proyecto, con otra máquina, otra versión de CUDA y su receta completa de
TurboQuant/MTP. No se trataron como resultados de LlamaCode.

## Revisión del upstream posterior

El checkout local de la prueba estaba en `67849b64b567`. Se comparó con el `main`
actual de `JakeATX/llamAmpere` (`207867db7ea27126ca00ca97edaefe1e4b34039c`).
El único cambio posterior fue reseedear el RNG del drafter p/q una vez por request,
en vez de reiniciarlo en cada ronda especulativa (`common/speculative.cpp`). Es una
corrección de reproducibilidad/distribución de muestreo; no corrige los accesos
ilegales observados en single-GPU, no agrega visión y no cambia la cuantización ni
el backend SM86. Por eso no justifica repetir la campaña completa ni cambiar la
decisión de promoción.

## Pruebas reproducidas

Hardware y software: 2× RTX 3090 de 24 GiB, driver 595.71.05, CUDA 12.0.140,
commit `67849b64b567` de `llamAmpere`, compilación local Release para
`CMAKE_CUDA_ARCHITECTURES=86`.

| Configuración | Resultado | Diagnóstico |
|---|---|---|
| Una RTX 3090, sin MTP, KV K/V `q8_0/q8_0`, 8K | Aborta durante la carga con `CUDA error: an illegal memory access` | No pasa el smoke test en una sola placa |
| Una RTX 3090, sin MTP, receta K `q8_0` + V `turbo3`, `FLASH_ATTN`, 8K | Inicia en la build MMQ, pero aborta en el primer prompt en `launch_mul_mat_q` | No es utilizable en una sola placa |
| Build alternativa `GGML_CUDA_FORCE_CUBLAS=ON`, una GPU, K/V `q8_0/q8_0` | Aborta durante la carga con acceso ilegal | No es sólo un problema de MMQ |
| Build alternativa cuBLAS, una GPU, K `q8_0` + V `turbo3` | Aborta en la inicialización del grafo, en `op_mul` | cuBLAS tampoco rescata el modo single-GPU |
| Dos RTX 3090, reparto `layer`, MTP3, K `q8_0` + V `turbo3`, 8K | **Funciona: 116,23 tok/s; MTP 84/90 (93,3%)** | Primera configuración local estable |
| Dos RTX 3090, misma receta a 55.032 tokens | **Prefill 928,15 tok/s; decode 58,00 tok/s; MTP 6/9** | Contexto profundo estable |
| Dos RTX 3090, misma receta a 99.032 tokens | **Prefill 772,47 tok/s; decode 63,84 tok/s; MTP 6/9** | Contexto largo estable y respondió el marcador esperado |
| Dos RTX 3090, KV estricto K/V `q8_0/q8_0`, MTP3, 8K | Smoke funcional; devolvió `6` y aceptó 3/3 tokens de draft | Compatible con el límite Q8, pero no se usó para la cifra principal |
| Tool-use OpenAI `read_file` | **Funciona**; `finish_reason=tool_calls`, argumentos JSON válidos, MTP 21/21 | Capacidad de herramientas confirmada en un caso |
| BCB/8 local | **1/8** | Calidad agentiva insuficiente frente a SOL 8/8 |
| Visión (`mmproj`) | No hay `mmproj` en el repositorio del modelo | No se puede agregar visión a este candidato |

Los dos primeros abortos también se observaron en la build normal del fork; la
recompilación con cuBLAS repitió el fallo en una GPU. El reparto dual por capas
sí evita el fallo y habilita el candidato en nuestra máquina, pero no convierte
la cuantización en una alternativa de calidad equivalente a SOL.
Los logs completos quedan en `/tmp/llamampere-atx-no-mtp.log`,
`/tmp/llamampere-atx-turbo3-no-mtp.log`,
`/tmp/llamampere-cublas-q8-no-mtp.log` y
`/tmp/llamampere-cublas-turbo3-no-mtp.log` durante esta sesión de diagnóstico.

## Comparación contra los perfiles actuales

| Candidato | Velocidad/calidad local | Contexto/visión | Decisión |
|---|---|---|---|
| ATX-IQ4_XS-M + llamAmpere dual | 116,23 tok/s a 8K; 58,00 a 55K; 63,84 a 99K; BCB 1/8 | Contexto largo estable; sin visión; tool-use puntual OK | Experimental, no default |
| SOL | 74 tok/s narrativo / 102 tok/s código; BCB 8/8; tool-use OK | 262K validado | Mantener como principal |
| QWEN38-Q8 | 41,3 tok/s a 8K / 22,1 a 262K | 262K validado; agentivo aún experimental | Mantener como experimental |

La idea de shortlist MTP es útil y el backend dual demuestra una ventaja de
throughput sobre QWEN38-Q8, especialmente a 8K y ~100K. Sin embargo, el BCB
1/8 frente a SOL 8/8 impide presentarlo como perfil general para coding y
agentes. La cifra de 116 tok/s tampoco es comparable directamente con el
74/102 de SOL: usa otra receta, otra cuantización, otra build y una condición
de prompt/decodificación distinta.

## Resultado operativo

- No se agregó un perfil nuevo ni se modificó SOL, QWEN38-Q8 o ASTRA.
- No se incorporó `llamAmpere` como runtime de producción ni como default.
- Se conserva como candidato experimental documentado: sólo funciona de forma
  estable con las dos GPU y el reparto por capas; el BCB queda en 1/8.
- El artefacto de 15,6 GB fue retirado durante la limpieza de modelos y actualmente
  `models/club-3090/` sólo conserva directorios vacíos de candidatos. No se vuelve a
  descargar: el cambio de upstream es sólo el reseed del RNG y las mediciones locales
  ya cubren la receta relevante. El candidato no participa del menú activo.
- Para reabrirlo haría falta una versión compatible con nuestro driver/CUDA o un
  parche upstream que elimine el acceso ilegal en Ampere y un BCB/HE0 reproducible.
