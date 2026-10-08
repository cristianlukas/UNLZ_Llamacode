# Evaluación de NInfer-3090 en Ubuntu — 2026-09-08

## Resultado actualizado

Se evaluó [NInfer-3090](https://github.com/Don-Chad/ninfer-3090) con dos RTX 3090
(SM86) y el artefacto Qwen3.8-27B de su [model card oficial](https://huggingface.co/neroued/Qwen3.8-27B-NInfer).
La primera ejecución parecía inválida porque el artefacto histórico producía
texto corrupto en la GPU0. La repetición controlada mostró que la ruta estable
es la GPU1: con el artefacto histórico, MTP3, KV INT8 y `--device 1` genera texto
correcto, acepta tool calls y conserva el contexto largo.

El perfil deja de estar marcado como “salida corrupta/rechazado”, pero continúa
siendo experimental: el BCB completo dio **3/8 con thinking de 2048 tokens**
(1/8 sin thinking). No reemplaza SOL por calidad, aunque sí es un backend
funcional para una RTX 3090 y una alternativa de contexto largo.

La reparación queda limitada a Linux mediante `platformModelFiles` y
`platformArgs`; Windows sigue apuntando al artefacto actual y conserva sus
argumentos originales.

## Entorno y build

- Ubuntu 24.04, dos RTX 3090, compute capability 8.6.
- CUDA Toolkit 12.8 instalado para cumplir el requisito del proyecto; el driver
  NVIDIA existente no se reemplazó.
- Fuente NInfer-3090: commit `75d94eab` (`ninfer-3090`).
- GCC 13, CMake/Ninja, CUDA SM86.
- Compilación: **288/288 pasos completados**.
- Binarios generados: `ninfer`, `ninfer-serve` y `ninfer-perplexity`.

## Artefactos probados

El artefacto actual del repositorio contiene pesos DFlash2 nuevos. El binario
compilado rechazó el arranque porque encontró el objeto no consumido
`dflash2/feature_projection`. No se modificó el artefacto para ocultar el
problema.

También se descargó el artefacto histórico compatible, correspondiente al
commit `3526913004b1cf552cb57b88d6a5c6f5e4a89a70`, y se verificó su SHA-256:

```text
eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e
```

Ese artefacto cargó en la GPU1, con 16,67 GiB de pesos. El artefacto actual
`qwen3_8_27b.ninfer` no es intercambiable: el binario SM86 lo rechaza por el
objeto DFlash2 `dflash2/feature_projection`, que todavía no consume.

## Pruebas de generación

| Configuración | Resultado de runtime | Resultado de calidad |
|---|---:|---|
| GPU0, MTP3 o sin MTP | 31,8–32,2 tok/s | Reproducía salida corrupta; no es la ruta reparada |
| GPU1, MTP3, sin thinking, KV INT8, 8K | 73–75 tok/s; aceptación 76,7% | Texto coherente y smoke-test correcto |
| GPU1, MTP3, thinking 2048, BCB | decode estable; coste depende del razonamiento | **3/8 BCB**; mejor que 1/8 sin thinking |
| GPU1, MTP3, KV INT8, 80K | prefill 745,3 tok/s; decode 50,1 tok/s | `NINFER_LONG_OK` correcto |
| GPU1, MTP3, KV INT8, 120K | prefill 660,7 tok/s; decode 62,9 tok/s | `NINFER_131K_LONG_OK` correcto; MTP 4,00/round |

El modo corregido supera el smoke test y el transporte de tool calls; el score
BCB sigue siendo una limitación de calidad del modelo, no una falla del servidor.

## Comparación práctica

NInfer-3090 está diseñado para **una sola RTX 3090** y el README declara que no
usa ejecución multi-GPU ni offload CPU/GPU. Eso lo hace conceptualmente distinto
del perfil TERRA/SOL actual de LlamaCode, que usa las dos GPUs y la configuración
CUDA compartida. El proyecto upstream publica buenos números de referencia para
una 3090, pero también indica que su calificación real de generación Linux aún
está abierta; esos números no sustituyen una validación local.

En esta máquina, el resultado accionable es:

- **TERRA/SOL:** siguen siendo las opciones estables y validadas para coding.
- **NInfer Qwen3.8:** queda como candidato experimental funcional, visible fuera
  de la cola prioritaria y fijado a la GPU1 en Linux.
- **NInfer MTP3:** se habilita en la variante reparada; la aceptación local es
  útil, pero no compensa el BCB 3/8 para convertirlo en agente principal.
- **NInfer DFlash2:** requiere una revisión del runtime que consuma el nuevo
  objeto del artefacto; no se incorporó una combinación parcialmente compatible.

LlamaCode conserva los tres perfiles `sys-ninfer3090-*` como scaffolding
experimental. `sys-ninfer3090-qwen38` ahora selecciona en Linux el artefacto
histórico y una configuración de 131K/UBATCH1024/GPU1, sin alterar Windows.

## Archivos de prueba fuera del repositorio

Los artefactos y el build de evaluación quedan en la caché nativa de Ubuntu:

- `/home/cristian/.cache/llamacode/ninfer-3090-src`
- `/home/cristian/.cache/llamacode/ninfer-3090-build-128`
- `/home/cristian/.cache/llamacode/ninfer-model/`

No se eliminaron los artefactos descargados para permitir una repetición cuando
el runtime upstream agregue soporte para DFlash2 o se publique una revisión
SM86 corregida.
