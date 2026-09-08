# Evaluación de club-3090 en Ubuntu

Fecha: 2026-09-08  
Equipo: Ubuntu 24.04, 2× RTX 3090, CUDA 12.8, 123 GiB de RAM visible

Fuente evaluada: [noonghunna/club-3090](https://github.com/noonghunna/club-3090).

## Qué aporta la receta

El proyecto propone dos caminos diferentes:

- `ik_llama` + Qwen3.6-27B IQ4_KS + MTP2 para baja latencia en una RTX 3090.
- vLLM + Qwen3.6-27B AutoRound INT4 + MTP3 + TP=2 para throughput con dos RTX 3090.

La configuración vLLM necesita un artefacto AutoRound y un cabezal MTP que no están instalados en esta máquina. Además, la propia receta fija una versión concreta de vLLM y advierte sobre un fallo de MTP; por eso no se incorporó como perfil local de LlamaCode. LlamaCode ya conserva perfiles externos vLLM experimentales sin presentarlos como servidores locales validados.

## Prueba local

Se compiló el commit `35845dd9` de `ik_llama` para `sm_86` con GCC 13, Ninja y el toolkit completo CUDA 12.8. La compilación terminó correctamente y detectó la RTX 3090.

Se probó el artefacto ya presente:

`Qwen3.6-27B-MTP-IQ4_XS.gguf`

Resultados:

| Variante | Carga del modelo | Generación HTTP | Resultado |
|---|---:|---:|---|
| `ik_llama`, configuración club, 32K, Q4 KV, Hadamard, sin MTP | Sí, ~15 GiB | No inicia | Acceso ilegal CUDA durante `llama_init_from_model` |
| `ik_llama`, mínima, 8K, KV F16, sin MTP | Sí, ~14,6 GiB | No inicia | El mismo acceso ilegal CUDA durante la limpieza del buffer |

El fallo ocurre antes de recibir peticiones, así que no existe un TPS local confiable para promover. También se había observado el mismo tipo de fallo con el runtime CUDA de LlamaCode para este artefacto; no es evidencia de que P2P esté desactivado.

## Decisión para LlamaCode

No se agregó ni se promovió un perfil `club-3090`/`ik_llama`: registrar un backend que carga el modelo pero se cae antes de generar sería peor que dejar el perfil experimental existente claramente separado. No se modificaron Windows, ASTRA, SOL, TERRA, LUNA ni METEOR.

La parte reutilizable queda documentada para una próxima iteración:

1. Obtener el artefacto exacto `IQ4_KS` de la receta, en lugar del `IQ4_XS` disponible.
2. Repetir la prueba con una build/revisión de `ik_llama` que declare compatibilidad con el formato Qwen3.6 actual.
3. Sólo después medir BCB y TPS y, si pasa carga, generación y BCB, registrar un perfil Linux opcional.

TERRA fue restaurado y quedó ejecutándose con el runtime estable de LlamaCode.
