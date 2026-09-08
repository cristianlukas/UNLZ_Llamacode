# Evaluación de NInfer-3090 en Ubuntu — 2026-09-08

## Resultado

Se evaluó [NInfer-3090](https://github.com/Don-Chad/ninfer-3090) con dos RTX 3090
(SM86) y el artefacto Qwen3.8-27B de su [model card oficial](https://huggingface.co/neroued/Qwen3.8-27B-NInfer).
El backend compila y carga el artefacto histórico, pero no produjo texto válido
ni con MTP3 ni sin MTP. Por ese motivo no se registró como perfil listo ni se
promovió a ASTRA/SOL/TERRA/LUNA/METEOR.

TERRA fue restaurado y quedó activo en LlamaCode al terminar la evaluación.
Windows no fue modificado.

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

Ese artefacto cargó en la GPU0 en 8,61 s, con 16,67 GiB de pesos, contexto de
8.192 tokens y 4,75 GiB libres después del arranque.

## Pruebas de generación

| Configuración | Resultado de runtime | Resultado de calidad |
|---|---:|---|
| MTP3 + thinking | 31,8 tok/s; aceptación MTP 17,0% | Falló: razonamiento repetitivo y texto corrupto/multilingüe sin relación con la consigna |
| Sin MTP + sin thinking | 32,2 tok/s de decode; 171,8 tok/s de prefill | Falló: salida igualmente repetitiva/corrupta |

La diferencia de velocidad no compensa el fallo semántico. Por lo tanto no se
ejecutó BCB: sus resultados serían inválidos si el servidor no supera primero
el smoke test de generación coherente y el transporte de tool calls.

## Comparación práctica

NInfer-3090 está diseñado para **una sola RTX 3090** y el README declara que no
usa ejecución multi-GPU ni offload CPU/GPU. Eso lo hace conceptualmente distinto
del perfil TERRA/SOL actual de LlamaCode, que usa las dos GPUs y la configuración
CUDA compartida. El proyecto upstream publica buenos números de referencia para
una 3090, pero también indica que su calificación real de generación Linux aún
está abierta; esos números no sustituyen una validación local.

En esta máquina, el resultado accionable es:

- **TERRA/SOL:** siguen siendo las opciones estables y validadas para coding.
- **NInfer Qwen3.8:** queda como candidato experimental, no disponible como
  perfil prioritario.
- **NInfer MTP3:** no se habilita porque la salida no es confiable.
- **NInfer DFlash2:** requiere una revisión del runtime que consuma el nuevo
  objeto del artefacto; no se incorporó una combinación parcialmente compatible.

LlamaCode ya conserva los tres perfiles `sys-ninfer3090-*` como scaffolding
experimental. No se cambió su visibilidad ni se presentó como listo: la prueba
local confirma que todavía debe permanecer fuera de la cola de perfiles
prioritarios.

## Archivos de prueba fuera del repositorio

Los artefactos y el build de evaluación quedan en la caché nativa de Ubuntu:

- `/home/cristian/.cache/llamacode/ninfer-3090-src`
- `/home/cristian/.cache/llamacode/ninfer-3090-build-128`
- `/home/cristian/.cache/llamacode/ninfer-model/`

No se eliminaron los artefactos descargados para permitir una repetición cuando
el runtime upstream agregue soporte para DFlash2 o se publique una revisión
SM86 corregida.
